import asyncio
import logging
from concurrent.futures.thread import ThreadPoolExecutor

import settings
from temporalio.common import VersioningBehavior
from temporalio.worker import Worker, WorkerDeploymentConfig, WorkerDeploymentVersion
from workflows.asyncop import async_activities, async_workflows
from workflows.faf import faf_workflows
from workflows.llm_review import llm_activities, llm_workflows
from workflows.longrunning import longrunning_activities, longrunning_workflows
from workflows.orchestration import workflows
from workflows.scrapper import scrapper_activities, scrapper_workflows


async def main():
    with ThreadPoolExecutor(max_workers=10) as executor:
        logging.info("Starting worker...")
        client = await settings.get_client()
        worker = Worker(
            client,
            task_queue=settings.EXAMPLE_SYNC_QUEUE,
            activities=async_activities
            + longrunning_activities
            + llm_activities
            + scrapper_activities,
            workflows=workflows
            + async_workflows
            + faf_workflows
            + longrunning_workflows
            + llm_workflows
            + scrapper_workflows,
            activity_executor=executor,
            workflow_task_executor=executor,
        )
        await worker.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
