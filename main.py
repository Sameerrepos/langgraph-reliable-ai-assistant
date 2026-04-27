from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

# =====================================================
# STATE DEFINITION
# =====================================================

class State(TypedDict):
    user_query: str
    intent: str
    response: str
    validation: str
    retries: int


# =====================================================
# LLM CONFIGURATION (Groq - Free)
# =====================================================

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2
)


# =====================================================
# PLANNER NODE (INTENT DETECTION)
# =====================================================

def planner_node(state: State) -> State:
    intent = llm.invoke(
        f"""
Identify the user's intent clearly.

User query:
{state['user_query']}
"""
    ).content

    return {
        "user_query": state["user_query"],
        "intent": intent,
        "response": "",
        "validation": "",
        "retries": 0
    }


# =====================================================
# RESPONDER NODE
# =====================================================

def responder_node(state: State) -> State:
    response = llm.invoke(
        f"""
Answer the user clearly and completely.

User query:
{state['user_query']}

User intent:
{state['intent']}
"""
    ).content

    return {
        **state,
        "response": response
    }


# =====================================================
# VALIDATOR NODE (GUARDRAIL)
# =====================================================

def validator_node(state: State) -> State:
    validation = llm.invoke(
        f"""
Validate the response based on these criteria:
- Is it relevant to the query?
- Is it clear and understandable?
- Is it reasonably complete?

Response:
{state['response']}

Reply ONLY with VALID or INVALID.
"""
    ).content.strip()

    return {
        **state,
        "validation": validation,
        "retries": state["retries"] + 1
    }


# =====================================================
# RETRY LOGIC
# =====================================================

MAX_RETRIES = 2

def retry_router(state: State):
    if "VALID" in state["validation"].upper():
        return END
    if state["retries"] >= MAX_RETRIES:
        return END
    return "responder"


# =====================================================
# BUILD LANGGRAPH
# =====================================================

graph = StateGraph(State)

graph.add_node("planner", planner_node)
graph.add_node("responder", responder_node)
graph.add_node("validator", validator_node)

graph.set_entry_point("planner")
graph.add_edge("planner", "responder")
graph.add_edge("responder", "validator")

graph.add_conditional_edges(
    "validator",
    retry_router,
    {
        "responder": "responder",
        END: END,
    }
)

app = graph.compile()


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":
    output = app.invoke({
        "user_query": "Explain what an AI agent is"
    })

    print("\n--- RESPONSE ---")
    print(output["response"])

    print("\n--- VALIDATION ---")
    print(output["validation"])

    print("\n--- RETRIES ---")
    print(output["retries"])
