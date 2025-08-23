"""Caching system for JIRA ticket data."""

import json
import typing
from datetime import datetime
from pathlib import Path

import appdirs


class TicketCache:
    """Cache for storing JIRA ticket data to avoid redundant API calls."""

    def __init__(self, cache_dir: typing.Optional[str] = None):
        """Initialize the ticket cache.

        Args:
            cache_dir: Directory to store cache files. If None, uses appdirs default.
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(appdirs.user_cache_dir("jira-contributor-summary"))

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tickets_file = self.cache_dir / "tickets.json"
        self.metadata_file = self.cache_dir / "metadata.json"

        self._tickets: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        self._metadata: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached data from disk."""
        try:
            if self.tickets_file.exists():
                with open(self.tickets_file, encoding="utf-8") as f:
                    self._tickets = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._tickets = {}

        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, encoding="utf-8") as f:
                    self._metadata = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._metadata = {}

    def _save_cache(self) -> None:
        """Save cached data to disk."""
        try:
            with open(self.tickets_file, "w", encoding="utf-8") as f:
                json.dump(self._tickets, f, indent=2, default=str)

            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except OSError as e:
            print(f"Warning: Failed to save cache: {e}")

    def get_ticket(
        self, ticket_key: str
    ) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """Get a ticket from cache.

        Args:
            ticket_key: JIRA ticket key

        Returns:
            Cached ticket data or None if not found
        """
        return self._tickets.get(ticket_key)

    def put_ticket(
        self, ticket_key: str, ticket_data: typing.Dict[str, typing.Any]
    ) -> None:
        """Store a ticket in cache.

        Args:
            ticket_key: JIRA ticket key
            ticket_data: Ticket data from JIRA API
        """
        self._tickets[ticket_key] = ticket_data

        # Store metadata about when this ticket was cached
        updated_str = ticket_data.get("fields", {}).get("updated")
        if updated_str:
            self._metadata[ticket_key] = {
                "cached_at": datetime.now().isoformat(),
                "last_updated": updated_str,
            }

        self._save_cache()

    def is_ticket_stale(self, ticket_key: str, current_updated: datetime) -> bool:
        """Check if a cached ticket is stale compared to the current version.

        Args:
            ticket_key: JIRA ticket key
            current_updated: Current updated timestamp from JIRA

        Returns:
            True if the cached ticket is stale or doesn't exist
        """
        if ticket_key not in self._tickets or ticket_key not in self._metadata:
            return True

        cached_updated_str = self._metadata[ticket_key].get("last_updated")
        if not cached_updated_str:
            return True

        try:
            cached_updated = datetime.fromisoformat(
                cached_updated_str.replace("Z", "+00:00")
            )
            return current_updated > cached_updated
        except (ValueError, TypeError):
            return True

    def get_cached_tickets(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        """Get all cached tickets.

        Returns:
            Dictionary mapping ticket keys to ticket data
        """
        return self._tickets.copy()

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._tickets.clear()
        self._metadata.clear()

        try:
            if self.tickets_file.exists():
                self.tickets_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
        except OSError as e:
            print(f"Warning: Failed to clear cache files: {e}")

    def get_cache_stats(self) -> typing.Dict[str, typing.Any]:
        """Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_tickets": len(self._tickets),
            "cache_dir": str(self.cache_dir),
            "cache_size_bytes": sum(
                f.stat().st_size
                for f in [self.tickets_file, self.metadata_file]
                if f.exists()
            ),
        }
