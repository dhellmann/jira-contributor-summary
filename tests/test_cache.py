"""Tests for caching functionality."""

import tempfile
from datetime import datetime
from pathlib import Path

from jira_contributor_summary.cache import TicketCache


class TestTicketCache:
    """Test cases for TicketCache class."""

    def test_init_with_custom_cache_dir(self):
        """Test initializing cache with custom directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)
            assert cache.cache_dir == Path(temp_dir)
            assert cache.cache_dir.exists()

    def test_init_with_default_cache_dir(self):
        """Test initializing cache with default directory."""
        cache = TicketCache()
        assert cache.cache_dir.exists()
        assert "jira-contributor-summary" in str(cache.cache_dir)

    def test_put_and_get_ticket(self):
        """Test storing and retrieving a ticket."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            ticket_data = {
                "key": "PROJ-1",
                "fields": {
                    "summary": "Test ticket",
                    "updated": "2023-01-01T12:00:00.000Z",
                },
            }

            cache.put_ticket("PROJ-1", ticket_data)
            retrieved = cache.get_ticket("PROJ-1")

            assert retrieved == ticket_data

    def test_get_nonexistent_ticket(self):
        """Test retrieving a ticket that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            retrieved = cache.get_ticket("NONEXISTENT")
            assert retrieved is None

    def test_is_ticket_stale_nonexistent(self):
        """Test checking staleness of nonexistent ticket."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            current_time = datetime.now()
            assert cache.is_ticket_stale("NONEXISTENT", current_time) is True

    def test_is_ticket_stale_newer_version(self):
        """Test checking staleness when current version is newer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            # Store old ticket
            old_ticket = {"fields": {"updated": "2023-01-01T12:00:00.000Z"}}
            cache.put_ticket("PROJ-1", old_ticket)

            # Check with newer timestamp
            newer_time = datetime.fromisoformat("2023-01-02T12:00:00.000+00:00")
            assert cache.is_ticket_stale("PROJ-1", newer_time) is True

    def test_is_ticket_stale_same_version(self):
        """Test checking staleness when versions are the same."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            # Store ticket
            ticket = {"fields": {"updated": "2023-01-01T12:00:00.000Z"}}
            cache.put_ticket("PROJ-1", ticket)

            # Check with same timestamp
            same_time = datetime.fromisoformat("2023-01-01T12:00:00.000+00:00")
            assert cache.is_ticket_stale("PROJ-1", same_time) is False

    def test_get_cached_tickets(self):
        """Test getting all cached tickets."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            ticket1 = {"key": "PROJ-1", "fields": {"summary": "Ticket 1"}}
            ticket2 = {"key": "PROJ-2", "fields": {"summary": "Ticket 2"}}

            cache.put_ticket("PROJ-1", ticket1)
            cache.put_ticket("PROJ-2", ticket2)

            all_tickets = cache.get_cached_tickets()
            assert len(all_tickets) == 2
            assert all_tickets["PROJ-1"] == ticket1
            assert all_tickets["PROJ-2"] == ticket2

    def test_clear_cache(self):
        """Test clearing the cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            # Add some tickets
            ticket = {"key": "PROJ-1", "fields": {"summary": "Test"}}
            cache.put_ticket("PROJ-1", ticket)

            assert len(cache.get_cached_tickets()) == 1

            # Clear cache
            cache.clear_cache()

            assert len(cache.get_cached_tickets()) == 0
            assert not cache.tickets_file.exists()
            assert not cache.metadata_file.exists()

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = TicketCache(temp_dir)

            # Add a ticket
            ticket = {"key": "PROJ-1", "fields": {"summary": "Test"}}
            cache.put_ticket("PROJ-1", ticket)

            stats = cache.get_cache_stats()

            assert stats["total_tickets"] == 1
            assert stats["cache_dir"] == str(cache.cache_dir)
            assert stats["cache_size_bytes"] > 0

    def test_persistence_across_instances(self):
        """Test that cache persists across different instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # First instance
            cache1 = TicketCache(temp_dir)
            ticket = {"key": "PROJ-1", "fields": {"summary": "Test"}}
            cache1.put_ticket("PROJ-1", ticket)

            # Second instance
            cache2 = TicketCache(temp_dir)
            retrieved = cache2.get_ticket("PROJ-1")

            assert retrieved == ticket

    def test_corrupted_cache_files(self):
        """Test handling of corrupted cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir)

            # Create corrupted files
            (cache_dir / "tickets.json").write_text("invalid json")
            (cache_dir / "metadata.json").write_text("invalid json")

            # Should handle gracefully
            cache = TicketCache(temp_dir)
            assert len(cache.get_cached_tickets()) == 0
