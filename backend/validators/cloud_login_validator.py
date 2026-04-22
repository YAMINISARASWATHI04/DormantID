"""
Cloud Last Login Validator - Final stage after BluPages validation

This module validates users against IBM Cloud IAM API to check their last login
activity in the cloud. This is the FINAL validation step after BluPages.

Workflow:
1. Takes users from to_be_deleted (after BluPages validation)
2. Fetches lastLogin from IBM Cloud IAM API
3. Uses UI-configured threshold (days/years)
4. Compares:
   - If lastLogin > threshold → keep in to_be_deleted
   - Else → move to not_to_be_deleted
5. Adds appropriate reasons

API Details:
- Token endpoint: https://iam.cloud.ibm.com/identity/token
- Statistics endpoint: https://iam.cloud.ibm.com/v1/statistics/identities
- Batch size: 50 users per request
- Handles missing lastLogin safely
"""

import json
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import os


class CloudLoginError(Exception):
    """Custom exception for cloud login validation errors"""
    pass


async def get_iam_token(api_key: str, session: aiohttp.ClientSession) -> str:
    """
    Get IBM Cloud IAM access token.
    
    Args:
        api_key: IBM Cloud API key
        session: aiohttp client session
        
    Returns:
        Access token string
        
    Raises:
        CloudLoginError: If token retrieval fails
    """
    token_url = "https://iam.cloud.ibm.com/identity/token"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    
    try:
        async with session.post(token_url, headers=headers, data=data, timeout=30) as response:
            if response.status != 200:
                error_text = await response.text()
                raise CloudLoginError(f"Failed to get IAM token: {response.status} - {error_text}")
            
            result = await response.json()
            return result.get("access_token")
    except asyncio.TimeoutError:
        raise CloudLoginError("Token request timed out")
    except Exception as e:
        raise CloudLoginError(f"Token request failed: {str(e)}")


