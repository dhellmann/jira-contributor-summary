# JIRA Contributor Summary

A Python tool that generates HTML summaries of JIRA ticket contributors by analyzing ticket hierarchies and extracting contributor information from assignees, additional assignees, and contributors fields.

## Features

- **Hierarchical Analysis**: Recursively processes JIRA tickets starting from root types (Feature, Issue, Bug) and traverses their children
- **Smart Caching**: Caches ticket data locally to avoid redundant API calls, only updating when tickets have been modified
- **Contributor Extraction**: Identifies contributors from multiple fields including assignee, reporter, custom fields, and contributors
- **Beautiful HTML Output**: Generates styled, responsive HTML reports with ticket hierarchy and contributor summaries
- **Flexible Configuration**: Supports custom JIRA instances, projects, issue types, and output locations

## Installation

### From Source

```bash
git clone <repository-url>
cd jira-contributor-summary
pip install -e .
```

### Development Installation

```bash
git clone <repository-url>
cd jira-contributor-summary
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

The tool provides a command-line interface with several options:

```bash
# Basic usage
jira-contributor-summary generate \
    --jira-url https://your-company.atlassian.net \
    --project MYPROJ

# With custom options
jira-contributor-summary generate \
    --jira-url https://your-company.atlassian.net \
    --project MYPROJ \
    --output /path/to/report.html \
    --cache-dir /path/to/cache \
    --issue-types "Epic,Story,Task" \
    --verbose

# Clear cache
jira-contributor-summary clear-cache

# View cache information
jira-contributor-summary cache-info
```

### Authentication

Set your JIRA API token as an environment variable:

```bash
export JIRA_TOKEN="your-jira-api-token"
```

Alternatively, you can pass it directly:

```bash
jira-contributor-summary generate --token "your-token" --jira-url ... --project ...
```

### Programmatic Usage

```python
from jira_contributor_summary import JiraClient, TicketCache, TicketHierarchy, ContributorExtractor, HtmlGenerator

# Initialize components
jira_client = JiraClient("https://your-company.atlassian.net", token)
cache = TicketCache()
hierarchy = TicketHierarchy(jira_client, cache)

# Build hierarchy and extract contributors
hierarchy.build_hierarchy("PROJ", ["Feature", "Issue", "Bug"])
all_tickets = hierarchy.get_all_tickets()
hierarchy_map = hierarchy.get_hierarchy_map()

contributor_extractor = ContributorExtractor()
contributor_summary = contributor_extractor.get_contributor_summary(all_tickets, hierarchy_map)

# Generate HTML report
html_generator = HtmlGenerator("https://your-company.atlassian.net")
display_data = hierarchy.get_hierarchy_for_display()
html_generator.generate_html(display_data, contributor_summary, "PROJ", "report.html")
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--jira-url` | Base URL of your JIRA instance | Required |
| `--project` | JIRA project key | Required |
| `--output` | Output HTML file path | `jira-contributor-summary.html` |
| `--cache-dir` | Cache directory | Uses `appdirs` default |
| `--issue-types` | Comma-separated root issue types | `Feature,Issue,Bug` |
| `--token` | JIRA API token | Uses `JIRA_TOKEN` env var |
| `--clear-cache` | Clear cache before running | False |
| `--verbose` | Enable verbose output | False |

## Development

### Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
hatch run test

# Run linting
hatch run lint

# Format code
hatch run format

# Run all checks
hatch run check
```

### Project Structure

```
src/jira_contributor_summary/
├── __init__.py          # Package initialization
├── cli.py              # Command-line interface
├── jira_client.py      # JIRA API client
├── cache.py            # Ticket caching system
├── hierarchy.py        # Ticket hierarchy building
├── contributors.py     # Contributor extraction
└── html_generator.py   # HTML report generation

tests/
├── test_cache.py       # Cache functionality tests
└── test_contributors.py # Contributor extraction tests
```

## How It Works

1. **Authentication**: Uses JIRA API bearer token for authentication
2. **Root Ticket Discovery**: Searches for tickets of specified types (Feature, Issue, Bug by default)
3. **Hierarchy Traversal**: Recursively follows subtasks and linked issues to build complete hierarchy
4. **Caching**: Stores ticket data locally, only refetching when tickets have been updated
5. **Contributor Extraction**: Analyzes multiple fields to identify all contributors
6. **HTML Generation**: Creates a styled report showing hierarchy and contributor summaries

## Output

The generated HTML report includes:

- **Project Overview**: Summary statistics and generation timestamp
- **Hierarchical Display**: Tickets organized by hierarchy with visual indentation
- **Contributor Lists**: All contributors for each ticket and its descendants
- **Interactive Links**: Direct links to JIRA tickets
- **Responsive Design**: Works well on desktop and mobile devices

## Requirements

- Python 3.8+
- JIRA API access with appropriate permissions
- Dependencies: `click`, `requests`, `appdirs`, `jinja2`

## License

MIT License - see LICENSE file for details.
