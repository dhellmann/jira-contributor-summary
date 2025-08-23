"""Tests for contributor extraction functionality."""

from jira_contributor_summary.contributors import ContributorExtractor


class TestContributorExtractor:
    """Test cases for ContributorExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ContributorExtractor()

    def test_extract_contributors_from_ticket_with_assignee(self):
        """Test extracting contributors when ticket has an assignee."""
        ticket_data = {"fields": {"assignee": {"displayName": "John Doe"}}}

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        assert contributors == {"John Doe"}

    def test_extract_contributors_from_ticket_with_reporter(self):
        """Test extracting contributors when ticket has a reporter."""
        ticket_data = {"fields": {"reporter": {"displayName": "Jane Smith"}}}

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        assert contributors == {"Jane Smith"}

    def test_extract_contributors_from_ticket_with_custom_fields(self):
        """Test extracting contributors from custom fields."""
        ticket_data = {
            "fields": {
                "customfield_10001": [
                    {"displayName": "Alice Johnson"},
                    {"displayName": "Bob Wilson"},
                ],
                "customfield_10002": {"displayName": "Charlie Brown"},
            }
        }

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        expected = {"Alice Johnson", "Bob Wilson", "Charlie Brown"}
        assert contributors == expected

    def test_extract_contributors_from_ticket_with_contributors_field(self):
        """Test extracting contributors from contributors field."""
        ticket_data = {
            "fields": {
                "contributors": [
                    {"displayName": "David Lee"},
                    {"displayName": "Eva Martinez"},
                ]
            }
        }

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        assert contributors == {"David Lee", "Eva Martinez"}

    def test_extract_contributors_from_ticket_empty(self):
        """Test extracting contributors from empty ticket."""
        ticket_data = {"fields": {}}

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        assert contributors == set()

    def test_extract_contributors_from_ticket_multiple_sources(self):
        """Test extracting contributors from multiple sources."""
        ticket_data = {
            "fields": {
                "assignee": {"displayName": "John Doe"},
                "reporter": {"displayName": "Jane Smith"},
                "customfield_10001": [{"displayName": "Alice Johnson"}],
                "contributors": [{"displayName": "Bob Wilson"}],
            }
        }

        contributors = self.extractor.extract_contributors_from_ticket(ticket_data)
        expected = {"John Doe", "Jane Smith", "Alice Johnson", "Bob Wilson"}
        assert contributors == expected

    def test_get_all_contributors_for_ticket_hierarchy_single_ticket(self):
        """Test getting contributors for a single ticket without children."""
        all_tickets = {"PROJ-1": {"fields": {"assignee": {"displayName": "John Doe"}}}}
        ticket_hierarchy = {}

        contributors = self.extractor.get_all_contributors_for_ticket_hierarchy(
            "PROJ-1", all_tickets, ticket_hierarchy
        )
        assert contributors == {"John Doe"}

    def test_get_all_contributors_for_ticket_hierarchy_with_children(self):
        """Test getting contributors for a ticket with children."""
        all_tickets = {
            "PROJ-1": {"fields": {"assignee": {"displayName": "John Doe"}}},
            "PROJ-2": {"fields": {"assignee": {"displayName": "Jane Smith"}}},
            "PROJ-3": {"fields": {"assignee": {"displayName": "Alice Johnson"}}},
        }
        ticket_hierarchy = {"PROJ-1": ["PROJ-2", "PROJ-3"]}

        contributors = self.extractor.get_all_contributors_for_ticket_hierarchy(
            "PROJ-1", all_tickets, ticket_hierarchy
        )
        expected = {"John Doe", "Jane Smith", "Alice Johnson"}
        assert contributors == expected

    def test_get_unique_contributors(self):
        """Test getting all unique contributors across tickets."""
        all_tickets = {
            "PROJ-1": {
                "fields": {
                    "assignee": {"displayName": "John Doe"},
                    "reporter": {"displayName": "Jane Smith"},
                }
            },
            "PROJ-2": {
                "fields": {
                    "assignee": {"displayName": "Jane Smith"},  # Duplicate
                    "reporter": {"displayName": "Alice Johnson"},
                }
            },
        }

        contributors = self.extractor.get_unique_contributors(all_tickets)
        expected = {"John Doe", "Jane Smith", "Alice Johnson"}
        assert contributors == expected

    def test_clear_cache(self):
        """Test clearing the contributor cache."""
        # Populate cache
        all_tickets = {"PROJ-1": {"fields": {"assignee": {"displayName": "John Doe"}}}}
        ticket_hierarchy = {}

        self.extractor.get_all_contributors_for_ticket_hierarchy(
            "PROJ-1", all_tickets, ticket_hierarchy
        )
        assert len(self.extractor.contributor_cache) > 0

        # Clear cache
        self.extractor.clear_cache()
        assert len(self.extractor.contributor_cache) == 0
