import asyncio
from datetime import timedelta
import time
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
import settings
import uuid

# --- Activities ---

@activity.defn
async def unreliable_activity(param: int) -> str:
    # Simulate possible failure
    if param % 2 == 0:
        raise RuntimeError("Simulated failure")
    await asyncio.sleep(param)
    return f"Processed {param}"

# --- Workflow ---

@workflow.defn
class AsyncWorkflow:
    @workflow.run
    async def run(self, param: int) -> str:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )
        try:
            result = await workflow.execute_activity(
                unreliable_activity,
                param,
                task_queue=settings.EXAMPLE_SYNC_QUEUE,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy,
            )
            return result
        except asyncio.exceptions.CancelledError:
            # Timeout recovery logic
            workflow.logger.error("Activity timed out")
            return "Fallback result due to timeout"
        except Exception as err:
            # Error recovery logic
            return f"Fallback result due to failure: {type(err)}"

# --- Worker Entrypoint ---

async_activities = [unreliable_activity]
async_workflows = [AsyncWorkflow]

async def main():
    client = await settings.get_client()
    result = await client.start_workflow(
        AsyncWorkflow.run,
        1,
        id=f"async-workflow-id-{uuid.uuid4()}",
        task_queue=settings.EXAMPLE_SYNC_QUEUE,
    )
    print("Workflow result:", result.result())

if __name__ == "__main__":
    asyncio.run(main())