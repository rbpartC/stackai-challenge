import logging
import os

from temporalio.client import Client

TEMPORAL_HOST: str = os.getenv("TEMPORAL_GRPC_HOST", "localhost")
TEMPORAL_PORT: int = int(os.getenv("FRONTEND_GRPC_PORT", 7233))

EXAMPLE_SYNC_QUEUE: str = "example-task-queue"
DEPLOYMENT_NAME: str = "sync-python-worker"
BUILD_ID: str = os.getenv("RENDER_GIT_COMMIT", "test")

target_host = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"


async def get_client() -> Client:
    client = await Client.connect(target_host)
    logging.info(f"Successfully connected to Temporal server at {target_host}")
    return client