async def fetch_cloud_login_batch(
    iam_ids: List[str],
    token: str,
    session: aiohttp.ClientSession
) -> Dict:
    """
    Fetch last login data for a batch of IAM IDs from IBM Cloud.
    
    Args:
        iam_ids: List of IAM IDs (e.g., ["IBMid-270007GXPG", "IBMid-550005A5HV"])
        token: IBM Cloud IAM access token
        session: aiohttp client session
        
    Returns:
        Dictionary mapping IAM ID to last login data
        
    Raises:
        CloudLoginError: If API request fails
    """
    stats_url = "https://iam.cloud.ibm.com/v1/statistics/identities"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    params = {
        "pagesize": "50"
    }
    
    payload = {
        "iam_ids": iam_ids
    }
    
    try:
        async with session.post(
            stats_url,
            headers=headers,
            params=params,
            json=payload,
            timeout=60
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise CloudLoginError(f"Cloud API request failed: {response.status} - {error_text}")
            
            result = await response.json()
            
            # Parse response and build mapping
            login_data = {}
            for item in result.get("identities", []):
                iam_id = item.get("iam_id")
                last_login = item.get("last_login")
                if iam_id:
                    login_data[iam_id] = last_login
            
            return login_data
    except asyncio.TimeoutError:
        raise CloudLoginError("Cloud API request timed out")
    except Exception as e:
        raise CloudLoginError(f"Cloud API request failed: {str(e)}")


async def validate_cloud_login(
    input_file: Optional[str] = None,
    users_data: Optional[List] = None,
    days_threshold: int = 1095,
    output_dir: str = "backend/outputs",
    timestamp: Optional[str] = None,
    api_key: Optional[str] = None,
    batch_size: int = 50,
    max_concurrent: int = 5
) -> Dict:
    """
    Validate users against IBM Cloud IAM last login data.
    
    This is the FINAL validation step after BluPages. Takes users from to_be_deleted
    and checks their cloud activity.
    
    Args:
        input_file: Path to to_be_deleted JSON file (after BluPages)
        users_data: List of user dictionaries (alternative to input_file)
        days_threshold: Days threshold for cloud login (from UI config)
        output_dir: Directory to save output files
        timestamp: Optional timestamp string for filenames
        api_key: IBM Cloud API key (from env if not provided)
        batch_size: Number of users per API batch (default: 50)
        max_concurrent: Maximum concurrent API requests (default: 5)
        
    Returns:
        Dictionary with validation results:
        {
            "success": True,
            "validator": "cloud_login",
            "input_count": 100,
            "output": {
                "exceeds_threshold": 80,
                "recent_activity": 20,
                "missing_data": 5
            },
            "files_created": {
                "to_delete": "path/to/to_be_deleted.json",
                "not_to_delete": "path/to/not_to_be_deleted.json"
            },
            "timestamp": "2026-04-21T10:00:00",
            "duration_seconds": 45
        }
        
    Raises:
        CloudLoginError: If validation fails
    """
    start_time = datetime.now()
    
    try:
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.getenv("IBM_CLOUD_API_KEY")
            if not api_key:
                return {
                    "success": False,
                    "error": "Missing API key",
                    "message": "IBM_CLOUD_API_KEY not found in environment",
                    "validator": "cloud_login",
                    "timestamp": datetime.now().isoformat()
                }
        
        # Load users from file or use provided data
        if users_data is not None:
            users = users_data
        elif input_file is not None:
            if not Path(input_file).exists():
                return {
                    "success": False,
                    "error": "Input file not found",
                    "message": f"File does not exist: {input_file}",
                    "validator": "cloud_login",
                    "timestamp": datetime.now().isoformat()
                }
            
            try:
                with open(input_file, 'r') as f:
                    users = json.load(f)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": "Invalid JSON format",
                    "message": f"Failed to parse input file: {str(e)}",
                    "validator": "cloud_login",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            return {
                "success": False,
                "error": "Missing input",
                "message": "Either input_file or users_data must be provided",
                "validator": "cloud_login",
                "timestamp": datetime.now().isoformat()
            }
        
        input_count = len(users)
        
        if input_count == 0:
            return {
                "success": True,
                "validator": "cloud_login",
                "input_count": 0,
                "output": {
                    "exceeds_threshold": 0,
                    "recent_activity": 0,
                    "missing_data": 0
                },
                "message": "No users to validate",
                "timestamp": datetime.now().isoformat()
            }
        
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # First, validate lastLogin field for all users
        # Users without valid lastLogin should skip Cloud Check
        users_with_valid_login = []
        users_without_valid_login = []
        
        print(f"\n{'='*70}")
        print(f"CLOUD LOGIN VALIDATOR - Starting")
        print(f"{'='*70}")
        print(f"Total users: {input_count}")
        print(f"Validating lastLogin field...")
        
        for user in users:
            last_login = user.get("lastLogin")
            
            # Check if lastLogin is valid (not null, not empty, not missing)
            if last_login is None or last_login == "" or not isinstance(last_login, str):
                # No valid lastLogin - skip Cloud Check
                user["cloud_last_login"] = None
                user["cloud_login_reason"] = "NO IBM Cloud Check - Missing/Invalid lastLogin in Cloudant"
                user["skip_cloud_check"] = True
                users_without_valid_login.append(user)
            else:
                # Valid lastLogin - proceed with Cloud Check
                users_with_valid_login.append(user)
        
        print(f"✓ Users with valid lastLogin: {len(users_with_valid_login)}")
        print(f"✓ Users without valid lastLogin (skip Cloud Check): {len(users_without_valid_login)}")
        
        # Extract IAM IDs only from users with valid lastLogin
        iam_id_to_user = {}
        for user in users_with_valid_login:
            # Try to extract IAM ID from user_id or email
            user_id = user.get("user_id", user.get("id", ""))
            email = user.get("email", user.get("username", ""))
            
            # IAM ID format: IBMid-XXXXXXXXXX
            iam_id = None
            if user_id.startswith("IBMid-"):
                iam_id = user_id
            elif email and "@" in email:
                # Try to construct IAM ID from email prefix
                # This is a fallback - ideally we'd have the IAM ID directly
                iam_id = user_id  # Use as-is for now
            
            if iam_id:
                iam_id_to_user[iam_id] = user
        
        print(f"Users with IAM IDs (for Cloud Check): {len(iam_id_to_user)}")
        print(f"Threshold: {days_threshold} days (~{days_threshold/365:.1f} years)")
        print(f"Batch size: {batch_size}")
        print(f"{'='*70}\n")
        
        # Create batches of IAM IDs
        iam_ids = list(iam_id_to_user.keys())
        batches = [iam_ids[i:i + batch_size] for i in range(0, len(iam_ids), batch_size)]
        
        # Fetch cloud login data in batches
        all_login_data = {}
        
        async with aiohttp.ClientSession() as session:
            # Get IAM token
            print("Getting IAM token...")
            token = await get_iam_token(api_key, session)
            print("✓ Token obtained\n")
            
            # Process batches with concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_batch(batch_ids, batch_num):
                async with semaphore:
                    print(f"Processing batch {batch_num}/{len(batches)} ({len(batch_ids)} users)...")
                    try:
                        login_data = await fetch_cloud_login_batch(batch_ids, token, session)
                        print(f"✓ Batch {batch_num} complete: {len(login_data)} records fetched")
                        return login_data
                    except Exception as e:
                        print(f"✗ Batch {batch_num} failed: {str(e)}")
                        return {}
            
            # Process all batches concurrently
            tasks = [process_batch(batch, i+1) for i, batch in enumerate(batches)]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Merge all batch results
            for result in batch_results:
                if isinstance(result, dict):
                    all_login_data.update(result)
        
        print(f"\n✓ Cloud login data fetched: {len(all_login_data)} records\n")
        
        # Current time for comparison
        current_time = datetime.now(timezone.utc)
        threshold_date = current_time - timedelta(days=days_threshold)
        
        # Categorize users based on cloud login
        exceeds_threshold_users = []  # Keep in to_be_deleted
        recent_activity_users = []     # Move to not_to_be_deleted
        missing_data_count = 0
        
        for iam_id, user in iam_id_to_user.items():
            cloud_last_login = all_login_data.get(iam_id)
            
            if cloud_last_login is None or cloud_last_login == "":
                # No cloud login data - keep in to_be_deleted
                user["cloud_last_login"] = None
                user["cloud_login_reason"] = "No cloud activity found"
                exceeds_threshold_users.append(user)
                missing_data_count += 1
            else:
                try:
                    # Parse cloud last login date
                    cloud_login_date = datetime.fromisoformat(cloud_last_login.replace('Z', '+00:00'))
                    days_since_cloud_login = (current_time - cloud_login_date).days
                    
                    user["cloud_last_login"] = cloud_last_login
                    user["cloud_days_since_login"] = days_since_cloud_login
                    
                    if days_since_cloud_login > days_threshold:
                        # Cloud login exceeds threshold - keep in to_be_deleted
                        user["cloud_login_reason"] = f"Cloud last login exceeds threshold ({days_since_cloud_login} days > {days_threshold} days)"
                        exceeds_threshold_users.append(user)
                    else:
                        # Recent cloud activity - move to not_to_be_deleted
                        user["cloud_login_reason"] = f"Recent activity found in Cloud ({days_since_cloud_login} days ≤ {days_threshold} days)"
                        recent_activity_users.append(user)
                except (ValueError, AttributeError):
                    # Unparseable date - keep in to_be_deleted
                    user["cloud_last_login"] = cloud_last_login
                    user["cloud_login_reason"] = "Invalid cloud login date format"
                    exceeds_threshold_users.append(user)
                    missing_data_count += 1
        
        # Add users without IAM IDs from valid login users to exceeds_threshold (keep in to_be_deleted)
        for user in users_with_valid_login:
            user_id = user.get("user_id", user.get("id", ""))
            if user_id not in iam_id_to_user:
                user["cloud_last_login"] = None
                user["cloud_login_reason"] = "No IAM ID found for cloud check"
                exceeds_threshold_users.append(user)
                missing_data_count += 1
        
        # Add users without valid lastLogin to recent_activity_users (move to not_to_be_deleted)
        # These users skip Cloud Check entirely
        recent_activity_users.extend(users_without_valid_login)
        
        # Create output file paths
        outputs_dir = Path(output_dir)
        to_delete_file = outputs_dir / f"to_be_deleted_{timestamp}.json"
        not_to_delete_file = outputs_dir / "not_to_be_deleted.json"
        
        # Save to_be_deleted (users who still need deletion)
        with open(to_delete_file, 'w') as f:
            json.dump(exceeds_threshold_users, f, indent=2)
        
        # Append recent activity users (including those without valid lastLogin) to not_to_be_deleted
        if recent_activity_users:
            if not_to_delete_file.exists():
                try:
                    with open(not_to_delete_file, 'r') as f:
                        existing_users = json.load(f)
                    
                    # Avoid duplicates by user_id
                    existing_user_ids = {u.get('user_id', u.get('id')) for u in existing_users}
                    new_users = [u for u in recent_activity_users 
                                if u.get('user_id', u.get('id')) not in existing_user_ids]
                    
                    combined_users = existing_users + new_users
                    
                    with open(not_to_delete_file, 'w') as f:
                        json.dump(combined_users, f, indent=2)
                except (json.JSONDecodeError, KeyError):
                    # If existing file is invalid, overwrite it
                    with open(not_to_delete_file, 'w') as f:
                        json.dump(recent_activity_users, f, indent=2)
            else:
                with open(not_to_delete_file, 'w') as f:
                    json.dump(recent_activity_users, f, indent=2)
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Print summary
        print(f"{'='*70}")
        print(f"CLOUD LOGIN VALIDATION COMPLETE")
        print(f"{'='*70}")
        print(f"Exceeds threshold (to delete): {len(exceeds_threshold_users)}")
        print(f"Recent activity (not to delete): {len(recent_activity_users)}")
        print(f"  - With recent cloud activity: {len(recent_activity_users) - len(users_without_valid_login)}")
        print(f"  - Without valid lastLogin (skipped Cloud Check): {len(users_without_valid_login)}")
        print(f"Missing/invalid cloud data: {missing_data_count}")
        print(f"Duration: {duration:.1f}s")
        print(f"{'='*70}\n")
        
        return {
            "success": True,
            "validator": "cloud_login",
            "input_count": input_count,
            "output": {
                "exceeds_threshold": len(exceeds_threshold_users),
                "recent_activity": len(recent_activity_users),
                "skipped_no_lastlogin": len(users_without_valid_login),
                "missing_data": missing_data_count
            },
            "files_created": {
                "to_delete": str(to_delete_file),
                "not_to_delete": str(not_to_delete_file)
            },
            "threshold_days": days_threshold,
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }
        
    except CloudLoginError:
        raise
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        return {
            "success": False,
            "error": "Unexpected error",
            "message": f"An unexpected error occurred: {str(e)}",
            "validator": "cloud_login",
            "timestamp": end_time.isoformat(),
            "duration_seconds": int(duration)
        }


def validate_cloud_login_sync(
    input_file: Optional[str] = None,
    users_data: Optional[List] = None,
    days_threshold: int = 1095,
    output_dir: str = "backend/outputs",
    timestamp: Optional[str] = None,
    api_key: Optional[str] = None,
    batch_size: int = 50,
    max_concurrent: int = 5
) -> Dict:
    """
    Synchronous wrapper for validate_cloud_login.
    
    Use this when calling from non-async code.
    """
    return asyncio.run(validate_cloud_login(
        input_file=input_file,
        users_data=users_data,
        days_threshold=days_threshold,
        output_dir=output_dir,
        timestamp=timestamp,
        api_key=api_key,
        batch_size=batch_size,
        max_concurrent=max_concurrent
    ))


# For direct usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python cloud_login_validator.py <to_be_deleted_file> [days_threshold]")
        print("\nExample:")
        print("  python cloud_login_validator.py to_be_deleted.json 1095")
        sys.exit(1)
    
    input_file = sys.argv[1]
    days_threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 1095
    
    try:
        result = validate_cloud_login_sync(input_file, days_threshold=days_threshold)
        print(f"\n✓ Cloud Login Validation Complete!")
        print(f"  Exceeds threshold: {result['output']['exceeds_threshold']}")
        print(f"  Recent activity: {result['output']['recent_activity']}")
        print(f"  Missing data: {result['output']['missing_data']}")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"\nFiles created:")
        print(f"  - To delete: {result['files_created']['to_delete']}")
        print(f"  - Not to delete: {result['files_created']['not_to_delete']}")
    except CloudLoginError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Made with Bob