"""
Unit tests for status API endpoints
Tests: GET /api/status, POST /api/reset-status
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestStatusEndpoints:
    """Test suite for status-related API endpoints"""
    
    def test_get_status_success(self, client, sample_status):
        """Test GET /api/status returns current status"""
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'not_started'
            assert data['records_processed'] == 0
            assert data['progress_percent'] == 0
    
    def test_get_status_under_processing(self, client):
        """Test GET /api/status when job is running"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500,
            'progress_percent': 50,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 6,
            'error': None,
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'under_processing'
            assert data['records_processed'] == 500
            assert data['progress_percent'] == 50
            assert data['completed_months'] == 6
    
    def test_get_status_completed(self, client):
        """Test GET /api/status when job is completed"""
        completed_status = {
            'status': 'completed',
            'current_month': None,
            'records_processed': 1000,
            'progress_percent': 100,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 12,
            'error': None,
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=completed_status):
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'completed'
            assert data['records_processed'] == 1000
            assert data['progress_percent'] == 100
    
    def test_get_status_with_error(self, client):
        """Test GET /api/status when job has error"""
        error_status = {
            'status': 'error',
            'current_month': '2024-06',
            'records_processed': 300,
            'progress_percent': 30,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 3,
            'error': 'Connection timeout',
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=error_status):
            response = client.get('/api/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'error'
            assert data['error'] == 'Connection timeout'
    
    def test_reset_status_success(self, client, sample_status):
        """Test POST /api/reset successfully resets status"""
        with patch('app.StatusManager.load_status', return_value=sample_status):
            with patch('app.StatusManager.save_status') as mock_save:
                response = client.post('/api/reset')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['message'] == 'Status reset successfully'
                
                # Verify save_status was called
                mock_save.assert_called_once()
                saved_status = mock_save.call_args[0][0]
                assert saved_status['status'] == 'not_started'
                assert saved_status['records_processed'] == 0
    
    def test_reset_status_while_processing(self, client):
        """Test POST /api/reset fails when job is running"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500,
            'progress_percent': 50,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 6,
            'error': None,
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            response = client.post('/api/reset')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Cannot reset while a job is running' in data['error']
    
    def test_reset_status_after_completion(self, client):
        """Test POST /api/reset works after job completion"""
        completed_status = {
            'status': 'completed',
            'current_month': None,
            'records_processed': 1000,
            'progress_percent': 100,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 12,
            'error': None,
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=completed_status):
            with patch('app.StatusManager.save_status') as mock_save:
                response = client.post('/api/reset')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                mock_save.assert_called_once()
    
    def test_reset_status_after_error(self, client):
        """Test POST /api/reset works after job error"""
        error_status = {
            'status': 'error',
            'current_month': '2024-06',
            'records_processed': 300,
            'progress_percent': 30,
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'total_months': 12,
            'completed_months': 3,
            'error': 'Connection timeout',
            'last_updated': datetime.now().isoformat()
        }
        
        with patch('app.StatusManager.load_status', return_value=error_status):
            with patch('app.StatusManager.save_status') as mock_save:
                response = client.post('/api/reset')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                mock_save.assert_called_once()
    
    def test_reset_status_exception_handling(self, client, sample_status):
        """Test POST /api/reset handles exceptions properly"""
        with patch('app.StatusManager.load_status', return_value=sample_status):
            with patch('app.StatusManager.save_status', side_effect=Exception('Database error')):
                response = client.post('/api/reset')
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'Database error' in data['error']

# Made with Bob
