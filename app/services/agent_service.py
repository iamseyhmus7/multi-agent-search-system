#Ekranda kusursuz bir "daktilo" efekti yaratır ve LangGraph yapını hiç bozmaz. 
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

    # 1. Ajanların arka planda işini bitirmesini bekle (Ainvoke)
    result = await graph.ainvoke(initial_state)
    final_answer = result.get("final_answer", "Sistemden bir cevap alınamadı.")

    # 2. Çıkan nihai cevabı kelime kelime fırlat (Yield)
    # Bu döngü, mobil taraftaki o şelale (streaming) etkisini kusursuz yaratır.
    for word in final_answer.split(" "):
        yield word + " "
        await asyncio.sleep(0.04)  # Kelimeler arası 40 milisaniye daktilo hızı (bunu zevkine göre değiştirebilirsin)