"""Logic for building and managing JIRA ticket hierarchies."""

import logging
import typing
from collections import defaultdict

from .jira_client import JiraClient

logger = logging.getLogger(__name__)


class TicketHierarchy:
    """Build and manage hierarchical relationships between JIRA tickets."""

    def __init__(self, jira_client: JiraClient):
        """Initialize the ticket hierarchy builder.

        Args:
            jira_client: JIRA API client
        """
        self.jira_client = jira_client
        self.all_tickets: dict[str, dict[str, typing.Any]] = {}
        self.hierarchy: dict[str, list[str]] = defaultdict(list)
        self.root_tickets: list[str] = []

    def build_hierarchy(
        self,
        project_key: str,
        root_issue_types: list[str] | None = None,
    ) -> None:
        """Build the complete ticket hierarchy for a project.

        Only includes top-level tickets that have a resolution of "Unresolved".
        Child tickets are included regardless of their resolution status.

        Args:
            project_key: JIRA project key
            root_issue_types: Issue types to use as root tickets (default: Feature, Issue, Bug)
        """
        if root_issue_types is None:
            root_issue_types = ["Feature", "Issue", "Bug"]

        # First, get all root tickets that are unresolved
        logger.info(
            f"Fetching unresolved root tickets of types {root_issue_types} from project {project_key}..."
        )
        root_tickets = self.jira_client.search_tickets(
            project_key, root_issue_types, "Unresolved"
        )

        # Process each root ticket and build hierarchy
        for ticket in root_tickets:
            ticket_key = ticket["key"]
            self.root_tickets.append(ticket_key)
            self._process_ticket_recursive(ticket_key, ticket)

    def build_hierarchy_from_ticket(self, ticket_key: str) -> None:
        """Build the complete ticket hierarchy starting from a single ticket.

        This method fetches the specified ticket and recursively processes all its
        children to build the complete hierarchy.

        Args:
            ticket_key: JIRA ticket key to start from (e.g., 'PROJ-123')
        """
        logger.info(f"Fetching ticket {ticket_key} and building hierarchy...")

        try:
            # Fetch the starting ticket
            ticket_data = self.jira_client.get_ticket(ticket_key)

            # Add it as a root ticket and process recursively
            self.root_tickets.append(ticket_key)
            self._process_ticket_recursive(ticket_key, ticket_data)

        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_key}: {e}")
            raise

    def _process_ticket_recursive(
        self,
        ticket_key: str,
        ticket_data: dict[str, typing.Any] | None = None,
    ) -> None:
        """Recursively process a ticket and all its children.

        Args:
            ticket_key: JIRA ticket key
            ticket_data: Optional ticket data (if already fetched)
        """
        # Skip if already processed
        if ticket_key in self.all_tickets:
            logger.debug(f"Ticket {ticket_key} already processed")
            return

        logger.info(f"Processing ticket {ticket_key}")

        # Fetch ticket data if not provided
        if ticket_data is None:
            try:
                ticket_data = self.jira_client.get_ticket(ticket_key)
                logger.debug(f"Fetched {ticket_key}")
            except Exception as e:
                logger.error(f"Error fetching {ticket_key}: {e}")
                return

        # Store the ticket
        self.all_tickets[ticket_key] = ticket_data

        # Get child tickets (subtasks and linked issues)
        child_keys = self._get_child_ticket_keys(ticket_data)

        if child_keys:
            self.hierarchy[ticket_key] = child_keys
            logger.debug(
                f"Found {len(child_keys)} children for {ticket_key}: {child_keys}"
            )

            # Recursively process children
            for child_key in child_keys:
                self._process_ticket_recursive(child_key)

    def _get_child_ticket_keys(self, ticket_data: dict[str, typing.Any]) -> list[str]:
        """Find all child tickets by searching for tickets that reference this ticket as their parent.

        Args:
            ticket_data: JIRA ticket data

        Returns:
            List of child ticket keys
        """
        child_keys = []
        fields = ticket_data.get("fields", {})
        ticket_key = ticket_data.get("key")

        if not ticket_key:
            return child_keys

        # Get subtasks (direct children in JIRA)
        subtasks = fields.get("subtasks", [])
        for subtask in subtasks:
            child_keys.append(subtask["key"])

        # Based on the ticket type, search for tickets that have this ticket as their parent
        issue_type = fields.get("issuetype", {})
        issue_type_name = issue_type.get("name", "").lower() if issue_type else ""

        try:
            if "epic" in issue_type_name:
                # For Epics, search for tickets with Epic Link pointing to this epic
                epic_children = self._search_tickets_with_epic_link(ticket_key)
                child_keys.extend(epic_children)

            elif any(
                parent_type in issue_type_name
                for parent_type in ["feature", "initiative", "theme"]
            ):
                # For Features/Initiatives, search for tickets with Parent Link pointing to this ticket
                parent_children = self._search_tickets_with_parent_link(ticket_key)
                child_keys.extend(parent_children)

        except Exception as e:
            logger.error(f"Error searching for children of {ticket_key}: {e}")

        return child_keys

    def _search_tickets_with_epic_link(self, epic_key: str) -> list[str]:
        """Search for tickets that have their Epic Link pointing to the given epic.

        Args:
            epic_key: The epic ticket key to search for

        Returns:
            List of ticket keys that have this epic as their Epic Link
        """
        child_keys = []

        try:
            # Search for tickets where the Epic Link field equals our epic key
            jql = f'"Epic Link" = "{epic_key}"'
            results = self.jira_client.jira.jql(jql=jql, limit=1000)

            if results and "issues" in results:
                for issue in results["issues"]:
                    child_key = issue.get("key")
                    if child_key and child_key not in child_keys:
                        child_keys.append(child_key)
                        logger.debug(
                            f"Found Epic Link child: {epic_key} -> {child_key}"
                        )

        except Exception as e:
            logger.error(f"Error searching Epic Link for {epic_key}: {e}")

        return child_keys

    def _search_tickets_with_parent_link(self, parent_key: str) -> list[str]:
        """Search for tickets that have their Parent Link pointing to the given parent.

        Args:
            parent_key: The parent ticket key to search for

        Returns:
            List of ticket keys that have this ticket as their Parent Link
        """
        child_keys = []

        try:
            # Search for tickets where the Parent Link field equals our parent key
            jql = f'"Parent Link" = "{parent_key}"'
            results = self.jira_client.jira.jql(jql=jql, limit=1000)

            if results and "issues" in results:
                for issue in results["issues"]:
                    child_key = issue.get("key")
                    if child_key and child_key not in child_keys:
                        child_keys.append(child_key)
                        logger.debug(f"Found {parent_key} -> {child_key}")

        except Exception as e:
            logger.error(f"Error searching Parent Link for {parent_key}: {e}")

        return child_keys

    def get_sorted_tickets_by_rank(self) -> list[str]:
        """Get all tickets sorted by their rank in ascending order.

        Returns:
            List of ticket keys sorted by rank
        """

        def get_rank(ticket_key: str) -> float:
            """Extract rank from ticket data."""
            ticket = self.all_tickets.get(ticket_key, {})
            fields = ticket.get("fields", {})

            # Get rank from the "Rank" field
            rank_value = fields.get("Rank")
            if isinstance(rank_value, (int, float)):
                return float(rank_value)
            elif isinstance(rank_value, str) and rank_value.replace(".", "").isdigit():
                return float(rank_value)

            # This should not happen as all tickets have a rank
            return 0.0

        return sorted(self.all_tickets.keys(), key=get_rank)

    def get_hierarchy_for_display(self) -> list[dict[str, typing.Any]]:
        """Get hierarchy organized for display purposes.

        Returns:
            List of ticket display data with hierarchy information
        """
        display_data = []
        processed = set()

        # Find all true root tickets (tickets that have no parent in our hierarchy)
        true_roots = self._find_true_root_tickets()

        # Sort root tickets by rank
        sorted_roots = [
            key for key in self.get_sorted_tickets_by_rank() if key in true_roots
        ]

        for root_key in sorted_roots:
            if root_key not in processed:
                self._add_ticket_to_display(root_key, display_data, processed, level=0)

        return display_data

    def _find_true_root_tickets(self) -> set[str]:
        """Find all tickets that are true roots (have no parent in our collected tickets).

        Returns:
            Set of ticket keys that are at the top of their hierarchies
        """
        # Start with all tickets
        all_ticket_keys = set(self.all_tickets.keys())

        # Remove tickets that have a parent in our hierarchy
        tickets_with_parents = set()
        for parent_key, children in self.hierarchy.items():
            if parent_key in all_ticket_keys:  # Only consider parents we have data for
                tickets_with_parents.update(children)

        # True roots are tickets that exist but are not children of any other ticket
        true_roots = all_ticket_keys - tickets_with_parents

        logger.debug(f"Found {len(true_roots)} true root tickets: {sorted(true_roots)}")
        return true_roots

    def _add_ticket_to_display(
        self,
        ticket_key: str,
        display_data: list[dict[str, typing.Any]],
        processed: set[str],
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

    def get_all_tickets(self) -> dict[str, dict[str, typing.Any]]:
        """Get all processed tickets.

        Returns:
            Dictionary mapping ticket keys to ticket data
        """
        return self.all_tickets.copy()

    def get_hierarchy_map(self) -> dict[str, list[str]]:
        """Get the hierarchy mapping.

        Returns:
            Dictionary mapping parent keys to lists of child keys
        """
        return dict(self.hierarchy)
