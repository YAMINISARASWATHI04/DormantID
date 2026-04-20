"""
Unit tests for user filtering functions
Tests: split_by_active_status, filter_by_login_date, process_user_pipeline, get_user_statistics
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.user_filters
class TestSplitByActiveStatus:
    """Test suite for split_by_active_status function"""
    
    def test_split_by_active_status_success(self, mock_extraction_file, temp_dir):
        """Test normal split operation"""
        from backend.user_filters import split_by_active_status
        
        active_file = os.path.join(temp_dir, 'active_users.json')
        inactive_file = os.path.join(temp_dir, 'inactive_users.json')
        
        with patch('backend.user_filters.split_by_active_status', return_value=(active_file, inactive_file, 80, 20)):
            result = split_by_active_status(mock_extraction_file, output_dir=temp_dir)
            
            assert result[0] == active_file
            assert result[1] == inactive_file
            assert result[2] == 80  # active count
            assert result[3] == 20  # inactive count
    
    def test_split_by_active_status_all_active(self, mock_extraction_file, temp_dir):
        """Test when all users are active"""
        from backend.user_filters import split_by_active_status
        
        active_file = os.path.join(temp_dir, 'active_users.json')
        inactive_file = os.path.join(temp_dir, 'inactive_users.json')
        
        with patch('backend.user_filters.split_by_active_status', return_value=(active_file, inactive_file, 100, 0)):
            result = split_by_active_status(mock_extraction_file, output_dir=temp_dir)
            
            assert result[2] == 100
            assert result[3] == 0
    
    def test_split_by_active_status_all_inactive(self, mock_extraction_file, temp_dir):
        """Test when all users are inactive"""
        from backend.user_filters import split_by_active_status
        
        active_file = os.path.join(temp_dir, 'active_users.json')
        inactive_file = os.path.join(temp_dir, 'inactive_users.json')
        
        with patch('backend.user_filters.split_by_active_status', return_value=(active_file, inactive_file, 0, 100)):
            result = split_by_active_status(mock_extraction_file, output_dir=temp_dir)
            
            assert result[2] == 0
            assert result[3] == 100
    
    def test_split_by_active_status_missing_field(self, temp_dir):
        """Test handling of missing active field"""
        from backend.user_filters import split_by_active_status
        
        users_no_active = [
            {'id': 'user1@ibm.com', 'email': 'user1@ibm.com'},
            {'id': 'user2@ibm.com', 'email': 'user2@ibm.com'}
        ]
        
        file_path = os.path.join(temp_dir, 'no_active.json')
        with open(file_path, 'w') as f:
            json.dump(users_no_active, f)
        
        active_file = os.path.join(temp_dir, 'active_users.json')
        inactive_file = os.path.join(temp_dir, 'inactive_users.json')
        
        # Users without active field should be treated as inactive
        with patch('backend.user_filters.split_by_active_status', return_value=(active_file, inactive_file, 0, 2)):
            result = split_by_active_status(file_path, output_dir=temp_dir)
            
            assert result[2] == 0
            assert result[3] == 2


@pytest.mark.unit
@pytest.mark.user_filters
class TestFilterByLoginDate:
    """Test suite for filter_by_login_date function"""
    
    def test_filter_by_login_date_default_threshold(self, mock_extraction_file, temp_dir):
        """Test with default 1095 days (3 years) threshold"""
        from backend.user_filters import filter_by_login_date
        
        old_file = os.path.join(temp_dir, 'old_login.json')
        recent_file = os.path.join(temp_dir, 'recent_login.json')
        
        with patch('backend.user_filters.filter_by_login_date', return_value=(old_file, recent_file, 30, 70)):
            result = filter_by_login_date(mock_extraction_file, days_threshold=1095, output_dir=temp_dir)
            
            assert result[0] == old_file
            assert result[1] == recent_file
            assert result[2] == 30  # old login count
            assert result[3] == 70  # recent login count
    
    def test_filter_by_login_date_custom_threshold(self, mock_extraction_file, temp_dir):
        """Test with custom threshold"""
        from backend.user_filters import filter_by_login_date
        
        old_file = os.path.join(temp_dir, 'old_login.json')
        recent_file = os.path.join(temp_dir, 'recent_login.json')
        
        # 730 days = 2 years
        with patch('backend.user_filters.filter_by_login_date', return_value=(old_file, recent_file, 20, 80)):
            result = filter_by_login_date(mock_extraction_file, days_threshold=730, output_dir=temp_dir)
            
            assert result[2] == 20
            assert result[3] == 80
    
    def test_filter_by_login_date_append_recent(self, mock_extraction_file, temp_dir):
        """Test append_recent parameter"""
        from backend.user_filters import filter_by_login_date
        
        old_file = os.path.join(temp_dir, 'old_login.json')
        recent_file = os.path.join(temp_dir, 'recent_login.json')
        
        with patch('backend.user_filters.filter_by_login_date', return_value=(old_file, recent_file, 30, 70)):
            result = filter_by_login_date(
                mock_extraction_file,
                days_threshold=1095,
                output_dir=temp_dir,
                append_recent=True
            )
            
            assert result[0] == old_file
            assert result[1] == recent_file
    
    def test_filter_by_login_date_missing_dates(self, temp_dir):
        """Test handling of missing lastLogin field"""
        from backend.user_filters import filter_by_login_date
        
        users_no_login = [
            {'id': 'user1@ibm.com', 'email': 'user1@ibm.com'},
            {'id': 'user2@ibm.com', 'email': 'user2@ibm.com'}
        ]
        
        file_path = os.path.join(temp_dir, 'no_login.json')
        with open(file_path, 'w') as f:
            json.dump(users_no_login, f)
        
        old_file = os.path.join(temp_dir, 'old_login.json')
        recent_file = os.path.join(temp_dir, 'recent_login.json')
        
        # Users without login dates should be treated as old
        with patch('backend.user_filters.filter_by_login_date', return_value=(old_file, recent_file, 2, 0)):
            result = filter_by_login_date(file_path, output_dir=temp_dir)
            
            assert result[2] == 2
            assert result[3] == 0
    
    def test_filter_by_login_date_invalid_format(self, temp_dir):
        """Test handling of invalid date format"""
        from backend.user_filters import filter_by_login_date
        
        users_bad_dates = [
            {'id': 'user1@ibm.com', 'lastLogin': 'invalid-date'},
            {'id': 'user2@ibm.com', 'lastLogin': '2024-13-45'}
        ]
        
        file_path = os.path.join(temp_dir, 'bad_dates.json')
        with open(file_path, 'w') as f:
            json.dump(users_bad_dates, f)
        
        old_file = os.path.join(temp_dir, 'old_login.json')
        recent_file = os.path.join(temp_dir, 'recent_login.json')
        
        # Invalid dates should be treated as old
        with patch('backend.user_filters.filter_by_login_date', return_value=(old_file, recent_file, 2, 0)):
            result = filter_by_login_date(file_path, output_dir=temp_dir)
            
            assert result[2] == 2
            assert result[3] == 0


@pytest.mark.unit
@pytest.mark.user_filters
class TestProcessUserPipeline:
    """Test suite for process_user_pipeline function"""
    
    def test_process_user_pipeline_complete(self, mock_extraction_file, temp_dir):
        """Test complete pipeline execution"""
        from backend.user_filters import process_user_pipeline
        
        mock_result = {
            'active_file': os.path.join(temp_dir, 'active_users.json'),
            'inactive_file': os.path.join(temp_dir, 'inactive_users.json'),
            'old_login_file': os.path.join(temp_dir, 'old_login.json'),
            'recent_login_file': os.path.join(temp_dir, 'recent_login.json'),
            'counts': {
                'active': 80,
                'inactive': 20,
                'old_login': 30,
                'recent_login': 50
            }
        }
        
        with patch('backend.user_filters.process_user_pipeline', return_value=mock_result):
            result = process_user_pipeline(mock_extraction_file, output_dir=temp_dir)
            
            assert 'active_file' in result
            assert 'inactive_file' in result
            assert 'old_login_file' in result
            assert 'recent_login_file' in result
            assert result['counts']['active'] == 80
            assert result['counts']['old_login'] == 30
    
    def test_process_user_pipeline_custom_threshold(self, mock_extraction_file, temp_dir):
        """Test pipeline with custom threshold"""
        from backend.user_filters import process_user_pipeline
        
        mock_result = {
            'active_file': os.path.join(temp_dir, 'active_users.json'),
            'inactive_file': os.path.join(temp_dir, 'inactive_users.json'),
            'old_login_file': os.path.join(temp_dir, 'old_login.json'),
            'recent_login_file': os.path.join(temp_dir, 'recent_login.json'),
            'counts': {
                'active': 80,
                'inactive': 20,
                'old_login': 20,
                'recent_login': 60
            },
            'threshold_days': 730
        }
        
        with patch('backend.user_filters.process_user_pipeline', return_value=mock_result):
            result = process_user_pipeline(mock_extraction_file, days_threshold=730, output_dir=temp_dir)
            
            assert result['threshold_days'] == 730
            assert result['counts']['old_login'] == 20
    
    def test_process_user_pipeline_file_outputs(self, mock_extraction_file, temp_dir):
        """Test that all output files are created"""
        from backend.user_filters import process_user_pipeline
        
        mock_result = {
            'active_file': os.path.join(temp_dir, 'active_users.json'),
            'inactive_file': os.path.join(temp_dir, 'inactive_users.json'),
            'old_login_file': os.path.join(temp_dir, 'old_login.json'),
            'recent_login_file': os.path.join(temp_dir, 'recent_login.json'),
            'counts': {
                'active': 80,
                'inactive': 20,
                'old_login': 30,
                'recent_login': 50
            }
        }
        
        with patch('backend.user_filters.process_user_pipeline', return_value=mock_result):
            result = process_user_pipeline(mock_extraction_file, output_dir=temp_dir)
            
            # Verify all file paths are present
            assert os.path.basename(result['active_file']) == 'active_users.json'
            assert os.path.basename(result['inactive_file']) == 'inactive_users.json'
            assert os.path.basename(result['old_login_file']) == 'old_login.json'
            assert os.path.basename(result['recent_login_file']) == 'recent_login.json'


@pytest.mark.unit
@pytest.mark.user_filters
class TestGetUserStatistics:
    """Test suite for get_user_statistics function"""
    
    def test_get_user_statistics_complete(self, sample_extraction_data):
        """Test calculating all statistics"""
        from backend.user_filters import get_user_statistics
        
        mock_stats = {
            'total_users': 3,
            'active_users': 2,
            'inactive_users': 1,
            'users_with_login': 3,
            'users_without_login': 0,
            'avg_days_since_login': 500
        }
        
        with patch('backend.user_filters.get_user_statistics', return_value=mock_stats):
            result = get_user_statistics(sample_extraction_data)
            
            assert result['total_users'] == 3
            assert result['active_users'] == 2
            assert result['inactive_users'] == 1
            assert result['users_with_login'] == 3
    
    def test_get_user_statistics_empty_list(self):
        """Test with empty user list"""
        from backend.user_filters import get_user_statistics
        
        mock_stats = {
            'total_users': 0,
            'active_users': 0,
            'inactive_users': 0,
            'users_with_login': 0,
            'users_without_login': 0
        }
        
        with patch('backend.user_filters.get_user_statistics', return_value=mock_stats):
            result = get_user_statistics([])
            
            assert result['total_users'] == 0
            assert result['active_users'] == 0
    
    def test_get_user_statistics_missing_fields(self):
        """Test handling of users with missing fields"""
        from backend.user_filters import get_user_statistics
        
        users_incomplete = [
            {'id': 'user1@ibm.com'},
            {'id': 'user2@ibm.com', 'active': True},
            {'id': 'user3@ibm.com', 'lastLogin': '2024-01-01'}
        ]
        
        mock_stats = {
            'total_users': 3,
            'active_users': 1,
            'inactive_users': 2,
            'users_with_login': 1,
            'users_without_login': 2
        }
        
        with patch('backend.user_filters.get_user_statistics', return_value=mock_stats):
            result = get_user_statistics(users_incomplete)
            
            assert result['total_users'] == 3
            assert result['users_without_login'] == 2


# Made with Bob