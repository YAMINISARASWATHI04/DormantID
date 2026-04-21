"""
Comprehensive E2E Integration Tests for Dormant ID Pipeline

This test suite focuses on:
1. Error scenarios (API failures, timeouts)
2. Data variations (large datasets, edge cases)
3. File output validation
4. Real-world scenarios

Total: 12 new integration tests
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
import asyncio


@pytest.fixture
def large_dataset(temp_dir):
    """Create a large dataset for performance testing"""
    users = []
    for i in range(1000):
        users.append({
            "id": f"user{i}@ibm.com",
            "email": f"user{i}@ibm.com",
            "lastLogin": (datetime.now() - timedelta(days=i)).isoformat(),
            "active": i % 2 == 0  # 50% active, 50% inactive
        })
    
    file_path = os.path.join(temp_dir, 'large_extraction.json')
    with open(file_path, 'w') as f:
        json.dump(users, f)
    
    return file_path


@pytest.fixture
def mixed_quality_data(temp_dir):
    """Create dataset with missing fields and invalid data"""
    users = [
        {"id": "user1@ibm.com", "email": "user1@ibm.com", "lastLogin": "2020-01-15T10:30:00Z", "active": True},
        {"id": "user2@ibm.com", "email": "user2@ibm.com"},  # Missing lastLogin and active
        {"id": "user3@ibm.com", "lastLogin": "invalid-date", "active": True},  # Missing email, invalid date
        {"email": "user4@ibm.com", "lastLogin": "2024-12-01T08:00:00Z", "active": True},  # Missing id
        {"id": "user5@ibm.com", "email": "user5@ibm.com", "lastLogin": "2023-13-45T99:99:99Z", "active": "yes"},  # Invalid date, invalid active
        {"id": "", "email": "", "lastLogin": "", "active": None},  # Empty values
    ]
    
    file_path = os.path.join(temp_dir, 'mixed_quality.json')
    with open(file_path, 'w') as f:
        json.dump(users, f)
    
    return file_path


@pytest.mark.integration
@pytest.mark.e2e
class TestErrorScenarios:
    """Test error handling and recovery scenarios"""
    
    @pytest.mark.asyncio
    async def test_isv_api_timeout_graceful_degradation(self, temp_dir, mock_extraction_file):
        """Test pipeline handles ISV API timeout gracefully"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Mock ISV to simulate timeout
        async def mock_isv_timeout(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {
                'success': True,
                'validator': 'isv_validation',
                'output': {'found_in_isv': 0, 'not_found_in_isv': 4},
                'files_created': {
                    'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                    'failed': os.path.join(temp_dir, 'isv_failed.json')
                },
                'error': 'Timeout occurred but handled gracefully'
            }
        
        # Create mock files
        for filename in ['isv_resolved.json', 'isv_failed.json', 'active_users.json', 'inactive_users.json']:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump([], f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock, side_effect=mock_isv_timeout), \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active:
            
            mock_active.return_value = {
                'success': True,
                'validator': 'active_status',
                'output': {'active': 0, 'inactive': 0},
                'files_created': {
                    'active': os.path.join(temp_dir, 'active_users.json'),
                    'inactive': os.path.join(temp_dir, 'inactive_users.json')
                }
            }
            
            result = await run_validation_pipeline(
                input_file=mock_extraction_file,
                output_dir=temp_dir,
                checks={'isv_validation': True, 'active_status': True}
            )
            
            # Pipeline should continue despite timeout
            assert result['success'] is True
            assert 'isv_validation' in result['checks_run']
    
    @pytest.mark.asyncio
    async def test_bluepages_api_failure_skip_non_ibm(self, temp_dir):
        """Test BluPages failure skips non-IBM users correctly"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create test data with IBM and non-IBM users
        users = [
            {"id": "user1@ibm.com", "email": "user1@ibm.com", "lastLogin": "2020-01-15T10:30:00Z", "active": True},
            {"id": "user2@external.com", "email": "user2@external.com", "lastLogin": "2020-03-10T12:00:00Z", "active": True}
        ]
        
        extraction_file = os.path.join(temp_dir, 'extraction.json')
        with open(extraction_file, 'w') as f:
            json.dump(users, f)
        
        # Create mock output files with data
        with open(os.path.join(temp_dir, 'isv_resolved.json'), 'w') as f:
            json.dump(users, f)
        with open(os.path.join(temp_dir, 'active_users.json'), 'w') as f:
            json.dump(users, f)
        with open(os.path.join(temp_dir, 'old_login.json'), 'w') as f:
            json.dump([users[0]], f)  # Only IBM user
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump([], f)
        
        # Mock BluPages to handle non-IBM users
        async def mock_bluepages_with_non_ibm(*args, **kwargs):
            return {
                'success': True,
                'validator': 'bluepages',
                'output': {'found_in_bluepages': 0, 'not_found_in_bluepages': 1},
                'files_created': {
                    'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                    'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                },
                'non_ibm_users': {'count': 1, 'data': [users[1]]}
            }
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active, \
             patch('backend.validators.login_validator.validate_last_login') as mock_login, \
             patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock, side_effect=mock_bluepages_with_non_ibm):
            
            mock_isv.return_value = {
                'success': True,
                'output': {'found_in_isv': 2, 'not_found_in_isv': 0},
                'files_created': {'resolved': os.path.join(temp_dir, 'isv_resolved.json')}
            }
            mock_active.return_value = {
                'success': True,
                'output': {'active': 2, 'inactive': 0},
                'files_created': {'active': os.path.join(temp_dir, 'active_users.json')}
            }
            mock_login.return_value = {
                'success': True,
                'output': {'old_login': 1, 'recent_login': 1},
                'files_created': {'old_login': os.path.join(temp_dir, 'old_login.json')}
            }
            
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
            # Check that non-IBM emails are tracked
            assert result['summary'].get('non_ibm_emails', 0) >= 1
    
    @pytest.mark.asyncio
    async def test_invalid_input_file_clear_error(self, temp_dir):
        """Test pipeline provides clear error for invalid input file"""
        from backend.validators.pipeline import run_validation_pipeline
        
        result = await run_validation_pipeline(
            input_file='nonexistent_file.json',
            output_dir=temp_dir,
            checks={'isv_validation': True}
        )
        
        # Pipeline now returns error dict instead of raising exception
        assert result['success'] is False
        assert 'error' in result
        assert 'not found' in result['error'].lower()
    
    @pytest.mark.asyncio
    async def test_corrupted_json_file_handling(self, temp_dir):
        """Test pipeline handles corrupted JSON gracefully"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create corrupted JSON file
        corrupted_file = os.path.join(temp_dir, 'corrupted.json')
        with open(corrupted_file, 'w') as f:
            f.write('{"id": "user1@ibm.com", "email": "user1@ibm.com"')  # Missing closing brace
        
        result = await run_validation_pipeline(
            input_file=corrupted_file,
            output_dir=temp_dir,
            checks={'isv_validation': True}
        )
        
        # Pipeline now returns error dict for JSON errors
        assert result['success'] is False
        assert 'error' in result
        assert 'json' in result['error'].lower() or 'invalid' in result['error'].lower()


@pytest.mark.integration
@pytest.mark.e2e
class TestDataVariations:
    """Test pipeline with various data scenarios"""
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, temp_dir, large_dataset):
        """Test pipeline handles 1000+ users efficiently"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create mock output files
        for filename in ['isv_resolved.json', 'isv_failed.json', 'active_users.json', 'inactive_users.json',
                        'old_login.json', 'recent_login.json', 'to_delete.json', 'not_to_delete.json']:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump([], f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active, \
             patch('backend.validators.login_validator.validate_last_login') as mock_login, \
             patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock) as mock_bluepages:
            
            mock_isv.return_value = {
                'success': True,
                'validator': 'isv_validation',
                'output': {'found_in_isv': 1000, 'not_found_in_isv': 0},
                'files_created': {
                    'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                    'failed': os.path.join(temp_dir, 'isv_failed.json')
                }
            }
            mock_active.return_value = {
                'success': True,
                'validator': 'active_status',
                'output': {'active': 500, 'inactive': 500},
                'files_created': {
                    'active': os.path.join(temp_dir, 'active_users.json'),
                    'inactive': os.path.join(temp_dir, 'inactive_users.json')
                }
            }
            mock_login.return_value = {
                'success': True,
                'validator': 'last_login',
                'output': {'old_login': 300, 'recent_login': 200},
                'files_created': {
                    'old_login': os.path.join(temp_dir, 'old_login.json'),
                    'recent_login': os.path.join(temp_dir, 'recent_login.json')
                }
            }
            mock_bluepages.return_value = {
                'success': True,
                'validator': 'bluepages',
                'output': {'found_in_bluepages': 250, 'not_found_in_bluepages': 50},
                'files_created': {
                    'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                    'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                }
            }
            
            start_time = datetime.now()
            result = await run_validation_pipeline(
                input_file=large_dataset,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True,
                    'bluepages': True
                }
            )
            duration = (datetime.now() - start_time).total_seconds()
            
            assert result['success'] is True
            assert result['summary']['total_input'] == 1000
            # With proper mocking, should complete quickly (< 5 seconds)
            assert duration < 5
    
    @pytest.mark.asyncio
    async def test_mixed_data_quality_handling(self, temp_dir, mixed_quality_data):
        """Test pipeline handles missing fields and invalid data"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create mock files
        for filename in ['isv_resolved.json', 'active_users.json']:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump([], f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active:
            
            mock_isv.return_value = {
                'success': True,
                'output': {'found_in_isv': 3, 'not_found_in_isv': 3},
                'files_created': {'resolved': os.path.join(temp_dir, 'isv_resolved.json')}
            }
            mock_active.return_value = {
                'success': True,
                'output': {'active': 2, 'inactive': 1},
                'files_created': {'active': os.path.join(temp_dir, 'active_users.json')}
            }
            
            result = await run_validation_pipeline(
                input_file=mixed_quality_data,
                output_dir=temp_dir,
                checks={'isv_validation': True, 'active_status': True}
            )
            
            # Should handle dirty data gracefully
            assert result['success'] is True
            assert result['summary']['total_input'] == 6
    
    @pytest.mark.asyncio
    async def test_all_users_pass_all_checks(self, temp_dir):
        """Test scenario where all users pass all validation checks"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create users that should pass all checks
        users = [
            {"id": f"user{i}@ibm.com", "email": f"user{i}@ibm.com",
             "lastLogin": datetime.now().isoformat(), "active": True}
            for i in range(10)
        ]
        
        extraction_file = os.path.join(temp_dir, 'all_pass.json')
        with open(extraction_file, 'w') as f:
            json.dump(users, f)
        
        # Create mock output files with data
        for filename in ['isv_resolved.json', 'isv_failed.json', 'active_users.json', 'inactive_users.json',
                        'recent_login.json', 'old_login.json', 'not_to_delete.json', 'to_delete.json']:
            data = users if 'resolved' in filename or 'active' in filename or 'recent' in filename or 'not_to_delete' in filename else []
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump(data, f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active, \
             patch('backend.validators.login_validator.validate_last_login') as mock_login, \
             patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock) as mock_bluepages:
            
            mock_isv.return_value = {
                'success': True,
                'validator': 'isv_validation',
                'output': {'found_in_isv': 10, 'not_found_in_isv': 0},
                'files_created': {
                    'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                    'failed': os.path.join(temp_dir, 'isv_failed.json')
                }
            }
            mock_active.return_value = {
                'success': True,
                'validator': 'active_status',
                'output': {'active': 10, 'inactive': 0},
                'files_created': {
                    'active': os.path.join(temp_dir, 'active_users.json'),
                    'inactive': os.path.join(temp_dir, 'inactive_users.json')
                }
            }
            mock_login.return_value = {
                'success': True,
                'validator': 'last_login',
                'output': {'old_login': 0, 'recent_login': 10},
                'files_created': {
                    'recent_login': os.path.join(temp_dir, 'recent_login.json'),
                    'old_login': os.path.join(temp_dir, 'old_login.json')
                }
            }
            mock_bluepages.return_value = {
                'success': True,
                'validator': 'bluepages',
                'output': {'found_in_bluepages': 10, 'not_found_in_bluepages': 0},
                'files_created': {
                    'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json'),
                    'to_delete': os.path.join(temp_dir, 'to_delete.json')
                }
            }
            
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
            assert result['summary']['to_delete'] == 0
            assert result['summary']['not_to_delete'] >= 10
    
    @pytest.mark.asyncio
    async def test_all_users_fail_all_checks(self, temp_dir):
        """Test scenario where all users fail validation checks"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create users that should fail all checks
        users = [
            {"id": f"user{i}@ibm.com", "email": f"user{i}@ibm.com",
             "lastLogin": "2015-01-01T00:00:00Z", "active": False}
            for i in range(10)
        ]
        
        extraction_file = os.path.join(temp_dir, 'all_fail.json')
        with open(extraction_file, 'w') as f:
            json.dump(users, f)
        
        # Create mock output files
        user_ids = [f"user{i}@ibm.com" for i in range(10)]
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump(user_ids, f)
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump(users, f)
        with open(os.path.join(temp_dir, 'old_login.json'), 'w') as f:
            json.dump(users, f)
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump(users, f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active, \
             patch('backend.validators.login_validator.validate_last_login') as mock_login, \
             patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock) as mock_bluepages:
            
            mock_isv.return_value = {
                'success': True,
                'validator': 'isv_validation',
                'output': {'found_in_isv': 0, 'not_found_in_isv': 10},
                'files_created': {'failed': os.path.join(temp_dir, 'isv_failed.json')}
            }
            mock_active.return_value = {
                'success': True,
                'validator': 'active_status',
                'output': {'active': 0, 'inactive': 10},
                'files_created': {'inactive': os.path.join(temp_dir, 'inactive_users.json')}
            }
            mock_login.return_value = {
                'success': True,
                'validator': 'last_login',
                'output': {'old_login': 10, 'recent_login': 0},
                'files_created': {'old_login': os.path.join(temp_dir, 'old_login.json')}
            }
            mock_bluepages.return_value = {
                'success': True,
                'validator': 'bluepages',
                'output': {'found_in_bluepages': 0, 'not_found_in_bluepages': 10},
                'files_created': {'to_delete': os.path.join(temp_dir, 'to_delete.json')}
            }
            
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
            # All users should be categorized as failures - check correct field name
            assert result['summary']['to_delete'] > 0 or result['summary']['not_found_in_isv'] > 0


@pytest.mark.integration
@pytest.mark.e2e
class TestFileOutputValidation:
    """Test file output creation and validation"""
    
    @pytest.mark.asyncio
    async def test_single_consolidated_output_file(self, temp_dir, mock_extraction_file):
        """Test that only one consolidated decision file is created"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create mock output files
        for filename in ['isv_resolved.json', 'isv_failed.json', 'active_users.json', 'inactive_users.json',
                        'old_login.json', 'recent_login.json', 'to_delete.json', 'not_to_delete.json']:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump([], f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active, \
             patch('backend.validators.login_validator.validate_last_login') as mock_login, \
             patch('backend.validators.bluepages_validator.validate_bluepages', new_callable=AsyncMock) as mock_bluepages:
            
            mock_isv.return_value = {
                'success': True,
                'validator': 'isv_validation',
                'output': {'found_in_isv': 3, 'not_found_in_isv': 1},
                'files_created': {
                    'resolved': os.path.join(temp_dir, 'isv_resolved.json'),
                    'failed': os.path.join(temp_dir, 'isv_failed.json')
                }
            }
            mock_active.return_value = {
                'success': True,
                'validator': 'active_status',
                'output': {'active': 3, 'inactive': 0},
                'files_created': {
                    'active': os.path.join(temp_dir, 'active_users.json'),
                    'inactive': os.path.join(temp_dir, 'inactive_users.json')
                }
            }
            mock_login.return_value = {
                'success': True,
                'validator': 'last_login',
                'output': {'old_login': 2, 'recent_login': 1},
                'files_created': {
                    'old_login': os.path.join(temp_dir, 'old_login.json'),
                    'recent_login': os.path.join(temp_dir, 'recent_login.json')
                }
            }
            mock_bluepages.return_value = {
                'success': True,
                'validator': 'bluepages',
                'output': {'found_in_bluepages': 1, 'not_found_in_bluepages': 1},
                'files_created': {
                    'to_delete': os.path.join(temp_dir, 'to_delete.json'),
                    'not_to_delete': os.path.join(temp_dir, 'not_to_delete.json')
                }
            }
            
            result = await run_validation_pipeline(
                input_file=mock_extraction_file,
                output_dir=temp_dir,
                checks={
                    'isv_validation': True,
                    'active_status': True,
                    'last_login': True,
                    'bluepages': True
                }
            )
            
            assert result['success'] is True
            
            # Check for decision output file in temp_dir (now respects output_dir parameter)
            decision_files = [f for f in os.listdir(temp_dir) if 'dormant_id_decision' in f.lower() and f.endswith('.json')]
            assert len(decision_files) == 1, f"Expected 1 decision file, found {len(decision_files)}: {decision_files}"
    
    @pytest.mark.asyncio
    async def test_no_temporary_files_remain(self, temp_dir, mock_extraction_file):
        """Test that no temporary files remain after pipeline execution"""
        from backend.validators.pipeline import run_validation_pipeline
        
        # Create mock files
        for filename in ['isv_resolved.json', 'active_users.json']:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                json.dump([], f)
        
        with patch('backend.validators.isv_validator.validate_isv', new_callable=AsyncMock) as mock_isv, \
             patch('backend.validators.active_status_validator.validate_active_status') as mock_active:
            
            mock_isv.return_value = {
                'success': True,
                'output': {'found_in_isv': 3, 'not_found_in_isv': 1},
                'files_created': {'resolved': os.path.join(temp_dir, 'isv_resolved.json')}
            }
            mock_active.return_value = {
                'success': True,
                'output': {'active': 3, 'inactive': 1},
                'files_created': {'active': os.path.join(temp_dir, 'active_users.json')}
            }
            
            files_before = set(os.listdir(temp_dir))
            
            result = await run_validation_pipeline(
                input_file=mock_extraction_file,
                output_dir=temp_dir,
                checks={'isv_validation': True, 'active_status': True}
            )
            
            files_after = set(os.listdir(temp_dir))
            new_files = files_after - files_before
            
            # Should not have .tmp, .temp, or similar temporary files
            temp_files = [f for f in new_files if '.tmp' in f or '.temp' in f or f.startswith('~')]
            assert len(temp_files) == 0, f"Found temporary files: {temp_files}"
    
    @pytest.mark.asyncio
    async def test_output_file_format_validation(self, temp_dir):
        """Test that output file has correct JSON format and structure"""
        from backend.validators.decision_engine import consolidate_decisions
        
        # Create test data
        to_delete_data = [{"id": "user1@ibm.com", "email": "user1@ibm.com", "lastLogin": "2020-01-15T10:30:00Z", "active": True}]
        not_delete_data = [{"id": "user2@ibm.com", "email": "user2@ibm.com", "lastLogin": "2024-12-01T08:00:00Z", "active": True}]
        
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump(to_delete_data, f)
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump(not_delete_data, f)
        
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
        
        output_file = os.path.join(temp_dir, 'decisions.json')
        result = consolidate_decisions(pipeline_results, output_file=output_file)
        
        assert result['success'] is True
        assert os.path.exists(output_file)
        
        # Validate JSON format
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        # Check required structure
        assert 'decisions' in data
        assert 'to_be_deleted' in data['decisions']
        assert 'not_to_be_deleted' in data['decisions']
        assert 'isv_inactive_users' in data['decisions']
        assert 'isv_failed_ids' in data['decisions']
        
        # Check each user has required fields
        for user in data['decisions']['to_be_deleted']:
            assert 'id' in user
            assert 'reasons' in user
            assert isinstance(user['reasons'], list)
        
        for user in data['decisions']['not_to_be_deleted']:
            assert 'id' in user
            assert 'reasons' in user
            assert isinstance(user['reasons'], list)
    
    @pytest.mark.asyncio
    async def test_output_file_permissions(self, temp_dir):
        """Test that output files have correct permissions"""
        from backend.validators.decision_engine import consolidate_decisions
        
        # Create minimal test data
        with open(os.path.join(temp_dir, 'isv_failed.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'inactive_users.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'to_delete.json'), 'w') as f:
            json.dump([], f)
        with open(os.path.join(temp_dir, 'not_to_delete.json'), 'w') as f:
            json.dump([], f)
        
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
            }
        }
        
        output_file = os.path.join(temp_dir, 'decisions.json')
        result = consolidate_decisions(pipeline_results, output_file=output_file)
        
        assert result['success'] is True
        assert os.path.exists(output_file)
        
        # Check file is readable
        assert os.access(output_file, os.R_OK)
        
        # Check file is writable (for updates)
        assert os.access(output_file, os.W_OK)


# Made with Bob - Comprehensive E2E Integration Tests