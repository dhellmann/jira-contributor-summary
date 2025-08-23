#!/usr/bin/env python3
"""Example usage of the JIRA contributor summary tool."""

import os
import sys

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from jira_contributor_summary.cache import TicketCache
from jira_contributor_summary.contributors import ContributorExtractor
from jira_contributor_summary.hierarchy import TicketHierarchy
from jira_contributor_summary.html_generator import HtmlGenerator
from jira_contributor_summary.jira_client import JiraClient


def main():
    """Example of how to use the JIRA contributor summary programmatically."""
    # Configuration
    jira_url = "https://your-company.atlassian.net"
    project_key = "PROJ"
    token = os.getenv("JIRA_TOKEN")

    if not token:
        print("Please set the JIRA_TOKEN environment variable")
        return 1

    try:
        # Initialize components
        print("Initializing JIRA client...")
        jira_client = JiraClient(jira_url, token)

        print("Setting up cache...")
        cache = TicketCache()

        # Build ticket hierarchy
        print("Building ticket hierarchy...")
        hierarchy = TicketHierarchy(jira_client, cache)
        hierarchy.build_hierarchy(project_key, ["Feature", "Issue", "Bug"])

        all_tickets = hierarchy.get_all_tickets()
        hierarchy_map = hierarchy.get_hierarchy_map()

        print(f"Processed {len(all_tickets)} tickets total")

        # Extract contributors
        print("Extracting contributors...")
        contributor_extractor = ContributorExtractor()
        contributor_summary = contributor_extractor.get_contributor_summary(
            all_tickets, hierarchy_map
        )

        unique_contributors = contributor_extractor.get_unique_contributors(all_tickets)
        print(f"Found {len(unique_contributors)} unique contributors")

        # Generate HTML output
        print("Generating HTML report...")
        html_generator = HtmlGenerator(jira_url)
        display_data = hierarchy.get_hierarchy_for_display()

        html_generator.generate_html(
            display_data, contributor_summary, project_key, "example-report.html"
        )

        print("Report generated successfully: example-report.html")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
