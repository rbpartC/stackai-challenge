import os 
from temporalio.client import Client

TEMPORAL_HOST = f"{os.getenv("TEMPORAL_HOST", "localhost")}:{os.getenv("TEMPORAL_PORT", "7233")}"

async def get_client() -> Client:
    return await Client.connect(TEMPORAL_HOST)