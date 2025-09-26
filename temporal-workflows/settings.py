from pydantic_settings import BaseSettings
from functools import lru_cache
from temporalio.client import Client



class Settings(BaseSettings):

    TEMPORAL_HOST: str = "localhost"
    TEMPORAL_PORT: int = 7233

    EXAMPLE_SYNC_QUEUE: str = "example-task-queue"
    EXAMPLE_ASYNC_QUEUE: str = "example-async-task-queue"

    @property
    def target_host(self) -> str:
        return f"{self.TEMPORAL_HOST}:{self.TEMPORAL_PORT}"

    @lru_cache(1)
    def get_client(self) -> Client:
        return Client.connect(self.target_host)


settings = Settings()