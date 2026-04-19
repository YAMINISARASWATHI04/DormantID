"""
Unit tests for miscellaneous API endpoints
Tests: GET /, GET /api/health, GET /api/filters
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestMiscellaneousEndpoints:
    """Test suite for miscellaneous API endpoints"""
    
    def test_root_endpoint(self, client):
        """Test GET / returns API information"""
        response = client.get('/')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['name'] == 'Cloudant Extractor API'
        assert data['version'] == '1.0.0'
        assert data['status'] == 'running'
        assert 'endpoints' in data
        assert '/api/status' in data['endpoints']['status']
    
    def test_health_check_endpoint(self, client):
        """Test GET /api/health returns healthy status"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        
        # Verify timestamp is valid ISO format
        try:
            datetime.fromisoformat(data['timestamp'])
            timestamp_valid = True
        except:
            timestamp_valid = False
        assert timestamp_valid is True
    
    def test_get_filters_success(self, client):
        """Test GET /api/filters returns available filters"""
        mock_filters = [
            {
                'id': 'isv_validation',
                'name': 'ISV Validation',
                'description': 'Validates records against ISV API',
                'enabled': False
            },
            {
                'id': 'dormancy_check',
                'name': 'Dormancy Check',
                'description': 'Filters out accounts inactive for more than 3 years',
                'enabled': False
            },
            {
                'id': 'federated_id_removal',
                'name': 'Federated ID Removal',
                'description': 'Removes records with email addresses not in: @ibm.com',
                'enabled': False
            },
            {
                'id': 'cloud_activity',
                'name': 'Cloud Activity Validation',
                'description': 'Validates records have active cloud activity',
                'enabled': False
            }
        ]
        
        with patch('app.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_available_filters.return_value = mock_filters
            mock_manager.return_value = mock_instance
            
            response = client.get('/api/filters')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'filters' in data
            assert len(data['filters']) == 4
            assert data['filters'][0]['id'] == 'isv_validation'
    
    def test_get_filters_empty(self, client):
        """Test GET /api/filters with no filters available"""
        with patch('app.FilterManager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_available_filters.return_value = []
            mock_manager.return_value = mock_instance
            
            response = client.get('/api/filters')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['filters'] == []
    
    def test_get_filters_exception_handling(self, client):
        """Test GET /api/filters handles exceptions"""
        with patch('app.FilterManager', side_effect=Exception('Filter initialization error')):
            response = client.get('/api/filters')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Filter initialization error' in data['error']
    
    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test wrong HTTP method returns 405"""
        # GET /api/reset should be POST only
        response = client.get('/api/reset')
        
        assert response.status_code == 405


@pytest.mark.unit
@pytest.mark.api
class TestUserFilteringEndpoints:
    """Test suite for user filtering API endpoints"""
    
    def test_split_users_by_status_success(self, client, mock_extraction_file):
        """Test POST /api/users/split-by-status successfully splits users"""
        request_data = {
            'input_file': mock_extraction_file,
            'output_dir': 'backend/resolutions'
        }
        
        with patch('app.user_filters.split_by_active_status') as mock_split:
            mock_split.return_value = (
                'backend/resolutions/active_users.json',
                'backend/resolutions/inactive_users.json',
                80,
                20
            )
            
            response = client.post(
                '/api/users/split-by-status',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['counts']['active'] == 80
            assert data['counts']['inactive'] == 20
    
    def test_split_users_by_status_missing_input(self, client):
        """Test POST /api/users/split-by-status fails without input_file"""
        request_data = {}
        
        response = client.post(
            '/api/users/split-by-status',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'input_file is required' in data['error']
    
    def test_filter_users_by_login_success(self, client, mock_extraction_file):
        """Test POST /api/users/filter-by-login successfully filters users"""
        request_data = {
            'input_file': mock_extraction_file,
            'days_threshold': 1095,
            'output_dir': 'backend/resolutions',
            'append_recent': True
        }
        
        with patch('app.user_filters.filter_by_login_date') as mock_filter:
            mock_filter.return_value = (
                'backend/resolutions/old_login_users.json',
                'backend/resolutions/recent_login_users.json',
                30,
                50
            )
            
            response = client.post(
                '/api/users/filter-by-login',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['counts']['old_login'] == 30
            assert data['counts']['recent_login'] == 50
            assert data['threshold_days'] == 1095
    
    def test_filter_users_by_login_custom_threshold(self, client, mock_extraction_file):
        """Test POST /api/users/filter-by-login with custom threshold"""
        request_data = {
            'input_file': mock_extraction_file,
            'days_threshold': 730  # 2 years
        }
        
        with patch('app.user_filters.filter_by_login_date') as mock_filter:
            mock_filter.return_value = (
                'backend/resolutions/old_login_users.json',
                'backend/resolutions/recent_login_users.json',
                20,
                60
            )
            
            response = client.post(
                '/api/users/filter-by-login',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['threshold_days'] == 730
    
    def test_process_user_pipeline_success(self, client, mock_extraction_file):
        """Test POST /api/users/process-pipeline runs complete pipeline"""
        request_data = {
            'input_file': mock_extraction_file,
            'days_threshold': 1095,
            'output_dir': 'backend/resolutions'
        }
        
        mock_result = {
            'active_file': 'backend/resolutions/active_users.json',
            'inactive_file': 'backend/resolutions/inactive_users.json',
            'old_login_file': 'backend/resolutions/old_login_users.json',
            'recent_login_file': 'backend/resolutions/recent_login_users.json',
            'counts': {
                'active': 80,
                'inactive': 20,
                'old_login': 30,
                'recent_login': 50
            }
        }
        
        with patch('app.user_filters.process_user_pipeline', return_value=mock_result):
            response = client.post(
                '/api/users/process-pipeline',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['counts']['active'] == 80
            assert data['counts']['old_login'] == 30
    
    def test_get_user_statistics_success(self, client, temp_dir, sample_extraction_data):
        """Test POST /api/users/statistics returns user statistics"""
        file_path = f'{temp_dir}/users.json'
        
        with open(file_path, 'w') as f:
            json.dump(sample_extraction_data, f)
        
        request_data = {
            'file_path': file_path
        }
        
        mock_stats = {
            'total_users': 3,
            'active_users': 2,
            'inactive_users': 1,
            'users_with_login': 3,
            'users_without_login': 0
        }
        
        with patch('app.user_filters.load_users_from_file', return_value=sample_extraction_data):
            with patch('app.user_filters.get_user_statistics', return_value=mock_stats):
                response = client.post(
                    '/api/users/statistics',
                    data=json.dumps(request_data),
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['statistics']['total_users'] == 3
                assert data['statistics']['active_users'] == 2
    
    def test_list_user_files_success(self, client):
        """Test GET /api/users/list-files returns resolution files"""
        mock_files = [
            {
                'filename': 'resolved_users_20260419_120000.json',
                'size': 1024,
                'created': '2026-04-19T12:00:00'
            },
            {
                'filename': 'active_users_20260419_120000.json',
                'size': 512,
                'created': '2026-04-19T12:00:00'
            }
        ]
        
        with patch('app.user_filters.list_resolution_files', return_value=mock_files):
            response = client.get('/api/users/list-files')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['files']) == 2
    
    def test_list_user_files_with_custom_dir(self, client):
        """Test GET /api/users/list-files with custom directory"""
        with patch('app.user_filters.list_resolution_files', return_value=[]):
            response = client.get('/api/users/list-files?resolution_dir=custom/path')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0

# Made with Bob
