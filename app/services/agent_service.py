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

    # 🌟 KRİTİK DÜZELTME: Şifreli kısmı normal metinden ayır!
    if "###UCUSLAR###" in final_answer:
        metin_kismi, json_kismi = final_answer.split("###UCUSLAR###")
        
        # 1. Normal metni (konuşmayı) daktilo gibi akıt
        for word in metin_kismi.split(" "):
            yield word + " "
            await asyncio.sleep(0.04)
            
        # 2. JSON uçuş verisini TEK SEFERDE, bütün olarak gönder! (Bozulmaması için)
        yield "###UCUSLAR###" + json_kismi
        
    else:
        # Şifre yoksa her şeyi daktilo gibi akıt
        for word in final_answer.split(" "):
            yield word + " "
            await asyncio.sleep(0.04)