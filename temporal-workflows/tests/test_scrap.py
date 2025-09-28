from datetime import datetime
from unittest.mock import patch

import pytest
from workflows.scrapper import gen_year_month

fixed_now = datetime(2025, 9, 1)


@patch("datetime.datetime")
@pytest.mark.asyncio
async def test_gen_list_1(mock_datetime):
    mock_datetime.now.return_value = fixed_now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    res = await gen_year_month("2025-09")
    assert res == ["2025/09"], "Should return only the current month"


@patch("datetime.datetime")
@pytest.mark.asyncio
async def test_gen_list_2(mock_datetime):
    mock_datetime.now.return_value = fixed_now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    res = await gen_year_month("2025-08")
    assert res == [
        "2025/08",
        "2025/09",
    ], "Should return the current and next month"


@patch("datetime.datetime")
@pytest.mark.asyncio
async def test_gen_list_3(mock_datetime):
    mock_datetime.now.return_value = fixed_now
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    res = await gen_year_month("2025-02")
    assert res == [
        "2025/02",
        "2025/03",
        "2025/04",
        "2025/05",
        "2025/06",
        "2025/07",
        "2025/08",
        "2025/09",
    ], "Should return all months from February to September, always in order"
