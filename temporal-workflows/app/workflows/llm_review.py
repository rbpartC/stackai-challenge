import asyncio
from datetime import timedelta
from typing import List, Optional

from pydantic import BaseModel
from settings import get_openai_client
from temporalio import activity, workflow
from workflows.utils.extract_text import extract_text_from_url

# --- Pydantic Models ---

REVIEW_TIMEOUT = timedelta(minutes=10)
REFRESH_RATE = 10  # seconds
AUTO_APPROVED_STATUS = "auto-approved"


class Entity(BaseModel):
    name: str
    type: str


class LLMEntities(BaseModel):
    entities: List[Entity]


class HumanReview(BaseModel):
    review: Optional[str] = None
    status: Optional[str] = None


class LLMResult(BaseModel):
    summary: str
    entities: LLMEntities
    type: str
    human_review: HumanReview


# --- Activities ---


@activity.defn
async def extract_text(url: str) -> str:
    return extract_text_from_url(url)


@activity.defn
async def summarize_doc(doc: str) -> str:
    # Call your LLM summarization API here
    summary = get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"Summarize the following document in less than 100 words: {doc}",
            }
        ],
    )
    return summary.choices[0].message.content


@activity.defn
async def extract_entities(doc: str) -> LLMEntities:
    # Call your LLM entity extraction API here
    entities = get_openai_client().responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "user", "content": f"Extract entities from the document: {doc}"}
        ],
        text_format=LLMEntities,
    )
    return entities.output_parsed


@activity.defn
async def classify_doc(doc: str) -> str:
    # Call your LLM classification API here
    classification = get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": f"Classify the document in less than 5 words: {doc}",
            }
        ],
    )
    return classification.choices[0].message.content


# --- Workflow ---


@workflow.defn
class WebPageReviewWorkflow:
    def __init__(self):
        self.human_review: Optional[HumanReview] = None

    @workflow.signal
    async def submit_human_review(self, review: str):
        self.human_review = HumanReview(review=review)

    @workflow.run
    async def run(self, url: str) -> LLMResult:

        # Step 1: Extract text from the URL
        doc = await workflow.execute_activity(
            extract_text, url, schedule_to_close_timeout=timedelta(seconds=30)
        )

        # Run LLM activities in parallel
        summary_fut = workflow.execute_activity(
            summarize_doc, doc, schedule_to_close_timeout=timedelta(seconds=30)
        )
        entities_fut = workflow.execute_activity(
            extract_entities, doc, schedule_to_close_timeout=timedelta(seconds=30)
        )
        class_fut = workflow.execute_activity(
            classify_doc, doc, schedule_to_close_timeout=timedelta(seconds=30)
        )
        summary, entities, doc_type = await asyncio.gather(
            summary_fut, entities_fut, class_fut
        )

        # Wait for human review (signal) or timeout
        try:
            await asyncio.wait_for(
                self._wait_for_review(), timeout=REVIEW_TIMEOUT.total_seconds()
            )  # 10 min
        except asyncio.TimeoutError:
            self.human_review = HumanReview(status=AUTO_APPROVED_STATUS)

        return LLMResult(
            summary=summary,
            entities=entities,
            type=doc_type,
            human_review=self.human_review or HumanReview(),
        )

    async def _wait_for_review(self):
        while self.human_review is None:
            await asyncio.sleep(REFRESH_RATE)


# --- Entrypoint for worker ---
llm_workflows = [WebPageReviewWorkflow]
llm_activities = [summarize_doc, extract_entities, classify_doc, extract_text]
