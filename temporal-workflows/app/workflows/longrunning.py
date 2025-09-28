import asyncio
from datetime import timedelta
from typing import Any, List

from pydantic import BaseModel, Field
from temporalio import activity, workflow


class DatasetParams(BaseModel):
    length: int = Field(strict=True, gt=0)  # Positive integer
    start_index: int = Field(default=0, ge=0)  # Non-negative integer
    total_processed: int = Field(default=0, ge=0)  # Non-negative integer


# Activity to process a chunk of data with heartbeat progress reporting
@activity.defn
async def process_data_chunk(data_chunk: List[Any]) -> int:
    chunk_size = len(data_chunk)
    for i, _ in enumerate(data_chunk):
        # Simulate processing
        await asyncio.sleep(0.1)
        # Heartbeat every 10 items
        if i % 10 == 0:
            activity.heartbeat(
                "Processed item {}/{} of chunk".format(i + 1, chunk_size)
            )
    return len(data_chunk)


# Workflow to process a large dataset using Continue As New


@workflow.defn
class ProcessLargeDatasetWorkflow:
    def __init__(self):
        self.chunk_size = 100

    @workflow.run
    async def run(self, dataset_params: DatasetParams) -> int:
        # If all data processed, return total
        if dataset_params.start_index >= dataset_params.length:
            return dataset_params.total_processed

        # Process next chunk
        end_index = min(
            dataset_params.start_index + self.chunk_size, dataset_params.length
        )
        chunk = range(dataset_params.start_index, end_index)  # Simulated data chunk
        processed = await workflow.execute_activity(
            process_data_chunk,
            chunk,
            schedule_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=30),
        )

        # Continue as new for next chunk
        return await workflow.continue_as_new(
            args=DatasetParams(
                length=dataset_params.length,
                start_index=end_index,
                total_processed=dataset_params.total_processed + processed,
            ),
        )


longrunning_workflows = [ProcessLargeDatasetWorkflow]
longrunning_activities = [process_data_chunk]
