from backend.prompts.document_agent_prompt import DOCUMENT_AGENT_PROMPT
from backend.tools.langchain_toolkits import FILE_MANAGMENT_TOOLS
from backend.llm.llm import deepsek_llm
from langchain.agents import create_agent
from backend.tools.word_file_tools import WORD_TOOLS
from backend.tools.excell_file_tools import EXCEL_TOOLS
from backend.tools.power_point_file_tools import POWERPOINT_TOOLS
from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv
import os

load_dotenv()

DOC_TOOLS = POWERPOINT_TOOLS + FILE_MANAGMENT_TOOLS + WORD_TOOLS + EXCEL_TOOLS
DB_URL = os.getenv("DATABASE_URL")


def chat_document_agent(request: str, session_id):
    with PostgresSaver.from_conn_string(DB_URL) as checkpointer:
        checkpointer.setup()

        doc_agent = create_agent(model=deepsek_llm, tools=DOC_TOOLS, system_prompt=DOCUMENT_AGENT_PROMPT,
                                 checkpointer=checkpointer)
        response = doc_agent.invoke({"messages": [{"role": "user", "content": request}]},
                                    config={"configurable": {"thread_id": session_id}})
    return response['messages'][-1].content


# while True:
#     user_input = input("REQUEST : ")
#     if user_input == "exit":
#         break
#     print(chat_document_agent(session_id="123456789asdfghj", request=user_input))
