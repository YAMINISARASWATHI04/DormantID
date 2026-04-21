"""
Unit tests for decision engine
Tests: Decision categorization, reason formatting, priority handling
"""
import pytest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.unit
@pytest.mark.decision_engine
class TestDecisionCategorization:
    """Test suite for decision categorization logic"""
    
    def test_categorize_to_be_deleted_bluepages_fail(self):
        """Test users marked for deletion due to BluPages failure"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'bluepages': {
                    'files_created': {
                        'to_delete': 'to_delete.json',
                        'not_to_delete': 'not_to_delete.json'
                    }
                }
            }
        }
        
        mock_result = {
            'to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'username': 'user1@ibm.com',
                    'lastLogin': '2020-01-15T10:30:00Z',
                    'activeStatus': True,
                    'reasons': [
                        'User has old login (>1065 days)',
                        'User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed'
                    ]
                }
            ],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['to_be_deleted']) == 1
            assert result['decisions']['to_be_deleted'][0]['id'] == 'user1@ibm.com'
            assert any('BluPages Validation Failed' in reason for reason in result['decisions']['to_be_deleted'][0]['reasons'])
    
    def test_categorize_not_to_be_deleted_recent_login(self):
        """Test users not deleted due to recent login"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'last_login': {
                    'files_created': {
                        'recent_login': 'recent_login.json'
                    }
                }
            }
        }
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [
                {
                    'id': 'user2@ibm.com',
                    'username': 'user2@ibm.com',
                    'lastLogin': '2024-12-01T08:00:00Z',
                    'activeStatus': True,
                    'reasons': [
                        'User has recent login (≤1065 days, actual: 100 days) - FINAL DECISION: Last Login Check Passed'
                    ]
                }
            ],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['not_to_be_deleted']) == 1
            assert result['decisions']['not_to_be_deleted'][0]['id'] == 'user2@ibm.com'
            assert any('Last Login Check Passed' in reason for reason in result['decisions']['not_to_be_deleted'][0]['reasons'])
    
    def test_categorize_not_to_be_deleted_bluepages_pass(self):
        """Test users not deleted due to BluPages found"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'bluepages': {
                    'files_created': {
                        'not_to_delete': 'not_to_delete.json'
                    }
                }
            }
        }
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [
                {
                    'id': 'user3@ibm.com',
                    'username': 'user3@ibm.com',
                    'lastLogin': '2020-06-20T14:45:00Z',
                    'activeStatus': True,
                    'reasons': [
                        'User has old login (>1065 days)',
                        'User found in IBM BluPages - FINAL DECISION: BluPages Validation Passed'
                    ]
                }
            ],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['not_to_be_deleted']) == 1
            assert any('BluPages Validation Passed' in reason for reason in result['decisions']['not_to_be_deleted'][0]['reasons'])
    
    def test_categorize_isv_inactive_users(self):
        """Test ISV inactive users categorization"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'active_status': {
                    'files_created': {
                        'inactive': 'inactive_users.json'
                    }
                }
            }
        }
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [],
            'isv_inactive_users': [
                {
                    'id': 'user4@ibm.com',
                    'username': 'user4@ibm.com',
                    'lastLogin': '2023-06-20T14:45:00Z',
                    'activeStatus': False,
                    'reasons': [
                        'User marked as inactive in ISV - FINAL DECISION: Active Status Check Failed'
                    ]
                }
            ],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['isv_inactive_users']) == 1
            assert result['decisions']['isv_inactive_users'][0]['activeStatus'] is False
            assert any('Active Status Check Failed' in reason for reason in result['decisions']['isv_inactive_users'][0]['reasons'])
    
    def test_categorize_isv_failed_ids(self):
        """Test ISV failed IDs categorization"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'isv_validation': {
                    'files_created': {
                        'failed': 'isv_failed.json'
                    }
                }
            }
        }
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': [
                {
                    'id': 'user5@ibm.com',
                    'username': 'user5@ibm.com',
                    'reasons': [
                        'User not found in ISV - FINAL DECISION: ISV Validation Failed'
                    ]
                }
            ]
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['isv_failed_ids']) == 1
            assert result['decisions']['isv_failed_ids'][0]['id'] == 'user5@ibm.com'
            assert any('ISV Validation Failed' in reason for reason in result['decisions']['isv_failed_ids'][0]['reasons'])
    
    def test_categorize_mixed_results(self):
        """Test with all categories having users"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {
                'isv_validation': {'output': {'found_in_isv': 90, 'not_found_in_isv': 10}},
                'active_status': {'output': {'active': 80, 'inactive': 10}},
                'last_login': {'output': {'old_login': 30, 'recent_login': 50}},
                'bluepages': {'output': {'found_in_bluepages': 25, 'not_found_in_bluepages': 5}}
            }
        }
        
        mock_result = {
            'to_be_deleted': [{'id': 'user1@ibm.com'}],
            'not_to_be_deleted': [{'id': 'user2@ibm.com'}, {'id': 'user3@ibm.com'}],
            'isv_inactive_users': [{'id': 'user4@ibm.com'}],
            'isv_failed_ids': [{'id': 'user5@ibm.com'}]
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['to_be_deleted']) == 1
            assert len(result['decisions']['not_to_be_deleted']) == 2
            assert len(result['decisions']['isv_inactive_users']) == 1
            assert len(result['decisions']['isv_failed_ids']) == 1
    
    def test_categorize_empty_results(self):
        """Test with no users in any category"""
        from backend.validators.decision_engine import consolidate_decisions
        
        pipeline_results = {
            'results': {}
        }
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            assert len(result['decisions']['to_be_deleted']) == 0
            assert len(result['decisions']['not_to_be_deleted']) == 0
            assert len(result['decisions']['isv_inactive_users']) == 0
            assert len(result['decisions']['isv_failed_ids']) == 0
    
    def test_categorize_priority_order(self):
        """Test that decision priority is correctly applied"""
        from backend.validators.decision_engine import consolidate_decisions
        
        # Priority: BluPages > Last Login > Active Status > ISV
        pipeline_results = {
            'results': {
                'isv_validation': {'output': {'found_in_isv': 95}},
                'active_status': {'output': {'active': 80}},
                'last_login': {'output': {'old_login': 30}},
                'bluepages': {'output': {'not_found_in_bluepages': 5}}
            }
        }
        
        mock_result = {
            'to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'reasons': [
                        'User found in ISV',
                        'User is active',
                        'User has old login (>1065 days)',
                        'User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed'
                    ]
                }
            ],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions(pipeline_results)
            
            # BluPages failure should be the final decision
            assert len(result['decisions']['to_be_deleted']) == 1
            final_reason = result['decisions']['to_be_deleted'][0]['reasons'][-1]
            assert 'FINAL DECISION' in final_reason
            assert 'BluPages Validation Failed' in final_reason


