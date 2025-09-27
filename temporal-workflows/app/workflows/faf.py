import asyncio

from pydantic import BaseModel, Field
from temporalio import workflow

from . import settings

# --- Workflow ---


class PositiveInt(BaseModel):
    value: int = Field(strict=True, gt=0)  # Positive integer


@workflow.defn
class ForgettableWorkflow:
    @workflow.run
    async def run(self, param: PositiveInt) -> str:
        await asyncio.sleep(param.value)


@workflow.defn
class FiringWorkflow:
    @workflow.run
    async def run(self, param: int) -> str:
        validated = PositiveInt(value=param)
        wf = await workflow.start_child_workflow(
            ForgettableWorkflow.run,
            validated,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            parent_close_policy=workflow.ParentClosePolicy.ABANDON,
        )
        return f"Fired forgettable workflow with run_id {wf.id} without waiting. The ForgettableWorkflow will run in the background for {param} seconds."


# --- Worker Entrypoint ---

faf_workflows = [ForgettableWorkflow, FiringWorkflow]
