from agents.graph import build_graph

graph = build_graph()

async def run_agent(user_input: str):
    # LangGraph'in yolda veri kaybetmemesi için TÜM olası anahtarları 
    # boş veya None olarak en başta tanımlıyoruz. (Kayıt Defteri açmak gibi)
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
    return result.get("final_answer", "Sistemden bir cevap alınamadı.")