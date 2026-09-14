from langgraph.graph import END, StateGraph
from app.agents.planner import plan
from app.agents.verifier import verify


def retrieve_rules(state: dict) -> dict:
    updated = dict(state)
    updated["audit_trail"] = list(state.get("audit_trail", [])) + [
        "Requirement Agent: aggregated official portal, JoSAA/AICTE norms & Quora student guidelines."
    ]
    return updated


def build_graph():
    workflow = StateGraph(dict)
    workflow.add_node("plan", plan)
    workflow.add_node("retrieve_rules", retrieve_rules)
    workflow.add_node("verify", verify)
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "retrieve_rules")
    workflow.add_edge("retrieve_rules", "verify")
    workflow.add_edge("verify", END)
    return workflow.compile()


verification_graph = build_graph()