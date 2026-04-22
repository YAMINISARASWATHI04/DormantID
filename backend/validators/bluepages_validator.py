"""
BluPages Validator - Validates users against IBM BluPages

This module provides a pluggable wrapper around the existing BluPages validator.
It checks if users exist in IBM BluPages directory.

Workflow:
1. Takes users with old login (>1065 days)
2. Queries IBM BluPages API
3. Returns:
   - Users found in BluPages → Not to be deleted
   - Users not found in BluPages → To be deleted
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bluepages_validator_async import validate_users_async
import asyncio


class BluePagesError(Exception):
    """Custom exception for BluPages validation errors"""
    pass


async def validate_bluepages(
    input_file: Optional[str] = None,
    users_data: Optional[List] = None,
    output_dir: str = "backend/outputs",
    timestamp: Optional[str] = None,
    max_concurrent: int = 50,
    batch_size: int = 100,
    skip_file_creation: bool = False,
    return_cloud_candidates: bool = False
) -> Dict:
    """
    Validate users against IBM BluPages.
    
    This is a wrapper around the existing bluepages_validator_async that provides
    a clean, pluggable interface for BluPages validation.
    
    Args:
        input_file: Path to users JSON file (old login users) - optional if users_data provided
        users_data: List of user dictionaries - optional if input_file provided
        output_dir: Directory to save output files
        timestamp: Optional timestamp string for filenames (auto-generated if None)
        max_concurrent: Maximum concurrent API requests
        batch_size: Number of users to process per batch
        skip_file_creation: If True, return data in-memory without creating files
        return_cloud_candidates: If True, return cloud check candidates in-memory instead of creating to_be_deleted file
        
    Returns:
        Dictionary with validation results:
        {
            "success": True,
            "validator": "bluepages",
            "input_count": 234,
            "output": {
                "found_in_bluepages": 200,
                "not_found_in_bluepages": 34
            },
            "files_created": {
                "to_delete": "path/to/to_be_deleted.json",
                "not_to_delete": "path/to/not_to_be_deleted.json"
            },
            "data": {  # Only present if skip_file_creation=True
                "to_delete_users": [...],
                "not_to_delete_users": [...]
            },
            "timestamp": "2026-04-06T10:00:00",
            "duration_seconds": 120
        }
        
    Raises:
        BluePagesError: If validation fails
    """
    start_time = datetime.now()
    
    try:
        # Load users from file or use provided data
        if users_data is not None:
            users = users_data
        elif input_file is not None:
            # Validate input file exists
            if not Path(input_file).exists():
                return {
                    "success": False,
                    "error": "Input file not found",
                    "message": f"File does not exist: {input_file}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Load users
            try:
                with open(input_file, 'r') as f:
                    users = json.load(f)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": "Invalid JSON format",
                    "message": f"Failed to parse input file: {str(e)}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": "File read error",
                    "message": f"Failed to read input file: {str(e)}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "success": False,
                "error": "Missing input",
                "message": "Either input_file or users_data must be provided",
                "validator": "bluepages",
                "timestamp": datetime.now().isoformat()
            }
        
        input_count = len(users)
        
        if input_count == 0:
            return {
                "success": False,
                "error": "No users found",
                "message": "Input contains no users to validate",
                "validator": "bluepages",
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
                "validator": "bluepages",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create outputs directory for final results
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
                "validator": "bluepages",
                "timestamp": datetime.now().isoformat()
            }
        
        # Create output file paths - final outputs go to outputs folder
        # Only create to_delete_file if not returning cloud candidates in-memory
        if not return_cloud_candidates:
            to_delete_file = outputs_dir / f"to_be_deleted_{timestamp}.json"
        else:
            to_delete_file = None
        
        not_to_delete_file = outputs_dir / "not_to_be_deleted.json"
        
        # Use a temporary file for BluPages results
        temp_bluepages_file = Path(output_dir) / f"temp_bluepages_{timestamp}.json"
        
        # If users_data provided, create a temporary input file in outputs directory
        temp_input_file = None
        if users_data is not None:
            try:
                temp_input_file = outputs_dir / f"temp_input_{timestamp}.json"
                with open(temp_input_file, 'w') as f:
                    json.dump(users, f, indent=2)
                input_file_to_use: str = str(temp_input_file)
            except Exception as e:
                return {
                    "success": False,
                    "error": "File write error",
                    "message": f"Failed to create temporary input file: {str(e)}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat()
                }
        elif input_file is not None:
            input_file_to_use = input_file
        else:
            return {
                "success": False,
                "error": "Missing input",
                "message": "Either input_file or users_data must be provided",
                "validator": "bluepages",
                "timestamp": datetime.now().isoformat()
            }
        
        # Run BluPages validation using existing async validator only if not skipping
        if not skip_file_creation:
            try:
                # Create a temporary to_delete file if returning cloud candidates
                if return_cloud_candidates:
                    temp_to_delete_file = Path(output_dir) / f"temp_to_delete_{timestamp}.json"
                    to_delete_file_str = str(temp_to_delete_file)
                else:
                    to_delete_file_str = str(to_delete_file)
                
                await asyncio.wait_for(
                    validate_users_async(
                        input_file=input_file_to_use,
                        to_delete_file=to_delete_file_str,
                        not_to_delete_file=str(temp_bluepages_file),  # Use temp file
                        test_mode=False,
                        resume=False,
                        max_concurrent=max_concurrent,
                        batch_size=batch_size
                    ),
                    timeout=600  # 10 minute timeout
                )
            except asyncio.TimeoutError:
                # Clean up temp file if exists
                if temp_input_file and temp_input_file.exists():
                    temp_input_file.unlink()
                return {
                    "success": False,
                    "error": "API timeout",
                    "message": "BluPages API request timed out after 600 seconds",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat(),
                    "input_count": input_count
                }
            except ConnectionError as e:
                # Clean up temp file if exists
                if temp_input_file and temp_input_file.exists():
                    temp_input_file.unlink()
                return {
                    "success": False,
                    "error": "Connection error",
                    "message": f"Failed to connect to BluPages API: {str(e)}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat(),
                    "input_count": input_count
                }
            except Exception as e:
                # Clean up temp file if exists
                if temp_input_file and temp_input_file.exists():
                    temp_input_file.unlink()
                return {
                    "success": False,
                    "error": "API error",
                    "message": f"BluPages API request failed: {str(e)}",
                    "validator": "bluepages",
                    "timestamp": datetime.now().isoformat(),
                    "input_count": input_count
                }
        
        # Clean up temporary input file if created
        if temp_input_file and temp_input_file.exists():
            try:
                temp_input_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors
        
        # Load or prepare BluPages results
        bluepages_users = []
        to_delete_users = []
        
        if skip_file_creation:
            # Simulate BluPages validation in-memory (for testing)
            # In real scenario, we'd still call the API but not save files
            bluepages_users = []
            to_delete_users = users  # Simplified for testing
        else:
            # Append BluPages results to not_to_be_deleted.json
            if temp_bluepages_file.exists():
                try:
                    with open(temp_bluepages_file, 'r') as f:
                        bluepages_users = json.load(f)
                except Exception as e:
                    return {
                        "success": False,
                        "error": "File read error",
                        "message": f"Failed to read BluPages results: {str(e)}",
                        "validator": "bluepages",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Merge with existing not_to_be_deleted.json
            if not_to_delete_file.exists():
                try:
                    with open(not_to_delete_file, 'r') as f:
                        existing_users = json.load(f)
                    
                    # Avoid duplicates by user_id
                    existing_user_ids = {user.get('user_id') for user in existing_users if 'user_id' in user}
                    new_users = [user for user in bluepages_users if user.get('user_id') not in existing_user_ids]
                    
                    combined_users = existing_users + new_users
                    
                    with open(not_to_delete_file, 'w') as f:
                        json.dump(combined_users, f, indent=2)
                except (json.JSONDecodeError, KeyError):
                    # If existing file is invalid, overwrite it
                    try:
                        with open(not_to_delete_file, 'w') as f:
                            json.dump(bluepages_users, f, indent=2)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": "File write error",
                            "message": f"Failed to write results: {str(e)}",
                            "validator": "bluepages",
                            "timestamp": datetime.now().isoformat()
                        }
            else:
                try:
                    with open(not_to_delete_file, 'w') as f:
                        json.dump(bluepages_users, f, indent=2)
                except Exception as e:
                    return {
                        "success": False,
                        "error": "File write error",
                        "message": f"Failed to write results: {str(e)}",
                        "validator": "bluepages",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Clean up temp file
            if temp_bluepages_file.exists():
                try:
                    temp_bluepages_file.unlink()
                except Exception:
                    pass  # Ignore cleanup errors
            
            # Load to_delete results
            if return_cloud_candidates:
                # Read from temporary file
                temp_to_delete_file = Path(output_dir) / f"temp_to_delete_{timestamp}.json"
                if temp_to_delete_file.exists():
                    try:
                        with open(temp_to_delete_file, 'r') as f:
                            to_delete_users = json.load(f)
                        # Clean up temp file
                        temp_to_delete_file.unlink()
                    except Exception as e:
                        return {
                            "success": False,
                            "error": "File read error",
                            "message": f"Failed to read to_delete results: {str(e)}",
                            "validator": "bluepages",
                            "timestamp": datetime.now().isoformat()
                        }
            elif to_delete_file and to_delete_file.exists():
                try:
                    with open(to_delete_file, 'r') as f:
                        to_delete_users = json.load(f)
                except Exception as e:
                    return {
                        "success": False,
                        "error": "File read error",
                        "message": f"Failed to read to_delete results: {str(e)}",
                        "validator": "bluepages",
                        "timestamp": datetime.now().isoformat()
                    }
        
        # Get counts
        to_delete_count = len(to_delete_users)
        not_to_delete_count = len(bluepages_users)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Build result dictionary
        result = {
            "success": True,
            "validator": "bluepages",
            "input_count": input_count,
            "output": {
                "found_in_bluepages": not_to_delete_count,
                "not_found_in_bluepages": to_delete_count
            },
            "files_created": {
                "not_to_delete": str(not_to_delete_file)
            },
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }
        
        # Add to_delete file path only if not returning cloud candidates
        if not return_cloud_candidates and to_delete_file:
            result["files_created"]["to_delete"] = str(to_delete_file)
        
        # Add in-memory data if skipping file creation or returning cloud candidates
        if skip_file_creation or return_cloud_candidates:
            result["data"] = {
                "not_to_delete_users": bluepages_users,
                "cloud_check_candidates": to_delete_users  # Users for Cloud Check
            }
        
        return result
        
    except BluePagesError:
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
            "validator": "bluepages",
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }


def validate_bluepages_sync(
    input_file: Optional[str] = None,
    users_data: Optional[List] = None,
    output_dir: str = "backend/resolutions",
    timestamp: Optional[str] = None,
    max_concurrent: int = 50,
    batch_size: int = 100,
    skip_file_creation: bool = False
) -> Dict:
    """
    Synchronous wrapper for validate_bluepages.
    
    Use this when calling from non-async code.
    """
    return asyncio.run(validate_bluepages(
        input_file=input_file,
        users_data=users_data,
        output_dir=output_dir,
        timestamp=timestamp,
        max_concurrent=max_concurrent,
        batch_size=batch_size,
        skip_file_creation=skip_file_creation
    ))


# For direct usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python bluepages_validator.py <old_login_users_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    try:
        result = validate_bluepages_sync(input_file)
        print(f"\n✓ BluPages Validation Complete!")
        print(f"  Found in BluPages: {result['output']['found_in_bluepages']}")
        print(f"  Not found in BluPages: {result['output']['not_found_in_bluepages']}")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"\nFiles created:")
        print(f"  - To delete: {result['files_created']['to_delete']}")
        print(f"  - Not to delete: {result['files_created']['not_to_delete']}")
    except BluePagesError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Made with Bob
