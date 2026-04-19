"""
Swagger API Specifications for Dormant ID Check System
Contains Python dictionaries for Flasgger decorators
"""

# Health Check Endpoint
health_check_spec = {
    "tags": ["System"],
    "summary": "Health check endpoint",
    "description": "Check if the API is running and healthy",
    "responses": {
        "200": {
            "description": "API is healthy",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "example": "healthy"},
                            "timestamp": {"type": "string", "example": "2026-04-19T10:30:00.000Z"}
                        }
                    }
                }
            }
        }
    }
}

# Get Status Endpoint
get_status_spec = {
    "tags": ["Job Management"],
    "summary": "Get current job status",
    "description": "Retrieve the current status of the extraction job including progress, records processed, and any errors",
    "responses": {
        "200": {
            "description": "Current job status",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["not_started", "under_processing", "completed", "failed", "stopped"],
                                "example": "under_processing"
                            },
                            "current_month": {"type": "string", "example": "2020-04"},
                            "records_processed": {"type": "integer", "example": 1500},
                            "progress_percent": {"type": "number", "example": 45.5},
                            "start_date": {"type": "string", "example": "2020-01-01"},
                            "end_date": {"type": "string", "example": "2020-12-31"},
                            "total_months": {"type": "integer", "example": 12},
                            "completed_months": {"type": "integer", "example": 5},
                            "error": {"type": "string", "nullable": True},
                            "last_updated": {"type": "string", "example": "2026-04-19T10:30:00"}
                        }
                    }
                }
            }
        }
    }
}

# Get Filters Endpoint
get_filters_spec = {
    "tags": ["Filters"],
    "summary": "Get available filters",
    "description": "Retrieve list of all available validation filters that can be applied during extraction",
    "responses": {
        "200": {
            "description": "List of available filters",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "filters": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string", "example": "dormancy_check"},
                                        "name": {"type": "string", "example": "Dormancy Check"},
                                        "description": {"type": "string", "example": "Check for dormant accounts"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string", "example": "Error message"}
                        }
                    }
                }
            }
        }
    }
}

