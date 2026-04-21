"""
Active Status Validator - Splits users by active/inactive status

This module provides a pluggable validator that checks user active status
and splits them into two groups.

Workflow:
1. Takes resolved users (from ISV validation)
2. Checks 'active' field
3. Returns:
   - Active users (active: true)
   - Inactive users (active: false) → ISV inactive list
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class ActiveStatusError(Exception):
    """Custom exception for active status validation errors"""
    pass


def validate_active_status(
    input_file: str,
    output_dir: str = "backend/outputs",
    timestamp: Optional[str] = None,
    skip_file_creation: bool = False
) -> Dict:
    """
    Validate and split users by active status.
    
    Args:
        input_file: Path to resolved users JSON file (from ISV validation)
        output_dir: Directory to save output files
        timestamp: Optional timestamp string for filenames (auto-generated if None)
        skip_file_creation: If True, return data in-memory without creating files
        
    Returns:
        Dictionary with validation results:
        {
            "success": True,
            "validator": "active_status",
            "input_count": 1000,
            "output": {
                "active": 950,
                "inactive": 50
            },
            "files_created": {
                "active": "path/to/isv_active_users.json",
                "inactive": "path/to/isv_inactive_users.json"
            },
            "data": {  # Only present if skip_file_creation=True
                "active_users": [...],
                "inactive_users": [...]
            },
            "timestamp": "2026-04-06T10:00:00",
            "duration_seconds": 2
        }
        
    Raises:
        ActiveStatusError: If validation fails
    """
    start_time = datetime.now()
    
    try:
        # Validate input file exists
        if not Path(input_file).exists():
            return {
                "success": False,
                "error": "Input file not found",
                "message": f"File does not exist: {input_file}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        # Load resolved users
        try:
            with open(input_file, 'r') as f:
                users = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": "Invalid JSON format",
                "message": f"Failed to parse input file: {str(e)}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "error": "File read error",
                "message": f"Failed to read input file: {str(e)}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        input_count = len(users)
        
        if input_count == 0:
            return {
                "success": False,
                "error": "No users found",
                "message": "Input file contains no users",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        # Split by active status
        try:
            active_users = [user for user in users if user.get('active') == True]
            inactive_users = [user for user in users if user.get('active') == False]
        except Exception as e:
            return {
                "success": False,
                "error": "Data processing error",
                "message": f"Failed to process user data: {str(e)}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": "Directory creation failed",
                "message": f"Failed to create output directory: {str(e)}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create outputs directory for inactive users
        # Use absolute path
        import os
        current_file = os.path.abspath(__file__)
        validators_dir = os.path.dirname(current_file)
        backend_dir = os.path.dirname(validators_dir)
        project_root = os.path.dirname(backend_dir)
        outputs_dir = Path(project_root) / "backend" / "outputs"
        
        try:
            outputs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {
                "success": False,
                "error": "Directory creation failed",
                "message": f"Failed to create outputs directory: {str(e)}",
                "validator": "active_status",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create output file paths
        # Active users stay in resolutions
        active_file = Path(output_dir) / f"isv_active_users_{timestamp}.json"
        # Inactive users go to outputs (always created even if empty)
        inactive_file = outputs_dir / f"isv_inactive_users_{timestamp}.json"
        
        # Save files only if not skipping file creation
        if not skip_file_creation:
            try:
                with open(active_file, 'w') as f:
                    json.dump(active_users, f, indent=2)
                
                with open(inactive_file, 'w') as f:
                    json.dump(inactive_users, f, indent=2)
            except Exception as e:
                return {
                    "success": False,
                    "error": "File write error",
                    "message": f"Failed to save results: {str(e)}",
                    "validator": "active_status",
                    "timestamp": datetime.now().isoformat(),
                    "input_count": input_count,
                    "output": {
                        "active": len(active_users),
                        "inactive": len(inactive_users)
                    }
                }
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Build result dictionary
        result = {
            "success": True,
            "validator": "active_status",
            "input_count": input_count,
            "output": {
                "active": len(active_users),
                "inactive": len(inactive_users)
            },
            "files_created": {
                "active": str(active_file),
                "inactive": str(inactive_file)
            },
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }
        
        # Add in-memory data if skipping file creation
        if skip_file_creation:
            result["data"] = {
                "active_users": active_users,
                "inactive_users": inactive_users
            }
        
        return result
        
    except ActiveStatusError:
        # Re-raise custom validation errors
        raise
    except Exception as e:
        # Catch any unexpected errors
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        return {
            "success": False,
            "error": "Unexpected error",
            "message": f"An unexpected error occurred: {str(e)}",
            "validator": "active_status",
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }


# For direct usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python active_status_validator.py <resolved_users_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        result = validate_active_status(input_file)
        print(f"\n✓ Active Status Validation Complete!")
        print(f"  Active users: {result['output']['active']}")
        print(f"  Inactive users: {result['output']['inactive']}")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"\nFiles created:")
        print(f"  - Active: {result['files_created']['active']}")
        print(f"  - Inactive: {result['files_created']['inactive']}")
    except ActiveStatusError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Made with Bob
