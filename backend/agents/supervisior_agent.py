from langchain.agents import create_agent
from backend.prompts.supervisior_agent_prompt import SUPERISIOR_AGENT_PROMPT
from backend.llm.llm import deepsek_llm
from langgraph.checkpoint.postgres import PostgresSaver
from backend.graph.states import SupervisiorState
from dotenv import load_dotenv
import os

load_dotenv()


def chat_supervisior_agent(session_id: str, request: str):
    """

    :param session_id:
    :param request:
    :return:
    """
    with PostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpoint:
        checkpoint.setup()
        agent = create_agent(model=deepsek_llm, system_prompt=SUPERISIOR_AGENT_PROMPT, checkpointer=checkpoint,
                             response_format=SupervisiorState)
        result = agent.invoke({"messages": [{"role": "user", "content": request}]},
                              config={"configurable": {"thread_id": session_id}})
        return result["structured_response"]
#
#
# while True:
#     user = input("REQUEST: ")
#     if user in ("exit", "quit"):
#         break
#     print(chat_supervisior_agent(request=user, session_id="daston8737ndwrunui311132323ddd131kksd"))
