import asyncio

from src.database.sqlite_manager import get_sqlite_manager
from src.database.repositories.agent_repository import AgentRepository

async def test_get_method():
    ctx = get_sqlite_manager()
    repo = AgentRepository(ctx)
    result = await repo.get_agent_prompt(prompt_index=6.0)
    print("RESULT:", result)

if __name__ == "__main__":
    asyncio.run(test_get_method())