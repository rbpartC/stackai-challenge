import asyncio
import logging
from concurrent.futures.thread import ThreadPoolExecutor

import settings
from temporalio.common import VersioningBehavior
from temporalio.worker import Worker, WorkerDeploymentConfig, WorkerDeploymentVersion
from workflows.asyncop import async_activities, async_workflows
from workflows.faf import faf_workflows
from workflows.longrunning import longrunning_activities, longrunning_workflows
from workflows.orchestration import workflows


async def main():
    with ThreadPoolExecutor(max_workers=10) as executor:
        logging.info("Starting worker...")
        client = await settings.get_client()
        worker = Worker(
            client,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            activities=async_activities + longrunning_activities,
            workflows=workflows
            + async_workflows
            + faf_workflows
            + longrunning_workflows,
            activity_executor=executor,
            workflow_task_executor=executor,
            # deployment_config=WorkerDeploymentConfig(
            #     use_worker_versioning=True,
            #     default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE,
            #     version=WorkerDeploymentVersion(
            #         deployment_name=settings.DEPLOYMENT_NAME, build_id=settings.BUILD_ID
            #     ),
            # ),
        )
        await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
