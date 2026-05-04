import asyncio
import sys
import os

# Add the current directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models.supervisor import Base
# We import these to ensure they are registered with Base.metadata
from app.models.run import Run
from app.models.activity import Activity

async def reset():
    print("--- ORDER SUPERVISOR DATABASE RESET ---")
    print("Connecting to database...")
    try:
        async with engine.begin() as conn:
            print("Dropping all tables (Supervisors, Runs, Activities)...")
            await conn.run_sync(Base.metadata.drop_all)
            print("Recreating all tables fresh...")
            await conn.run_sync(Base.metadata.create_all)
        print("SUCCESS: Database reset complete. You now have a clean slate!")
    except Exception as e:
        print(f"ERROR: Could not reset database: {e}")

if __name__ == "__main__":
    asyncio.run(reset())
