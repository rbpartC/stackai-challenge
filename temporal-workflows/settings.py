from functools import lru_cache
from temporalio.client import Client




TEMPORAL_HOST: str = "localhost"
TEMPORAL_PORT: int = 7233

EXAMPLE_SYNC_QUEUE: str = "example-task-queue"
EXAMPLE_ASYNC_QUEUE: str = "example-async-task-queue"

target_host = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"

@lru_cache(1)
def get_client() -> Client:
    return Client.connect(target_host)
