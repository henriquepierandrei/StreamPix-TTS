import asyncio
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
from pathlib import Path

# Chave da API - corrigido o nome da variável
load_dotenv()  # lê o .env

API_KEY_APP = os.getenv("API_KEY_APP")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Verificar configuração
config = cloudinary.config()
print(f"Configuração final - Cloud: {config.cloud_name}, Key: {config.api_key}")
print("=== FIM CONFIGURAÇÃO ===\n")

VOZES = {
    "male": "pt-BR-AntonioNeural",
    "female": "pt-BR-FranciscaNeural",
}

app = FastAPI(title="TTS API")


class TextRequest(BaseModel):
    uuid: str  # Nome único do arquivo vindo do backend Java
    text: str  # Texto para gerar áudio
    voice_type: str  # "male" ou "female"


async def gerar_audio(text: str, voice_type: str, file_name: str):
    tts = edge_tts.Communicate(text, voice_type)
    await tts.save(file_name)


@app.post("/gerar-audio", response_class=PlainTextResponse)
async def gerar_audio_endpoint(dados: TextRequest, key: str):
    # Validação da chave (agora vem da URL como query parameter)
    if key != API_KEY_APP:  # Corrigido: usando API_KEY_APP
        raise HTTPException(status_code=401, detail="Chave inválida!")

    # Validação da voz
    if dados.voice_type not in VOZES:
        raise HTTPException(status_code=400, detail="Voz inválida. Use 'male' ou 'female'.")

    file_name = f"{dados.uuid}.mp3"

    try:
        # Gerar áudio localmente
        await gerar_audio(dados.text, VOZES[dados.voice_type], file_name)

        # Verificar se arquivo foi criado
        if not os.path.exists(file_name):
            raise HTTPException(status_code=500, detail="Arquivo de áudio não foi gerado.")

        # Fazer upload para Cloudinary - versão mais simples
        print(f"Iniciando upload do arquivo: {file_name}")
        print(f"UUID: {dados.uuid}")

        upload_result = cloudinary.uploader.upload(
            file_name,
            resource_type="video",  # Para áudio
            public_id=dados.uuid
            # Removemos todas as opções extras para testar
        )

        print(f"Upload realizado com sucesso!")
        print(f"Public ID: {upload_result.get('public_id')}")
        print(f"URL: {upload_result.get('secure_url')}")

        # Retornar apenas a URL sem as aspas (string pura)
        return upload_result.get("secure_url")

    except cloudinary.exceptions.Error as e:
        # Log detalhado do erro do Cloudinary
        print(f"=== ERRO CLOUDINARY ===")
        print(f"Tipo do erro: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        print(f"Arquivo tentando upload: {file_name}")
        print(f"Arquivo existe: {os.path.exists(file_name)}")
        if os.path.exists(file_name):
            print(f"Tamanho do arquivo: {os.path.getsize(file_name)} bytes")
        print("=== FIM ERRO ===")
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")

    except Exception as e:
        # Log de outros erros
        print(f"Erro geral: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

    finally:
        # Remover arquivo local sempre
        if os.path.exists(file_name):
            os.remove(file_name)


@app.get("/health")
async def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return {"status": "OK", "message": "TTS API está funcionando"}


@app.get("/debug-cloudinary")
async def debug_cloudinary():
    """Endpoint para debug detalhado do Cloudinary"""
    try:
        config = cloudinary.config()

        # Teste de assinatura básica
        from cloudinary.utils import cloudinary_url
        test_url = cloudinary_url("sample.jpg")

        return {
            "status": "OK",
            "config": {
                "cloud_name": config.cloud_name,
                "api_key": config.api_key,
                "api_secret_length": len(config.api_secret) if config.api_secret else 0,
                "secure": config.secure
            },
            "test_url": test_url[0] if test_url else None
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "type": type(e).__name__}


@app.get("/test-cloudinary")
async def test_cloudinary():
    """Endpoint para testar a configuração do Cloudinary"""
    try:
        # Verificar se as credenciais estão configuradas
        config = cloudinary.config()

        return {
            "status": "OK",
            "cloud_name": config.cloud_name,
            "api_key": config.api_key,
            "api_secret_configured": bool(config.api_secret),
            "api_secret_length": len(config.api_secret) if config.api_secret else 0
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


if __name__ == "__main__":
    print("Server iniciado - código atualizado")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)