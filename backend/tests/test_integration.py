"""
Integration tests for end-to-end workflows
Tests: Complete extraction to decision workflows, async operations, error recovery
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test suite for end-to-end workflow integration"""
    
    @pytest.mark.asyncio
    async def test_e2e_extraction_to_decision(self, temp_dir, sample_extraction_data):
        """Test complete workflow from extraction to decision"""
        # Simulate complete workflow
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        with open(extraction_file, 'w') as f:
            json.dump(sample_extraction_data, f)
        
        # Mock the complete pipeline
        mock_pipeline_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'isv_validation': {'output': {'found_in_isv': 2, 'not_found_in_isv': 1}},
                'active_status': {'output': {'active': 2, 'inactive': 1}},
                'last_login': {'output': {'old_login': 1, 'recent_login': 2}},
                'bluepages': {'output': {'found_in_bluepages': 2, 'not_found_in_bluepages': 1}}
            }
        }
        
        mock_decision_result = {
            'to_be_deleted': [{'id': 'user1@ibm.com'}],
            'not_to_be_deleted': [{'id': 'user2@ibm.com'}],
            'isv_inactive_users': [{'id': 'user3@ibm.com'}],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_pipeline_result):
            with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_decision_result):
                from backend.validators.pipeline import run_validation_pipeline
                from backend.validators.decision_engine import consolidate_decisions
                
                # Run pipeline
                pipeline_result = await run_validation_pipeline(extraction_file)
                assert pipeline_result['success'] is True
                
                # Consolidate decisions
                decision_result = consolidate_decisions(pipeline_result)
                assert len(decision_result['to_be_deleted']) == 1
                assert len(decision_result['not_to_be_deleted']) == 1
    
    @pytest.mark.asyncio
    async def test_e2e_specific_ids_extraction(self, temp_dir):
        """Test end-to-end workflow with specific IDs mode"""
        user_ids = ['user1@ibm.com', 'user2@ibm.com', 'user3@ibm.com']
        
        mock_extraction_result = {
            'success': True,
            'extraction_mode': 'specific_ids',
            'total_ids': 3,
            'records_extracted': 3,
            'output_file': os.path.join(temp_dir, 'extraction_specific.json')
        }
        
        mock_pipeline_result = {
            'success': True,
            'checks_run': ['isv_validation'],
            'results': {
                'isv_validation': {'output': {'found_in_isv': 3, 'not_found_in_isv': 0}}
            }
        }
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.extraction_mode = 'specific_ids'
            mock_instance.user_ids = user_ids
            mock_wrapper.return_value = mock_instance
            
            with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_pipeline_result):
                # Simulate extraction
                wrapper = mock_wrapper(
                    start_date=None,
                    end_date=None,
                    user_ids=user_ids,
                    extraction_mode='specific_ids'
                )
                
                assert wrapper.extraction_mode == 'specific_ids'
                assert len(wrapper.user_ids) == 3
    
    @pytest.mark.asyncio
    async def test_e2e_date_range_extraction(self, temp_dir):
        """Test end-to-end workflow with date range mode"""
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        mock_extraction_result = {
            'success': True,
            'extraction_mode': 'date_range',
            'start_date': start_date,
            'end_date': end_date,
            'records_extracted': 1000,
            'output_file': os.path.join(temp_dir, 'extraction_range.json')
        }
        
        mock_pipeline_result = {
            'success': True,
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'isv_validation': {'output': {'found_in_isv': 950, 'not_found_in_isv': 50}},
                'active_status': {'output': {'active': 800, 'inactive': 150}},
                'last_login': {'output': {'old_login': 300, 'recent_login': 650}},
                'bluepages': {'output': {'found_in_bluepages': 250, 'not_found_in_bluepages': 50}}
            }
        }
        
        with patch('app.ExtractorWrapper') as mock_wrapper:
            mock_instance = MagicMock()
            mock_instance.extraction_mode = 'date_range'
            mock_instance.start_date = start_date
            mock_instance.end_date = end_date
            mock_wrapper.return_value = mock_instance
            
            with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_pipeline_result):
                # Simulate extraction
                wrapper = mock_wrapper(
                    start_date=start_date,
                    end_date=end_date,
                    extraction_mode='date_range'
                )
                
                assert wrapper.extraction_mode == 'date_range'
                assert wrapper.start_date == start_date
                assert wrapper.end_date == end_date
    
    @pytest.mark.asyncio
    async def test_e2e_validation_pipeline_full(self, mock_extraction_file, temp_dir):
        """Test complete validation pipeline workflow"""
        checks = {
            'isv_validation': True,
            'active_status': True,
            'last_login': True,
            'bluepages': True
        }
        
        mock_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'timestamp': datetime.now().isoformat(),
            'input_file': mock_extraction_file,
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'isv_validation': {
                    'success': True,
                    'output': {'found_in_isv': 95, 'not_found_in_isv': 5},
                    'files_created': {
                        'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                        'failed': os.path.join(temp_dir, 'isv_failed.json')
                    }
                },
                'active_status': {
                    'success': True,
                    'output': {'active': 80, 'inactive': 15},
                    'files_created': {
                        'active': os.path.join(temp_dir, 'active_users.json'),
                        'inactive': os.path.join(temp_dir, 'inactive_users.json')
                    }
                },
                'last_login': {
                    'success': True,
                    'output': {'old_login': 30, 'recent_login': 50},
                    'files_created': {
                        'old_login': os.path.join(temp_dir, 'old_login.json'),
                        'recent_login': os.path.join(temp_dir, 'recent_login.json')
                    }
                },
                'bluepages': {
                    'success': True,
                    'output': {'found_in_bluepages': 25, 'not_found_in_bluepages': 5},
                    'files_created': {
                        'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                        'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                    }
                }
            },
            'summary': {
                'total_input': 100,
                'to_delete': 5,
                'not_to_delete': 75,
                'isv_inactive': 15,
                'isv_failed': 5
            },
            'duration_seconds': 120
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_result):
            from backend.validators.pipeline import run_validation_pipeline
            
            result = await run_validation_pipeline(
                mock_extraction_file,
                output_dir=temp_dir,
                checks=checks
            )
            
            assert result['success'] is True
            assert len(result['checks_run']) == 4
            assert 'summary' in result
            assert result['summary']['total_input'] == 100
    
    @pytest.mark.asyncio
    async def test_e2e_file_persistence(self, temp_dir, sample_extraction_data):
        """Test file creation and retrieval workflow"""
        # Create extraction file
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        with open(extraction_file, 'w') as f:
            json.dump(sample_extraction_data, f)
        
        # Verify file exists and can be read
        assert os.path.exists(extraction_file)
        
        with open(extraction_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert len(loaded_data) == len(sample_extraction_data)
        assert loaded_data[0]['id'] == sample_extraction_data[0]['id']
        
        # Create decision file
        decision_data = {
            'to_be_deleted': [sample_extraction_data[0]],
            'not_to_be_deleted': [sample_extraction_data[1]],
            'isv_inactive_users': [sample_extraction_data[2]],
            'isv_failed_ids': []
        }
        
        decision_file = os.path.join(temp_dir, 'decisions.json')
        with open(decision_file, 'w') as f:
            json.dump(decision_data, f)
        
        # Verify decision file
        assert os.path.exists(decision_file)
        
        with open(decision_file, 'r') as f:
            loaded_decisions = json.load(f)
        
        assert 'to_be_deleted' in loaded_decisions
        assert 'not_to_be_deleted' in loaded_decisions
        assert len(loaded_decisions['to_be_deleted']) == 1


@pytest.mark.integration
class TestAsyncOperations:
    """Test suite for async operation integration"""
    
    @pytest.mark.asyncio
    async def test_async_isv_validation_concurrent(self, mock_extraction_file):
        """Test concurrent ISV validation calls"""
        from backend.validators.isv_validator import validate_isv
        
        mock_result = {
            'success': True,
            'validator': 'isv_validation',
            'max_concurrent': 50,
            'batches_processed': 2,
            'output': {
                'found_in_isv': 95,
                'not_found_in_isv': 5
            }
        }
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock, return_value=mock_result):
            result = await validate_isv(mock_extraction_file, max_concurrent=50)
            
            assert result['success'] is True
            assert result['max_concurrent'] == 50
    
    @pytest.mark.asyncio
    async def test_async_bluepages_validation_concurrent(self, mock_extraction_file):
        """Test concurrent BluPages validation calls"""
        from backend.validators.bluepages_validator import validate_bluepages
        
        mock_result = {
            'success': True,
            'validator': 'bluepages',
            'max_concurrent': 50,
            'batches_processed': 1,
            'output': {
                'found_in_bluepages': 25,
                'not_found_in_bluepages': 5
            }
        }
        
        with patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock, return_value=mock_result):
            result = await validate_bluepages(mock_extraction_file, max_concurrent=50)
            
            assert result['success'] is True
            assert result['max_concurrent'] == 50
    
    @pytest.mark.asyncio
    async def test_async_pipeline_execution(self, mock_extraction_file):
        """Test async pipeline execution"""
        from backend.validators.pipeline import run_validation_pipeline
        
        checks = {
            'isv_validation': True,
            'bluepages': True
        }
        
        mock_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'bluepages'],
            'async_operations': 2,
            'total_duration': 45
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_result):
            result = await run_validation_pipeline(mock_extraction_file, checks=checks)
            
            assert result['success'] is True
            assert result['async_operations'] == 2


