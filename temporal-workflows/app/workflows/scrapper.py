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

    def gen_year_month(up_to: str) -> list[str]:
        up_to_date = datetime.strptime(up_to, DATEFORMAT)
        current_date = datetime.now()
        days = [
            up_to_date + timedelta(days=date)
            for date in range(0, (current_date - up_to_date).days + 1)
        ]
        year_months = list(set([date.strftime("%Y/%m") for date in days]))
        year_months.sort()
        return year_months


class ScrapParams(BaseModel):
    tag: str = Field(min_length=1)
    # Validate go_back_to and current_date as YYYY-MM if not None
    go_back_to: Optional[str] = None
    current_date_index: Optional[int] = None
    urls: list[str] = []

    @pydantic.field_validator("go_back_to")
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, DATEFORMAT)
            except ValueError:
                raise ValueError(f"{v} is not in YYYY-MM format")
        return v


# Activity to process a chunk of data with heartbeat progress reporting
@activity.defn
async def get_links(tag: str, archive_date: str = "") -> list[str]:
    url = f"{BASE}/tag/{tag}/archive"
    urls = ["/".join([url, s]) for s in archive_date]
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

        if scrap_params.go_back_to is None:
            archive_dates = [datetime.now().strftime(DATEFORMAT)]
        else:
            archive_dates = gen_year_month(scrap_params.go_back_to)

        if len(archive_dates) == scrap_params.current_date_index + 1:
            return urls

        if scrap_params.current_date_index is not None:
            urls = await workflow.execute_activity(
                get_links,
                scrap_params.tag,
                archive_date=archive_dates[scrap_params.current_date_index],
            )
        # Continue as new for next chunk
        return await workflow.continue_as_new(
            args=[
                ScrapParams(
                    tag=scrap_params.tag,
                    go_back_to=scrap_params.go_back_to,
                    current_date_index=scrap_params.current_date_index + 1 or 0,
                    urls=scrap_params.urls + urls,
                )
            ],
        )


scrapper_workflows = [ExtractLinksWorkflow]
scrapper_activities = [get_links]
