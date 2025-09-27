import asyncio
from datetime import timedelta
from typing import Any, List

from temporalio import activity, workflow


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
    async def run(
        self, dataset_length, start_index: int = 0, total_processed: int = 0
    ) -> int:
        # If all data processed, return total
        if start_index >= dataset_length:
            return total_processed

        # Process next chunk
        end_index = min(start_index + self.chunk_size, dataset_length)
        chunk = range(start_index, end_index)  # Simulated data chunk
        processed = await workflow.execute_activity(
            process_data_chunk,
            chunk,
            schedule_to_close_timeout=timedelta(minutes=10),
            heartbeat_timeout=timedelta(seconds=30),
        )

        # Continue as new for next chunk
        return await workflow.continue_as_new(
            args=[dataset_length, end_index, total_processed + processed],
        )


longrunning_workflows = [ProcessLargeDatasetWorkflow]
longrunning_activities = [process_data_chunk]
