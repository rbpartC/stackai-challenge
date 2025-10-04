from typing import Optional

import pydantic
from pydantic import BaseModel, Field
from temporalio import activity, workflow

BASE = "https://medium.com"
DATEFORMAT = "%Y-%m"

with workflow.unsafe.imports_passed_through():
    from datetime import datetime, timedelta

    import requests
    from bs4 import BeautifulSoup


class ScrapParams(BaseModel):
    tag: str = Field(min_length=1)
    # Validate go_back_to and current_date as YYYY-MM if not None
    go_back_to: Optional[str] = None
    current_date_index: int = 0
    archives_dates: Optional[list[str]] = None
    urls: list[str] = []

    @pydantic.field_validator("go_back_to")
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, DATEFORMAT)
            except ValueError:
                raise ValueError(f"{v} is not in YYYY-MM format")
        return v


class GetLinksParams(BaseModel):
    tag: str = Field(min_length=1)
    archive_date: str = Field(min_length=7, max_length=7)  # YYYY-MM format


@activity.defn
async def gen_year_month(up_to: str) -> list[str]:
    up_to_date = datetime.strptime(up_to, DATEFORMAT)
    current_date = datetime.now()
    days = [
        up_to_date + timedelta(days=date)
        for date in range(0, (current_date - up_to_date).days + 1)
    ]
    year_months = list(set([date.strftime(DATEFORMAT) for date in days]))
    year_months.sort()
    return year_months


# Activity to process a chunk of data with heartbeat progress reporting
@activity.defn
async def get_links(params: GetLinksParams) -> list[str]:
    url = f"{BASE}/tag/{params.tag}/archive"
    urls = ["/".join([url, s]) for s in params.archive_date]
    links = []
    for url in urls:
        data = requests.get(url)
        soup = BeautifulSoup(data.content, "html.parser")
        articles = soup.find_all("a", href=True)
        for i in articles:
            href = i.get("href")
            if not href.startswith(BASE):
                link = BASE + href
            links.append(link)
    return links


@workflow.defn
class ExtractLinksWorkflow:
    def __init__(self):
        self.chunk_size = 100

    @workflow.run
    async def run(self, scrap_params: ScrapParams) -> list[str]:
        # If all data processed, return total
        urls = []

        if scrap_params.go_back_to is None and scrap_params.archives_dates is None:
            archive_dates = [datetime.now().strftime(DATEFORMAT)]
        else:
            archive_dates = await workflow.execute_activity(
                gen_year_month,
                scrap_params.go_back_to,
                start_to_close_timeout=timedelta(seconds=30),
            )

        urls = await workflow.execute_activity(
            get_links,
            GetLinksParams(
                tag=scrap_params.tag,
                archive_date=archive_dates[scrap_params.current_date_index],
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        if len(archive_dates) == scrap_params.current_date_index + 1:
            return urls
        # Continue as new for next chunk
        return await workflow.continue_as_new(
            args=[
                ScrapParams(
                    tag=scrap_params.tag,
                    archives_dates=archive_dates,
                    go_back_to=scrap_params.go_back_to,
                    current_date_index=scrap_params.current_date_index + 1,
                    urls=scrap_params.urls + urls,
                )
            ],
        )


scrapper_workflows = [ExtractLinksWorkflow]
scrapper_activities = [get_links, gen_year_month]
