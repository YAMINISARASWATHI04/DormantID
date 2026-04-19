"""
Pytest configuration and fixtures for backend tests
"""
import pytest
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
import sys

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import app as flask_app


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': False,
    })
    yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_extraction_data():
    """Sample extraction data for testing."""
    return [
        {
            "id": "user1@ibm.com",
            "user_id": "user1@ibm.com",
            "email": "user1@ibm.com",
            "username": "user1",
            "lastLogin": "2023-01-15T10:30:00Z",
            "active": True
        },
        {
            "id": "user2@ibm.com",
            "user_id": "user2@ibm.com",
            "email": "user2@ibm.com",
            "username": "user2",
            "lastLogin": "2020-06-20T14:45:00Z",
            "active": True
        },
        {
            "id": "user3@ibm.com",
            "user_id": "user3@ibm.com",
            "email": "user3@ibm.com",
            "username": "user3",
            "lastLogin": "2024-12-01T08:00:00Z",
            "active": False
        }
    ]


@pytest.fixture
def sample_status():
    """Sample status data for testing."""
    return {
        'status': 'not_started',
        'current_month': None,
        'records_processed': 0,
        'progress_percent': 0,
        'start_date': None,
        'end_date': None,
        'total_months': 0,
        'completed_months': 0,
        'error': None,
        'last_updated': datetime.now().isoformat()
    }


@pytest.fixture
def sample_history():
    """Sample history data for testing."""
    return [
        {
            'id': '20260419_120000',
            'filename': 'extraction_20260419_120000.json',
            'output_file': 'dormant_id_decisions_20260419_120000.json',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'records_count': 1000,
            'timestamp': '2026-04-19T12:00:00Z',
            'status': 'completed'
        }
    ]


@pytest.fixture
def sample_decision_data():
    """Sample decision engine output for testing."""
    return {
        "to_be_deleted": [
            {
                "id": "user1@ibm.com",
                "username": "user1@ibm.com",
                "lastLogin": "2020-01-15T10:30:00Z",
                "activeStatus": True,
                "reasons": [
                    "User has old login (>1065 days)",
                    "User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed"
                ]
            }
        ],
        "not_to_be_deleted": [
            {
                "id": "user2@ibm.com",
                "username": "user2@ibm.com",
                "lastLogin": "2024-12-01T08:00:00Z",
                "activeStatus": True,
                "reasons": [
                    "User has recent login (≤1065 days, actual: 100 days) - FINAL DECISION: Last Login Check Passed"
                ]
            }
        ],
        "isv_inactive_users": [
            {
                "id": "user3@ibm.com",
                "username": "user3@ibm.com",
                "lastLogin": "2023-06-20T14:45:00Z",
                "activeStatus": False,
                "reasons": [
                    "User marked as inactive in ISV - FINAL DECISION: Active Status Check Failed"
                ]
            }
        ],
        "isv_failed_ids": []
    }


@pytest.fixture
def mock_extraction_file(temp_dir, sample_extraction_data):
    """Create a mock extraction file for testing."""
    file_path = os.path.join(temp_dir, 'extraction_test.json')
    with open(file_path, 'w') as f:
        json.dump(sample_extraction_data, f)
    return file_path


@pytest.fixture
def mock_decision_file(temp_dir, sample_decision_data):
    """Create a mock decision file for testing."""
    file_path = os.path.join(temp_dir, 'dormant_id_decisions_test.json')
    with open(file_path, 'w') as f:
        json.dump(sample_decision_data, f)
    return file_path


@pytest.fixture
def mock_status_file(temp_dir, sample_status):
    """Create a mock status file for testing."""
    file_path = os.path.join(temp_dir, 'status.json')
    with open(file_path, 'w') as f:
        json.dump(sample_status, f)
    return file_path


@pytest.fixture
def mock_history_file(temp_dir, sample_history):
    """Create a mock history file for testing."""
    file_path = os.path.join(temp_dir, 'history.json')
    with open(file_path, 'w') as f:
        json.dump(sample_history, f)
    return file_path


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup test files after each test."""
    yield
    # Cleanup logic can be added here if needed
    pass

# Made with Bob
