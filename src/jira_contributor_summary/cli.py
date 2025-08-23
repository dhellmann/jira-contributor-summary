"""Command-line interface for JIRA contributor summary tool."""

import logging
import sys
import typing
from pathlib import Path

import click

from .contributors import ContributorExtractor
from .hierarchy import TicketHierarchy
from .html_generator import HtmlGenerator
from .jira_client import JiraClient


@click.command()
@click.option(
    "--jira-url",
    required=True,
    help="Base URL of the JIRA instance (e.g., https://company.atlassian.net)",
)
@click.option(
    "--project",
    required=True,
    help="JIRA project key (e.g., PROJ)",
)
@click.option(
    "--output",
    default="jira-contributor-summary.html",
    help="Output HTML file path (default: jira-contributor-summary.html)",
)
@click.option(
    "--issue-types",
    default="Feature,Issue,Bug",
    help="Comma-separated list of root issue types (default: Feature,Issue,Bug)",
)
@click.option(
    "--token",
    help="JIRA API token (default: uses JIRA_API_TOKEN environment variable)",
)
@click.option(
    "--email",
    help="Email address for JIRA Cloud (default: uses JIRA_EMAIL environment variable)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def main(
    jira_url: str,
    project: str,
    output: str,
    issue_types: str,
    token: typing.Optional[str],
    email: typing.Optional[str],
    verbose: bool,
) -> None:
    """Generate HTML summaries of JIRA ticket contributors.

    This tool fetches JIRA tickets of specified types (Feature, Issue, Bug by default)
    and recursively collects information about their children. It then generates a
    styled HTML report showing the ticket hierarchy and all contributors for each
    ticket and its descendants.

    Authentication is handled via a JIRA API token, which should be provided either
    via the --token option or the JIRA_TOKEN environment variable.

    Examples:

        # Basic usage
        jira-contributor-summary --jira-url https://company.atlassian.net --project MYPROJ

        # Custom output file and cache directory
        jira-contributor-summary --jira-url https://company.atlassian.net --project MYPROJ \\
            --output /path/to/report.html --cache-dir /path/to/cache

        # Include only specific issue types
        jira-contributor-summary --jira-url https://company.atlassian.net --project MYPROJ \\
            --issue-types "Epic,Story,Task"
    """
    try:
        # Configure logging for debugging when verbose is enabled
        if verbose:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                stream=sys.stderr,
            )
            # Set logging level for our modules
            logging.getLogger("jira_contributor_summary").setLevel(logging.DEBUG)
            logging.getLogger("atlassian").setLevel(
                logging.INFO
            )  # Reduce noise from atlassian library
            logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

        # Parse issue types
        root_issue_types = [t.strip() for t in issue_types.split(",")]

        if verbose:
            click.echo(f"JIRA URL: {jira_url}")
            click.echo(f"Project: {project}")
            click.echo(f"Root issue types: {root_issue_types}")
            click.echo(f"Output file: {output}")

        # Initialize components
        click.echo("Initializing JIRA client...")
        jira_client = JiraClient(jira_url, token, email)

        # Build ticket hierarchy
        click.echo("Building ticket hierarchy...")
        hierarchy = TicketHierarchy(jira_client)
        hierarchy.build_hierarchy(project, root_issue_types)

        all_tickets = hierarchy.get_all_tickets()
        hierarchy_map = hierarchy.get_hierarchy_map()

        click.echo(f"Processed {len(all_tickets)} tickets total")

        # Extract contributors
        click.echo("Extracting contributors...")
        contributor_extractor = ContributorExtractor()
        contributor_summary = contributor_extractor.get_contributor_summary(
            all_tickets, hierarchy_map
        )

        unique_contributors = contributor_extractor.get_unique_contributors(all_tickets)
        click.echo(f"Found {len(unique_contributors)} unique contributors")

        if verbose:
            click.echo("Contributors:")
            for contributor in sorted(unique_contributors):
                click.echo(f"  - {contributor}")

        # Generate HTML output
        click.echo("Generating HTML report...")
        html_generator = HtmlGenerator(jira_url)
        display_data = hierarchy.get_hierarchy_for_display()

        html_generator.generate_html(display_data, contributor_summary, project, output)

        click.echo(f"Report generated successfully: {Path(output).absolute()}")

    except KeyboardInterrupt:
        click.echo("\\nOperation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
