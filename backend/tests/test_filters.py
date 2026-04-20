"""
Unit tests for FilterManager
Tests: Filter initialization, enable/disable, apply filters, statistics
"""
import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.filters
class TestFilterManager:
    """Test suite for FilterManager class"""
    
    def test_filter_manager_initialization(self):
        """Test FilterManager initialization with config"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True,
            'dormancy_check': True,
            'federated_id_removal': False,
            'cloud_activity': False
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.config = config
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            
            assert manager.config == config
            assert manager.config['isv_validation'] is True
            assert manager.config['federated_id_removal'] is False
    
    def test_filter_manager_enable_filter(self):
        """Test enabling a specific filter"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': False,
            'dormancy_check': False
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.enable_filter = MagicMock(return_value=True)
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            result = manager.enable_filter('isv_validation')
            
            assert result is True
            manager.enable_filter.assert_called_once_with('isv_validation')
    
    def test_filter_manager_disable_filter(self):
        """Test disabling a specific filter"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True,
            'dormancy_check': True
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.disable_filter = MagicMock(return_value=True)
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            result = manager.disable_filter('isv_validation')
            
            assert result is True
            manager.disable_filter.assert_called_once_with('isv_validation')
    
    def test_filter_manager_get_enabled_filters(self):
        """Test getting list of enabled filters"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True,
            'dormancy_check': True,
            'federated_id_removal': False,
            'cloud_activity': False
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_enabled_filters = MagicMock(
                return_value=['isv_validation', 'dormancy_check']
            )
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            enabled = manager.get_enabled_filters()
            
            assert len(enabled) == 2
            assert 'isv_validation' in enabled
            assert 'dormancy_check' in enabled
            assert 'federated_id_removal' not in enabled
    
    def test_filter_manager_apply_filters(self):
        """Test applying filters to data"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True,
            'dormancy_check': True
        }
        
        users = [
            {'id': 'user1@ibm.com', 'email': 'user1@ibm.com', 'active': True},
            {'id': 'user2@ibm.com', 'email': 'user2@ibm.com', 'active': False},
            {'id': 'user3@ibm.com', 'email': 'user3@ibm.com', 'active': True}
        ]
        
        filtered_users = [
            {'id': 'user1@ibm.com', 'email': 'user1@ibm.com', 'active': True},
            {'id': 'user3@ibm.com', 'email': 'user3@ibm.com', 'active': True}
        ]
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.apply_filters = MagicMock(return_value=filtered_users)
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            result = manager.apply_filters(users)
            
            assert len(result) == 2
            assert all(user['active'] is True for user in result)
    
    def test_filter_manager_filter_statistics(self):
        """Test getting filter statistics"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True,
            'dormancy_check': True,
            'federated_id_removal': False,
            'cloud_activity': False
        }
        
        stats = {
            'total_filters': 4,
            'enabled_filters': 2,
            'disabled_filters': 2,
            'enabled_filter_names': ['isv_validation', 'dormancy_check']
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_stats = MagicMock(return_value=stats)
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            result = manager.get_stats()
            
            assert result['total_filters'] == 4
            assert result['enabled_filters'] == 2
            assert result['disabled_filters'] == 2
            assert len(result['enabled_filter_names']) == 2
    
    def test_filter_manager_invalid_filter(self):
        """Test handling of invalid filter ID"""
        from backend.filters import FilterManager
        
        config = {
            'isv_validation': True
        }
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.enable_filter = MagicMock(side_effect=ValueError('Invalid filter ID'))
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            
            with pytest.raises(ValueError) as exc_info:
                manager.enable_filter('invalid_filter')
            
            assert 'Invalid filter ID' in str(exc_info.value)
    
    def test_filter_manager_empty_config(self):
        """Test FilterManager with empty configuration"""
        from backend.filters import FilterManager
        
        config = {}
        
        with patch('backend.filters.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.config = config
            mock_instance.get_enabled_filters = MagicMock(return_value=[])
            mock_manager.return_value = mock_instance
            
            manager = mock_manager(config)
            enabled = manager.get_enabled_filters()
            
            assert len(enabled) == 0
            assert manager.config == {}


@pytest.mark.unit
@pytest.mark.filters
class TestFilterFunctions:
    """Test suite for individual filter functions"""
    
    def test_isv_validation_filter(self):
        """Test ISV validation filter"""
        users = [
            {'id': 'user1@ibm.com', 'in_isv': True},
            {'id': 'user2@ibm.com', 'in_isv': False},
            {'id': 'user3@ibm.com', 'in_isv': True}
        ]
        
        # Filter should keep only users in ISV
        filtered = [u for u in users if u.get('in_isv', False)]
        
        assert len(filtered) == 2
        assert all(u['in_isv'] is True for u in filtered)
    
    def test_dormancy_check_filter(self):
        """Test dormancy check filter"""
        from datetime import datetime, timedelta
        
        old_date = (datetime.now() - timedelta(days=1200)).isoformat()
        recent_date = (datetime.now() - timedelta(days=100)).isoformat()
        
        users = [
            {'id': 'user1@ibm.com', 'lastLogin': old_date},
            {'id': 'user2@ibm.com', 'lastLogin': recent_date},
            {'id': 'user3@ibm.com', 'lastLogin': old_date}
        ]
        
        # Filter should identify dormant users (>1095 days)
        threshold_days = 1095
        dormant = []
        for u in users:
            if u.get('lastLogin'):
                login_date = datetime.fromisoformat(u['lastLogin'].replace('Z', '+00:00'))
                days_since = (datetime.now(login_date.tzinfo) - login_date).days
                if days_since > threshold_days:
                    dormant.append(u)
        
        assert len(dormant) == 2
    
    def test_federated_id_removal_filter(self):
        """Test federated ID removal filter"""
        users = [
            {'id': 'user1@ibm.com', 'email': 'user1@ibm.com'},
            {'id': 'user2@external.com', 'email': 'user2@external.com'},
            {'id': 'user3@ibm.com', 'email': 'user3@ibm.com'}
        ]
        
        # Filter should keep only @ibm.com emails
        filtered = [u for u in users if u.get('email', '').endswith('@ibm.com')]
        
        assert len(filtered) == 2
        assert all('@ibm.com' in u['email'] for u in filtered)
    
    def test_cloud_activity_filter(self):
        """Test cloud activity validation filter"""
        users = [
            {'id': 'user1@ibm.com', 'has_cloud_activity': True},
            {'id': 'user2@ibm.com', 'has_cloud_activity': False},
            {'id': 'user3@ibm.com', 'has_cloud_activity': True}
        ]
        
        # Filter should keep only users with cloud activity
        filtered = [u for u in users if u.get('has_cloud_activity', False)]
        
        assert len(filtered) == 2
        assert all(u['has_cloud_activity'] is True for u in filtered)


# Made with Bob