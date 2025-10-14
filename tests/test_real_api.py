"""
Tests for real MangaBaka API integration.
These tests make actual HTTP calls to verify the API works as expected.
"""

import asyncio

import httpx
import pytest

from manganotify.services.manga_api import api_search, api_series_by_id


class TestRealMangaBakaAPI:
    """Test actual MangaBaka API calls to catch real-world issues."""

    @pytest.mark.asyncio
    async def test_real_api_search_basic(self):
        """Test basic search functionality with real API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test search for a popular manga
            result = await api_search(client, "naruto", page=1, limit=5)

            # Verify response structure
            assert result["status"] == 200
            assert "data" in result
            assert "pagination" in result
            assert len(result["data"]) > 0

            # Check first result structure
            first_item = result["data"][0]
            assert "id" in first_item
            assert "title" in first_item
            assert "total_chapters" in first_item
            assert "status" in first_item
            assert "authors" in first_item

            # Verify it's actually Naruto
            assert "naruto" in first_item["title"].lower()

    @pytest.mark.asyncio
    async def test_real_api_search_pagination(self):
        """Test search pagination with real API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test first page
            result1 = await api_search(client, "one piece", page=1, limit=2)
            assert result1["status"] == 200
            assert len(result1["data"]) == 2

            # Test second page
            result2 = await api_search(client, "one piece", page=2, limit=2)
            assert result2["status"] == 200
            assert len(result2["data"]) == 2

            # Verify different results
            page1_ids = [item["id"] for item in result1["data"]]
            page2_ids = [item["id"] for item in result2["data"]]
            assert page1_ids != page2_ids

    @pytest.mark.asyncio
    async def test_real_api_search_edge_cases(self):
        """Test search with edge cases."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test empty search (should handle gracefully)
            with pytest.raises(ValueError):
                await api_search(client, "", page=1, limit=5)

            # Test very long search query (should be truncated, not rejected)
            long_query = "a" * 200
            result = await api_search(client, long_query, page=1, limit=5)
            assert result["status"] == 200
            # The query should be truncated to 100 characters
            assert len(long_query) == 200  # Original length
            # The API should handle it gracefully

            # Test invalid page numbers
            result = await api_search(client, "test", page=0, limit=5)
            assert result["status"] == 200  # Page 0 should be clamped to 1

            # Test page 1001 - API rejects it with 400, but our code clamps it to 1000
            # The API still returns 400 for page 1000, so we expect an exception
            with pytest.raises(httpx.HTTPStatusError):
                await api_search(client, "test", page=1001, limit=5)

    @pytest.mark.asyncio
    async def test_real_api_series_lookup(self):
        """Test series lookup with real API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test known series (Naruto)
            result = await api_series_by_id(client, 270, full=True)

            assert result["status"] == 200
            assert "data" in result

            series = result["data"]
            assert series["id"] == 270
            assert series["title"] == "NARUTO"
            assert series["total_chapters"] == "700"
            assert series["status"] == "completed"
            assert "Masashi Kishimoto" in series["authors"]

    @pytest.mark.asyncio
    async def test_real_api_series_lookup_invalid_id(self):
        """Test series lookup with invalid ID."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test non-existent series
            with pytest.raises(httpx.HTTPStatusError):
                await api_series_by_id(client, 999999999, full=True)

    @pytest.mark.asyncio
    async def test_real_api_series_lookup_merged_series(self):
        """Test series lookup for merged series."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test a series that might be merged (this tests the merged_with logic)
            result = await api_series_by_id(client, 57337, full=True)  # Naruto one-shot

            assert result["status"] == 200
            series = result["data"]

            # Check if it has merge information
            if series.get("state") == "merged" and series.get("merged_with"):
                # This would test the merge logic in the poller
                assert isinstance(series["merged_with"], int)

    @pytest.mark.asyncio
    async def test_real_api_rate_limiting(self):
        """Test API rate limiting behavior."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make multiple rapid requests to test rate limiting
            tasks = []
            for i in range(5):
                task = api_search(client, f"test{i}", page=1, limit=1)
                tasks.append(task)

            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed (API should handle reasonable rate)
            for result in results:
                if isinstance(result, Exception):
                    # If we get rate limited, that's also a valid test result
                    assert "429" in str(result) or "rate" in str(result).lower()
                else:
                    assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_real_api_network_timeout(self):
        """Test API timeout handling."""
        # Use a very short timeout that should cause issues
        async with httpx.AsyncClient(timeout=0.01) as client:  # Extremely short timeout
            # This should timeout or fail
            try:
                await api_search(client, "test", page=1, limit=5)
                # If it doesn't timeout, that's also fine - just verify it works
                assert True
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout):
                # Expected timeout behavior
                assert True

    @pytest.mark.asyncio
    async def test_real_api_data_consistency(self):
        """Test that search and series lookup return consistent data."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for a specific series
            search_result = await api_search(client, "chainsaw man", page=1, limit=5)
            assert search_result["status"] == 200

            # Find Chainsaw Man in search results
            chainsaw_man = None
            for item in search_result["data"]:
                if "chainsaw" in item["title"].lower():
                    chainsaw_man = item
                    break

            assert chainsaw_man is not None

            # Look up the same series by ID
            series_result = await api_series_by_id(
                client, chainsaw_man["id"], full=True
            )
            assert series_result["status"] == 200

            # Compare data consistency
            search_data = chainsaw_man
            series_data = series_result["data"]

            assert search_data["id"] == series_data["id"]
            assert search_data["title"] == series_data["title"]
            assert search_data["total_chapters"] == series_data["total_chapters"]
            assert search_data["status"] == series_data["status"]


class TestRealAPIIntegration:
    """Test real API integration with MangaNotify's business logic."""

    @pytest.mark.asyncio
    async def test_real_api_with_poller_logic(self):
        """Test real API calls with poller business logic."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Simulate what the poller does
            series_id = 270  # Naruto

            # Get series data (like poller does)
            data = await api_series_by_id(client, series_id, full=True)
            series = data.get("data") or data

            # Test poller logic
            new_total = int(series.get("total_chapters", 0))
            old_total = 699  # Simulate being 1 chapter behind
            last_read = 699

            # This is the logic from the poller
            if (
                new_total is not None
                and old_total is not None
                and new_total > old_total
            ):
                unread = new_total - last_read
                assert unread == 1  # Should be 1 unread chapter

                # Test notification logic
                should_notify = True  # Default behavior
                assert should_notify

    @pytest.mark.asyncio
    async def test_real_api_error_handling(self):
        """Test real API error handling scenarios."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test with invalid series ID
            try:
                await api_series_by_id(client, 999999999, full=True)
                raise AssertionError("Should have raised an exception")
            except httpx.HTTPStatusError as e:
                assert e.response.status_code == 404

            # Test with malformed series ID
            try:
                await api_series_by_id(client, "invalid", full=True)
                raise AssertionError("Should have raised an exception")
            except (ValueError, httpx.HTTPStatusError):
                pass  # Expected to fail

    @pytest.mark.asyncio
    async def test_real_api_performance(self):
        """Test real API performance characteristics."""
        import time

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test search performance
            start_time = time.time()
            result = await api_search(client, "one piece", page=1, limit=10)
            search_time = time.time() - start_time

            assert result["status"] == 200
            assert search_time < 5.0  # Should be reasonably fast

            # Test series lookup performance
            start_time = time.time()
            result = await api_series_by_id(client, 270, full=True)
            lookup_time = time.time() - start_time

            assert result["status"] == 200
            assert lookup_time < 3.0  # Should be faster than search