# Start Retrieval Endpoint (Main endpoint with two modes)
start_retrieval_spec = {
    "tags": ["Data Extraction"],
    "summary": "Start data extraction job",
    "description": """
    Start a data extraction job with two modes:
    
    **Mode 1: Date Range Extraction**
    - Extracts data from Cloudant database for a specific date range
    - Pulls all records created/modified within the date range
    - Applies optional filters during validation pipeline
    
    **Mode 2: Specific IDs Validation**
    - Validates a list of specific user IDs directly via ISV
    - Does not query Cloudant database
    - Useful for validating known user IDs
    
    Both modes support optional filters that are applied during the validation pipeline (NOT during extraction).
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {
                            "type": "object",
                            "required": ["extraction_mode", "start_date", "end_date"],
                            "properties": {
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["date_range"],
                                    "example": "date_range",
                                    "description": "Mode 1: Extract data from Cloudant by date range"
                                },
                                "start_date": {
                                    "type": "string",
                                    "example": "2020-04-15",
                                    "description": "Start date (YYYY-MM-DD, YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS)"
                                },
                                "end_date": {
                                    "type": "string",
                                    "example": "2020-04-15",
                                    "description": "End date (YYYY-MM-DD, YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS)"
                                },
                                "filters": {
                                    "type": "object",
                                    "description": "Optional filters to apply during validation pipeline",
                                    "example": {
                                        "dormancy_check": True,
                                        "federated_id_removal": True,
                                        "isv_validation": True
                                    }
                                },
                                "batch_size": {
                                    "type": "integer",
                                    "minimum": 100,
                                    "maximum": 10000,
                                    "default": 3000,
                                    "example": 3000,
                                    "description": "Number of records to process per batch"
                                }
                            }
                        },
                        {
                            "type": "object",
                            "required": ["extraction_mode", "user_ids"],
                            "properties": {
                                "extraction_mode": {
                                    "type": "string",
                                    "enum": ["specific_ids"],
                                    "example": "specific_ids",
                                    "description": "Mode 2: Validate specific user IDs via ISV"
                                },
                                "user_ids": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "example": ["user1@ibm.com", "user2@ibm.com"],
                                    "description": "List of user IDs to validate"
                                },
                                "filters": {
                                    "type": "object",
                                    "description": "Optional filters to apply during validation",
                                    "example": {
                                        "isv_validation": True
                                    }
                                },
                                "batch_size": {
                                    "type": "integer",
                                    "minimum": 100,
                                    "maximum": 10000,
                                    "default": 3000,
                                    "example": 3000
                                }
                            }
                        }
                    ]
                },
                "examples": {
                    "date_range_example": {
                        "summary": "Date Range Extraction",
                        "value": {
                            "extraction_mode": "date_range",
                            "start_date": "2020-04-15",
                            "end_date": "2020-04-15",
                            "filters": {
                                "dormancy_check": True,
                                "federated_id_removal": True,
                                "isv_validation": True
                            },
                            "batch_size": 3000
                        }
                    },
                    "specific_ids_example": {
                        "summary": "Specific IDs Validation",
                        "value": {
                            "extraction_mode": "specific_ids",
                            "user_ids": ["user1@ibm.com", "user2@ibm.com", "user3@ibm.com"],
                            "filters": {
                                "isv_validation": True
                            },
                            "batch_size": 1000
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Extraction job started successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "message": {"type": "string", "example": "Data retrieval started successfully"},
                            "extraction_mode": {"type": "string", "example": "date_range"},
                            "start_date": {"type": "string", "example": "2020-04-15"},
                            "end_date": {"type": "string", "example": "2020-04-15"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input or job already running",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string", "example": "A job is already running. Please wait for it to complete."}
                        }
                    }
                }
            }
        },
        "422": {
            "description": "Unprocessable entity - Missing required fields",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string", "example": "start_date and end_date are required for date range extraction"}
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string", "example": "Internal error message"}
                        }
                    }
                }
            }
        }
    }
}

# Reset Status Endpoint
reset_status_spec = {
    "tags": ["Job Management"],
    "summary": "Reset job status",
    "description": "Reset the job status to 'not_started' and clear all progress data",
    "responses": {
        "200": {
            "description": "Status reset successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "message": {"type": "string", "example": "Status reset successfully"}
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}

# Stop Extraction Endpoint
stop_extraction_spec = {
    "tags": ["Job Management"],
    "summary": "Stop running extraction job",
    "description": "Stop the currently running extraction job gracefully",
    "responses": {
        "200": {
            "description": "Extraction stopped successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "message": {"type": "string", "example": "Extraction stopped successfully"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "No extraction running",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string", "example": "No extraction is currently running"}
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": False},
                            "error": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}

# Download File Endpoint
download_file_spec = {
    "tags": ["File Management"],
    "summary": "Download extraction or output file",
    "description": "Download a specific extraction or output file by filename",
    "parameters": [
        {
            "name": "filename",
            "in": "query",
            "required": True,
            "schema": {"type": "string"},
            "description": "Name of the file to download",
            "example": "extraction_20260419_143122.json"
        }
    ],
    "responses": {
        "200": {
            "description": "File downloaded successfully",
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            }
        },
        "400": {
            "description": "Filename parameter missing",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "filename parameter is required"}
                        }
                    }
                }
            }
        },
        "404": {
            "description": "File not found",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "File not found"}
                        }
                    }
                }
            }
        }
    }
}

# View File Endpoint
view_file_spec = {
    "tags": ["File Management"],
    "summary": "View file contents",
    "description": "View the contents of an extraction or output file",
    "parameters": [
        {
            "name": "filename",
            "in": "query",
            "required": True,
            "schema": {"type": "string"},
            "description": "Name of the file to view",
            "example": "extraction_20260419_143122.json"
        }
    ],
    "responses": {
        "200": {
            "description": "File contents",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {"type": "array", "items": {"type": "object"}}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Filename parameter missing"
        },
        "404": {
            "description": "File not found"
        }
    }
}

# List Extractions Endpoint
list_extractions_spec = {
    "tags": ["File Management"],
    "summary": "List all extraction files",
    "description": "Get a list of all extraction files with metadata",
    "responses": {
        "200": {
            "description": "List of extraction files",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "extractions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "filename": {"type": "string"},
                                        "size": {"type": "integer"},
                                        "created": {"type": "string"},
                                        "record_count": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Get History Endpoint
get_history_spec = {
    "tags": ["History"],
    "summary": "Get extraction history",
    "description": "Retrieve the history of all extraction jobs",
    "responses": {
        "200": {
            "description": "Extraction history",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "history": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "start_date": {"type": "string"},
                                        "end_date": {"type": "string"},
                                        "status": {"type": "string"},
                                        "records_processed": {"type": "integer"},
                                        "timestamp": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Process User Pipeline Endpoint
process_pipeline_spec = {
    "tags": ["User Processing"],
    "summary": "Run complete user processing pipeline",
    "description": """
    Run the complete user processing pipeline:
    1. Split users by active/inactive status
    2. Filter active users by login date
    3. Apply validation filters
    
    This endpoint processes a previously extracted file through the validation pipeline.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/extractions/extraction_20260419_143122.json",
                            "description": "Path to the input extraction file"
                        },
                        "days_threshold": {
                            "type": "integer",
                            "default": 1095,
                            "example": 1095,
                            "description": "Number of days for dormancy threshold (default: 1095 = 3 years)"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for processed files"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Pipeline completed successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "active_users": {"type": "integer", "example": 150},
                            "inactive_users": {"type": "integer", "example": 50},
                            "dormant_users": {"type": "integer", "example": 30},
                            "output_files": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input"
        },
        "500": {
            "description": "Internal server error"
        }
    }
}

