from agents.graph import build_graph

graph = build_graph()

def run_agent(user_input: str):
    initial_state = {
        "user_input": user_input,
        "intent": None,
        "tool_result": None,
        "final_answer": None,
    }

    result = graph.invoke(initial_state)
    return result["final_answer"]
