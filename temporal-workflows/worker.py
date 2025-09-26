from pickle import BUILD
from temporalio.worker import Worker, WorkerDeploymentConfig, WorkerDeploymentVersion
from temporalio.common import VersioningBehavior
import asyncio
from orchestration import OrchestrationWorkflow, add_one, multiply_by_two, sum_values
import settings
from concurrent.futures.thread import ThreadPoolExecutor

async def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        client = await settings.get_client()
        worker = Worker(
            client,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            workflows=[OrchestrationWorkflow],
            activities=[add_one, multiply_by_two, sum_values],
            activity_executor=executor,
            deployment_config=WorkerDeploymentConfig(
                use_worker_versioning=True,
                default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE,
                version=WorkerDeploymentVersion(deployment_name="sync-python-worker",build_id=settings.BUILD_ID),
            )
        )
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())