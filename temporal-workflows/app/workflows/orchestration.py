import asyncio
import logging
import uuid
from datetime import timedelta
from typing import Annotated, List

import settings
from pydantic import BaseModel, Field
from temporalio import workflow

# --- Data models with validation ---


class InputData(BaseModel):
    value: Annotated[int, Field(strict=True, ge=0)]  # Non-negative integer


class ResultData(BaseModel):
    result: int

    def as_input(self) -> InputData:
        return InputData(value=self.result)


# --- Child Workflows ---


@workflow.defn
class AddOneWorkflow:
    @workflow.run
    async def run(self, input_data: InputData) -> ResultData:
        return ResultData(result=input_data.value + 1)


@workflow.defn
class MultiplyByTwoWorkflow:
    @workflow.run
    async def run(self, input_data: InputData) -> ResultData:
        return ResultData(result=input_data.value * 2)


@workflow.defn
class SumValuesWorkflow:
    @workflow.run
    async def run(self, input_data: List[InputData]) -> ResultData:
        total = sum(item.value for item in input_data)
        return ResultData(result=total)


# --- Main Orchestration Workflow ---


@workflow.defn
class OrchestrationWorkflow:
    @workflow.run
    async def run(self, values: List[int]) -> int:
        logging.info(f"Starting orchestration with values: {values}")
        validated_inputs = [InputData(value=v) for v in values]

        # Sequential execution: add_one to the first value (as child workflow)
        seq_result: ResultData = await workflow.execute_child_workflow(
            AddOneWorkflow.run,
            validated_inputs[0],
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            execution_timeout=timedelta(seconds=10),
        )

        # Parallel execution: multiply_by_two to the rest (as child workflows)
        parallel_futures = [
            workflow.execute_child_workflow(
                MultiplyByTwoWorkflow.run,
                inp,
                task_queue=settings.EXAMPLE_SYNC_QUEUE,
                execution_timeout=timedelta(seconds=10),
            )
            for i, inp in enumerate(validated_inputs[1:])
        ]
        parallel_results: List[ResultData] = await asyncio.gather(*parallel_futures)

        # Collect all results
        all_results = [seq_result] + parallel_results
        final_result: ResultData = await workflow.execute_child_workflow(
            SumValuesWorkflow.run,
            [res.as_input() for res in all_results],
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            execution_timeout=timedelta(seconds=10),
        )
        return final_result.result


# --- Example client code to start workflow (for reference) ---
# Simply run this with python orchestration.py from the worker container

workflows = [
    OrchestrationWorkflow,
    AddOneWorkflow,
    MultiplyByTwoWorkflow,
    SumValuesWorkflow,
]


async def main():
    client = await settings.get_client()
    result = await client.execute_workflow(
        OrchestrationWorkflow.run,
        [1, 2, 3],
        id=f"orchestration-workflow-{uuid.uuid4()}",
        task_queue=settings.EXAMPLE_SYNC_QUEUE,
    )
    print(f"Workflow result: {result}")
    return result


if __name__ == "__main__":
    asyncio.run(main())
