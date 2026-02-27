from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from services.agent_service import run_agent

app = FastAPI()

# Gerçek bir stream deneyimi için backend'in tek bir JSON dönmemeli; 
# kelimeleri üretildikçe düz metin (plain text) olarak parça parça dışarı tükürmelidir.
@app.post("/chat") 
async def chat(payload: dict):
    user_input = payload.get("message")
    image_input = payload.get("image")  # 🖼️ Yeni: Base64 formatında görsel
    # 🌟 YENİ EKLENEN KABLO: Geçmiş sohbeti (hafızayı) alıyoruz
    chat_history = payload.get("chat_history", "")
    
    # Kelimeleri parça parça gönderecek olan jeneratör fonksiyonumuz
    async def generate_response():
        # run_agent artık tüm metni tek seferde dönmek yerine,
        # kelimeleri/cümleleri parça parça "yield" ile fırlatmalı.
        async for chunk in run_agent(user_input, image_input, chat_history):
            # Eğer chunk dict/json formatındaysa onu sadece string'e çevirip gönderiyoruz
            if isinstance(chunk, dict) and "response" in chunk:
                yield chunk["response"]
            else:
                yield str(chunk)

    # Cevabı JSON olarak değil, akan bir metin (stream) olarak döndürüyoruz
    return StreamingResponse(generate_response(), media_type="text/plain")