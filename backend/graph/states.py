from typing import TypedDict, Literal
from pydantic import BaseModel, Field, validator


class GeneralState(TypedDict):
    # bu userning sorovini oladi
    user_request: str
    session_id: str
    # bu qolganlarini supervisiordan kelgan narsalarni olamiz !
    next_agent: str
    agent_task: str
    respoonse_agent: str
    response_agent_approved: bool
    feedback: str
    attempts: int
    max_attempts: int
    # supervisiorni yakuniy javobi !
    finally_response: str


class SupervisiorState(BaseModel):
    response: str
    next_agent: Literal["brauzer", "database", "document", "game", "lesson", "rag", "research"] = Field(
        description="Qaysi agentga topshiriq berilishi. Yani qaysi agentga topshiriq berilishi")
    agent_task: str = Field(
        description="Agentga beriladigan task. Yani qaysi agentga qanday topshiriq berilishini berasiz.")
    feedback: str = Field(description="Kelgan javob maqul bo'lmaydigan bo'lsa javobni kamchiligi yoziladi.")
    approved: bool = Field(
        description="Javo maqul bolsa True, agarda javob yoqmaydigan bolsa False qilib feedback berilsin.")
    # oxirgi yakuniy javob
    finally_response: str = Field(description="Supervisiorning javobi !")