# ISV Validation Endpoint
validate_isv_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Validate users against ISV",
    "description": """
    Validate users against IBM ISV (IBM Users API).
    
    This endpoint checks if users exist in the ISV system and retrieves their current status.
    Useful for verifying user accounts before further processing.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/extractions/extraction_20260419_143122.json",
                            "description": "Path to the input extraction file"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for validated files"
                        },
                        "batch_size": {
                            "type": "integer",
                            "default": 100,
                            "example": 100,
                            "description": "Number of users to process per batch"
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "default": 50,
                            "example": 50,
                            "description": "Maximum concurrent API requests"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "ISV validation completed successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "validated_users": {"type": "integer", "example": 150},
                            "invalid_users": {"type": "integer", "example": 10},
                            "output_file": {"type": "string", "example": "backend/outputs/isv_resolved_users_20260419_143122.json"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "input_file is required"}
                        }
                    }
                }
            }
        },
        "500": {
            "description": "Internal server error"
        }
    }
}

# Active Status Validation Endpoint
validate_active_status_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Split users by active/inactive status",
    "description": """
    Split users into active and inactive categories based on their account status.
    
    This endpoint separates users who have active accounts from those with inactive accounts,
    creating separate output files for each category.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/outputs/isv_resolved_users_20260419_143122.json",
                            "description": "Path to the ISV validated file"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for split files"
                        },
                        "timestamp": {
                            "type": "string",
                            "example": "20260419_143122",
                            "description": "Optional timestamp for output files"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Users split successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "active_users": {"type": "integer", "example": 120},
                            "inactive_users": {"type": "integer", "example": 30},
                            "active_file": {"type": "string", "example": "backend/outputs/isv_active_users_20260419_143122.json"},
                            "inactive_file": {"type": "string", "example": "backend/outputs/isv_inactive_users_20260419_143122.json"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input"
        },
        "500": {
            "description": "Internal server error"
        }
    }
}

