from typing import TypedDict, Optional, Dict, Any

class AgentState(TypedDict):
    user_input: str
    intent: Optional[str]
    search_query: Optional[str]  # <-- İŞTE EKSİK OLAN SİHİRLİ SATIR BURASI
    tool_result: Optional[Dict[str, Any]]
    final_answer: Optional[str]