from langgraph.graph import StateGraph , END
from agents.state import AgentState
from agents.nodes import supervisor_agent , transport_agent , search_agent , responder_agent

def build_graph():
    workflow = StateGraph(AgentState)
    # Supervisor hepsini orkestra şefi gibi yönetecek!
    # Ajanları düğümler olarak ekle
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("transport", transport_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("responder", responder_agent)
    # Sistem Supervisor ile başlar
    workflow.set_entry_point("supervisor")
    # Supervisor'ın kararına göre diğer düğümlere yönlendir
    workflow.add_conditional_edges(
        "supervisor",
        lambda state:state["next_node"],
        {
            "transport":"transport",
            "search":"search",
            "responder":"responder"
        }
    )
    # Alt ajanlar işini bitirince tekrar Supervisor'a döner (Döngü/Kontrol noktası)
    workflow.add_edge("transport", "responder")
    workflow.add_edge("search", "responder")
    # Responder işini bitirince süreci sonlandırır
    workflow.add_edge("responder", END)
    return workflow.compile()

