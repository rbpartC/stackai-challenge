from temporalio.worker import Worker
import asyncio
from orchestration import OrchestrationWorkflow, add_one, multiply_by_two, sum_values
from client import get_client
from concurrent.futures.thread import ThreadPoolExecutor

async def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        client = await get_client()
        worker = Worker(
            client,
            task_queue="example-task-queue",
            workflows=[OrchestrationWorkflow],
            activities=[add_one, multiply_by_two, sum_values],
            activity_executor=executor,
            use_worker_versioning=True,
        )
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())