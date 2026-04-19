"""
Unit tests for extraction API endpoints
Tests: POST /api/retrieve, POST /api/stop
"""
import pytest
import json
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestExtractionEndpoints:
    """Test suite for extraction-related API endpoints"""
    
    def test_start_retrieval_date_range_success(self, client, sample_status):
        """Test POST /api/retrieve with date range mode"""
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'batch_size': 3000,
            'filters': {}
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            with patch('app.ExtractorWrapper') as mock_wrapper:
                with patch('threading.Thread') as mock_thread:
                    response = client.post(
                        '/api/retrieve',
                        data=json.dumps(request_data),
                        content_type='application/json'
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert data['extraction_mode'] == 'date_range'
                    assert data['start_date'] == '2024-01-01'
                    assert data['end_date'] == '2024-12-31'
                    
                    # Verify ExtractorWrapper was created
                    mock_wrapper.assert_called_once()
    
    def test_start_retrieval_with_timestamp(self, client, sample_status):
        """Test POST /api/retrieve with timestamp in dates"""
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': '2024-01-01 00:00:00',
            'end_date': '2024-12-31 23:59:59',
            'batch_size': 3000
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            with patch('app.ExtractorWrapper') as mock_wrapper:
                with patch('threading.Thread') as mock_thread:
                    response = client.post(
                        '/api/retrieve',
                        data=json.dumps(request_data),
                        content_type='application/json'
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
    
    def test_start_retrieval_specific_ids_success(self, client, sample_status):
        """Test POST /api/retrieve with specific IDs mode"""
        request_data = {
            'extraction_mode': 'specific_ids',
            'user_ids': ['user1@ibm.com', 'user2@ibm.com', 'user3@ibm.com'],
            'batch_size': 1000,
            'filters': {}
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            with patch('app.ExtractorWrapper') as mock_wrapper:
                with patch('threading.Thread') as mock_thread:
                    response = client.post(
                        '/api/retrieve',
                        data=json.dumps(request_data),
                        content_type='application/json'
                    )
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert data['extraction_mode'] == 'specific_ids'
                    assert data['user_count'] == 3
    
    def test_start_retrieval_already_running(self, client):
        """Test POST /api/retrieve fails when job is already running"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500,
            'progress_percent': 50
        }
        
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'already running' in data['error']
    
    def test_start_retrieval_missing_dates(self, client, sample_status):
        """Test POST /api/retrieve fails with missing dates"""
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': '2024-01-01'
            # Missing end_date
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'required' in data['error'].lower()
    
    def test_start_retrieval_invalid_date_format(self, client, sample_status):
        """Test POST /api/retrieve fails with invalid date format"""
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': 'invalid-date',
            'end_date': '2024-12-31'
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Invalid date format' in data['error']
    
    def test_start_retrieval_invalid_batch_size(self, client, sample_status):
        """Test POST /api/retrieve fails with invalid batch size"""
        request_data = {
            'extraction_mode': 'date_range',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'batch_size': 50  # Too small
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Batch size must be between 100 and 10000' in data['error']
    
    def test_start_retrieval_empty_user_ids(self, client, sample_status):
        """Test POST /api/retrieve fails with empty user_ids"""
        request_data = {
            'extraction_mode': 'specific_ids',
            'user_ids': []
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'at least one ID' in data['error']
    
    def test_start_retrieval_invalid_mode(self, client, sample_status):
        """Test POST /api/retrieve fails with invalid extraction mode"""
        request_data = {
            'extraction_mode': 'invalid_mode',
            'start_date': '2024-01-01',
            'end_date': '2024-12-31'
        }
        
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post(
                '/api/retrieve',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Invalid extraction_mode' in data['error']
    
    def test_stop_extraction_success(self, client):
        """Test POST /api/stop successfully stops extraction"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500
        }
        
        mock_extractor = MagicMock()
        mock_extractor.extractor = MagicMock()
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            with patch('app.current_extractor', mock_extractor):
                with patch('app.current_extractor_lock', MagicMock()):
                    response = client.post('/api/stop')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert 'Stop requested' in data['message']
                    
                    # Verify request_stop was called
                    mock_extractor.extractor.request_stop.assert_called_once()
    
    def test_stop_extraction_not_running(self, client, sample_status):
        """Test POST /api/stop fails when no extraction is running"""
        with patch('app.StatusManager.load_status', return_value=sample_status):
            response = client.post('/api/stop')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'No extraction is currently running' in data['error']
    
    def test_stop_extraction_no_extractor_reference(self, client):
        """Test POST /api/stop handles missing extractor reference"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500
        }
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            with patch('app.current_extractor', None):
                with patch('app.current_extractor_lock', MagicMock()):
                    with patch('app.StatusManager.update_status') as mock_update:
                        response = client.post('/api/stop')
                        
                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data['success'] is True
                        assert 'server was reloaded' in data['message']
                        
                        # Verify status was updated
                        mock_update.assert_called_once()
    
    def test_stop_extraction_not_initialized(self, client):
        """Test POST /api/stop when extractor not initialized yet"""
        processing_status = {
            'status': 'under_processing',
            'current_month': None,
            'records_processed': 0
        }
        
        mock_extractor = MagicMock()
        mock_extractor.extractor = None
        mock_extractor.stop_requested = False
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            with patch('app.current_extractor', mock_extractor):
                with patch('app.current_extractor_lock', MagicMock()):
                    response = client.post('/api/stop')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert mock_extractor.stop_requested is True
    
    def test_stop_extraction_exception_handling(self, client):
        """Test POST /api/stop handles exceptions properly"""
        processing_status = {
            'status': 'under_processing',
            'current_month': '2024-06',
            'records_processed': 500
        }
        
        with patch('app.StatusManager.load_status', return_value=processing_status):
            with patch('app.current_extractor_lock', side_effect=Exception('Lock error')):
                response = client.post('/api/stop')
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert data['success'] is False
                assert 'Lock error' in data['error']

# Made with Bob
