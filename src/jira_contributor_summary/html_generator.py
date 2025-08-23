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
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            margin: 0 0 10px 0;
            font-size: 2.5em;
            font-weight: 300;
        }

        .header .subtitle {
            opacity: 0.9;
            font-size: 1.1em;
        }

        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }

        .stat-card.active {
            background: #e3f2fd;
            color: #1565c0;
            border: 2px solid #1976d2;
        }

        .stat-card.active .stat-number {
            color: #1565c0;
        }

        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }

        .stat-label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .tickets-container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .ticket {
            border-bottom: 1px solid #eee;
            padding: 20px;
            transition: background-color 0.2s ease;
        }

        .ticket:hover {
            background-color: #f8f9fa;
        }

        .ticket:last-child {
            border-bottom: none;
        }

        .ticket-level-0 {
            background-color: #fff;
            border-left: 4px solid #667eea;
        }

        .ticket-level-1 {
            background-color: #f8f9fa;
            border-left: 4px solid #28a745;
            margin-left: 20px;
        }

        .ticket-level-2 {
            background-color: #f1f3f4;
            border-left: 4px solid #ffc107;
            margin-left: 40px;
        }

        .ticket-level-3 {
            background-color: #f8f9fa;
            border-left: 4px solid #dc3545;
            margin-left: 60px;
        }

        .ticket-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .ticket-key {
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
            font-size: 0.9em;
            margin-right: 15px;
            transition: background-color 0.2s ease;
        }

        .ticket-key:hover {
            background: #5a6fd8;
            color: white;
        }

        .ticket-summary {
            font-weight: 500;
            color: #333;
            flex: 1;
        }

        .contributor-count {
            background: #e9ecef;
            color: #495057;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
        }

        .issue-type {
            background: #f8f9fa;
            color: #6c757d;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
            border: 1px solid #dee2e6;
        }

        .status {
            background: #e3f2fd;
            color: #1976d2;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
            border: 1px solid #bbdefb;
        }

        .status.done {
            background: #e8f5e8;
            color: #2e7d32;
            border-color: #c8e6c9;
        }

        .status.in-progress {
            background: #fff3e0;
            color: #f57c00;
            border-color: #ffcc02;
        }

        .status.to-do {
            background: #fafafa;
            color: #616161;
            border-color: #e0e0e0;
        }

        .contributors {
            color: #666;
            font-size: 0.95em;
            margin-top: 8px;
        }

        /* Contributors View Styles */
        .contributors-container {
            display: none;
        }

        .contributor-item {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            overflow: hidden;
        }

        .contributor-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
        }

        .contributor-name {
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }

        .contributor-stats {
            color: #666;
            font-size: 0.9em;
        }

        .contributor-tickets {
            padding: 15px 20px;
        }

        .contributor-ticket {
            display: flex;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }

        .contributor-ticket:last-child {
            border-bottom: none;
        }

        .contributor-ticket-key {
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 8px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 500;
            margin-right: 12px;
            min-width: 80px;
            text-align: center;
        }

        .contributor-ticket-key:hover {
            background: #bbdefb;
            text-decoration: none;
        }

        .contributor-ticket-summary {
            flex: 1;
            color: #333;
        }

        .contributors strong {
            color: #333;
        }

        .contributor-list {
            margin-top: 5px;
        }

        .contributor {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            margin: 2px 4px 2px 0;
        }

        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }

        @media (max-width: 768px) {
            body {
                padding: 10px;
            }

            .header h1 {
                font-size: 2em;
            }

            .ticket-level-1,
            .ticket-level-2,
            .ticket-level-3 {
                margin-left: 10px;
            }

            .ticket-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .ticket-key {
                margin-bottom: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>JIRA Contributor Summary</h1>
        <div class="subtitle">Project: {{ project_key }} | Generated: {{ generated_at }}</div>
    </div>

    <div class="summary-stats">
        <div class="stat-card active" id="tickets-card" onclick="showTicketsView()">
            <div class="stat-number">{{ tickets|length }}</div>
            <div class="stat-label">Total Tickets</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{{ tickets|selectattr('level', 'equalto', 0)|list|length }}</div>
            <div class="stat-label">Root Tickets</div>
        </div>
        <div class="stat-card" id="contributors-card" onclick="showContributorsView()">
            <div class="stat-number">{{ contributors|length }}</div>
            <div class="stat-label">Unique Contributors</div>
        </div>
    </div>

    <div class="tickets-container">
        {% for ticket in tickets %}
        <div class="ticket ticket-level-{{ ticket.level }}">
            <div class="ticket-header">
                <a href="{{ ticket.url }}" class="ticket-key" target="_blank">{{ ticket.key }}</a>
                <div class="ticket-summary">{{ ticket.summary }}</div>
                <div class="issue-type">{{ ticket.issue_type }}</div>
                <div class="status {{ ticket.status_class }}">{{ ticket.status }}</div>
                <div class="contributor-count">{{ ticket.contributor_count }} contributors</div>
            </div>

            {% if ticket.contributors %}
            <div class="contributors">
                <strong>Contributors:</strong>
                <div class="contributor-list">
                    {% for contributor in ticket.contributors %}
                    <span class="contributor">{{ contributor }}</span>
                    {% endfor %}
                </div>
            </div>
            {% else %}
            <div class="contributors">
                <em>No contributors found</em>
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <div class="contributors-container" id="contributors-container">
        {% for contributor in contributors %}
        <div class="contributor-item">
            <div class="contributor-header">
                <div class="contributor-name">{{ contributor.name }}</div>
                <div class="contributor-stats">Contributing to {{ contributor.ticket_count }} top-level ticket{{ 's' if contributor.ticket_count != 1 else '' }}</div>
            </div>
            <div class="contributor-tickets">
                {% for ticket in contributor.tickets %}
                <div class="contributor-ticket">
                    <a href="{{ ticket.url }}" class="contributor-ticket-key" target="_blank">{{ ticket.key }}</a>
                    <div class="contributor-ticket-summary">{{ ticket.summary }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        Generated by JIRA Contributor Summary tool
    </div>

    <script>
        function showTicketsView() {
            // Update active state
            document.getElementById('tickets-card').classList.add('active');
            document.getElementById('contributors-card').classList.remove('active');

            // Show/hide containers
            document.querySelector('.tickets-container').style.display = 'block';
            document.getElementById('contributors-container').style.display = 'none';
        }

        function showContributorsView() {
            // Update active state
            document.getElementById('contributors-card').classList.add('active');
            document.getElementById('tickets-card').classList.remove('active');

            // Show/hide containers
            document.querySelector('.tickets-container').style.display = 'none';
            document.getElementById('contributors-container').style.display = 'block';
        }
    </script>
</body>
</html>
        """.strip()

        template = Template(template_str)
        return template.render(**data)