# Last Login Validation Endpoint
validate_last_login_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Filter users by last login date (3 years threshold)",
    "description": """
    Filter users based on their last login date with a 3-year (1095 days) threshold.
    
    **Two Categories:**
    - **Greater than 3 years**: Users who haven't logged in for more than 3 years (dormant)
    - **Less than 3 years**: Users who logged in within the last 3 years (active)
    
    This helps identify dormant accounts that may need to be deleted.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/outputs/isv_active_users_20260419_143122.json",
                            "description": "Path to the active users file"
                        },
                        "days_threshold": {
                            "type": "integer",
                            "default": 1095,
                            "example": 1095,
                            "description": "Number of days threshold (default: 1095 = 3 years)"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for filtered files"
                        },
                        "timestamp": {
                            "type": "string",
                            "example": "20260419_143122",
                            "description": "Optional timestamp for output files"
                        },
                        "append_recent": {
                            "type": "boolean",
                            "default": True,
                            "example": True,
                            "description": "Whether to append recent login users to output"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Users filtered by login date successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "old_login_count": {
                                "type": "integer",
                                "example": 80,
                                "description": "Users with last login > 3 years (dormant)"
                            },
                            "recent_login_count": {
                                "type": "integer",
                                "example": 40,
                                "description": "Users with last login < 3 years (active)"
                            },
                            "old_login_file": {
                                "type": "string",
                                "example": "backend/outputs/isv_last_login_>3_20260419_143122.json",
                                "description": "File containing dormant users (>3 years)"
                            },
                            "recent_login_file": {
                                "type": "string",
                                "example": "backend/outputs/isv_last_login_<3_20260419_143122.json",
                                "description": "File containing active users (<3 years)"
                            }
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input"
        },
        "500": {
            "description": "Internal server error"
        }
    }
}

# BluPages Validation Endpoint
validate_bluepages_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Validate users against IBM BluPages",
    "description": """
    Validate users against IBM BluPages directory.
    
    This endpoint checks if users exist in the IBM BluPages system and retrieves
    their current directory information. Useful for verifying IBM employee status.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/outputs/isv_last_login_>3_20260419_143122.json",
                            "description": "Path to the input file (typically dormant users)"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for validated files"
                        },
                        "timestamp": {
                            "type": "string",
                            "example": "20260419_143122",
                            "description": "Optional timestamp for output files"
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "default": 50,
                            "example": 50,
                            "description": "Maximum concurrent API requests"
                        },
                        "batch_size": {
                            "type": "integer",
                            "default": 100,
                            "example": 100,
                            "description": "Number of users to process per batch"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "BluPages validation completed successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "validated_users": {"type": "integer", "example": 70},
                            "not_found_users": {"type": "integer", "example": 10},
                            "output_file": {"type": "string", "example": "backend/outputs/bluepages_validated_20260419_143122.json"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input"
        },
        "500": {
            "description": "Internal server error"
        }
    }
}

# Complete Validation Pipeline Endpoint
validate_pipeline_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Run complete validation pipeline",
    "description": """
    Run the complete validation pipeline with selected checks.
    
    **Pipeline Steps:**
    1. ISV Validation - Validate against IBM Users API
    2. Active Status Check - Split by active/inactive
    3. Last Login Check - Filter by 3-year threshold
    4. BluPages Validation - Validate against IBM BluPages
    
    You can select which checks to run by providing a checks array.
    """,
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["input_file"],
                    "properties": {
                        "input_file": {
                            "type": "string",
                            "example": "backend/extractions/extraction_20260419_143122.json",
                            "description": "Path to the input extraction file"
                        },
                        "output_dir": {
                            "type": "string",
                            "default": "backend/outputs",
                            "example": "backend/outputs",
                            "description": "Output directory for all pipeline files"
                        },
                        "checks": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["isv", "active_status", "last_login", "bluepages"]
                            },
                            "example": ["isv", "active_status", "last_login", "bluepages"],
                            "description": "List of validation checks to run"
                        },
                        "days_threshold": {
                            "type": "integer",
                            "default": 1095,
                            "example": 1095,
                            "description": "Days threshold for last login check (3 years = 1095 days)"
                        },
                        "max_concurrent": {
                            "type": "integer",
                            "default": 50,
                            "example": 50,
                            "description": "Maximum concurrent API requests"
                        }
                    }
                }
            }
        }
    },
    "responses": {
        "200": {
            "description": "Pipeline completed successfully",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean", "example": True},
                            "pipeline_results": {
                                "type": "object",
                                "properties": {
                                    "isv": {"type": "object"},
                                    "active_status": {"type": "object"},
                                    "last_login": {"type": "object"},
                                    "bluepages": {"type": "object"}
                                }
                            },
                            "final_output": {"type": "string", "example": "backend/outputs/final_validated_20260419_143122.json"}
                        }
                    }
                }
            }
        },
        "400": {
            "description": "Bad request - Invalid input"
        },
        "500": {
            "description": "Internal server error"
        }
    }
}


