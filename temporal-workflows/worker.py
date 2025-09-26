from temporalio.worker import Worker, WorkerDeploymentConfig, WorkerDeploymentVersion
from temporalio.common import VersioningBehavior
import asyncio
from orchestration import workflows
from asyncop import async_activities, async_workflows
from faf import faf_workflows
from longrunning import longrunning_workflows, longrunning_activities
import settings
from concurrent.futures.thread import ThreadPoolExecutor

async def main():
    with ThreadPoolExecutor(max_workers=5) as executor:
        client = await settings.get_client()
        worker = Worker(
            client,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            activities=async_activities + longrunning_activities,
            workflows=workflows + async_workflows + faf_workflows + longrunning_workflows,
            activity_executor=executor,
            workflow_task_executor=executor,
            # deployment_config=WorkerDeploymentConfig(
            #     use_worker_versioning=True,
            #     default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE,
            #     version=WorkerDeploymentVersion(deployment_name="sync-python-worker",build_id=settings.BUILD_ID),
            # )
        )
        await worker.run()

if __name__ == "__main__":
    asyncio.run(main())