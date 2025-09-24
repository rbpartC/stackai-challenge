from temporalio.worker import Worker
import asyncio
from orchestration import OrchestrationWorkflow, add_one, multiply_by_two
from client import get_client

async def main():
    client = await get_client()
    worker = Worker(
        client,
        task_queue="example-task-queue",
        workflows=[OrchestrationWorkflow],
        activities=[add_one, multiply_by_two],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())