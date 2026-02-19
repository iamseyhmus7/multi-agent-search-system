from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.nodes import intent_detection, tool_execution, final_response

def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("intent", intent_detection)
    workflow.add_node("tool", tool_execution)
    workflow.add_node("final", final_response)

    workflow.set_entry_point("intent")

    workflow.add_conditional_edges(
        "intent",
        lambda state: state["intent"],
        {
            "search": "tool",
            "general": "final"
        }
    )

    workflow.add_edge("tool", "final")
    workflow.add_edge("final", END)

    return workflow.compile()
