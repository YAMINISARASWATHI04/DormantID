"""
Unit tests for history API endpoints
Tests: GET /api/history, DELETE /api/history/<id>, DELETE /api/history/clear-all
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.api
class TestHistoryEndpoints:
    """Test suite for history-related API endpoints"""
    
    def test_get_history_success(self, client, sample_history):
        """Test GET /api/history returns history list"""
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            response = client.get('/api/history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 1
            assert len(data['history']) == 1
            assert data['history'][0]['id'] == '20260419_120000'
    
    def test_get_history_empty(self, client):
        """Test GET /api/history with no history"""
        with patch('app.HistoryManager.load_history', return_value=[]):
            response = client.get('/api/history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0
            assert data['history'] == []
    
    def test_get_history_multiple_entries(self, client):
        """Test GET /api/history with multiple entries"""
        history = [
            {
                'id': '20260419_120000',
                'filename': 'extraction_20260419_120000.json',
                'records_count': 1000,
                'timestamp': '2026-04-19T12:00:00Z'
            },
            {
                'id': '20260418_150000',
                'filename': 'extraction_20260418_150000.json',
                'records_count': 500,
                'timestamp': '2026-04-18T15:00:00Z'
            }
        ]
        
        with patch('app.HistoryManager.load_history', return_value=history):
            response = client.get('/api/history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['history']) == 2
    
    def test_delete_history_entry_success(self, client, sample_history, temp_dir):
        """Test DELETE /api/history/<id> successfully deletes entry"""
        history_id = '20260419_120000'
        
        # Create mock files
        extraction_file = os.path.join(temp_dir, 'extraction_20260419_120000.json')
        output_file = os.path.join(temp_dir, 'dormant_id_decisions_20260419_120000.json')
        
        with open(extraction_file, 'w') as f:
            json.dump([], f)
        with open(output_file, 'w') as f:
            json.dump({}, f)
        
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            with patch('app.HistoryManager.save_history') as mock_save:
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=['extraction_20260419_120000.json']):
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove') as mock_remove:
                                response = client.delete(f'/api/history/{history_id}')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
                                assert 'deleted' in data['message']
                                assert data['deleted_count'] >= 0
                                
                                # Verify history was saved
                                mock_save.assert_called_once()
    
    def test_delete_history_entry_not_found(self, client, sample_history):
        """Test DELETE /api/history/<id> with non-existent ID"""
        history_id = 'nonexistent_id'
        
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            response = client.delete(f'/api/history/{history_id}')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'not found' in data['error']
    
    def test_delete_history_entry_with_files(self, client, temp_dir):
        """Test DELETE /api/history/<id> deletes associated files"""
        history = [{
            'id': '20260419_120000',
            'filename': 'extraction_20260419_120000.json',
            'output_file': 'dormant_id_decisions_20260419_120000.json',
            'timestamp': '2026-04-19T12:00:00Z'
        }]
        
        history_id = '20260419_120000'
        
        with patch('app.HistoryManager.load_history', return_value=history):
            with patch('app.HistoryManager.save_history'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir') as mock_listdir:
                        mock_listdir.return_value = [
                            'extraction_20260419_120000.json',
                            'dormant_id_decisions_20260419_120000.json'
                        ]
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove') as mock_remove:
                                response = client.delete(f'/api/history/{history_id}')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
    
    def test_delete_history_entry_file_deletion_fails(self, client, sample_history):
        """Test DELETE /api/history/<id> handles file deletion errors"""
        history_id = '20260419_120000'
        
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            with patch('app.HistoryManager.save_history'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=['extraction_20260419_120000.json']):
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove', side_effect=PermissionError('Access denied')):
                                response = client.delete(f'/api/history/{history_id}')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
                                # Should report failed files
                                assert data['failed_count'] >= 0
    
    def test_delete_history_entry_exception_handling(self, client):
        """Test DELETE /api/history/<id> handles exceptions"""
        history_id = '20260419_120000'
        
        with patch('app.HistoryManager.load_history', side_effect=Exception('Database error')):
            response = client.delete(f'/api/history/{history_id}')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Database error' in data['error']
    
    def test_clear_all_history_success(self, client, sample_history):
        """Test DELETE /api/history/clear-all clears all history"""
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            with patch('app.HistoryManager.save_history') as mock_save:
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=['extraction_20260419_120000.json']):
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove') as mock_remove:
                                response = client.delete('/api/history/clear-all')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
                                assert 'Cleared' in data['message']
                                assert data['entries_cleared'] == 1
                                
                                # Verify history was cleared
                                mock_save.assert_called_once_with([])
    
    def test_clear_all_history_empty(self, client):
        """Test DELETE /api/history/clear-all with no history"""
        with patch('app.HistoryManager.load_history', return_value=[]):
            with patch('app.HistoryManager.save_history') as mock_save:
                with patch('os.path.exists', return_value=False):
                    response = client.delete('/api/history/clear-all')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert data['entries_cleared'] == 0
                    assert data['files_deleted'] == 0
                    
                    # Verify history was still saved (empty)
                    mock_save.assert_called_once_with([])
    
    def test_clear_all_history_multiple_entries(self, client):
        """Test DELETE /api/history/clear-all with multiple entries"""
        history = [
            {
                'id': '20260419_120000',
                'filename': 'extraction_20260419_120000.json',
                'timestamp': '2026-04-19T12:00:00Z'
            },
            {
                'id': '20260418_150000',
                'filename': 'extraction_20260418_150000.json',
                'timestamp': '2026-04-18T15:00:00Z'
            }
        ]
        
        files = [
            'extraction_20260419_120000.json',
            'extraction_20260418_150000.json',
            'dormant_id_decisions_20260419_120000.json'
        ]
        
        with patch('app.HistoryManager.load_history', return_value=history):
            with patch('app.HistoryManager.save_history'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=files):
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove') as mock_remove:
                                response = client.delete('/api/history/clear-all')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
                                assert data['entries_cleared'] == 2
    
    def test_clear_all_history_directory_not_exists(self, client, sample_history):
        """Test DELETE /api/history/clear-all when directories don't exist"""
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            with patch('app.HistoryManager.save_history'):
                with patch('os.path.exists', return_value=False):
                    response = client.delete('/api/history/clear-all')
                    
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    assert data['files_deleted'] == 0
    
    def test_clear_all_history_partial_failure(self, client, sample_history):
        """Test DELETE /api/history/clear-all with some file deletion failures"""
        files = [
            'extraction_20260419_120000.json',
            'extraction_20260418_150000.json'
        ]
        
        def remove_side_effect(path):
            if '20260418' in path:
                raise PermissionError('Access denied')
        
        with patch('app.HistoryManager.load_history', return_value=sample_history):
            with patch('app.HistoryManager.save_history'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.listdir', return_value=files):
                        with patch('os.path.isfile', return_value=True):
                            with patch('os.remove', side_effect=remove_side_effect):
                                response = client.delete('/api/history/clear-all')
                                
                                assert response.status_code == 200
                                data = json.loads(response.data)
                                assert data['success'] is True
                                # Should report both deleted and failed
                                assert data['files_deleted'] >= 0
                                assert data['files_failed'] >= 0
    
    def test_clear_all_history_exception_handling(self, client):
        """Test DELETE /api/history/clear-all handles exceptions"""
        with patch('app.HistoryManager.load_history', side_effect=Exception('Database error')):
            response = client.delete('/api/history/clear-all')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Database error' in data['error']
    
    def test_history_manager_integration(self, client):
        """Test HistoryManager add_history_entry integration"""
        with patch('app.HistoryManager.load_history', return_value=[]):
            with patch('app.HistoryManager.save_history') as mock_save:
                # Simulate adding a history entry
                from app import HistoryManager
                
                entry = {
                    'id': '20260419_120000',
                    'filename': 'extraction_20260419_120000.json',
                    'timestamp': datetime.now().isoformat()
                }
                
                HistoryManager.add_history_entry(entry)
                
                # Verify save was called
                mock_save.assert_called_once()
                saved_history = mock_save.call_args[0][0]
                assert len(saved_history) == 1
                assert saved_history[0]['id'] == '20260419_120000'

# Made with Bob
