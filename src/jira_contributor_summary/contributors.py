"""Logic for extracting contributors from JIRA tickets."""

import typing
from collections import defaultdict


class ContributorExtractor:
    """Extract and manage contributor information from JIRA tickets."""

    def __init__(self):
        """Initialize the contributor extractor."""
        self.contributor_cache: typing.Dict[str, typing.Set[str]] = defaultdict(set)

    def extract_contributors_from_ticket(
        self, ticket_data: typing.Dict[str, typing.Any]
    ) -> typing.Set[str]:
        """Extract all contributors from a single ticket.

        Args:
            ticket_data: JIRA ticket data dictionary

        Returns:
            Set of contributor full names
        """
        contributors = set()
        fields = ticket_data.get("fields", {})

        # Extract assignee
        assignee = fields.get("assignee")
        if assignee and assignee.get("displayName"):
            contributors.add(assignee["displayName"])

        # Look for additional assignees in custom fields
        # JIRA custom fields are typically named customfield_XXXXX
        for field_name, field_value in fields.items():
            if field_name.startswith("customfield_") and field_value:
                # Handle different types of custom field values
                if isinstance(field_value, list):
                    # Multiple assignees field
                    for item in field_value:
                        if isinstance(item, dict) and item.get("displayName"):
                            contributors.add(item["displayName"])
                elif isinstance(field_value, dict) and field_value.get("displayName"):
                    # Single assignee field
                    contributors.add(field_value["displayName"])

        # Look for contributors field (might be in different formats)
        contributors_field = fields.get("contributors")
        if contributors_field:
            if isinstance(contributors_field, list):
                for contributor in contributors_field:
                    if isinstance(contributor, dict) and contributor.get("displayName"):
                        contributors.add(contributor["displayName"])
            elif isinstance(contributors_field, dict) and contributors_field.get(
                "displayName"
            ):
                contributors.add(contributors_field["displayName"])

        # Also check for reporter as a potential contributor
        reporter = fields.get("reporter")
        if reporter and reporter.get("displayName"):
            contributors.add(reporter["displayName"])

        return contributors

    def get_all_contributors_for_ticket_hierarchy(
        self,
        ticket_key: str,
        all_tickets: typing.Dict[str, typing.Dict[str, typing.Any]],
        ticket_hierarchy: typing.Dict[str, typing.List[str]],
    ) -> typing.Set[str]:
        """Get all contributors for a ticket and its descendants.

        Args:
            ticket_key: Root ticket key
            all_tickets: Dictionary mapping ticket keys to ticket data
            ticket_hierarchy: Dictionary mapping parent keys to child keys

        Returns:
            Set of all contributor names for the ticket and its descendants
        """
        if ticket_key in self.contributor_cache:
            return self.contributor_cache[ticket_key].copy()

        all_contributors = set()

        # Get contributors from the current ticket
        if ticket_key in all_tickets:
            ticket_contributors = self.extract_contributors_from_ticket(
                all_tickets[ticket_key]
            )
            all_contributors.update(ticket_contributors)

        # Recursively get contributors from child tickets
        children = ticket_hierarchy.get(ticket_key, [])
        for child_key in children:
            child_contributors = self.get_all_contributors_for_ticket_hierarchy(
                child_key, all_tickets, ticket_hierarchy
            )
            all_contributors.update(child_contributors)

        # Cache the result
        self.contributor_cache[ticket_key] = all_contributors.copy()
        return all_contributors

    def get_contributor_summary(
        self,
        all_tickets: typing.Dict[str, typing.Dict[str, typing.Any]],
        ticket_hierarchy: typing.Dict[str, typing.List[str]],
    ) -> typing.Dict[str, typing.Set[str]]:
        """Get contributor summary for all tickets.

        Args:
            all_tickets: Dictionary mapping ticket keys to ticket data
            ticket_hierarchy: Dictionary mapping parent keys to child keys

        Returns:
            Dictionary mapping ticket keys to sets of contributor names
        """
        summary = {}

        for ticket_key in all_tickets:
            contributors = self.get_all_contributors_for_ticket_hierarchy(
                ticket_key, all_tickets, ticket_hierarchy
            )
            summary[ticket_key] = contributors

        return summary

    def clear_cache(self) -> None:
        """Clear the contributor cache."""
        self.contributor_cache.clear()

    def get_unique_contributors(
        self, all_tickets: typing.Dict[str, typing.Dict[str, typing.Any]]
    ) -> typing.Set[str]:
        """Get all unique contributors across all tickets.

        Args:
            all_tickets: Dictionary mapping ticket keys to ticket data

        Returns:
            Set of all unique contributor names
        """
        all_contributors = set()

        for ticket_data in all_tickets.values():
            ticket_contributors = self.extract_contributors_from_ticket(ticket_data)
            all_contributors.update(ticket_contributors)

        return all_contributors