# ISV Validation Endpoint
validate_isv_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Validate users against ISV",
    "description": "Validate users against IBM ISV (IBM Users API). Checks if users exist in the ISV system and retrieves their current status.",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["input_file"],
                "properties": {
                    "input_file": {"type": "string", "example": "backend/extractions/extraction_20260419_143122.json"},
                    "output_dir": {"type": "string", "default": "backend/outputs", "example": "backend/outputs"},
                    "batch_size": {"type": "integer", "default": 100, "example": 100},
                    "max_concurrent": {"type": "integer", "default": 50, "example": 50}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "ISV validation completed successfully"},
        "400": {"description": "Bad request - Invalid input"},
        "500": {"description": "Internal server error"}
    }
}

# Active Status Validation Endpoint
validate_active_status_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Split users by active/inactive status",
    "description": "Split users into active and inactive categories based on their account status.",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["input_file"],
                "properties": {
                    "input_file": {"type": "string", "example": "backend/outputs/isv_resolved_users_20260419_143122.json"},
                    "output_dir": {"type": "string", "default": "backend/outputs", "example": "backend/outputs"},
                    "timestamp": {"type": "string", "example": "20260419_143122"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "Users split successfully"},
        "400": {"description": "Bad request"},
        "500": {"description": "Internal server error"}
    }
}

# Last Login Validation Endpoint
validate_last_login_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Filter users by last login date (3 years threshold)",
    "description": "Filter users based on their last login date with a 3-year (1095 days) threshold. Creates two categories: >3 years (dormant) and <3 years (active).",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["input_file"],
                "properties": {
                    "input_file": {"type": "string", "example": "backend/outputs/isv_active_users_20260419_143122.json"},
                    "days_threshold": {"type": "integer", "default": 1095, "example": 1095, "description": "3 years = 1095 days"},
                    "output_dir": {"type": "string", "default": "backend/outputs", "example": "backend/outputs"},
                    "timestamp": {"type": "string", "example": "20260419_143122"},
                    "append_recent": {"type": "boolean", "default": True, "example": True}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "Users filtered by login date successfully"},
        "400": {"description": "Bad request"},
        "500": {"description": "Internal server error"}
    }
}

# BluPages Validation Endpoint
validate_bluepages_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Validate users against IBM BluPages",
    "description": "Validate users against IBM BluPages directory. Checks if users exist in the IBM BluPages system.",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["input_file"],
                "properties": {
                    "input_file": {"type": "string", "example": "backend/outputs/isv_last_login_>3_20260419_143122.json"},
                    "output_dir": {"type": "string", "default": "backend/outputs", "example": "backend/outputs"},
                    "timestamp": {"type": "string", "example": "20260419_143122"},
                    "max_concurrent": {"type": "integer", "default": 50, "example": 50},
                    "batch_size": {"type": "integer", "default": 100, "example": 100}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "BluPages validation completed successfully"},
        "400": {"description": "Bad request"},
        "500": {"description": "Internal server error"}
    }
}

# Complete Validation Pipeline Endpoint
validate_pipeline_spec = {
    "tags": ["Validation Pipeline"],
    "summary": "Run complete validation pipeline",
    "description": "Run the complete validation pipeline with selected checks: ISV, Active Status, Last Login (3-year threshold), and BluPages.",
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["input_file"],
                "properties": {
                    "input_file": {"type": "string", "example": "backend/extractions/extraction_20260419_143122.json"},
                    "output_dir": {"type": "string", "default": "backend/outputs", "example": "backend/outputs"},
                    "checks": {"type": "array", "items": {"type": "string"}, "example": ["isv", "active_status", "last_login", "bluepages"]},
                    "days_threshold": {"type": "integer", "default": 1095, "example": 1095},
                    "max_concurrent": {"type": "integer", "default": 50, "example": 50}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "Pipeline completed successfully"},
        "400": {"description": "Bad request"},
        "500": {"description": "Internal server error"}
    }
}
