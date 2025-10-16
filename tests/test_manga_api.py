"""Offline tests for the MangaBaka API client helpers."""

import httpx
import pytest
import respx
from httpx import Response

from manganotify.services.manga_api import api_search, api_series_by_id


@pytest.mark.asyncio
async def test_api_search_sanitises_parameters():
    """The search helper should trim, clamp and forward parameters correctly."""
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.get("https://api.mangabaka.dev/v1/series/search").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "data": [
                        {
                            "id": 1,
                            "title": "Naruto",
                            "total_chapters": "700",
                            "status": "completed",
                        }
                    ],
                    "pagination": {"page": 2, "limit": 3},
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await api_search(client, " naruto  ", page=2, limit=3)

    request = route.calls[0].request
    assert request.url.params["q"] == "naruto"
    assert request.url.params["page"] == "2"
    assert request.url.params["limit"] == "3"
    assert result["data"][0]["title"] == "Naruto"


@pytest.mark.asyncio
async def test_api_search_truncates_long_queries():
    with respx.mock(assert_all_called=True) as respx_mock:
        route = respx_mock.get("https://api.mangabaka.dev/v1/series/search").mock(
            return_value=Response(200, json={"status": 200, "data": [], "pagination": {}})
        )
        async with httpx.AsyncClient() as client:
            await api_search(client, "a" * 200, page=1, limit=5)

    request = route.calls[0].request
    assert len(request.url.params["q"]) == 100


@pytest.mark.asyncio
async def test_api_search_rejects_empty_queries():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await api_search(client, " ")


@pytest.mark.asyncio
async def test_api_series_lookup_success():
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get("https://api.mangabaka.dev/v1/series/270/full").mock(
            return_value=Response(
                200,
                json={
                    "status": 200,
                    "data": {
                        "id": 270,
                        "title": "NARUTO",
                        "total_chapters": "700",
                        "status": "completed",
                    },
                },
            )
        )
        async with httpx.AsyncClient() as client:
            result = await api_series_by_id(client, "270", full=True)

    assert result["data"]["id"] == 270
    assert result["data"]["title"] == "NARUTO"


@pytest.mark.asyncio
async def test_api_series_lookup_propagates_http_errors():
    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get("https://api.mangabaka.dev/v1/series/999/full").mock(
            return_value=Response(404, json={"status": 404, "message": "Not Found"})
        )
        async with httpx.AsyncClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await api_series_by_id(client, 999, full=True)


@pytest.mark.asyncio
async def test_api_series_lookup_validates_identifier():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await api_series_by_id(client, "abc")
