"""
Unit tests for file operation API endpoints
Tests: GET /api/download/<filename>, GET /api/view/<filename>, GET /api/extractions
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestFileOperationEndpoints:
    """Test suite for file operation API endpoints"""
    
    def test_download_file_success(self, client, temp_dir, sample_extraction_data):
        """Test GET /api/download/<filename> successfully downloads file"""
        filename = 'extraction_test.json'
        file_path = os.path.join(temp_dir, filename)
        
        # Create test file
        with open(file_path, 'w') as f:
            json.dump(sample_extraction_data, f)
        
        with patch('app._get_extraction_file_path', return_value=(file_path, None)):
            response = client.get(f'/api/download/{filename}')
            
            assert response.status_code == 200
            assert response.mimetype == 'application/json'
            # Verify content
            data = json.loads(response.data)
            assert len(data) == 3
            assert data[0]['id'] == 'user1@ibm.com'
    
    def test_download_file_not_found(self, client):
        """Test GET /api/download/<filename> returns 404 for missing file"""
        filename = 'nonexistent.json'
        
        with patch('app._get_extraction_file_path', return_value=(None, 'File not found')):
            response = client.get(f'/api/download/{filename}')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'File not found' in data['error']
    
    def test_download_file_invalid_type(self, client):
        """Test GET /api/download/<filename> rejects non-JSON files"""
        filename = 'test.txt'
        
        with patch('app._get_extraction_file_path', return_value=(None, 'Invalid file type')):
            response = client.get(f'/api/download/{filename}')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Invalid file type' in data['error']
    
    def test_download_file_exception_handling(self, client):
        """Test GET /api/download/<filename> handles exceptions"""
        filename = 'extraction_test.json'
        
        with patch('app._get_extraction_file_path', side_effect=Exception('Disk error')):
            response = client.get(f'/api/download/{filename}')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Disk error' in data['error']
    
    def test_view_file_success(self, client, temp_dir, sample_extraction_data):
        """Test GET /api/view/<filename> successfully returns file content"""
        filename = 'extraction_test.json'
        file_path = os.path.join(temp_dir, filename)
        
        # Create test file
        with open(file_path, 'w') as f:
            json.dump(sample_extraction_data, f)
        
        with patch('app._get_extraction_file_path', return_value=(file_path, None)):
            response = client.get(f'/api/view/{filename}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 3
            assert data[0]['id'] == 'user1@ibm.com'
            assert data[1]['email'] == 'user2@ibm.com'
    
    def test_view_file_decision_format(self, client, temp_dir, sample_decision_data):
        """Test GET /api/view/<filename> returns decision file structure"""
        filename = 'dormant_id_decisions_test.json'
        file_path = os.path.join(temp_dir, filename)
        
        # Create test file
        with open(file_path, 'w') as f:
            json.dump(sample_decision_data, f)
        
        with patch('app._get_extraction_file_path', return_value=(file_path, None)):
            response = client.get(f'/api/view/{filename}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'to_be_deleted' in data
            assert 'not_to_be_deleted' in data
            assert 'isv_inactive_users' in data
            assert 'isv_failed_ids' in data
            assert len(data['to_be_deleted']) == 1
            assert len(data['not_to_be_deleted']) == 1
    
    def test_view_file_not_found(self, client):
        """Test GET /api/view/<filename> returns 404 for missing file"""
        filename = 'nonexistent.json'
        
        with patch('app._get_extraction_file_path', return_value=(None, 'File not found')):
            response = client.get(f'/api/view/{filename}')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'File not found' in data['error']
    
    def test_view_file_invalid_json(self, client, temp_dir):
        """Test GET /api/view/<filename> handles invalid JSON"""
        filename = 'invalid.json'
        file_path = os.path.join(temp_dir, filename)
        
        # Create invalid JSON file
        with open(file_path, 'w') as f:
            f.write('{ invalid json }')
        
        with patch('app._get_extraction_file_path', return_value=(file_path, None)):
            response = client.get(f'/api/view/{filename}')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
    
    def test_list_extractions_success(self, client, temp_dir):
        """Test GET /api/extractions returns list of extraction files"""
        # Create mock extraction files
        files = [
            'extraction_20260419_120000.json',
            'extraction_20260418_150000.json',
            'extraction_20260417_100000.json'
        ]
        
        for filename in files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                json.dump([], f)
        
        mock_extractions = [
            {
                'filename': 'extraction_20260419_120000.json',
                'size': 1024,
                'size_mb': 0.001,
                'created': '2026-04-19T12:00:00',
                'modified': '2026-04-19T12:00:00'
            },
            {
                'filename': 'extraction_20260418_150000.json',
                'size': 2048,
                'size_mb': 0.002,
                'created': '2026-04-18T15:00:00',
                'modified': '2026-04-18T15:00:00'
            }
        ]
        
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=files):
                with patch('os.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    mock_stat.return_value.st_ctime = datetime(2026, 4, 19, 12, 0, 0).timestamp()
                    mock_stat.return_value.st_mtime = datetime(2026, 4, 19, 12, 0, 0).timestamp()
                    
                    response = client.get('/api/extractions')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert data['count'] == 3
                    assert len(data['extractions']) == 3
    
    def test_list_extractions_empty_directory(self, client):
        """Test GET /api/extractions with no extraction files"""
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=[]):
                response = client.get('/api/extractions')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['count'] == 0
                assert data['extractions'] == []
    
    def test_list_extractions_directory_not_exists(self, client):
        """Test GET /api/extractions when directory doesn't exist"""
        with patch('os.path.exists', return_value=False):
            response = client.get('/api/extractions')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0
            assert data['extractions'] == []
    
    def test_list_extractions_filters_non_json(self, client):
        """Test GET /api/extractions filters out non-JSON files"""
        files = [
            'extraction_20260419_120000.json',
            'readme.txt',
            'config.yaml',
            'extraction_20260418_150000.json'
        ]
        
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=files):
                with patch('os.stat') as mock_stat:
                    mock_stat.return_value.st_size = 1024
                    mock_stat.return_value.st_ctime = datetime.now().timestamp()
                    mock_stat.return_value.st_mtime = datetime.now().timestamp()
                    
                    response = client.get('/api/extractions')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    # Should only include JSON files starting with 'extraction_'
                    assert data['count'] == 2
    
    def test_list_extractions_sorted_by_date(self, client):
        """Test GET /api/extractions returns files sorted by creation date"""
        files = [
            'extraction_20260417_100000.json',
            'extraction_20260419_120000.json',
            'extraction_20260418_150000.json'
        ]
        
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=files):
                with patch('os.stat') as mock_stat:
                    # Mock different creation times
                    def stat_side_effect(path):
                        mock = MagicMock()
                        mock.st_size = 1024
                        if '20260419' in path:
                            mock.st_ctime = datetime(2026, 4, 19).timestamp()
                            mock.st_mtime = datetime(2026, 4, 19).timestamp()
                        elif '20260418' in path:
                            mock.st_ctime = datetime(2026, 4, 18).timestamp()
                            mock.st_mtime = datetime(2026, 4, 18).timestamp()
                        else:
                            mock.st_ctime = datetime(2026, 4, 17).timestamp()
                            mock.st_mtime = datetime(2026, 4, 17).timestamp()
                        return mock
                    
                    mock_stat.side_effect = stat_side_effect
                    
                    response = client.get('/api/extractions')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    # First file should be the newest
                    assert '20260419' in data['extractions'][0]['filename']
    
    def test_list_extractions_exception_handling(self, client):
        """Test GET /api/extractions handles exceptions"""
        with patch('os.path.exists', side_effect=Exception('Permission denied')):
            response = client.get('/api/extractions')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Permission denied' in data['error']
    
    def test_get_extraction_file_path_helper(self):
        """Test _get_extraction_file_path helper function"""
        from app import _get_extraction_file_path
        
        # Test invalid file type
        path, error = _get_extraction_file_path('test.txt')
        assert path is None
        assert error == 'Invalid file type'
        
        # Test valid JSON file (would need actual file to exist)
        with patch('os.path.exists', return_value=False):
            path, error = _get_extraction_file_path('extraction_test.json')
            assert path is None
            assert error == 'File not found'

# Made with Bob
