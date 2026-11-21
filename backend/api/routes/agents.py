"""Mavjud agentlar ro'yxati."""
from fastapi import APIRouter

from backend.api.agents_registry import AGENTS
from backend.api.schemas import AgentInfo

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=list[AgentInfo], summary="Mutaxassis agentlar ro'yxati")
def list_agents() -> list[AgentInfo]:
    return AGENTS
