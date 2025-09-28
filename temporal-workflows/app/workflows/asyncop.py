import asyncio
from datetime import timedelta

import settings
from temporalio import activity, exceptions, workflow
from temporalio.common import RetryPolicy
from workflows.utils.types import PositiveInt


class IsEvenError(Exception):
    pass


# --- Activities ---


@activity.defn
async def unreliable_activity(param: PositiveInt) -> str:
    # Simulate possible failure
    if param.value % 2 == 0:
        raise IsEvenError("Simulated failure because param is even")
    await asyncio.sleep(param.value)
    return f"Processed {param.value}"


# --- Workflow ---


@workflow.defn
class AsyncWorkflow:
    @workflow.run
    async def run(self, param: int) -> str:
        validated = PositiveInt(value=param)
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )
        try:
            result = await workflow.execute_activity(
                unreliable_activity,
                validated,
                task_queue=settings.EXAMPLE_SYNC_QUEUE,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy,
            )
            return result
        except exceptions.ActivityError as err:
            # Timeout recovery logic
            if "timed out" in str(err):
                workflow.logger.error("Activity timed out")
                return "Fallback result due to timeout"
            raise err
        except IsEvenError as err:
            # Error recovery logic
            return f"Fallback result due to simulated failure"


# --- Worker Entrypoint ---

async_activities = [unreliable_activity]
async_workflows = [AsyncWorkflow]
