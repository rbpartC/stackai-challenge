import asyncio
from pydantic import BaseModel, Field
from temporalio import workflow
import settings
import uuid

# --- Workflow ---

class PositiveInt(BaseModel):
    value:int = Field(strict=True, gt=0)  # Positive integer


@workflow.defn
class ForgettableWorkflow:
    @workflow.run
    async def run(self, param: PositiveInt) -> str:
        await asyncio.sleep(param.value)

@workflow.defn
class FiringWorkflow:
    @workflow.run
    async def run(self, param: PositiveInt) -> str:
        wf = await workflow.start_child_workflow(
            ForgettableWorkflow.run,
            param,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
        )
        return f"Fired forgettable workflow with run_id {wf.id} without waiting. The ForgettableWorkflow will run in the background for {param} seconds."
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