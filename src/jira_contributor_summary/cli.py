"""Command-line interface for JIRA contributor summary tool."""

import sys
import typing
from pathlib import Path

import click

from .cache import TicketCache
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
    "--cache-dir",
    help="Directory to store cache files (default: uses appdirs)",
)
@click.option(
    "--issue-types",
    default="Feature,Issue,Bug",
    help="Comma-separated list of root issue types (default: Feature,Issue,Bug)",
)
@click.option(
    "--clear-cache",
    is_flag=True,
    help="Clear the cache before running",
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
    cache_dir: typing.Optional[str],
    issue_types: str,
    clear_cache: bool,
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
        # Parse issue types
        root_issue_types = [t.strip() for t in issue_types.split(",")]

        if verbose:
            click.echo(f"JIRA URL: {jira_url}")
            click.echo(f"Project: {project}")
            click.echo(f"Root issue types: {root_issue_types}")
            click.echo(f"Output file: {output}")
            click.echo(f"Cache directory: {cache_dir or 'default (appdirs)'}")

        # Initialize components
        click.echo("Initializing JIRA client...")
        jira_client = JiraClient(jira_url, token, email)

        click.echo("Setting up cache...")
        cache = TicketCache(cache_dir)

        if clear_cache:
            click.echo("Clearing cache...")
            cache.clear_cache()

        if verbose:
            stats = cache.get_cache_stats()
            click.echo(
                f"Cache stats: {stats['total_tickets']} tickets, "
                f"{stats['cache_size_bytes']} bytes"
            )

        # Build ticket hierarchy
        click.echo("Building ticket hierarchy...")
        hierarchy = TicketHierarchy(jira_client, cache)
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

        # Final stats
        if verbose:
            final_stats = cache.get_cache_stats()
            click.echo(
                f"Final cache stats: {final_stats['total_tickets']} tickets, "
                f"{final_stats['cache_size_bytes']} bytes"
            )

    except KeyboardInterrupt:
        click.echo("\\nOperation cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@click.command()
@click.option(
    "--cache-dir",
    help="Cache directory to inspect (default: uses appdirs)",
)
def cache_info(cache_dir: typing.Optional[str]) -> None:
    """Display information about the ticket cache."""
    try:
        cache = TicketCache(cache_dir)
        stats = cache.get_cache_stats()
        cached_tickets = cache.get_cached_tickets()

        click.echo(f"Cache Directory: {stats['cache_dir']}")
        click.echo(f"Total Tickets: {stats['total_tickets']}")
        click.echo(f"Cache Size: {stats['cache_size_bytes']} bytes")
        click.echo()

        if cached_tickets:
            click.echo("Cached Tickets:")
            for ticket_key in sorted(cached_tickets.keys()):
                ticket = cached_tickets[ticket_key]
                summary = ticket.get("fields", {}).get("summary", "No summary")
                updated = ticket.get("fields", {}).get("updated", "Unknown")
                click.echo(f"  {ticket_key}: {summary[:60]}... (updated: {updated})")
        else:
            click.echo("No tickets in cache")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option(
    "--cache-dir",
    help="Cache directory to clear (default: uses appdirs)",
)
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def clear_cache_cmd(cache_dir: typing.Optional[str]) -> None:
    """Clear the ticket cache."""
    try:
        cache = TicketCache(cache_dir)
        cache.clear_cache()
        click.echo("Cache cleared successfully")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Create a group for multiple commands
@click.group()
def cli() -> None:
    """JIRA Contributor Summary Tool."""
    pass


cli.add_command(main, name="generate")
cli.add_command(cache_info, name="cache-info")
cli.add_command(clear_cache_cmd, name="clear-cache")


if __name__ == "__main__":
    main()
