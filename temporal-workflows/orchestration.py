from datetime import timedelta
from temporalio import workflow, activity
from temporalio.api.workflowservice.v1 import ListNamespacesRequest, RegisterNamespaceRequest
from pydantic import BaseModel, ValidationError, Field
from typing import Annotated, List
import settings
import asyncio

import uuid
# --- Data models with validation ---

class InputData(BaseModel):
    value: Annotated[int, Field(strict=True, ge=0)]  # Non-negative integer


class ResultData(BaseModel):
    result: int

    def as_input(self) -> InputData:
        return InputData(value=self.result)

# --- Activities ---

@activity.defn
async def add_one(input_data: InputData) -> ResultData:
    return ResultData(result=input_data.value + 1)

@activity.defn
async def multiply_by_two(input_data: InputData) -> ResultData:
    return ResultData(result=input_data.value * 2)

@activity.defn
async def sum_values(input_data: List[InputData]) -> ResultData:
    total = sum(item.value for item in input_data)
    return ResultData(result=total)

# --- Workflow ---

@workflow.defn
class OrchestrationWorkflow:
    @workflow.run
    async def run(self, values: List[int]) -> List[int]:
        # Validate input
        validated_inputs = [InputData(value=v) for v in values]

        # Sequential execution: add_one to the first value
        seq_result = await workflow.execute_activity(
            add_one,
            validated_inputs[0],
            schedule_to_close_timeout=timedelta(seconds=5)
        )

        # Parallel execution: multiply_by_two to the rest
        parallel_futures = [
            workflow.execute_activity(
                multiply_by_two,
                inp,
                schedule_to_close_timeout=timedelta(seconds=5)
            )
            for inp in validated_inputs[1:]
        ]
        
        parallel_results = await asyncio.gather(*parallel_futures)

        # Collect all results
        all_results = [seq_result] + parallel_results
        final_result = await workflow.execute_activity(
            sum_values,
            [res.as_input() for res in all_results],
            schedule_to_close_timeout=timedelta(seconds=5)
        )
        return final_result.result

# --- Example client code to start workflow (for reference) ---
# Simply run this with python orchestration.py from the worker container

async def main():
    client = await settings.get_client()

    result = await client.start_workflow(
        OrchestrationWorkflow.run,
        [1, 2, 3],
        id=f"orchestration-workflow-id-{uuid.uuid4()}",
        task_queue=settings.EXAMPLE_SYNC_QUEUE,
    )
    print("Workflow result:", result.result())
    


if __name__ == "__main__":
    asyncio.run(main())