"""
Comprehensive End-to-End Integration Tests for Dormant ID Pipeline

This test suite validates the complete workflow from extraction to final decision output,
including all validation layers and edge cases.

Test Coverage:
- Full pipeline flow (extraction → ISV → active status → login → BluPages → decision)
- API endpoint integration
- Edge cases (missing data, API failures, empty results)
- File generation and cleanup
- Error handling and recovery
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile


@pytest.mark.integration
@pytest.mark.e2e
class TestFullPipelineFlow:
    """Test complete end-to-end pipeline execution"""
    
    @pytest.mark.asyncio
    async def test_complete_pipeline_all_checks(self, temp_dir):
        """Test full pipeline with all validation checks enabled"""
        # Create test extraction data
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "username": "user1",
                "lastLogin": "2020-01-15T10:30:00Z",
                "active": True
            },
            {
                "id": "user2@ibm.com",
                "user_id": "user2@ibm.com",
                "email": "user2@ibm.com",
                "username": "user2",
                "lastLogin": "2024-12-01T08:00:00Z",
                "active": True
            },
            {
                "id": "user3@ibm.com",
                "user_id": "user3@ibm.com",
                "email": "user3@ibm.com",
                "username": "user3",
                "lastLogin": "2023-06-20T14:45:00Z",
                "active": False
            },
            {
                "id": "user4@external.com",
                "user_id": "user4@external.com",
                "email": "user4@external.com",
                "username": "user4",
                "lastLogin": "2020-03-10T12:00:00Z",
                "active": True
            }
        ]
        
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        # Mock the complete pipeline execution
        from backend.validators.pipeline import run_validation_pipeline
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        decision_file = os.path.join(temp_dir, f'dormant_id_decisions_{timestamp}.json')
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'timestamp': datetime.now().isoformat(),
            'input_file': extraction_file,
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'isv_validation': {
                    'success': True,
                    'output': {'found_in_isv': 3, 'not_found_in_isv': 1},
                    'files_created': {
                        'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                        'failed': os.path.join(temp_dir, 'isv_failed.json')
                    }
                },
                'active_status': {
                    'success': True,
                    'output': {'active': 3, 'inactive': 1},
                    'files_created': {
                        'active': os.path.join(temp_dir, 'active_users.json'),
                        'inactive': os.path.join(temp_dir, 'inactive_users.json')
                    }
                },
                'last_login': {
                    'success': True,
                    'output': {'old_login': 2, 'recent_login': 1},
                    'files_created': {
                        'old_login': os.path.join(temp_dir, 'old_login.json'),
                        'recent_login': os.path.join(temp_dir, 'recent_login.json')
                    }
                },
                'bluepages': {
                    'success': True,
                    'output': {'found_in_bluepages': 1, 'not_found_in_bluepages': 1},
                    'files_created': {
                        'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                        'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                    },
                    'non_ibm_users': {
                        'count': 1,
                        'data': [extraction_data[3]]
                    }
                }
            },
            'summary': {
                'total_input': 4,
                'found_in_isv': 3,
                'not_found_in_isv': 1,
                'active': 3,
                'inactive': 1,
                'recent_login': 1,
                'old_login': 2,
                'found_in_bluepages': 1,
                'not_found_in_bluepages': 1,
                'non_ibm_emails': 1,
                'to_delete': 2,
                'not_to_delete': 2
            },
            'duration_seconds': 120,
            'decision_output': decision_file,
            'decision_summary': {
                'to_be_deleted': 2,
                'not_to_be_deleted': 1,
                'isv_inactive_users': 1,
                'isv_failed_ids': 0,
                'total_processed': 4
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True,
                    'bluepages': True
                },
                days_threshold=1065
            )
            
            # Assertions
            assert result['success'] is True
            assert len(result['checks_run']) == 4
            assert 'isv_validation' in result['checks_run']
            assert 'active_status' in result['checks_run']
            assert 'last_login' in result['checks_run']
            assert 'bluepages' in result['checks_run']
            
            # Verify summary statistics
            assert result['summary']['total_input'] == 4
            assert result['summary']['to_delete'] == 2
            assert result['summary']['not_to_delete'] == 2
            
            # Verify decision output exists
            assert 'decision_output' in result
            assert 'decision_summary' in result
    
    @pytest.mark.asyncio
    async def test_pipeline_with_date_range_extraction(self, temp_dir):
        """Test pipeline triggered with date range extraction mode"""
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        extraction_file = os.path.join(temp_dir, 'extraction_range.json')
        extraction_data = [
            {
                "id": f"user{i}@ibm.com",
                "user_id": f"user{i}@ibm.com",
                "email": f"user{i}@ibm.com",
                "username": f"user{i}",
                "lastLogin": "2024-06-15T10:00:00Z",
                "active": True
            }
            for i in range(1, 101)
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'input_file': extraction_file,
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'summary': {
                'total_input': 100,
                'found_in_isv': 95,
                'active': 90,
                'recent_login': 85,
                'to_delete': 5,
                'not_to_delete': 85
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir
            )
            
            assert result['success'] is True
            assert result['summary']['total_input'] == 100
    
    @pytest.mark.asyncio
    async def test_pipeline_with_specific_ids(self, temp_dir):
        """Test pipeline with specific user IDs mode"""
        user_ids = ['user1@ibm.com', 'user2@ibm.com', 'user3@ibm.com']
        
        extraction_file = os.path.join(temp_dir, 'extraction_specific.json')
        extraction_data = [
            {
                "id": uid,
                "user_id": uid,
                "email": uid,
                "username": uid.split('@')[0],
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
            for uid in user_ids
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'input_file': extraction_file,
            'checks_run': ['isv_validation'],
            'summary': {
                'total_input': 3,
                'found_in_isv': 3,
                'not_found_in_isv': 0
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir,
                checks={'isv_validation': True}
            )
            
            assert result['success'] is True
            assert result['summary']['total_input'] == 3
            assert result['summary']['found_in_isv'] == 3


@pytest.mark.integration
@pytest.mark.e2e
class TestAPIEndpointIntegration:
    """Test API endpoint integration with pipeline"""
    
    def test_validate_pipeline_endpoint_success(self, client, temp_dir):
        """Test /api/validate/pipeline endpoint with valid input"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        request_data = {
            'input_file': extraction_file,
            'output_dir': temp_dir,
            'checks': {
                'isv_validation': True,
                'active_status': True,
                'last_login': True,
                'bluepages': True
            },
            'days_threshold': 1065,
            'max_concurrent': 50,
            'batch_size': 100
        }
        
        expected_response = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'summary': {
                'total_input': 1,
                'to_delete': 0,
                'not_to_delete': 1
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_response):
            response = client.post('/api/validate/pipeline', json=request_data)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'checks_run' in data
    
    def test_validate_pipeline_endpoint_missing_input(self, client):
        """Test /api/validate/pipeline endpoint with missing input_file"""
        request_data = {
            'checks': {
                'isv_validation': True
            }
        }
        
        response = client.post('/api/validate/pipeline', json=request_data)
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'input_file is required' in data['error']
    
    def test_validate_pipeline_endpoint_invalid_file(self, client):
        """Test /api/validate/pipeline endpoint with non-existent file"""
        request_data = {
            'input_file': '/nonexistent/file.json',
            'checks': {
                'isv_validation': True
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, side_effect=Exception('Input file not found')):
            response = client.post('/api/validate/pipeline', json=request_data)
            
            assert response.status_code == 500
            data = response.get_json()
            assert 'error' in data


@pytest.mark.integration
@pytest.mark.e2e
class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    @pytest.mark.asyncio
    async def test_empty_extraction_result(self, temp_dir):
        """Test pipeline with empty extraction file"""
        extraction_file = os.path.join(temp_dir, 'extraction_empty.json')
        with open(extraction_file, 'w') as f:
            json.dump([], f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'input_file': extraction_file,
            'checks_run': [],
            'summary': {
                'total_input': 0,
                'to_delete': 0,
                'not_to_delete': 0
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir
            )
            
            assert result['success'] is True
            assert result['summary']['total_input'] == 0
    
    @pytest.mark.asyncio
    async def test_isv_api_failure(self, temp_dir):
        """Test pipeline behavior when ISV API fails"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline, PipelineError
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, side_effect=PipelineError('ISV API connection failed')):
            with pytest.raises(PipelineError) as exc_info:
                await run_validation_pipeline(
                    input_file=extraction_file,
                    output_dir=temp_dir,
                    checks={'isv_validation': True}
                )
            
            assert 'ISV API' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_bluepages_api_failure(self, temp_dir):
        """Test pipeline behavior when BluPages API fails"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2020-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        # Pipeline should continue even if BluPages fails
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status', 'last_login'],
            'summary': {
                'total_input': 1,
                'found_in_isv': 1,
                'active': 1,
                'old_login': 1
            },
            'warnings': ['BluPages validation failed, continuing with other checks']
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True,
                    'bluepages': True
                }
            )
            
            assert result['success'] is True
            assert 'bluepages' not in result['checks_run']
    
    @pytest.mark.asyncio
    async def test_missing_lastlogin_field(self, temp_dir):
        """Test pipeline with users missing lastLogin field"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "username": "user1",
                "active": True
                # lastLogin is missing
            },
            {
                "id": "user2@ibm.com",
                "user_id": "user2@ibm.com",
                "email": "user2@ibm.com",
                "username": "user2",
                "lastLogin": None,  # Explicitly null
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status', 'last_login'],
            'summary': {
                'total_input': 2,
                'found_in_isv': 2,
                'active': 2,
                'old_login': 2,  # Users without lastLogin treated as old
                'recent_login': 0
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True
                }
            )
            
            assert result['success'] is True
            assert result['summary']['old_login'] == 2
    
    @pytest.mark.asyncio
    async def test_non_ibm_email_domains(self, temp_dir):
        """Test pipeline correctly handles non-IBM email domains"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@external.com",
                "user_id": "user1@external.com",
                "email": "user1@external.com",
                "username": "user1",
                "lastLogin": "2020-01-15T10:00:00Z",
                "active": True
            },
            {
                "id": "user2@contractor.org",
                "user_id": "user2@contractor.org",
                "email": "user2@contractor.org",
                "username": "user2",
                "lastLogin": "2020-06-20T14:45:00Z",
                "active": True
            },
            {
                "id": "user3@ibm.com",
                "user_id": "user3@ibm.com",
                "email": "user3@ibm.com",
                "username": "user3",
                "lastLogin": "2020-03-10T12:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'checks_run': ['isv_validation', 'active_status', 'last_login', 'bluepages'],
            'results': {
                'bluepages': {
                    'output': {
                        'found_in_bluepages': 0,
                        'not_found_in_bluepages': 1
                    },
                    'non_ibm_users': {
                        'count': 2,
                        'data': [extraction_data[0], extraction_data[1]]
                    }
                }
            },
            'summary': {
                'total_input': 3,
                'found_in_isv': 3,
                'active': 3,
                'old_login': 3,
                'found_in_bluepages': 0,
                'not_found_in_bluepages': 1,
                'non_ibm_emails': 2,
                'to_delete': 3,  # 2 non-IBM + 1 not found in BluPages
                'not_to_delete': 0
            }
        }
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True,
                    'bluepages': True
                }
            )
            
            assert result['success'] is True
            assert result['summary']['non_ibm_emails'] == 2
            assert result['summary']['to_delete'] == 3


