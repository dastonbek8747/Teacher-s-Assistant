import asyncio
import traceback
import uuid

from langgraph.graph.state import START, END, StateGraph

from backend.agents.rag_agent import chat_rag_agent
from backend.agents.brauzer_agent import chat_brauzer_agent
from backend.agents.DB_agent import chat_db_agent
from backend.agents.document_agent import chat_document_agent
from backend.agents.game_agent import chat_game_agent
from backend.agents.lesson_agent import chat_lesson_agent
from backend.agents.research_agent import chat_research_agent
from backend.agents.supervisior_agent import chat_supervisior_agent
from backend.graph.states import GeneralState
from backend.tools.brauzer_tools import shutdown_browser


# ---------------------------------------------------------------------------
# Agent node'lari
# ---------------------------------------------------------------------------

def make_sync_agent_node(agent_func):
    """
    Sinxron agent (def) uchun async node yasaydi.
    Agent alohida threadda ishlaydi, shuning uchun event loop bloklanmaydi
    (brauzer va Postgres ulanishlari uzilmaydi).
    """

    async def node(state: GeneralState) -> dict:
        response = await asyncio.to_thread(
            agent_func,
            session_id=state["session_id"],
            request=state["agent_task"],
        )
        return {"respoonse_agent": str(response)}

    return node


async def brauzer_node(state: GeneralState) -> dict:
    """Brauzer agenti async, shuning uchun to'g'ridan-to'g'ri await qilinadi."""
    response = await chat_brauzer_agent(
        session_id=state["session_id"],
        request=state["agent_task"],
    )
    return {"respoonse_agent": str(response)}


rag_node = make_sync_agent_node(chat_rag_agent)
db_node = make_sync_agent_node(chat_db_agent)
document_node = make_sync_agent_node(chat_document_agent)
game_node = make_sync_agent_node(chat_game_agent)
lesson_node = make_sync_agent_node(chat_lesson_agent)
research_node = make_sync_agent_node(chat_research_agent)


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

async def supervisior_node(state: GeneralState) -> dict:
    request = (
        f"user_request: {state['user_request']}\n"
        f"agent_task: {state['agent_task']}\n"
        f"response_agent: {state['respoonse_agent']}\n"
        f"attempts: {state['attempts']}, max_attempts: {state['max_attempts']}"
    )

    result = await asyncio.to_thread(
        chat_supervisior_agent,
        session_id=state["session_id"],
        request=request,
    )

    attempts = state["attempts"]
    finally_response = result.finally_response

    if result.approved:
        attempts = 0
    elif result.feedback:
        attempts += 1

    if attempts > state["max_attempts"] and not finally_response:
        finally_response = "Kechirasiz, bu vazifani bajara olmadim. So'rovni aniqroq yozing."

    return {
        "next_agent": result.next_agent,
        "agent_task": result.agent_task,
        "response_agent_approved": result.approved,
        "feedback": result.feedback,
        "finally_response": str(finally_response) if finally_response else "",
        "attempts": attempts,
    }


def route_from_supervisor(state: GeneralState):
    if state["finally_response"] or not state["agent_task"]:
        return END
    return state["next_agent"]


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

AGENT_NODES = {
    "brauzer_node": brauzer_node,
    "db_node": db_node,
    "document_node": document_node,
    "game_node": game_node,
    "lesson_node": lesson_node,
    "rag_node": rag_node,
    "research_node": research_node,
}

builder = StateGraph(GeneralState)
builder.add_node("supervisior_node", supervisior_node)
for name, func in AGENT_NODES.items():
    builder.add_node(name, func)
    builder.add_edge(name, "supervisior_node")

builder.add_edge(START, "supervisior_node")
builder.add_conditional_edges(
    "supervisior_node",
    route_from_supervisor,
    {
        "brauzer": "brauzer_node",
        "database": "db_node",
        "document": "document_node",
        "game": "game_node",
        "lesson": "lesson_node",
        "rag": "rag_node",
        "research": "research_node",
        END: END,
    },
)

graph = builder.compile()


# ---------------------------------------------------------------------------
# Kirish nuqtasi
# ---------------------------------------------------------------------------

async def chat_techflow_ai(request: str, session_id: str):
    initial_state = {
        "user_request": request,
        "session_id": session_id,
        "next_agent": "",
        "agent_task": "",
        "respoonse_agent": "",
        "response_agent_approved": False,
        "feedback": "",
        "attempts": 0,
        "max_attempts": 5,
        "finally_response": "",
    }
    return await graph.ainvoke(initial_state, config={"recursion_limit": 30})


async def main():
    session_id = f"test-{uuid.uuid4()}"
    try:
        while True:
            request = await asyncio.to_thread(input, "REQUEST: ")
            if request.strip().lower() in ("exit", "quit"):
                break
            if not request.strip():
                continue
            try:
                result = await chat_techflow_ai(request=request, session_id=session_id)
                print(result["finally_response"] or result)
            except Exception:
                traceback.print_exc()
    finally:
        await shutdown_browser()


# from IPython.display import display, Image
#
# image_data = graph.get_graph().draw_mermaid_png()
# png = display(Image(image_data))
# with open("graph.png", "wb") as fh:
#     fh.write(image_data)
if __name__ == "__main__":
    asyncio.run(main())  # butun dasturda FAQAT BITTA asyncio.run
