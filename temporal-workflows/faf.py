import asyncio
from datetime import timedelta
import time
from temporalio import workflow, activity, exceptions
from temporalio.common import RetryPolicy
import settings
import uuid

# --- Workflow ---


@workflow.defn
class ForgettableWorkflow:
    @workflow.run
    async def run(self, param: int) -> str:
        await asyncio.sleep(param)

@workflow.defn
class FiringWorkflow:
    @workflow.run
    async def run(self, param: int) -> str:
        workflow.start_child_workflow(
            ForgettableWorkflow.run,
            param,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
        )
        return f"Fired forgettable workflow without waiting. The ForgettableWorkflow will run in the background for {param} seconds."
# --- Worker Entrypoint ---

faf_workflows = [ForgettableWorkflow, FiringWorkflow]

async def main():
    client = await settings.get_client()
    result = await client.start_workflow(
        FiringWorkflow.run,
        1,
        id=f"faf-workflow-id-{uuid.uuid4()}",
        task_queue=settings.EXAMPLE_SYNC_QUEUE,
    )
    print("Workflow result:", result.result())

if __name__ == "__main__":
    asyncio.run(main())