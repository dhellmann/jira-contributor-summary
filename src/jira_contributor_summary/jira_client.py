"""JIRA API client for fetching ticket data."""

import logging
import os
from datetime import datetime
from typing import Any

from atlassian import Jira

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for interacting with JIRA REST API."""

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        email: str | None = None,
    ):
        """Initialize JIRA client.

        Args:
            base_url: Base URL of the JIRA instance (e.g., https://company.atlassian.net)
            token: API token for authentication. If None, uses JIRA_API_TOKEN env var.
            email: Email address for JIRA Cloud. If None, uses JIRA_EMAIL env var.
                  Required for JIRA Cloud, optional for JIRA Server/DC.
        """
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("JIRA_API_TOKEN")
        self.email = email or os.getenv("JIRA_EMAIL")

        if not self.token:
            raise ValueError(
                "JIRA token must be provided or set in JIRA_API_TOKEN environment variable"
            )

        # Initialize the Jira client from atlassian-python-api
        if self.email:
            # JIRA Cloud with email + API token
            self.jira = Jira(
                url=self.base_url, username=self.email, password=self.token, cloud=True
            )
        else:
            # JIRA Server/DC with token
            self.jira = Jira(url=self.base_url, token=self.token, cloud=False)

    def get_ticket(self, ticket_key: str) -> dict[str, Any]:
        """Fetch a single ticket by key.

        Args:
            ticket_key: JIRA ticket key (e.g., 'PROJ-123')

        Returns:
            Dictionary containing ticket data

        Raises:
            Exception: If the API request fails
        """
        try:
            # Use the atlassian-python-api to get the issue
            issue = self.jira.issue(
                key=ticket_key,
                expand="names,schema",
                fields="summary,issuetype,status,assignee,customfield_*,subtasks,issuelinks,updated,created,priority,labels,components,fixVersions",
            )
            return issue
        except Exception as e:
            raise Exception(
                f"Failed to fetch ticket {ticket_key}. Please check your JIRA credentials and URL. Error: {e}"
            ) from e

    def search_tickets(
        self,
        project_key: str,
        issue_types: list[str] | None = None,
        resolution: str | None = None,
        max_results: int = 1000,
    ) -> list[dict[str, Any]]:
        """Search for tickets in a project.

        Args:
            project_key: JIRA project key
            issue_types: List of issue types to filter by (e.g., ['Feature', 'Bug', 'Issue'])
            resolution: Resolution to filter by (e.g., 'Unresolved', 'Done', etc.)
            max_results: Maximum number of results to return

        Returns:
            List of ticket dictionaries

        Raises:
            Exception: If the API request fails
        """
        try:
            jql_parts = [f"project = {project_key}"]

            if issue_types:
                types_str = ", ".join(f'"{t}"' for t in issue_types)
                jql_parts.append(f"issuetype in ({types_str})")

            if resolution:
                if resolution.lower() == "unresolved":
                    jql_parts.append("resolution = Unresolved")
                else:
                    jql_parts.append(f'resolution = "{resolution}"')

            jql = " AND ".join(jql_parts)
            jql += " ORDER BY Rank ASC"

            # Use the atlassian-python-api to search for issues
            logger.debug(f"searching for tickets with jql: {jql}")
            issues = self.jira.jql(
                jql=jql,
                limit=max_results,
                expand="names,schema",
                fields="summary,issuetype,status,assignee,customfield_*,subtasks,issuelinks,updated,created,priority,labels,components,fixVersions",
            )

            return issues.get("issues", [])
        except Exception as e:
            raise Exception(
                f"Failed to search tickets in project {project_key}. Please check your JIRA credentials and URL. Error: {e}"
            ) from e

    def get_subtasks(self, ticket_key: str) -> list[dict[str, Any]]:
        """Get all subtasks for a given ticket.

        Args:
            ticket_key: Parent ticket key

        Returns:
            List of subtask dictionaries
        """
        ticket = self.get_ticket(ticket_key)
        subtasks = ticket.get("fields", {}).get("subtasks", [])

        # Fetch full details for each subtask
        full_subtasks = []
        for subtask in subtasks:
            try:
                full_subtask = self.get_ticket(subtask["key"])
                full_subtasks.append(full_subtask)
            except Exception:
                # Skip subtasks we can't access
                continue

        return full_subtasks

    def get_linked_issues(self, ticket_key: str) -> list[dict[str, Any]]:
        """Get all linked issues for a given ticket.

        Args:
            ticket_key: Ticket key to get links for

        Returns:
            List of linked issue dictionaries
        """
        ticket = self.get_ticket(ticket_key)
        issue_links = ticket.get("fields", {}).get("issuelinks", [])

        linked_issues = []
        for link in issue_links:
            # Check both inward and outward links
            for direction in ["inwardIssue", "outwardIssue"]:
                if direction in link:
                    try:
                        linked_issue = self.get_ticket(link[direction]["key"])
                        linked_issues.append(linked_issue)
                    except Exception:
                        # Skip issues we can't access
                        continue

        return linked_issues

    def get_ticket_updated_time(self, ticket_data: dict[str, Any]) -> datetime:
        """Extract the updated timestamp from ticket data.

        Args:
            ticket_data: Ticket data dictionary from JIRA API

        Returns:
            datetime object representing when the ticket was last updated
        """
        updated_str = ticket_data.get("fields", {}).get("updated")
        if updated_str:
            # Parse JIRA datetime format (ISO 8601)
            return datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        return datetime.min
