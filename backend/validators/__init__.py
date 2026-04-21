"""
Validators Module - Pluggable validation functions for user data processing.

This module provides independent validators that can be:
1. Used directly by importing functions
2. Called via API endpoints
3. Chained together in a pipeline

Each validator follows the same pattern:
- Takes input data (file path or user list)
- Performs validation
- Returns results with passed/failed users
- Creates output files

Available validators:
- ISV Validator: Check if users exist in ISV system
- Active Status Validator: Check if users are active/inactive
- Login Validator: Check last login date (Cloudant)
- BluPages Validator: Validate against IBM BluPages
- Cloud Login Validator: Check last login in IBM Cloud IAM (Final Stage)
"""

from .isv_validator import validate_isv, ISVValidationError
from .active_status_validator import validate_active_status, ActiveStatusError
from .login_validator import validate_last_login, LoginValidationError
from .bluepages_validator import validate_bluepages, BluePagesError
from .cloud_login_validator import validate_cloud_login, CloudLoginError
from .pipeline import run_validation_pipeline, PipelineError

__all__ = [
    'validate_isv',
    'validate_active_status',
    'validate_last_login',
    'validate_bluepages',
    'validate_cloud_login',
    'run_validation_pipeline',
    'ISVValidationError',
    'ActiveStatusError',
    'LoginValidationError',
    'BluePagesError',
    'CloudLoginError',
    'PipelineError'
]

# Made with Bob
