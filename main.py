import asyncio
import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

# =============================
# Configuração inicial
# =============================
load_dotenv()

API_KEY_APP = os.getenv("API_KEY_APP")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

VOZES = {
    "female": "pt-BR-FranciscaNeural",
    "female_two": "pt-BR-LeilaNeural",
    "female_three": "pt-BR-LeticiaNeural",
    "female_four": "pt-BR-ThalitaNeural",
    "female_five": "pt-BR-BrendaNeural",
    "female_six": "pt-BR-ElzaNeural",
    "female_seven": "pt-BR-GiovannaNeural",
    "female_eight": "pt-BR-ElzaNeural",
    "female_nine": "pt-BR-ManuelaNeural",
    "female_ten": "pt-BR-YaraNeural",


    "male": "pt-BR-AntonioNeural",
    "male_two": "pt-BR-MacerioMultilingualNeural",
    "male_three": "pt-BR-DonatoNeural",
    "male_four": "pt-BR-FabioNeural",
    "male_five": "pt-BR-HumbertoNeural",
    "male_six": "pt-BR-JulioNeural",
    "male_seven": "pt-BR-NicolauNeural",
    "male_eight": "pt-BR-ValerioNeural",

}

app = FastAPI(title="TTS API")


# =============================
# Models
# =============================
class TextRequest(BaseModel):
    uuid: str
    text: str
    voice_type: str  # "male", "female", "young_male" etc.
    rate: str | None = None  # Ex: "+10%", "-5%"
    pitch: str | None = None  # Ex: "+5%", "-3%"
    volume: str | None = None  # Ex: "+0%", "-10%"
    style: str | None = None  # Ex: "cheerful", "angry", "chat"
    styledegree: int | None = None  # Intensidade (1-2)


# =============================
# Funções auxiliares
# =============================
async def gerar_audio(dados: TextRequest, file_name: str):
    """Gera o áudio usando edge-tts com parâmetros corretos."""
    if dados.voice_type not in VOZES:
        raise HTTPException(status_code=400, detail="Voz inválida.")

    voice = VOZES[dados.voice_type]

    # CORREÇÃO: edge-tts usa parâmetros diretos, não SSML
    # Constrói os parâmetros de rate, pitch e volume
    rate = dados.rate or "+0%"
    pitch = dados.pitch or "+0%"
    volume = dados.volume or "+0%"

    # Para edge-tts, você precisa passar o texto limpo e os parâmetros separadamente
    tts = edge_tts.Communicate(
        text=dados.text,  # Texto puro, sem SSML
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume
    )

    # Salva o arquivo
    await tts.save(file_name)


# =============================
# Endpoints
# =============================
@app.post("/generate-audio", response_class=PlainTextResponse)
async def gerar_audio_endpoint(dados: TextRequest, key: str):
    if key != API_KEY_APP:
        raise HTTPException(status_code=401, detail="Chave inválida!")

    file_name = f"{dados.uuid}.mp3"

    try:
        await gerar_audio(dados, file_name)

        if not os.path.exists(file_name):
            raise HTTPException(status_code=500, detail="Falha ao gerar áudio.")


        upload_result = cloudinary.uploader.upload(
            file_name,
            folder="stream-pix-audio",
            resource_type="video",
            public_id=dados.uuid
        )

        return upload_result.get("secure_url")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)


@app.post("/generate-audio-simple", response_class=PlainTextResponse)
async def gerar_audio_simples_endpoint(dados: TextRequest, key: str):
    """Versão simplificada sem parâmetros extras."""
    if key != API_KEY_APP:
        raise HTTPException(status_code=401, detail="Chave inválida!")

    file_name = f"{dados.uuid}.mp3"

    try:
        if dados.voice_type not in VOZES:
            raise HTTPException(status_code=400, detail="Voz inválida.")

        voice = VOZES[dados.voice_type]

        # Versão simplificada - apenas texto e voz
        tts = edge_tts.Communicate(dados.text, voice)

        # Tenta salvar com timeout menor
        try:
            await asyncio.wait_for(tts.save(file_name), timeout=30)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=500, detail="Timeout ao gerar áudio - tente texto menor")

        if not os.path.exists(file_name):
            raise HTTPException(status_code=500, detail="Falha ao gerar áudio.")

        upload_result = cloudinary.uploader.upload(
            file_name,
            folder="stream-pix-audio",
            resource_type="video",
            public_id=dados.uuid
        )

        return upload_result.get("secure_url")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)


@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "TTS API funcionando"}


# =============================
# Endpoint alternativo com SSML (se necessário)
# =============================
@app.post("/generate-audio-ssml", response_class=PlainTextResponse)
async def gerar_audio_ssml_endpoint(dados: TextRequest, key: str):
    """Versão que usa SSML corretamente."""
    if key != API_KEY_APP:
        raise HTTPException(status_code=401, detail="Chave inválida!")

    file_name = f"{dados.uuid}.mp3"

    try:
        if dados.voice_type not in VOZES:
            raise HTTPException(status_code=400, detail="Voz inválida.")

        voice = VOZES[dados.voice_type]

        # Se você realmente precisar usar SSML com edge-tts,
        # precisa criar o SSML de forma diferente
        rate = dados.rate or "+0%"
        pitch = dados.pitch or "+0%"
        volume = dados.volume or "+0%"

        # Cria SSML básico sem namespaces complexos
        ssml_text = f'''
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-BR">
            <voice name="{voice}">
                <prosody rate="{rate}" pitch="{pitch}" volume="{volume}">
                    {dados.text}
                </prosody>
            </voice>
        </speak>
        '''

        # IMPORTANTE: Para usar SSML com edge-tts, você precisa passar
        # o texto SSML como se fosse texto normal, MAS o edge-tts pode
        # não processar todo SSML corretamente
        tts = edge_tts.Communicate(
            text=ssml_text,
            voice=voice
        )

        await tts.save(file_name)

        if not os.path.exists(file_name):
            raise HTTPException(status_code=500, detail="Falha ao gerar áudio.")

        upload_result = cloudinary.uploader.upload(
            file_name,
            folder="stream-pix-audio",
            resource_type="video",
            public_id=dados.uuid
        )

        return upload_result.get("secure_url")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)



@app.post("/generate-all-voices")
async def gerar_todas_vozes_endpoint(key: str):
    if key != API_KEY_APP:
        raise HTTPException(status_code=401, detail="Chave inválida!")

    texto = "Essa é a minha voz, podemos criar isso juntos!"
    resultados = {}

    for chave, voice in VOZES.items():
        file_name = f"{chave}.mp3"

        try:
            tts = edge_tts.Communicate(texto, voice)
            await tts.save(file_name)

            upload_result = cloudinary.uploader.upload(
                file_name,
                folder="stream-pix-audio",
                resource_type="video",
                public_id=chave
            )

            resultados[chave] = upload_result.get("secure_url")

        except Exception as e:
            resultados[chave] = f"Erro: {str(e)}"

        finally:
            if os.path.exists(file_name):
                os.remove(file_name)

    return resultados


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
