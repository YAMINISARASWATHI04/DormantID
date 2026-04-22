"""
Validation Pipeline Orchestrator

This module orchestrates the complete validation pipeline, running selected
validators in sequence based on user configuration (UI checkboxes).

Pipeline Flow:
1. ISV Validation (if selected)
2. Active Status Check (if selected)
3. Last Login Check (if selected)
4. BluPages Validation (if selected)
5. Cloud Last Login Check (if selected) - FINAL STAGE

Each step uses the output from the previous step.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable
import asyncio

from .isv_validator import validate_isv
from .active_status_validator import validate_active_status
from .login_validator import validate_last_login
from .bluepages_validator import validate_bluepages
from .cloud_login_validator import validate_cloud_login
from .decision_engine import consolidate_decisions


class PipelineError(Exception):
    """Custom exception for pipeline errors"""
    pass


async def run_validation_pipeline(
    input_file: str,
    output_dir: str = "backend/outputs",
    checks: Optional[Dict[str, bool]] = None,
    days_threshold: int = 1065,
    max_concurrent: int = 10,
    batch_size: int = 100,
    status_callback: Optional[Callable] = None
) -> Dict:
    """
    Run the complete validation pipeline with selected checks.
    
    Args:
        input_file: Path to extraction JSON file
        output_dir: Directory to save output files
        checks: Dictionary of checks to run:
            {
                "isv_validation": True/False,
                "active_status": True/False,
                "last_login": True/False,
                "bluepages": True/False,
                "cloud_login": True/False
            }
        days_threshold: Days threshold for login check (default: 1065 = ~3 years)
        max_concurrent: Maximum concurrent requests for async operations
        batch_size: Batch size for processing
        
    Returns:
        Dictionary with complete pipeline results:
        {
            "success": True,
            "pipeline": "validation_pipeline",
            "timestamp": "2026-04-06T10:00:00",
            "input_file": "extraction_*.json",
            "checks_run": ["isv_validation", "active_status", ...],
            "results": {
                "isv_validation": {...},
                "active_status": {...},
                "last_login": {...},
                "bluepages": {...}
            },
            "final_outputs": {
                "to_delete": "path/to/to_be_deleted.json",
                "not_to_delete": "path/to/not_to_be_deleted.json",
                "inactive": "path/to/isv_inactive_users.json"
            },
            "summary": {
                "total_input": 1000,
                "found_in_isv": 950,
                "active": 900,
                "recent_login": 700,
                "old_login": 200,
                "to_delete": 50,
                "not_to_delete": 850
            },
            "duration_seconds": 180
        }
        
    Raises:
        PipelineError: If pipeline execution fails
    """
    try:
        start_time = datetime.now()
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        # Default checks: run all if not specified
        if checks is None:
            checks = {
                "isv_validation": True,
                "active_status": True,
                "last_login": True,
                "bluepages": True,
                "cloud_login": True
            }
        
        # Validate input file - return error dict instead of raising exception
        if not Path(input_file).exists():
            return {
                "success": False,
                "error": f"Input file not found: {input_file}",
                "pipeline": "validation_pipeline",
                "timestamp": datetime.now().isoformat()
            }
        
        # Validate JSON format - return error dict for corrupted files
        try:
            with open(input_file, 'r') as f:
                initial_data = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON format in input file: {str(e)}",
                "pipeline": "validation_pipeline",
                "timestamp": datetime.now().isoformat()
            }
        
        # Track results from each step
        results = {}
        checks_run = []
        current_file = input_file
        
        # Summary statistics
        summary = {
            "total_input": len(initial_data),
            "found_in_isv": 0,
            "not_found_in_isv": 0,
            "active": 0,
            "inactive": 0,
            "recent_login": 0,
            "old_login": 0,
            "found_in_bluepages": 0,
            "not_found_in_bluepages": 0,
            "to_delete": 0,
            "not_to_delete": 0
        }
        
        print(f"\n{'='*70}")
        print(f"VALIDATION PIPELINE - Starting")
        print(f"{'='*70}")
        print(f"Input file: {input_file}")
        print(f"Total records: {summary['total_input']}")
        print(f"Checks to run: {[k for k, v in checks.items() if v]}")
        print(f"{'='*70}\n")
        
        # Step 1: ISV Validation
        if checks.get("isv_validation", False):
            print(f"\n{'='*70}")
            print(f"[1/5] STARTING ISV VALIDATION")
            print(f"{'='*70}")
            if status_callback:
                status_callback("ISV Validation", "running")
            result = await validate_isv(
                input_file=current_file,
                output_dir=output_dir,
                batch_size=batch_size,
                max_concurrent=max_concurrent
            )
            results["isv_validation"] = result
            checks_run.append("isv_validation")
            
            # Safely extract output values with defaults
            summary["found_in_isv"] = result.get("output", {}).get("found_in_isv", 0)
            summary["not_found_in_isv"] = result.get("output", {}).get("not_found_in_isv", 0)
            
            # Use resolved file for next step
            current_file = result.get("files_created", {}).get("resolved", current_file)
            print(f"✓ ISV Validation complete: {summary['found_in_isv']} found, {summary['not_found_in_isv']} not found\n")
            if status_callback:
                status_callback("ISV Validation", "completed")
        
        # Step 2: Active Status Check
        if checks.get("active_status", False):
            print(f"\n{'='*70}")
            print(f"[2/5] STARTING DORMANCY CHECK (Active Status)")
            print(f"{'='*70}")
            if status_callback:
                status_callback("Dormancy Check", "running")
            result = validate_active_status(
                input_file=current_file,
                output_dir=output_dir,
                timestamp=timestamp
            )
            results["active_status"] = result
            checks_run.append("active_status")
            
            # Safely extract output values with defaults
            summary["active"] = result.get("output", {}).get("active", 0)
            summary["inactive"] = result.get("output", {}).get("inactive", 0)
            
            # Use active file for next step
            current_file = result.get("files_created", {}).get("active", current_file)
            print(f"✓ Active Status Check complete: {summary['active']} active, {summary['inactive']} inactive\n")
            if status_callback:
                status_callback("Dormancy Check", "completed")
        
        # Step 3: Last Login Check
        if checks.get("last_login", False):
            print(f"\n{'='*70}")
            print(f"[3/5] STARTING LAST LOGIN CHECK")
            print(f"{'='*70}")
            if status_callback:
                status_callback("Last Login Check", "running")
            result = validate_last_login(
                input_file=current_file,
                days_threshold=days_threshold,
                output_dir=output_dir,
                timestamp=timestamp,
                append_recent=True
            )
            results["last_login"] = result
            checks_run.append("last_login")
            
            # Safely extract output values with defaults
            summary["old_login"] = result.get("output", {}).get("old_login", 0)
            summary["recent_login"] = result.get("output", {}).get("recent_login", 0)
            
            # Use old login file for BluPages check
            current_file = result.get("files_created", {}).get("old_login", current_file)
            print(f"✓ Last Login Check complete: {summary['old_login']} old (>{days_threshold} days), {summary['recent_login']} recent\n")
            if status_callback:
                status_callback("Last Login Check", "completed")
        
        # Step 4: BluPages Validation
        if checks.get("bluepages", False):
            print(f"\n{'='*70}")
            print(f"[4/5] STARTING BLUEPAGES VALIDATION")
            print(f"{'='*70}")
            if status_callback:
                status_callback("BluPages Validation", "running")
            
            # Filter to only @ibm.com or *.ibm.com emails before BluPages
            with open(current_file, 'r') as f:
                users = json.load(f)
            
            ibm_users = []
            non_ibm_users = []
            
            for user in users:
                email = user.get('email', '')
                # Only IBM emails (ending with @ibm.com or .ibm.com) go to BluPages
                # Exclude mail.test.*.ibm.com and malinator.com (already filtered in bluepages_validator_async.py)
                if email.endswith('@ibm.com') or '.ibm.com' in email:
                    ibm_users.append(user)
                else:
                    non_ibm_users.append(user)
            
            print(f"  IBM emails: {len(ibm_users)}, Non-IBM emails: {len(non_ibm_users)}")
            
            # Mark non-IBM users as skipping BluPages check (will go to Cloud Check)
            if non_ibm_users:
                for user in non_ibm_users:
                    user['skip_bluepages'] = True
                    user['skip_reason'] = 'Non-IBM Email Domain - Will check Cloud activity'
            
            # Run BluPages validation only on IBM users - pass data directly
            # Use return_cloud_candidates=True to get in-memory data instead of creating to_be_deleted file
            if ibm_users:
                result = await validate_bluepages(
                    users_data=ibm_users,
                    output_dir=output_dir,
                    timestamp=timestamp,
                    max_concurrent=max_concurrent,
                    batch_size=batch_size,
                    return_cloud_candidates=True  # Return in-memory data for Cloud Check
                )
                results["bluepages"] = result
                
                # Get cloud check candidates from in-memory data
                cloud_check_candidates = result.get("data", {}).get("cloud_check_candidates", [])
                
                # Merge non-IBM users with BluPages not_found users for Cloud Check
                # Both groups will go to Cloud Check in Step 5 (in-memory)
                if non_ibm_users:
                    cloud_check_candidates.extend(non_ibm_users)
                    print(f"  Added {len(non_ibm_users)} non-IBM users to Cloud Check candidates")
                
                # Store cloud check candidates for Step 5
                results["bluepages"]["cloud_check_candidates"] = cloud_check_candidates
                
                checks_run.append("bluepages")
                
                # Safely extract output values with defaults
                summary["found_in_bluepages"] = result.get("output", {}).get("found_in_bluepages", 0)
                summary["not_found_in_bluepages"] = result.get("output", {}).get("not_found_in_bluepages", 0)
                summary["non_ibm_emails"] = len(non_ibm_users)
                # Users not found in BluPages + non-IBM users will go to Cloud Check
                summary["to_cloud_check"] = summary["not_found_in_bluepages"] + len(non_ibm_users)
                # Users found in BluPages + recent login users = not_to_delete
                summary["not_to_delete"] = summary["found_in_bluepages"] + summary.get("recent_login", 0)
                
                print(f"✓ BluPages Validation complete: {summary['found_in_bluepages']} found, {summary['not_found_in_bluepages']} not found")
                print(f"  Non-IBM emails (will check Cloud): {len(non_ibm_users)}")
                print(f"  Total users for Cloud Check: {summary['to_cloud_check']}")
                if status_callback:
                    status_callback("BluPages Validation", "completed")
            else:
                print(f"✓ No IBM users to validate via BluPages")
                
                # Use the provided output_dir parameter
                outputs_dir = Path(output_dir)
                outputs_dir.mkdir(parents=True, exist_ok=True)
                
                # Store cloud check candidates (only non-IBM users in this case)
                cloud_check_candidates = non_ibm_users if non_ibm_users else []
                
                if non_ibm_users:
                    print(f"  Non-IBM emails (will check Cloud): {len(non_ibm_users)}")
                    print(f"  Total users for Cloud Check: {len(non_ibm_users)}")
                
                # Store result for final outputs (no files created yet)
                results["bluepages"] = {
                    "success": True,
                    "validator": "bluepages",
                    "input_count": len(non_ibm_users),
                    "output": {
                        "found_in_bluepages": 0,
                        "not_found_in_bluepages": 0
                    },
                    "files_created": {
                        "not_to_delete": str(outputs_dir / "not_to_be_deleted.json")
                    },
                    "cloud_check_candidates": cloud_check_candidates
                }
                
                summary["non_ibm_emails"] = len(non_ibm_users)
                summary["to_cloud_check"] = len(non_ibm_users)
                summary["not_to_delete"] = summary.get("recent_login", 0)
                
                checks_run.append("bluepages")
                if status_callback:
                    status_callback("BluPages Validation", "completed")
            
            print()
        
        # Step 5: Cloud Last Login Check (FINAL STAGE)
        # Use the same threshold as Last Login Check (from UI configuration)
        # This ensures consistency across all validation steps
        
        if checks.get("cloud_login", False):
            print(f"\n{'='*70}")
            print(f"[5/5] STARTING CLOUD VALIDATION (FINAL STAGE)")
            print(f"{'='*70}")
            print(f"  Cloud Login Threshold: {days_threshold} days (~{days_threshold/365:.1f} years - user-defined)")
            if status_callback:
                status_callback("Cloud Validation", "running")
            
            # Get cloud check candidates from BluPages (in-memory)
            # Priority: BluPages cloud_check_candidates > Last Login old_login file > fallback to file-based
            cloud_check_users = None
            cloud_input_file = None
            
            if "bluepages" in results and "cloud_check_candidates" in results["bluepages"]:
                # Use in-memory cloud check candidates from BluPages (preferred)
                cloud_check_users = results["bluepages"]["cloud_check_candidates"]
                print(f"  Using in-memory cloud check candidates from BluPages")
                print(f"  Total candidates: {len(cloud_check_users)}")
            elif "last_login" in results:
                # Fallback: Use old_login file from Last Login check
                cloud_input_file = results["last_login"].get("files_created", {}).get("old_login")
                if cloud_input_file and Path(cloud_input_file).exists():
                    print(f"  Using Last Login old_login file as input: {cloud_input_file}")
            elif "active_status" in results:
                # Fallback: Use active users file from Active Status check
                cloud_input_file = results["active_status"].get("files_created", {}).get("active")
                if cloud_input_file and Path(cloud_input_file).exists():
                    print(f"  Using Active Status active users file as input: {cloud_input_file}")
            elif "isv_validation" in results:
                # Fallback: Use resolved users file from ISV validation
                cloud_input_file = results["isv_validation"].get("files_created", {}).get("resolved")
                if cloud_input_file and Path(cloud_input_file).exists():
                    print(f"  Using ISV resolved users file as input: {cloud_input_file}")
            else:
                # Fallback: Use original extraction file
                cloud_input_file = input_file
                if cloud_input_file and Path(cloud_input_file).exists():
                    print(f"  Using original extraction file as input: {cloud_input_file}")
            
            # Run Cloud Check with in-memory data or file
            if cloud_check_users is not None:
                # Use in-memory data (preferred)
                result = await validate_cloud_login(
                    users_data=cloud_check_users,  # Pass in-memory data
                    days_threshold=days_threshold,  # Use dynamic threshold from UI
                    output_dir=output_dir,
                    timestamp=timestamp,
                    batch_size=50,  # Fixed batch size as per requirements
                    max_concurrent=max_concurrent
                )
                results["cloud_login"] = result
                checks_run.append("cloud_login")
                
                # Update summary with cloud login results
                summary["cloud_exceeds_threshold"] = result.get("output", {}).get("exceeds_threshold", 0)
                summary["cloud_recent_activity"] = result.get("output", {}).get("recent_activity", 0)
                summary["cloud_missing_data"] = result.get("output", {}).get("missing_data", 0)
                
                # Update final counts
                summary["to_delete"] = summary["cloud_exceeds_threshold"]
                summary["not_to_delete"] = summary.get("found_in_bluepages", 0) + summary.get("recent_login", 0) + summary["cloud_recent_activity"]
                
                print(f"✓ Cloud Login Check complete: {summary['cloud_exceeds_threshold']} exceed threshold, {summary['cloud_recent_activity']} recent activity")
                if status_callback:
                    status_callback("Cloud Validation", "completed")
            elif 'cloud_input_file' in locals() and cloud_input_file and Path(cloud_input_file).exists():
                # Fallback to file-based input
                result = await validate_cloud_login(
                    input_file=cloud_input_file,
                    days_threshold=days_threshold,
                    output_dir=output_dir,
                    timestamp=timestamp,
                    batch_size=50,
                    max_concurrent=max_concurrent
                )
                results["cloud_login"] = result
                checks_run.append("cloud_login")
                
                # Update summary
                summary["cloud_exceeds_threshold"] = result.get("output", {}).get("exceeds_threshold", 0)
                summary["cloud_recent_activity"] = result.get("output", {}).get("recent_activity", 0)
                summary["cloud_missing_data"] = result.get("output", {}).get("missing_data", 0)
                summary["to_delete"] = summary["cloud_exceeds_threshold"]
                summary["not_to_delete"] = summary.get("found_in_bluepages", 0) + summary.get("recent_login", 0) + summary["cloud_recent_activity"]
                
                print(f"✓ Cloud Login Check complete: {summary['cloud_exceeds_threshold']} exceed threshold, {summary['cloud_recent_activity']} recent activity")
                if status_callback:
                    status_callback("Cloud Validation", "completed")
            else:
                print(f"✓ No users to validate via Cloud Login Check (no input data available)")
                if status_callback:
                    status_callback("Cloud Validation", "completed")
            
            print()
        
        # Calculate total duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Collect final output files (safely)
        final_outputs = {}
        if "bluepages" in results:
            if "files_created" in results["bluepages"]:
                final_outputs["to_delete"] = results["bluepages"]["files_created"].get("to_delete")
                final_outputs["not_to_delete"] = results["bluepages"]["files_created"].get("not_to_delete")
        elif "last_login" in results:
            if "files_created" in results["last_login"]:
                final_outputs["old_login"] = results["last_login"]["files_created"].get("old_login")
                final_outputs["recent_login"] = results["last_login"]["files_created"].get("recent_login")
        
        if "active_status" in results:
            if "files_created" in results["active_status"]:
                final_outputs["inactive"] = results["active_status"]["files_created"].get("inactive")
        
        if "isv_validation" in results:
            if "files_created" in results["isv_validation"]:
                final_outputs["failed_isv"] = results["isv_validation"]["files_created"].get("failed")
        
        print(f"{'='*70}")
        print(f"PIPELINE COMPLETE")
        print(f"{'='*70}")
        print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"Checks run: {len(checks_run)}")
        print(f"\nSummary:")
        for key, value in summary.items():
            if value > 0:
                print(f"  {key}: {value}")
        print(f"{'='*70}\n")
        
        # Build pipeline results for decision engine
        pipeline_result = {
            "success": True,
            "pipeline": "validation_pipeline",
            "timestamp": end_time.isoformat(),
            "input_file": input_file,
            "checks_run": checks_run,
            "results": results,
            "final_outputs": final_outputs,
            "summary": summary,
            "duration_seconds": int(duration),
            "threshold_days": days_threshold  # Pass threshold to decision engine
        }
        
        # Run decision engine to consolidate all results into single JSON with timestamp
        print(f"Running Decision Engine to consolidate results...")
        decision_result = consolidate_decisions(
            pipeline_results=pipeline_result,
            timestamp=timestamp,
            threshold_days=days_threshold  # Pass threshold to decision engine
        )
        
        # Add decision engine output to pipeline result
        pipeline_result["decision_output"] = decision_result["output_file"]
        pipeline_result["decision_summary"] = decision_result["summary"]
        
        # Clean up intermediate files - keep only the final decision file
        print(f"\nCleaning up intermediate files...")
        files_to_remove = []
        
        # Collect all intermediate files from validation steps
        for step_name, step_result in results.items():
            if "files_created" in step_result:
                for file_type, file_path in step_result["files_created"].items():
                    if file_path and Path(file_path).exists():
                        # Don't delete the final decision file
                        if file_path != decision_result["output_file"]:
                            files_to_remove.append(file_path)
        
        # Clean up intermediate files in output directory (but preserve previous decision files)
        # Only remove files that were created during THIS pipeline run
        outputs_dir = Path(output_dir)
        
        if outputs_dir.exists():
            for file_path in outputs_dir.glob("*.json"):
                # Skip the final decision file
                if str(file_path) == decision_result["output_file"]:
                    continue
                
                # Skip previous decision files (preserve history)
                if file_path.name.startswith('dormant_id_decisions_'):
                    continue
                
                # Only remove intermediate files (not decision files)
                if str(file_path) not in files_to_remove:
                    files_to_remove.append(str(file_path))
        
        # Remove intermediate files
        removed_count = 0
        for file_path in files_to_remove:
            try:
                Path(file_path).unlink()
                removed_count += 1
            except Exception as e:
                print(f"  Warning: Could not remove {file_path}: {e}")
        
        print(f"✓ Removed {removed_count} intermediate files")
        print(f"✓ Final output: {decision_result['output_file']}\n")
        
        return pipeline_result
        
    except Exception as e:
        raise PipelineError(f"Pipeline execution failed: {str(e)}")


def run_validation_pipeline_sync(
    input_file: str,
    output_dir: str = "backend/outputs",
    checks: Optional[Dict[str, bool]] = None,
    days_threshold: int = 1065,
    max_concurrent: int = 10,
    batch_size: int = 100
) -> Dict:
    """
    Synchronous wrapper for run_validation_pipeline.
    
    Use this when calling from non-async code.
    """
    return asyncio.run(run_validation_pipeline(
        input_file, output_dir, checks, days_threshold, max_concurrent, batch_size
    ))


# For direct usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <extraction_file> [checks]")
        print("\nExample:")
        print("  python pipeline.py extraction.json")
        print("  python pipeline.py extraction.json isv,active,login,bluepages")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Parse checks from command line
    checks = None
    if len(sys.argv) > 2:
        check_names = sys.argv[2].split(',')
        checks = {
            "isv_validation": "isv" in check_names,
            "active_status": "active" in check_names,
            "last_login": "login" in check_names,
            "bluepages": "bluepages" in check_names
        }
    
    try:
        result = run_validation_pipeline_sync(input_file, checks=checks)
        print(f"\n✓ Pipeline Complete!")
        print(f"  Duration: {result['duration_seconds']}s")
        print(f"  Checks run: {', '.join(result['checks_run'])}")
        print(f"\nFinal outputs:")
        for name, path in result['final_outputs'].items():
            print(f"  - {name}: {path}")
    except PipelineError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Made with Bob
