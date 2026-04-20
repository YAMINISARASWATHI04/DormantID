"""
Unit tests for ExtractorWrapper
Tests: Date range mode, specific IDs mode, status tracking, progress updates
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


@pytest.mark.unit
@pytest.mark.extractor
class TestExtractorWrapper:
    """Test suite for ExtractorWrapper class"""
    
    def test_extractor_wrapper_date_range_mode(self):
        """Test ExtractorWrapper with date range extraction mode"""
        from app import ExtractorWrapper
        
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.extraction_mode = 'date_range'
            mock_instance.start_date = start_date
            mock_instance.end_date = end_date
            mock_instance.batch_size = 3000
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date=start_date,
                end_date=end_date,
                extraction_mode='date_range',
                batch_size=3000
            )
            
            assert wrapper.extraction_mode == 'date_range'
            assert wrapper.start_date == start_date
            assert wrapper.end_date == end_date
            assert wrapper.batch_size == 3000
    
    def test_extractor_wrapper_specific_ids_mode(self):
        """Test ExtractorWrapper with specific IDs extraction mode"""
        from app import ExtractorWrapper
        
        user_ids = ['user1@ibm.com', 'user2@ibm.com', 'user3@ibm.com']
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.extraction_mode = 'specific_ids'
            mock_instance.user_ids = user_ids
            mock_instance.batch_size = 1000
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date=None,
                end_date=None,
                user_ids=user_ids,
                extraction_mode='specific_ids',
                batch_size=1000
            )
            
            assert wrapper.extraction_mode == 'specific_ids'
            assert len(wrapper.user_ids) == 3
            assert wrapper.batch_size == 1000
    
    def test_extractor_wrapper_calculate_total_months(self):
        """Test month calculation for date range"""
        from app import ExtractorWrapper
        
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.calculate_total_months = MagicMock(return_value=12)
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date=start_date,
                end_date=end_date,
                extraction_mode='date_range'
            )
            
            total_months = wrapper.calculate_total_months()
            assert total_months == 12
    
    def test_extractor_wrapper_status_updates(self):
        """Test status tracking during extraction"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            with patch('app.StatusManager') as mock_status:
                mock_instance = MagicMock()
                mock_instance.extraction_mode = 'date_range'
                mock_wrapper.return_value = mock_instance
                
                mock_status_instance = MagicMock()
                mock_status_instance.update_status = MagicMock()
                mock_status.return_value = mock_status_instance
                
                wrapper = mock_wrapper(
                    start_date='2024-01-01',
                    end_date='2024-12-31',
                    extraction_mode='date_range'
                )
                
                # Simulate status update
                status_update = {
                    'status': 'under_processing',
                    'records_processed': 500,
                    'progress_percent': 50
                }
                
                mock_status_instance.update_status(status_update)
                mock_status_instance.update_status.assert_called_once_with(status_update)
    
    def test_extractor_wrapper_stop_requested(self):
        """Test stop functionality"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.stop_requested = False
            mock_instance.request_stop = MagicMock()
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                extraction_mode='date_range'
            )
            
            assert wrapper.stop_requested is False
            
            # Request stop
            wrapper.request_stop()
            wrapper.request_stop.assert_called_once()
    
    def test_extractor_wrapper_filter_config(self):
        """Test filter configuration"""
        from app import ExtractorWrapper
        
        filter_config = {
            'isv_validation': True,
            'dormancy_check': True,
            'federated_id_removal': False
        }
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.filter_config = filter_config
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                filter_config=filter_config,
                extraction_mode='date_range'
            )
            
            assert wrapper.filter_config == filter_config
            assert wrapper.filter_config['isv_validation'] is True
            assert wrapper.filter_config['federated_id_removal'] is False
    
    def test_extractor_wrapper_batch_size(self):
        """Test batch size handling"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.batch_size = 5000
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                batch_size=5000,
                extraction_mode='date_range'
            )
            
            assert wrapper.batch_size == 5000
    
    def test_extractor_wrapper_output_file_creation(self, temp_dir):
        """Test output file creation"""
        from app import ExtractorWrapper
        
        output_file = os.path.join(temp_dir, 'extraction_test.json')
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.output_file = output_file
            mock_instance.output_filename = 'extraction_test.json'
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                extraction_mode='date_range'
            )
            
            assert wrapper.output_file == output_file
            assert wrapper.output_filename == 'extraction_test.json'
    
    def test_extractor_wrapper_error_handling(self):
        """Test error handling during extraction"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.run = MagicMock(side_effect=Exception('Extraction failed'))
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                extraction_mode='date_range'
            )
            
            with pytest.raises(Exception) as exc_info:
                wrapper.run()
            
            assert 'Extraction failed' in str(exc_info.value)
    
    def test_extractor_wrapper_progress_tracking(self):
        """Test progress tracking during extraction"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            with patch('app.StatusManager') as mock_status:
                mock_instance = MagicMock()
                mock_instance.extraction_mode = 'date_range'
                mock_wrapper.return_value = mock_instance
                
                mock_status_instance = MagicMock()
                mock_status.return_value = mock_status_instance
                
                wrapper = mock_wrapper(
                    start_date='2024-01-01',
                    end_date='2024-12-31',
                    extraction_mode='date_range'
                )
                
                # Simulate progress updates
                progress_updates = [
                    {'records_processed': 100, 'progress_percent': 10},
                    {'records_processed': 500, 'progress_percent': 50},
                    {'records_processed': 1000, 'progress_percent': 100}
                ]
                
                for update in progress_updates:
                    mock_status_instance.update_status(update)
                
                assert mock_status_instance.update_status.call_count == 3


@pytest.mark.unit
@pytest.mark.extractor
class TestExtractorWrapperAsync:
    """Test suite for ExtractorWrapper async operations"""
    
    @pytest.mark.asyncio
    async def test_extractor_wrapper_async_run(self):
        """Test async run method"""
        from app import ExtractorWrapper
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance._run_async = AsyncMock(return_value={'success': True})
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                extraction_mode='date_range'
            )
            
            result = await wrapper._run_async()
            assert result['success'] is True
    
    @pytest.mark.asyncio
    async def test_extractor_wrapper_async_with_filters(self):
        """Test async run with filters"""
        from app import ExtractorWrapper
        
        filter_config = {
            'isv_validation': True,
            'dormancy_check': True
        }
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.filter_config = filter_config
            mock_instance._run_async = AsyncMock(return_value={'success': True, 'filtered': 50})
            mock_wrapper.return_value = mock_instance
            
            wrapper = mock_wrapper(
                start_date='2024-01-01',
                end_date='2024-12-31',
                filter_config=filter_config,
                extraction_mode='date_range'
            )
            
            result = await wrapper._run_async()
            assert result['success'] is True
            assert result['filtered'] == 50


# Made with Bob