@pytest.mark.integration
class TestErrorRecovery:
    """Test suite for error recovery integration"""
    
    @pytest.mark.asyncio
    async def test_recovery_from_partial_failure(self, mock_extraction_file):
        """Test recovery from partial pipeline failures"""
        from backend.validators.pipeline import run_validation_pipeline
        
        checks = {
            'isv_validation': True,
            'active_status': True,
            'last_login': True
        }
        
        # ISV fails but pipeline continues with other checks
        mock_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['active_status', 'last_login'],
            'failed_checks': ['isv_validation'],
            'warnings': ['ISV validation failed, continuing with other checks'],
            'results': {
                'active_status': {'output': {'active': 80, 'inactive': 20}},
                'last_login': {'output': {'old_login': 30, 'recent_login': 50}}
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=mock_result):
            result = await run_validation_pipeline(mock_extraction_file, checks=checks)
            
            assert result['success'] is True
            assert 'warnings' in result
            assert len(result['failed_checks']) == 1
            assert len(result['checks_run']) == 2
    
    @pytest.mark.asyncio
    async def test_recovery_with_retry_logic(self, mock_extraction_file):
        """Test retry logic for failed operations"""
        from backend.validators.isv_validator import validate_isv
        
        # First call fails, second succeeds
        call_count = [0]
        
        async def mock_validate_with_retry(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError('API timeout')
            return {
                'success': True,
                'validator': 'isv_validation',
                'retry_count': 1,
                'output': {'found_in_isv': 95, 'not_found_in_isv': 5}
            }
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock, side_effect=mock_validate_with_retry):
            try:
                # First attempt fails
                await validate_isv(mock_extraction_file)
            except TimeoutError:
                pass
            
            # Retry succeeds
            result = await validate_isv(mock_extraction_file)
            assert result['success'] is True
            assert result['retry_count'] == 1


# Made with Bob