import asyncio
from langchain.agents import create_agent
from backend.llm.llm import deepsek_llm
from backend.prompts.brauzer_agent_prompt import BRAUZER_AGENT_PROMPT
from backend.tools.brauzer_tools import BROWSER_TOOLS, shutdown_browser
from dotenv import load_dotenv
import os
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def chat_brauzer_agent(session_id: str, request: str):
    async with AsyncPostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpoint:
        await checkpoint.setup()
        agent = create_agent(model=deepsek_llm, system_prompt=BRAUZER_AGENT_PROMPT, tools=BROWSER_TOOLS,
                             checkpointer=checkpoint)

        response = await agent.ainvoke({"messages": [{"role": "user", "content": request}]},
                                       config={"configurable": {"thread_id": session_id}})
        # print(response['messages'][-1].content)

        return response['messages'][-1].content

# if __name__ == '__main__':
#     asyncio.run(chat_brauzer_agent(session_id="dasddstoddnbek76363873ddddd4y7283r7kfskf"))
