"""JIRA API client for fetching ticket data."""

import os
import typing
from datetime import datetime

import requests


class JiraClient:
    """Client for interacting with JIRA REST API."""

    def __init__(self, base_url: str, token: typing.Optional[str] = None):
        """Initialize JIRA client.

        Args:
            base_url: Base URL of the JIRA instance (e.g., https://company.atlassian.net)
            token: Bearer token for authentication. If None, uses JIRA_API_TOKEN env var.
        """
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("JIRA_API_TOKEN")
        if not self.token:
            raise ValueError(
                "JIRA token must be provided or set in JIRA_API_TOKEN environment variable"
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def get_ticket(self, ticket_key: str) -> typing.Dict[str, typing.Any]:
        """Fetch a single ticket by key.

        Args:
            ticket_key: JIRA ticket key (e.g., 'PROJ-123')

        Returns:
            Dictionary containing ticket data

        Raises:
            requests.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/rest/api/3/issue/{ticket_key}"
        params = {
            "expand": "names,schema",
            "fields": "summary,issuetype,status,assignee,customfield_*,subtasks,issuelinks,updated,created,priority,labels,components,fixVersions",
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        # Check if we got HTML instead of JSON (common auth failure symptom)
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            raise requests.HTTPError(
                f"Received HTML response instead of JSON. This usually indicates authentication failure. "
                f"Please check your JIRA credentials and URL. Response: {response.text[:200]}..."
            )

        try:
            return response.json()
        except ValueError as e:
            raise requests.HTTPError(
                f"Failed to parse JSON response from JIRA API. Response: {response.text[:200]}..."
            ) from e

    def search_tickets(
        self,
        project_key: str,
        issue_types: typing.Optional[typing.List[str]] = None,
        max_results: int = 1000,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Search for tickets in a project.

        Args:
            project_key: JIRA project key
            issue_types: List of issue types to filter by (e.g., ['Feature', 'Bug', 'Issue'])
            max_results: Maximum number of results to return

        Returns:
            List of ticket dictionaries

        Raises:
            requests.HTTPError: If the API request fails
        """
        jql_parts = [f"project = {project_key}"]

        if issue_types:
            types_str = ", ".join(f'"{t}"' for t in issue_types)
            jql_parts.append(f"issuetype in ({types_str})")

        jql = " AND ".join(jql_parts)

        url = f"{self.base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "expand": "names,schema",
            "fields": "summary,issuetype,status,assignee,customfield_*,subtasks,issuelinks,updated,created,priority,labels,components,fixVersions",
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        # Check if we got HTML instead of JSON (common auth failure symptom)
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            raise requests.HTTPError(
                f"Received HTML response instead of JSON. This usually indicates authentication failure. "
                f"Please check your JIRA credentials and URL. Response: {response.text[:200]}..."
            )

        try:
            data = response.json()
        except ValueError as e:
            raise requests.HTTPError(
                f"Failed to parse JSON response from JIRA API. Response: {response.text[:200]}..."
            ) from e

        return data.get("issues", [])

    def get_subtasks(
        self, ticket_key: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
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
            except requests.HTTPError:
                # Skip subtasks we can't access
                continue

        return full_subtasks

    def get_linked_issues(
        self, ticket_key: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
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
                    except requests.HTTPError:
                        # Skip issues we can't access
                        continue

        return linked_issues

    def get_ticket_updated_time(
        self, ticket_data: typing.Dict[str, typing.Any]
    ) -> datetime:
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
