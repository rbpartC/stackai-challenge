from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.api.workflowservice.v1 import ListNamespacesRequest, RegisterNamespaceRequest
from pydantic import BaseModel, ValidationError, Field
from typing import Annotated, List

# --- Data models with validation ---

class InputData(BaseModel):
    value: Annotated[int, Field(strict=True, ge=0)]  # Non-negative integer

class ResultData(BaseModel):
    result: int

# --- Activities ---

@activity.defn
async def add_one(input_data: InputData) -> ResultData:
    return ResultData(result=input_data.value + 1)

@activity.defn
async def multiply_by_two(input_data: InputData) -> ResultData:
    return ResultData(result=input_data.value * 2)

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
            schedule_to_close_timeout=5
        )

        # Parallel execution: multiply_by_two to the rest
        parallel_futures = [
            workflow.execute_activity(
                multiply_by_two,
                inp,
                schedule_to_close_timeout=5
            )
            for inp in validated_inputs[1:]
        ]
        parallel_results = await workflow.await_all(*parallel_futures)

        # Collect all results
        all_results = [seq_result.result] + [r.result for r in parallel_results]
        return all_results

# --- Example client code to start workflow (for reference) ---
import os 
async def main():
    TEMPORAL_HOST = f"{os.getenv("TEMPORAL_HOST", "localhost")}:{os.getenv("TEMPORAL_PORT", "7233")}"

    client = await Client.connect(TEMPORAL_HOST)
    list_resp = await client.workflow_service.list_namespaces(ListNamespacesRequest())
    print(f"First page of {len(list_resp.namespaces)} namespaces:")
    for namespace in list_resp.namespaces:
        print(f"  Namespace: {namespace.namespace_info.name}")

    print("Attempting to add namespace 'my-namespace'")
    await client.workflow_service.register_namespace(
        RegisterNamespaceRequest(
            namespace="default",
            workflow_execution_retention_period=3600
        )
    )
    print("Registration complete (may take a few seconds to be usable)")
    result = await client.start_workflow(
        OrchestrationWorkflow.run,
        [1, 2, 3],
        id="example-workflow-id",
        task_queue="example-task-queue"
    )
    print("Workflow result:", result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())