"""Logic for building and managing JIRA ticket hierarchies."""

import typing
from collections import defaultdict

from .jira_client import JiraClient


class TicketHierarchy:
    """Build and manage hierarchical relationships between JIRA tickets."""

    def __init__(self, jira_client: JiraClient):
        """Initialize the ticket hierarchy builder.

        Args:
            jira_client: JIRA API client
        """
        self.jira_client = jira_client
        self.all_tickets: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        self.hierarchy: typing.Dict[str, typing.List[str]] = defaultdict(list)
        self.root_tickets: typing.List[str] = []

    def build_hierarchy(
        self,
        project_key: str,
        root_issue_types: typing.Optional[typing.List[str]] = None,
    ) -> None:
        """Build the complete ticket hierarchy for a project.

        Args:
            project_key: JIRA project key
            root_issue_types: Issue types to use as root tickets (default: Feature, Issue, Bug)
        """
        if root_issue_types is None:
            root_issue_types = ["Feature", "Issue", "Bug"]

        # First, get all root tickets
        print(
            f"Fetching root tickets of types {root_issue_types} from project {project_key}..."
        )
        root_tickets = self.jira_client.search_tickets(project_key, root_issue_types)

        # Process each root ticket and build hierarchy
        for ticket in root_tickets:
            ticket_key = ticket["key"]
            self.root_tickets.append(ticket_key)
            self._process_ticket_recursive(ticket_key, ticket)

    def _process_ticket_recursive(
        self,
        ticket_key: str,
        ticket_data: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        """Recursively process a ticket and all its children.

        Args:
            ticket_key: JIRA ticket key
            ticket_data: Optional ticket data (if already fetched)
        """
        # Skip if already processed
        if ticket_key in self.all_tickets:
            return

        # Fetch ticket data if not provided
        if ticket_data is None:
            try:
                ticket_data = self.jira_client.get_ticket(ticket_key)
                print(f"Fetched {ticket_key}")
            except Exception as e:
                print(f"Error fetching {ticket_key}: {e}")
                return

        # Store the ticket
        self.all_tickets[ticket_key] = ticket_data

        # Get child tickets (subtasks and linked issues)
        child_keys = self._get_child_ticket_keys(ticket_data)

        if child_keys:
            self.hierarchy[ticket_key] = child_keys
            print(f"Found {len(child_keys)} children for {ticket_key}: {child_keys}")

            # Recursively process children
            for child_key in child_keys:
                self._process_ticket_recursive(child_key)

    def _get_child_ticket_keys(
        self, ticket_data: typing.Dict[str, typing.Any]
    ) -> typing.List[str]:
        """Extract child ticket keys from ticket data.

        Args:
            ticket_data: JIRA ticket data

        Returns:
            List of child ticket keys
        """
        child_keys = []
        fields = ticket_data.get("fields", {})

        # Get subtasks
        subtasks = fields.get("subtasks", [])
        for subtask in subtasks:
            child_keys.append(subtask["key"])

        # Get linked issues that represent parent-child relationships
        issue_links = fields.get("issuelinks", [])
        for link in issue_links:
            link_type = link.get("type", {})
            link_name = link_type.get("name", "").lower()

            # Look for common parent-child link types
            if any(
                rel in link_name
                for rel in ["blocks", "epic", "parent", "child", "subtask"]
            ):
                # Check outward links (this ticket blocks/contains others)
                if "outwardIssue" in link:
                    child_keys.append(link["outwardIssue"]["key"])

        return child_keys

    def get_sorted_tickets_by_rank(self) -> typing.List[str]:
        """Get all tickets sorted by their rank in ascending order.

        Returns:
            List of ticket keys sorted by rank
        """

        def get_rank(ticket_key: str) -> float:
            """Extract rank from ticket data."""
            ticket = self.all_tickets.get(ticket_key, {})
            fields = ticket.get("fields", {})

            # Look for rank in various possible fields
            rank_fields = [
                "rank",
                "priority",
                "customfield_10020",
                "customfield_10021",
            ]  # Common rank field IDs

            for field in rank_fields:
                rank_value = fields.get(field)
                if rank_value is not None:
                    if isinstance(rank_value, (int, float)):
                        return float(rank_value)
                    elif (
                        isinstance(rank_value, str)
                        and rank_value.replace(".", "").isdigit()
                    ):
                        return float(rank_value)
                    elif isinstance(rank_value, dict) and "id" in rank_value:
                        # Priority object with numeric ID
                        try:
                            return float(rank_value["id"])
                        except (ValueError, TypeError):
                            pass

            # Fallback: use creation date as a sort key
            created = fields.get("created", "")
            if created:
                return hash(created) % 1000000  # Convert to numeric for sorting

            return float("inf")  # Put tickets without rank at the end

        return sorted(self.all_tickets.keys(), key=get_rank)

    def get_hierarchy_for_display(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """Get hierarchy organized for display purposes.

        Returns:
            List of ticket display data with hierarchy information
        """
        display_data = []
        processed = set()

        # Sort root tickets by rank
        sorted_roots = [
            key for key in self.get_sorted_tickets_by_rank() if key in self.root_tickets
        ]

        for root_key in sorted_roots:
            if root_key not in processed:
                self._add_ticket_to_display(root_key, display_data, processed, level=0)

        return display_data

    def _add_ticket_to_display(
        self,
        ticket_key: str,
        display_data: typing.List[typing.Dict[str, typing.Any]],
        processed: typing.Set[str],
        level: int,
    ) -> None:
        """Recursively add ticket and children to display data.

        Args:
            ticket_key: Ticket key to add
            display_data: List to append display data to
            processed: Set of already processed ticket keys
            level: Hierarchy level (0 = root)
        """
        if ticket_key in processed:
            return

        processed.add(ticket_key)
        ticket_data = self.all_tickets.get(ticket_key, {})
        fields = ticket_data.get("fields", {})

        display_item = {
            "key": ticket_key,
            "summary": fields.get("summary", ""),
            "level": level,
            "ticket_data": ticket_data,
        }
        display_data.append(display_item)

        # Add children sorted by rank
        children = self.hierarchy.get(ticket_key, [])
        sorted_children = [
            key for key in self.get_sorted_tickets_by_rank() if key in children
        ]

        for child_key in sorted_children:
            self._add_ticket_to_display(child_key, display_data, processed, level + 1)

    def get_all_tickets(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        """Get all processed tickets.

        Returns:
            Dictionary mapping ticket keys to ticket data
        """
        return self.all_tickets.copy()

    def get_hierarchy_map(self) -> typing.Dict[str, typing.List[str]]:
        """Get the hierarchy mapping.

        Returns:
            Dictionary mapping parent keys to lists of child keys
        """
        return dict(self.hierarchy)
