"""
Unit tests for validation pipeline API endpoints
Tests: POST /api/validate/isv, POST /api/validate/active-status, 
       POST /api/validate/last-login, POST /api/validate/bluepages,
       POST /api/validate/pipeline
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestValidationEndpoints:
    """Test suite for validation pipeline API endpoints"""
    
    @pytest.mark.asyncio
    async def test_validate_isv_success(self, client, mock_extraction_file):
        """Test POST /api/validate/isv successfully validates users"""
        request_data = {
            'input_file': mock_extraction_file,
            'output_dir': 'backend/outputs',
            'batch_size': 100,
            'max_concurrent': 50
        }
        
        mock_result = {
            'success': True,
            'validator': 'isv_validation',
            'input_count': 100,
            'output': {
                'found_in_isv': 95,
                'not_found_in_isv': 5
            },
            'files_created': {
                'resolved': 'backend/outputs/isv_resolved_users.json',
                'failed': 'backend/outputs/isv_failed_ids.json'
            }
        }
        
        with patch('app.validators.validate_isv', new_callable=AsyncMock, return_value=mock_result):
            response = client.post(
                '/api/validate/isv',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['validator'] == 'isv_validation'
            assert data['output']['found_in_isv'] == 95
    
    def test_validate_isv_missing_input_file(self, client):
        """Test POST /api/validate/isv fails without input_file"""
        request_data = {
            'output_dir': 'backend/outputs'
        }
        
        response = client.post(
            '/api/validate/isv',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'input_file is required' in data['error']
    
    def test_validate_active_status_success(self, client, mock_extraction_file):
        """Test POST /api/validate/active-status successfully splits users"""
        request_data = {
            'input_file': mock_extraction_file,
            'output_dir': 'backend/outputs',
            'timestamp': '20260419_120000'
        }
        
        mock_result = {
            'success': True,
            'validator': 'active_status',
            'input_count': 100,
            'output': {
                'active': 80,
                'inactive': 20
            },
            'files_created': {
                'active': 'backend/outputs/isv_active_users.json',
                'inactive': 'backend/outputs/isv_inactive_users.json'
            }
        }
        
        with patch('app.validators.validate_active_status', return_value=mock_result):
            response = client.post(
                '/api/validate/active-status',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['output']['active'] == 80
            assert data['output']['inactive'] == 20
    
    def test_validate_active_status_missing_input(self, client):
        """Test POST /api/validate/active-status fails without input_file"""
        request_data = {}
        
        response = client.post(
            '/api/validate/active-status',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'input_file is required' in data['error']
    
    def test_validate_last_login_success(self, client, mock_extraction_file):
        """Test POST /api/validate/last-login successfully filters by login date"""
        request_data = {
            'input_file': mock_extraction_file,
            'days_threshold': 1095,
            'output_dir': 'backend/outputs',
            'timestamp': '20260419_120000',
            'append_recent': True
        }
        
        mock_result = {
            'success': True,
            'validator': 'last_login',
            'input_count': 80,
            'output': {
                'old_login': 30,
                'recent_login': 50
            },
            'files_created': {
                'old_login': 'backend/outputs/isv_last_login_old.json',
                'recent_login': 'backend/outputs/isv_last_login_recent.json'
            }
        }
        
        with patch('app.validators.validate_last_login', return_value=mock_result):
            response = client.post(
                '/api/validate/last-login',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['output']['old_login'] == 30
            assert data['output']['recent_login'] == 50
    
    def test_validate_last_login_custom_threshold(self, client, mock_extraction_file):
        """Test POST /api/validate/last-login with custom threshold"""
        request_data = {
            'input_file': mock_extraction_file,
            'days_threshold': 730,  # 2 years
            'output_dir': 'backend/outputs'
        }
        
        mock_result = {
            'success': True,
            'validator': 'last_login',
            'input_count': 80,
            'output': {
                'old_login': 20,
                'recent_login': 60
            }
        }
        
        with patch('app.validators.validate_last_login', return_value=mock_result):
            response = client.post(
                '/api/validate/last-login',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    @pytest.mark.asyncio
    async def test_validate_bluepages_success(self, client, mock_extraction_file):
        """Test POST /api/validate/bluepages successfully validates against BluPages"""
        request_data = {
            'input_file': mock_extraction_file,
            'output_dir': 'backend/outputs',
            'timestamp': '20260419_120000',
            'max_concurrent': 50,
            'batch_size': 100
        }
        
        mock_result = {
            'success': True,
            'validator': 'bluepages',
            'input_count': 30,
            'output': {
                'found_in_bluepages': 25,
                'not_found_in_bluepages': 5
            },
            'files_created': {
                'to_delete': 'backend/outputs/to_be_deleted.json',
                'not_to_delete': 'backend/outputs/not_to_be_deleted.json'
            }
        }
        
        with patch('app.validators.validate_bluepages', new_callable=AsyncMock, return_value=mock_result):
            response = client.post(
                '/api/validate/bluepages',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['output']['found_in_bluepages'] == 25
            assert data['output']['not_found_in_bluepages'] == 5
    
    @pytest.mark.asyncio
    async def test_validate_pipeline_full_success(self, client, mock_extraction_file):
        """Test POST /api/validate/pipeline runs complete pipeline"""
        request_data = {
            'input_file': mock_extraction_file,
            'output_dir': 'backend/outputs',
            'checks': {
                'isv_validation': True,
                'active_status': True,
                'last_login': True,
                'bluepages': True
            },
            'days_threshold': 1095,
            'max_concurrent': 50,
            'batch_size': 100
        }
        
        mock_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'timestamp': datetime.now().isoformat(),
            'input_file': mock_extraction_file,
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'isv_validation': {'output': {'found_in_isv': 95, 'not_found_in_isv': 5}},
                'active_status': {'output': {'active': 80, 'inactive': 15}},
                'last_login': {'output': {'old_login': 30, 'recent_login': 50}},
                'bluepages': {'output': {'found_in_bluepages': 25, 'not_found_in_bluepages': 5}}
            },
            'summary': {
                'total_input': 100,
                'found_in_isv': 95,
                'active': 80,
                'old_login': 30,
                'recent_login': 50,
                'found_in_bluepages': 25,
                'to_delete': 5,
                'not_to_delete': 75
            },
            'duration_seconds': 120
        }
        
        with patch('app.validators.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_result):
            response = client.post(
                '/api/validate/pipeline',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['pipeline'] == 'validation_pipeline'
            assert len(data['checks_run']) == 4
            assert data['summary']['total_input'] == 100
    
    @pytest.mark.asyncio
    async def test_validate_pipeline_partial_checks(self, client, mock_extraction_file):
        """Test POST /api/validate/pipeline with selective checks"""
        request_data = {
            'input_file': mock_extraction_file,
            'checks': {
                'isv_validation': True,
                'active_status': True,
                'last_login': False,
                'bluepages': False
            }
        }
        
        mock_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status'],
            'summary': {
                'total_input': 100,
                'found_in_isv': 95,
                'active': 80
            }
        }
        
        with patch('app.validators.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_result):
            response = client.post(
                '/api/validate/pipeline',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert len(data['checks_run']) == 2
    
    def test_validate_pipeline_missing_input(self, client):
        """Test POST /api/validate/pipeline fails without input_file"""
        request_data = {
            'checks': {
                'isv_validation': True
            }
        }
        
        response = client.post(
            '/api/validate/pipeline',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'input_file is required' in data['error']
    
    def test_validate_isv_exception_handling(self, client, mock_extraction_file):
        """Test POST /api/validate/isv handles exceptions"""
        request_data = {
            'input_file': mock_extraction_file
        }
        
        with patch('app.validators.validate_isv', side_effect=Exception('API error')):
            response = client.post(
                '/api/validate/isv',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'API error' in data['error']
    
    def test_validate_active_status_exception_handling(self, client, mock_extraction_file):
        """Test POST /api/validate/active-status handles exceptions"""
        request_data = {
            'input_file': mock_extraction_file
        }
        
        with patch('app.validators.validate_active_status', side_effect=Exception('File error')):
            response = client.post(
                '/api/validate/active-status',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'File error' in data['error']
    
    def test_validate_last_login_exception_handling(self, client, mock_extraction_file):
        """Test POST /api/validate/last-login handles exceptions"""
        request_data = {
            'input_file': mock_extraction_file
        }
        
        with patch('app.validators.validate_last_login', side_effect=Exception('Date error')):
            response = client.post(
                '/api/validate/last-login',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'Date error' in data['error']

# Made with Bob
