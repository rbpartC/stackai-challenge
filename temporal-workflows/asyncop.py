import asyncio
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
            initial_interval=1.0,
            maximum_interval=10.0,
            maximum_attempts=3
        )
        try:
            result = await workflow.execute_activity(
                unreliable_activity,
                param,
                start_to_close_timeout=5,
                retry_policy=retry_policy,
            )
            return result
        except Exception as err:
            # Error recovery logic
            workflow.logger.error(f"Activity failed after retries: {err}")
            return "Fallback result due to failure"

# --- Worker Entrypoint ---

async_activities = [unreliable_activity]
async_workflows = [AsyncWorkflow]

async def main():
    client = await settings.get_client()
    result = await client.start_workflow(
        AsyncWorkflow.run,
        [1, 2, 3],
        id=f"async-workflow-id-{uuid.uuid4()}",
        task_queue=settings.EXAMPLE_SYNC_QUEUE,
    )
    print("Workflow result:", result.result())

if __name__ == "__main__":
    asyncio.run(main())