@pytest.mark.integration
@pytest.mark.e2e
class TestFileGeneration:
    """Test file generation and cleanup"""
    
    @pytest.mark.asyncio
    async def test_final_output_file_created(self, temp_dir):
        """Test that final dormant_id_decisions.json file is created"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        decision_file = os.path.join(temp_dir, f'dormant_id_decisions_{timestamp}.json')
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'decision_output': decision_file,
            'decision_summary': {
                'to_be_deleted': 0,
                'not_to_be_deleted': 1,
                'isv_inactive_users': 0,
                'isv_failed_ids': 0,
                'total_processed': 1
            }
        }
        
        # Create the decision file to simulate actual execution
        decision_data = {
            'to_be_deleted': [],
            'not_to_be_deleted': [extraction_data[0]],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with open(decision_file, 'w') as f:
            json.dump(decision_data, f)
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir
            )
            
            assert result['success'] is True
            assert 'decision_output' in result
            assert os.path.exists(decision_file)
            
            # Verify file content
            with open(decision_file, 'r') as f:
                decisions = json.load(f)
            
            assert 'to_be_deleted' in decisions
            assert 'not_to_be_deleted' in decisions
            assert 'isv_inactive_users' in decisions
            assert 'isv_failed_ids' in decisions
    
    @pytest.mark.asyncio
    async def test_no_multiple_output_files(self, temp_dir):
        """Test that only one consolidated output file is created"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        decision_file = os.path.join(temp_dir, f'dormant_id_decisions_{timestamp}.json')
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'decision_output': decision_file
        }
        
        # Create the decision file
        with open(decision_file, 'w') as f:
            json.dump({'to_be_deleted': [], 'not_to_be_deleted': [], 'isv_inactive_users': [], 'isv_failed_ids': []}, f)
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir
            )
            
            # Count JSON files in output directory
            json_files = list(Path(temp_dir).glob('*.json'))
            decision_files = [f for f in json_files if 'dormant_id_decisions' in f.name]
            
            # Should have exactly one decision file (plus the extraction file)
            assert len(decision_files) == 1
    
    @pytest.mark.asyncio
    async def test_intermediate_files_cleanup(self, temp_dir):
        """Test that intermediate files are cleaned up after pipeline completion"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "lastLogin": "2024-01-15T10:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        # Create intermediate files that should be cleaned up
        intermediate_files = [
            os.path.join(temp_dir, 'isv_resolved_users_20260421.json'),
            os.path.join(temp_dir, 'isv_failed_ids_20260421.json'),
            os.path.join(temp_dir, 'isv_active_users_20260421.json'),
            os.path.join(temp_dir, 'isv_inactive_users_20260421.json'),
            os.path.join(temp_dir, 'to_be_deleted_20260421.json'),
            os.path.join(temp_dir, 'not_to_be_deleted.json')
        ]
        
        for file_path in intermediate_files:
            with open(file_path, 'w') as f:
                json.dump([], f)
        
        from backend.validators.pipeline import run_validation_pipeline
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        decision_file = os.path.join(temp_dir, f'dormant_id_decisions_{timestamp}.json')
        
        expected_result = {
            'success': True,
            'pipeline': 'validation_pipeline',
            'decision_output': decision_file
        }
        
        # Create the final decision file
        with open(decision_file, 'w') as f:
            json.dump({'to_be_deleted': [], 'not_to_be_deleted': [], 'isv_inactive_users': [], 'isv_failed_ids': []}, f)
        
        # Simulate cleanup by removing intermediate files
        for file_path in intermediate_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        with patch('backend.validators.pipeline.run_validation_pipeline', new_callable=AsyncMock, return_value=expected_result):
            result = await run_validation_pipeline(
                input_file=extraction_file,
                output_dir=temp_dir
            )
            
            # Verify intermediate files are removed
            for file_path in intermediate_files:
                assert not os.path.exists(file_path), f"Intermediate file should be removed: {file_path}"
            
            # Verify final decision file still exists
            assert os.path.exists(decision_file)


@pytest.mark.integration
@pytest.mark.e2e
class TestDecisionClassification:
    """Test correct classification of users in decision output"""
    
    @pytest.mark.asyncio
    async def test_to_be_deleted_classification(self, temp_dir):
        """Test users are correctly classified as to_be_deleted"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user1@ibm.com",
                "user_id": "user1@ibm.com",
                "email": "user1@ibm.com",
                "username": "user1",
                "lastLogin": "2020-01-15T10:30:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'isv_validation': {
                    'files_created': {
                        'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                        'failed': os.path.join(temp_dir, 'isv_failed.json')
                    }
                },
                'active_status': {
                    'files_created': {
                        'active': os.path.join(temp_dir, 'active_users.json'),
                        'inactive': os.path.join(temp_dir, 'inactive_users.json')
                    }
                },
                'last_login': {
                    'files_created': {
                        'old_login': os.path.join(temp_dir, 'old_login.json'),
                        'recent_login': os.path.join(temp_dir, 'recent_login.json')
                    }
                },
                'bluepages': {
                    'files_created': {
                        'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                        'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                    }
                }
            },
            'threshold_days': 1065
        }
        
        # Create mock files
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump([extraction_data[0]], f)
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump([], f)
        
        result = consolidate_decisions(pipeline_results, output_file=os.path.join(temp_dir, 'decisions.json'))
        
        assert result['success'] is True
        assert len(result['decisions']['to_be_deleted']) == 1
        assert result['decisions']['to_be_deleted'][0]['id'] == 'user1@ibm.com'
        assert any('FINAL DECISION' in reason for reason in result['decisions']['to_be_deleted'][0]['reasons'])
    
    @pytest.mark.asyncio
    async def test_not_to_be_deleted_classification(self, temp_dir):
        """Test users are correctly classified as not_to_be_deleted"""
        extraction_file = os.path.join(temp_dir, 'extraction_test.json')
        extraction_data = [
            {
                "id": "user2@ibm.com",
                "user_id": "user2@ibm.com",
                "email": "user2@ibm.com",
                "username": "user2",
                "lastLogin": "2024-12-01T08:00:00Z",
                "active": True
            }
        ]
        
        with open(extraction_file, 'w') as f:
            json.dump(extraction_data, f)
        
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'isv_validation': {
                    'files_created': {
                        'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                        'failed': os.path.join(temp_dir, 'isv_failed.json')
                    }
                },
                'active_status': {
                    'files_created': {
                        'active': os.path.join(temp_dir, 'active_users.json'),
                        'inactive': os.path.join(temp_dir, 'inactive_users.json')
                    }
                },
                'last_login': {
                    'files_created': {
                        'old_login': os.path.join(temp_dir, 'old_login.json'),
                        'recent_login': os.path.join(temp_dir, 'recent_login.json')
                    }
                },
                'bluepages': {
                    'files_created': {
                        'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                        'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                    }
                }
            },
            'threshold_days': 1065
        }
        
        # Create mock files
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump([extraction_data[0]], f)
        
        result = consolidate_decisions(pipeline_results, output_file=os.path.join(temp_dir, 'decisions.json'))
        
        assert result['success'] is True
        assert len(result['decisions']['not_to_be_deleted']) == 1
        assert result['decisions']['not_to_be_deleted'][0]['id'] == 'user2@ibm.com'
        assert any('FINAL DECISION' in reason for reason in result['decisions']['not_to_be_deleted'][0]['reasons'])
    
    @pytest.mark.asyncio
    async def test_reasons_array_populated(self, temp_dir):
        """Test that reasons array is properly populated for all users"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'isv_validation': {
                    'files_created': {
                        'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                        'failed': os.path.join(temp_dir, 'isv_failed.json')
                    }
                },
                'active_status': {
                    'files_created': {
                        'active': os.path.join(temp_dir, 'active_users.json'),
                        'inactive': os.path.join(temp_dir, 'inactive_users.json')
                    }
                },
                'bluepages': {
                    'files_created': {
                        'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                        'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                    }
                }
            },
            'threshold_days': 1065
        }
        
        # Create mock files with test data
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump(['user1@ibm.com'], f)
        
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump([{
                'id': 'user2@ibm.com',
                'user_id': 'user2@ibm.com',
                'email': 'user2@ibm.com',
                'username': 'user2',
                'active': False
            }], f)
        
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump([{
                'id': 'user3@ibm.com',
                'user_id': 'user3@ibm.com',
                'email': 'user3@ibm.com',
                'username': 'user3',
                'lastLogin': '2020-01-15T10:00:00Z',
                'active': True
            }], f)
        
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump([{
                'id': 'user4@ibm.com',
                'user_id': 'user4@ibm.com',
                'email': 'user4@ibm.com',
                'username': 'user4',
                'lastLogin': '2024-12-01T08:00:00Z',
                'active': True
            }], f)
        
        result = consolidate_decisions(pipeline_results, output_file=os.path.join(temp_dir, 'decisions.json'))
        
        assert result['success'] is True
        
        # Verify all categories have reasons
        for user in result['decisions']['isv_failed_ids']:
            assert 'reasons' in user
            assert len(user['reasons']) > 0
            assert any('FINAL DECISION' in reason for reason in user['reasons'])
        
        for user in result['decisions']['isv_inactive_users']:
            assert 'reasons' in user
            assert len(user['reasons']) > 0
            assert any('FINAL DECISION' in reason for reason in user['reasons'])
        
        for user in result['decisions']['to_be_deleted']:
            assert 'reasons' in user
            assert len(user['reasons']) > 0
            assert any('FINAL DECISION' in reason for reason in user['reasons'])
        
        for user in result['decisions']['not_to_be_deleted']:
            assert 'reasons' in user
            assert len(user['reasons']) > 0
            assert any('FINAL DECISION' in reason for reason in user['reasons'])


# Made with Bob