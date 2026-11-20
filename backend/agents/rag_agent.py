from langchain.agents import create_agent
from backend.prompts.rag_agent_prompt import RAG_AGENT_PROMPT
from backend.tools.vektor_db import RAG_TOOLS
from backend.llm.llm import deepsek_llm
from backend.tools.langchain_toolkits import file_management_tools
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def chat_rag_agent(session_id: str, request: str):
    with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        checkpointer.setup()
        rag_agent = create_agent(model=deepsek_llm, tools=RAG_TOOLS,
                                 system_prompt=RAG_AGENT_PROMPT,
                                 checkpointer=checkpointer)
        response = rag_agent.invoke({"messages": [{"role": "user", "content": request}]},
                                    config={"configurable": {"thread_id": session_id}})
        return response["messages"][-1].content


# while True:
#     user_request = input("REQUEST : ")
#     if user_request in ("exit", "quit"):
#         break
#     response = chat_rag_agent(session_id="dastonbek87473akkjaaaaaaaaefn182rh3249", request=user_request)
#     print("\n\n", response, "\n")
