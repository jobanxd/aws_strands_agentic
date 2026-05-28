import sys
import asyncio
sys.path.insert(0, "src")   # ← add this before any local imports

from database.sqlite_manager import get_sqlite_manager
from database.repositories.kyc_repository import KYCRepository

async def test_get_method():
    ctx = get_sqlite_manager()
    repo = KYCRepository(ctx)
    result = await repo.get_party_info(party_id="1000001")
    print("RESULT:", result)

if __name__ == "__main__":
    asyncio.run(test_get_method())