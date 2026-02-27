import asyncio
import logging
from agents.graph import build_graph

logger = logging.getLogger(__name__)
graph = build_graph()

async def run_agent(user_input: str, image_input: str = None, chat_history: str = ""):    
    initial_state = {
        "user_input": user_input,
        "image_input": image_input,  # 🌟 Görsel input'u state'e ekle
        "chat_history": chat_history,
        "next_nodes": [],  # Supervisor kararı
        "search_query": "",
        "origin": "",
        "destination": "",
        "date": "",
        "amount": 1.0,
        "from_currency": "EUR",
        "transport_result": {},
        "search_result": {},
        "currency_result": None,
        "vision_result": None,
        "accommodation_result": None,  # 🌟 Yeni: Otel arama sonuçları için alan
        "final_answer": "",
    }

    result = await graph.ainvoke(initial_state)
    
    # 🗐️ DEBUG: Supervisor'un ne karar verdiğini gör
    supervisor_nodes = result.get("next_nodes", [])
    currency_result = result.get("currency_result")
    logger.info(f"🞯 Supervisor Kararı: {supervisor_nodes}")
    logger.info(f"💰 Currency Result: {currency_result}")
    
    final_answer = result.get("final_answer", "Sistemden bir cevap alınamadı.")

    # 🌟 MANTIKLI SIRALAMA AYRIŞTIRICISI
    ucus_var_mi = "###UCUSLAR###" in final_answer
    hava_var_mi = "###HAVA_DURUMU###" in final_answer
    
    # 🗐️ DEBUG: Değişkenleri kontrol et
    logger.debug(f"🗐️ Final Answer Pattern: ucus={ucus_var_mi}, hava={hava_var_mi}")

    # 1. ADIM: Saf Metni (Konuşma) Ayıkla ve Akıt
    saf_metin = final_answer
    if ucus_var_mi:
        saf_metin = saf_metin.split("###UCUSLAR###")[0]
    if hava_var_mi:
        saf_metin = saf_metin.split("###HAVA_DURUMU###")[0]

    for word in saf_metin.split(" "):
        yield word + " "
        await asyncio.sleep(0.04)

    # 2. ADIM: Önce Hava Durumunu Gönder (Hiyerarşide Üstte)
    if hava_var_mi:
        try:
            # Hava durumu JSON'ını diğerlerinden izole et
            hava_parçası = final_answer.split("###HAVA_DURUMU###")[1]
            if "###UCUSLAR###" in hava_parçası:
                hava_parçası = hava_parçası.split("###UCUSLAR###")[0]
            yield "###HAVA_DURUMU###" + hava_parçası
        except: pass

    # 3. ADIM: En Son Uçuş Bilgilerini Gönder
    if ucus_var_mi:
        try:
            # Uçuş JSON'ını diğerlerinden izole et
            ucus_parçası = final_answer.split("###UCUSLAR###")[1]
            if "###HAVA_DURUMU###" in ucus_parçası:
                ucus_parçası = ucus_parçası.split("###HAVA_DURUMU###")[0]
            yield "###UCUSLAR###" + ucus_parçası
        except: pass