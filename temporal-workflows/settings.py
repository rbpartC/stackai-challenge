from functools import lru_cache
from temporalio.client import Client
import os

TEMPORAL_HOST: str = os.getenv("TEMPORAL_HOST", "localhost")
TEMPORAL_PORT: int = int(os.getenv("TEMPORAL_PORT", 7233))

EXAMPLE_SYNC_QUEUE: str = "example-task-queue"
EXAMPLE_ASYNC_QUEUE: str = "example-async-task-queue"

BUILD_ID: str = os.getenv("RENDER_GIT_COMMIT", "test")

target_host = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"

@lru_cache(1)
async def get_client() -> Client:
    return await Client.connect(target_host)
