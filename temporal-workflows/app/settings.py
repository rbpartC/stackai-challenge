import logging
import os

from openai import OpenAI
from temporalio.client import Client

logging.basicConfig(level=logging.INFO)

TEMPORAL_HOST: str = os.getenv("TEMPORAL_GRPC_HOST", "localhost")
TEMPORAL_PORT: int = int(os.getenv("FRONTEND_GRPC_PORT", 7233))

EXAMPLE_SYNC_QUEUE: str = "example-task-queue-2"
DEPLOYMENT_NAME: str = "sync-python-worker"
BUILD_ID: str = os.getenv("RENDER_GIT_COMMIT", "test")
NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your-api-key")

target_host = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"


async def get_client() -> Client:
    client = await Client.connect(target_host, namespace=NAMESPACE)
    logging.info(f"Successfully connected to Temporal server at {target_host}")
    return client


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)
