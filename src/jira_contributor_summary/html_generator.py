"""HTML output generation for JIRA contributor summaries."""

import typing
from datetime import datetime
from pathlib import Path

from jinja2 import Template


class HtmlGenerator:
    """Generate styled HTML output for JIRA ticket contributor summaries."""

    def __init__(self, jira_base_url: str):
        """Initialize the HTML generator.

        Args:
            jira_base_url: Base URL of the JIRA instance for creating ticket links
        """
        self.jira_base_url = jira_base_url.rstrip("/")

    def generate_html(
        self,
        display_data: typing.List[typing.Dict[str, typing.Any]],
        contributor_summary: typing.Dict[str, typing.Set[str]],
        project_key: str,
        output_file: str = "jira-contributor-summary.html",
    ) -> None:
        """Generate HTML output file.

        Args:
            display_data: List of ticket display data with hierarchy
            contributor_summary: Dictionary mapping ticket keys to contributor sets
            project_key: JIRA project key
            output_file: Output file path
        """
        # Prepare data for template
        tickets_list = []
        contributors_data = self._generate_contributors_data(
            display_data, contributor_summary
        )

        template_data = {
            "project_key": project_key,
            "jira_base_url": self.jira_base_url,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tickets": tickets_list,
            "contributors": contributors_data,
        }

        for item in display_data:
            ticket_key = item["key"]
            contributors = contributor_summary.get(ticket_key, set())

            # Extract issue type and status from ticket data
            ticket_data = item.get("ticket_data", {})
            fields = ticket_data.get("fields", {})
            issue_type = fields.get("issuetype", {})
            issue_type_name = (
                issue_type.get("name", "Unknown") if issue_type else "Unknown"
            )

            status = fields.get("status", {})
            status_name = status.get("name", "Unknown") if status else "Unknown"
            status_class = self._get_status_css_class(status_name)

            ticket_info = {
                "key": ticket_key,
                "summary": item["summary"],
                "level": item["level"],
                "url": f"{self.jira_base_url}/browse/{ticket_key}",
                "contributors": sorted(contributors),
                "contributor_count": len(contributors),
                "issue_type": issue_type_name,
                "status": status_name,
                "status_class": status_class,
            }
            tickets_list.append(ticket_info)

        # Generate HTML
        html_content = self._render_template(template_data)

        # Write to file
        output_path = Path(output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"HTML report generated: {output_path.absolute()}")

    def _generate_contributors_data(
        self,
        display_data: typing.List[typing.Dict[str, typing.Any]],
        contributor_summary: typing.Dict[str, typing.Set[str]],
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Generate contributors view data.

        Args:
            display_data: List of ticket display data with hierarchy
            contributor_summary: Dictionary mapping ticket keys to contributor sets

        Returns:
            List of contributor data for the contributors view
        """
        # Build a mapping of contributors to their top-level tickets
        contributor_tickets = {}

        for item in display_data:
            ticket_key = item["key"]
            contributors = contributor_summary.get(ticket_key, set())

            # Only consider top-level tickets (level 0)
            if item["level"] == 0:
                for contributor in contributors:
                    if contributor not in contributor_tickets:
                        contributor_tickets[contributor] = []

                    contributor_tickets[contributor].append(
                        {
                            "key": ticket_key,
                            "summary": item["summary"],
                            "url": f"{self.jira_base_url}/browse/{ticket_key}",
                        }
                    )

        # Convert to sorted list format
        contributors_list = []
        for contributor in sorted(contributor_tickets.keys()):
            tickets = contributor_tickets[contributor]
            contributors_list.append(
                {
                    "name": contributor,
                    "ticket_count": len(tickets),
                    "tickets": sorted(tickets, key=lambda x: x["key"]),
                }
            )

        return contributors_list

    def _get_status_css_class(self, status_name: str) -> str:
        """Get CSS class for status based on status name.

        Args:
            status_name: The JIRA status name

        Returns:
            CSS class name for styling the status
        """
        status_lower = status_name.lower()

        # Map common JIRA status names to CSS classes
        if any(
            done_status in status_lower
            for done_status in ["done", "closed", "resolved", "complete"]
        ):
            return "done"
        elif any(
            progress_status in status_lower
            for progress_status in [
                "in progress",
                "in-progress",
                "development",
                "review",
            ]
        ):
            return "in-progress"
        elif any(
            todo_status in status_lower
            for todo_status in ["to do", "to-do", "open", "new", "backlog"]
        ):
            return "to-do"
        else:
            return ""  # Default styling

    def _render_template(self, data: typing.Dict[str, typing.Any]) -> str:
        """Render the HTML template with data.

        Args:
            data: Template data dictionary

        Returns:
            Rendered HTML string
        """
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JIRA Contributor Summary - {{ project_key }}</title>
    <link rel="stylesheet" href="https://unpkg.com/@patternfly/patternfly/patternfly.css">
    <style>
        /* Custom overrides for PatternFly */
        .custom-header {
            background: linear-gradient(135deg, #e57373 0%, #ad1457 100%);
        }

        .custom-stat-card.pf-m-selectable.pf-m-selected {
            border-color: #d32f2f;
            background-color: #ffebee;
        }

        .custom-stat-card.pf-m-selectable.pf-m-selected .pf-c-card__title {
            color: #c62828;
        }

        .custom-ticket-key {
            background-color: #e57373;
        }

        .custom-ticket-key:hover {
            background-color: #d32f2f;
        }
    </style>
</head>
<body class="pf-c-page">
    <div class="pf-c-page__main">
        <section class="pf-c-page__main-section pf-m-light">
            <div class="pf-c-content">
                <div class="pf-c-card custom-header">
                    <div class="pf-c-card__body">
                        <h1 class="pf-c-title pf-m-2xl" style="color: white; margin-bottom: 0.5rem;">JIRA Contributor Summary</h1>
                        <p style="color: rgba(255,255,255,0.9); margin: 0;">Project: {{ project_key }} | Generated: {{ generated_at }}</p>
                    </div>
                </div>
            </div>
        </section>

        <section class="pf-c-page__main-section">
            <div class="pf-l-gallery pf-m-gutter" style="--pf-l-gallery--GridTemplateColumns--min: 180px;">
                <div class="pf-c-card pf-m-selectable custom-stat-card pf-m-selected" id="tickets-card" onclick="showTicketsView()">
                    <div class="pf-c-card__body pf-m-no-fill">
                        <div class="pf-c-card__title pf-m-lg">{{ tickets|length }}</div>
                        <small class="pf-c-content">Total Tickets</small>
                    </div>
                </div>
                <div class="pf-c-card pf-m-selectable custom-stat-card" id="root-tickets-card" onclick="showRootTicketsView()">
                    <div class="pf-c-card__body pf-m-no-fill">
                        <div class="pf-c-card__title pf-m-lg">{{ tickets|selectattr('level', 'equalto', 0)|list|length }}</div>
                        <small class="pf-c-content">Root Tickets</small>
                    </div>
                </div>
                <div class="pf-c-card pf-m-selectable custom-stat-card" id="contributors-card" onclick="showContributorsView()">
                    <div class="pf-c-card__body pf-m-no-fill">
                        <div class="pf-c-card__title pf-m-lg">{{ contributors|length }}</div>
                        <small class="pf-c-content">Unique Contributors</small>
                    </div>
                </div>
            </div>
        </section>

        <section class="pf-c-page__main-section">
            <div class="pf-c-card tickets-container">
                <div class="pf-c-card__body">
                    {% for ticket in tickets %}
                    <div class="pf-c-data-list__item" style="padding: 0.75rem; {% if ticket.level > 0 %}margin-left: {{ ticket.level * 1.5 }}rem; border-left: 3px solid #06c;{% endif %}">
                        <div class="pf-c-data-list__item-content">
                            <div class="pf-c-data-list__item-row">
                                <div class="pf-c-data-list__item-control" style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                                    <a href="{{ ticket.url }}" class="pf-c-button pf-m-primary pf-m-small custom-ticket-key" target="_blank">{{ ticket.key }}</a>
                                    <span class="pf-c-content" style="flex: 1;">{{ ticket.summary }}</span>
                                    <span class="pf-c-label pf-m-outline">{{ ticket.issue_type }}</span>
                                    <span class="pf-c-label custom-status {% if 'done' in ticket.status.lower() or 'closed' in ticket.status.lower() %}pf-m-green{% elif 'progress' in ticket.status.lower() %}pf-m-orange{% else %}pf-m-grey{% endif %}">{{ ticket.status }}</span>
                                    <span class="pf-c-label pf-m-outline pf-m-compact">{{ ticket.contributor_count }} contributors</span>
                                </div>
                            </div>
                            {% if ticket.contributors %}
                            <div class="pf-c-data-list__item-row" style="margin-top: 0.5rem;">
                                <div class="pf-c-data-list__item-control">
                                    <strong>Contributors:</strong>
                                    <div style="margin-top: 0.25rem;">
                                        {% for contributor in ticket.contributors %}
                                        <span class="pf-c-label pf-m-compact" style="margin-right: 0.25rem; margin-bottom: 0.25rem;">{{ contributor }}</span>
                                        {% endfor %}
                                    </div>
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <div class="pf-c-card root-tickets-container" id="root-tickets-container" style="display: none;">
                <div class="pf-c-card__body">
                    {% for ticket in tickets %}
                    {% if ticket.level == 0 %}
                    <div class="pf-c-data-list__item" style="padding: 0.75rem;">
                        <div class="pf-c-data-list__item-content">
                            <div class="pf-c-data-list__item-row">
                                <div class="pf-c-data-list__item-control" style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
                                    <a href="{{ ticket.url }}" class="pf-c-button pf-m-primary pf-m-small custom-ticket-key" target="_blank">{{ ticket.key }}</a>
                                    <span class="pf-c-content" style="flex: 1;">{{ ticket.summary }}</span>
                                    <span class="pf-c-label pf-m-outline">{{ ticket.issue_type }}</span>
                                    <span class="pf-c-label custom-status {% if 'done' in ticket.status.lower() or 'closed' in ticket.status.lower() %}pf-m-green{% elif 'progress' in ticket.status.lower() %}pf-m-orange{% else %}pf-m-grey{% endif %}">{{ ticket.status }}</span>
                                    <span class="pf-c-label pf-m-outline pf-m-compact">{{ ticket.contributor_count }} contributors</span>
                                </div>
                            </div>
                            {% if ticket.contributors %}
                            <div class="pf-c-data-list__item-row" style="margin-top: 0.5rem;">
                                <div class="pf-c-data-list__item-control">
                                    <strong>Contributors:</strong>
                                    <div style="margin-top: 0.25rem;">
                                        {% for contributor in ticket.contributors %}
                                        <span class="pf-c-label pf-m-compact" style="margin-right: 0.25rem; margin-bottom: 0.25rem;">{{ contributor }}</span>
                                        {% endfor %}
                                    </div>
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>

            <div class="pf-c-card contributors-container" id="contributors-container" style="display: none;">
                <div class="pf-c-card__body">
                    {% for contributor in contributors %}
                    <div class="pf-c-data-list__item" style="margin-bottom: 1rem;">
                        <div class="pf-c-data-list__item-content">
                            <div class="pf-c-data-list__item-row">
                                <div class="pf-c-data-list__item-control">
                                    <h3 class="pf-c-title pf-m-lg">{{ contributor.name }}</h3>
                                    <p class="pf-c-content">Contributing to {{ contributor.ticket_count }} top-level ticket{{ 's' if contributor.ticket_count != 1 else '' }}</p>
                                </div>
                            </div>
                            {% for ticket in contributor.tickets %}
                            <div class="pf-c-data-list__item-row" style="padding: 0.5rem 0;">
                                <div class="pf-c-data-list__item-control" style="display: flex; align-items: center; gap: 0.75rem;">
                                    <a href="{{ ticket.url }}" class="pf-c-button pf-m-primary pf-m-small custom-ticket-key" target="_blank">{{ ticket.key }}</a>
                                    <span class="pf-c-content">{{ ticket.summary }}</span>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>
    </div>

    <script>
        function showTicketsView() {
            // Update active state
            document.getElementById('tickets-card').classList.add('pf-m-selected');
            document.getElementById('root-tickets-card').classList.remove('pf-m-selected');
            document.getElementById('contributors-card').classList.remove('pf-m-selected');

            // Show/hide containers
            document.querySelector('.tickets-container').style.display = 'block';
            document.getElementById('root-tickets-container').style.display = 'none';
            document.getElementById('contributors-container').style.display = 'none';
        }

        function showRootTicketsView() {
            // Update active state
            document.getElementById('root-tickets-card').classList.add('pf-m-selected');
            document.getElementById('tickets-card').classList.remove('pf-m-selected');
            document.getElementById('contributors-card').classList.remove('pf-m-selected');

            // Show/hide containers
            document.querySelector('.tickets-container').style.display = 'none';
            document.getElementById('root-tickets-container').style.display = 'block';
            document.getElementById('contributors-container').style.display = 'none';
        }

        function showContributorsView() {
            // Update active state
            document.getElementById('contributors-card').classList.add('pf-m-selected');
            document.getElementById('tickets-card').classList.remove('pf-m-selected');
            document.getElementById('root-tickets-card').classList.remove('pf-m-selected');

            // Show/hide containers
            document.querySelector('.tickets-container').style.display = 'none';
            document.getElementById('root-tickets-container').style.display = 'none';
            document.getElementById('contributors-container').style.display = 'block';
        }
    </script>
</body>
</html>
        """.strip()

        template = Template(template_str)
        return template.render(**data)
