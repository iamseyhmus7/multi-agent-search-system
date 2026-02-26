import asyncio
from agents.graph import build_graph

graph = build_graph()

async def run_agent(user_input: str):
    initial_state = {
        "user_input": user_input,
        "next_node": None,
        "search_query": "",
        "origin": "",
        "destination": "",
        "date": "",
        "tool_result": None,
        "final_answer": "",
    }

    result = await graph.ainvoke(initial_state)
    final_answer = result.get("final_answer", "Sistemden bir cevap alınamadı.")

    # 🌟 MANTIKLI SIRALAMA AYRIŞTIRICISI
    ucus_var_mi = "###UCUSLAR###" in final_answer
    hava_var_mi = "###HAVA_DURUMU###" in final_answer

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