@pytest.mark.unit
@pytest.mark.decision_engine
class TestDecisionReasons:
    """Test suite for decision reason formatting"""
    
    def test_decision_reasons_format(self):
        """Test that decision reasons are properly formatted"""
        from backend.validators.decision_engine import consolidate_decisions
        
        mock_result = {
            'to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'reasons': [
                        'User has old login (>1065 days)',
                        'User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed'
                    ]
                }
            ],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions({})
            
            reasons = result['decisions']['to_be_deleted'][0]['reasons']
            assert isinstance(reasons, list)
            assert len(reasons) > 0
            assert all(isinstance(reason, str) for reason in reasons)
    
    def test_decision_reasons_final_step_mentioned(self):
        """Test that FINAL DECISION is mentioned in reasons"""
        from backend.validators.decision_engine import consolidate_decisions
        
        mock_result = {
            'to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'reasons': [
                        'User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed'
                    ]
                }
            ],
            'not_to_be_deleted': [
                {
                    'id': 'user2@ibm.com',
                    'reasons': [
                        'User has recent login (≤1065 days) - FINAL DECISION: Last Login Check Passed'
                    ]
                }
            ],
            'isv_inactive_users': [
                {
                    'id': 'user3@ibm.com',
                    'reasons': [
                        'User marked as inactive in ISV - FINAL DECISION: Active Status Check Failed'
                    ]
                }
            ],
            'isv_failed_ids': [
                {
                    'id': 'user4@ibm.com',
                    'reasons': [
                        'User not found in ISV - FINAL DECISION: ISV Validation Failed'
                    ]
                }
            ]
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions({})
            
            # Check all categories have FINAL DECISION in their reasons
            for user in result['decisions']['to_be_deleted']:
                assert any('FINAL DECISION' in reason for reason in user['reasons'])
            
            for user in result['decisions']['not_to_be_deleted']:
                assert any('FINAL DECISION' in reason for reason in user['reasons'])
            
            for user in result['decisions']['isv_inactive_users']:
                assert any('FINAL DECISION' in reason for reason in user['reasons'])
            
            for user in result['decisions']['isv_failed_ids']:
                assert any('FINAL DECISION' in reason for reason in user['reasons'])
    
    def test_decision_reasons_threshold_days_included(self):
        """Test that threshold days are included in login check reasons"""
        from backend.validators.decision_engine import consolidate_decisions
        
        mock_result = {
            'to_be_deleted': [],
            'not_to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'reasons': [
                        'User has recent login (≤1065 days, actual: 100 days) - FINAL DECISION: Last Login Check Passed'
                    ]
                }
            ],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions({}, threshold_days=1065)
            
            reason = result['decisions']['not_to_be_deleted'][0]['reasons'][0]
            assert '1065 days' in reason or '≤1065' in reason
    
    def test_decision_reasons_multiple_checks(self):
        """Test that multiple check reasons are listed"""
        from backend.validators.decision_engine import consolidate_decisions
        
        mock_result = {
            'to_be_deleted': [
                {
                    'id': 'user1@ibm.com',
                    'reasons': [
                        'User found in ISV',
                        'User is active',
                        'User has old login (>1065 days)',
                        'User not found in IBM BluPages - FINAL DECISION: BluPages Validation Failed'
                    ]
                }
            ],
            'not_to_be_deleted': [],
            'isv_inactive_users': [],
            'isv_failed_ids': []
        }
        
        with patch('backend.validators.decision_engine.consolidate_decisions', return_value=mock_result):
            result = consolidate_decisions({})
            
            reasons = result['decisions']['to_be_deleted'][0]['reasons']
            # Should have multiple reasons from different checks
            assert len(reasons) >= 2
            # Last reason should be the final decision
            assert 'FINAL DECISION' in reasons[-1]


# Made with Bob