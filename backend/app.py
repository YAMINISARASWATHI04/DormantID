"""
Flask Backend for Cloudant Data Extraction Control System
Provides REST APIs for job management and status tracking
"""

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import sys

# Add parent directory to path to import cloudant_extractor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cloudant_extractor_async import CloudantExtractorAsync
from backend.filters import FilterManager
import asyncio

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Status file path
STATUS_FILE = 'status.json'
HISTORY_FILE = 'extraction_history.json'

# Global lock for thread-safe status updates
status_lock = threading.Lock()

# Global reference to current extractor (for stop functionality)
current_extractor = None
current_extractor_lock = threading.Lock()


class StatusManager:
    """Manages job status persistence and updates"""
    
    @staticmethod
    def load_status():
        """Load status from file"""
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading status: {e}")
        
        # Return default status
        return {
            'status': 'not_started',
            'current_month': None,
            'records_processed': 0,
            'progress_percent': 0,
            'start_date': None,
            'end_date': None,
            'total_months': 0,
            'completed_months': 0,
            'error': None,
            'last_updated': None
        }
    
    @staticmethod
    def save_status(status_data):
        """Save status to file"""
        with status_lock:
            try:
                status_data['last_updated'] = datetime.now().isoformat()
                with open(STATUS_FILE, 'w') as f:
                    json.dump(status_data, f, indent=2)
            except Exception as e:
                print(f"Error saving status: {e}")
    
    @staticmethod
    def update_status(updates):
        """Update specific fields in status"""
        status = StatusManager.load_status()
        status.update(updates)
        StatusManager.save_status(status)
        return status


class HistoryManager:
    """Manages extraction history persistence"""
    
    @staticmethod
    def load_history():
        """Load history from file"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
        
        return []
    
    @staticmethod
    def save_history(history_data):
        """Save history to file"""
        with status_lock:
            try:
                with open(HISTORY_FILE, 'w') as f:
                    json.dump(history_data, f, indent=2)
            except Exception as e:
                print(f"Error saving history: {e}")
    
    @staticmethod
    def add_history_entry(entry):
        """Add a new history entry"""
        history = HistoryManager.load_history()
        history.insert(0, entry)  # Add to beginning (most recent first)
        
        # Keep only last 100 entries
        if len(history) > 100:
            history = history[:100]
        
        HistoryManager.save_history(history)
        return history


class ExtractorWrapper:
    """Wrapper for CloudantExtractor with status tracking"""
    
    def __init__(self, start_date, end_date, filter_config=None, batch_size=3000):
        self.start_date = start_date
        self.end_date = end_date
        self.extractor = None
        self.filter_config = filter_config or {}
        self.filter_manager = None
        self.batch_size = batch_size
        
    def calculate_total_months(self):
        """Calculate total months in date range"""
        # Parse datetime with or without timestamp
        try:
            start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M')
            except ValueError:
                start = datetime.strptime(self.start_date, '%Y-%m-%d')
        
        try:
            end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M')
            except ValueError:
                end = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        return months
    
    def run(self):
        """Run extraction with status updates (wraps async execution)"""
        # Run async extraction in a new event loop
        asyncio.run(self._run_async())
    
    async def _run_async(self):
        """Async extraction logic"""
        start_time = time.time()
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"extraction_{timestamp}.json"
        output_path = os.path.join('backend', 'extractions', output_filename)
        
        # Create extractions directory if it doesn't exist
        os.makedirs(os.path.join('backend', 'extractions'), exist_ok=True)
        
        # Initialize output file
        self.output_file = output_path
        self.extracted_data = []
        
        try:
            # Parse dates with or without timestamp
            try:
                start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M')
                except ValueError:
                    start = datetime.strptime(self.start_date, '%Y-%m-%d')
            
            try:
                end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M')
                except ValueError:
                    end = datetime.strptime(self.end_date, '%Y-%m-%d')
            
            # Calculate total months
            total_months = self.calculate_total_months()
            
            # Update status to under_processing
            StatusManager.update_status({
                'status': 'under_processing',
                'start_date': self.start_date,
                'end_date': self.end_date,
                'total_months': total_months,
                'completed_months': 0,
                'records_processed': 0,
                'progress_percent': 0,
                'current_month': f"{start.year}-{start.month:02d}",
                'error': None,
                'start_time': start_time,
                'output_file': output_filename,
                'filters': self.filter_config
            })
            
            # Initialize filter manager
            self.filter_manager = FilterManager(self.filter_config)
            logger.info(f"Filter configuration: {self.filter_config}")
            logger.info(f"Enabled filters: {self.filter_manager.get_stats()['enabled_filters']}")
            
            # Initialize extractor
            username = os.getenv('CLOUDANT_USERNAME')
            password = os.getenv('CLOUDANT_PASSWORD')
            base_url = os.getenv('CLOUDANT_URL')
            
            if not all([username, password, base_url]):
                raise Exception("Missing Cloudant credentials in environment variables")
            
            self.extractor = CloudantExtractorWithCallback(
                base_url=base_url,
                username=username,
                password=password,
                batch_size=self.batch_size,
                status_callback=self.update_progress,
                data_storage_callback=self.store_batch_data,
                total_months=total_months
            )
            
            # Create session and run extraction
            await self.extractor.create_session()
            
            # Run extraction
            await self.extractor.extract_date_range(
                start_year=start.year,
                start_month=start.month,
                end_year=end.year,
                end_month=end.month
            )
            
            # Calculate duration
            end_time = time.time()
            duration_seconds = int(end_time - start_time)
            
            # Mark as finished
            StatusManager.update_status({
                'status': 'finished',
                'progress_percent': 100,
                'error': None,
                'duration_seconds': duration_seconds,
                'filters': self.filter_config
            })
            
            # Add to history
            HistoryManager.add_history_entry({
                'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'start_date': self.start_date,
                'end_date': self.end_date,
                'records_processed': self.extractor.total_records_processed if self.extractor else 0,
                'months_processed': self.extractor.months_processed if self.extractor else 0,
                'status': 'completed',
                'error': None,
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration_seconds,
                'filename': output_filename,
                'filters': self.filter_config
            })
            
        except InterruptedError as e:
            # Handle user-requested stop
            end_time = time.time()
            duration_seconds = int(end_time - start_time)
            
            # Mark as stopped
            StatusManager.update_status({
                'status': 'stopped',
                'error': 'Stopped by user',
                'duration_seconds': duration_seconds,
                'filters': self.filter_config
            })
            
            # Add stopped entry to history
            HistoryManager.add_history_entry({
                'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'start_date': self.start_date,
                'end_date': self.end_date,
                'records_processed': self.extractor.total_records_processed if self.extractor else 0,
                'months_processed': self.extractor.months_processed if self.extractor else 0,
                'status': 'stopped',
                'error': 'Stopped by user',
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration_seconds,
                'filename': output_filename if hasattr(self, 'output_file') else None,
                'filters': self.filter_config
            })
            
            print(f"Extraction stopped by user")
            
        except Exception as e:
            # Calculate duration even for failed jobs
            end_time = time.time()
            duration_seconds = int(end_time - start_time)
            
            # Mark as finished with error
            StatusManager.update_status({
                'status': 'finished',
                'error': str(e),
                'duration_seconds': duration_seconds,
                'filters': self.filter_config
            })
            
            # Add failed entry to history
            HistoryManager.add_history_entry({
                'id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'start_date': self.start_date,
                'end_date': self.end_date,
                'records_processed': self.extractor.total_records_processed if self.extractor else 0,
                'months_processed': self.extractor.months_processed if self.extractor else 0,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration_seconds,
                'filename': None,
                'filters': self.filter_config
            })
            
            print(f"Extraction error: {e}")
        
        finally:
            # Finalize the output file
            if hasattr(self, 'output_file') and hasattr(self, 'extracted_data'):
                self.finalize_output_file()
            
            if self.extractor:
                await self.extractor.close()
    
    def store_batch_data(self, batch):
        """Store batch data to file incrementally with date and plugin filtering"""
        try:
            # Filter records to ensure they're within the requested date range
            # Parse with or without timestamp
            try:
                start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    start = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M')
                except ValueError:
                    start = datetime.strptime(self.start_date, '%Y-%m-%d')
            
            try:
                end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    end = datetime.strptime(self.end_date, '%Y-%m-%d %H:%M')
                except ValueError:
                    end = datetime.strptime(self.end_date, '%Y-%m-%d')
            
            filtered_batch = []
            date_filtered_out = 0
            plugin_filtered_out = 0
            
            for record in batch:
                key = record.get('key', [])
                if len(key) >= 7:
                    # Extract datetime from key: [boolean, year, month, day, hour, minute, second]
                    try:
                        record_datetime = datetime(key[1], key[2], key[3], key[4], key[5], key[6])
                        # Only include if within datetime range
                        if start <= record_datetime <= end:
                            # Apply plugin filters if filter manager is available
                            if self.filter_manager:
                                if self.filter_manager.filter_record(record):
                                    filtered_batch.append(record)
                                else:
                                    plugin_filtered_out += 1
                            else:
                                filtered_batch.append(record)
                        else:
                            date_filtered_out += 1
                            logger.debug(f"Filtered out record with datetime {record_datetime} (outside range {start} to {end})")
                    except (ValueError, IndexError) as e:
                        # Skip invalid dates
                        logger.warning(f"Invalid date in record key {key}: {e}")
                        continue
            
            if date_filtered_out > 0:
                logger.info(f"Date filter: {date_filtered_out} records outside date range from batch of {len(batch)}")
            
            if plugin_filtered_out > 0:
                logger.info(f"Plugin filters: {plugin_filtered_out} records filtered from batch")
            
            # Append filtered batch to extracted data
            self.extracted_data.extend(filtered_batch)
            
            # Write to file every 10,000 records to avoid memory issues
            if len(self.extracted_data) >= 10000:
                self.flush_to_file()
        except Exception as e:
            logger.error(f"Error storing batch data: {e}")
    
    def flush_to_file(self):
        """Flush accumulated data to file"""
        if not self.extracted_data:
            return
        
        try:
            # Check if file exists to determine if we need to add opening bracket
            file_exists = os.path.exists(self.output_file)
            
            with open(self.output_file, 'a') as f:
                if not file_exists:
                    # Start JSON array
                    f.write('[\n')
                
                # Write records - one per line, compact format
                for i, record in enumerate(self.extracted_data):
                    # Compact JSON (no indentation)
                    json_str = json.dumps(record, separators=(',', ':'))
                    # Add comma if not the first record in file
                    if file_exists or i > 0:
                        f.write(',\n')
                    f.write(json_str)
            
            # Clear the buffer
            self.extracted_data = []
            
        except Exception as e:
            logger.error(f"Error flushing data to file: {e}")
    
    def finalize_output_file(self):
        """Finalize the output file by closing JSON array"""
        try:
            # Flush any remaining data
            self.flush_to_file()
            
            # Close JSON array
            with open(self.output_file, 'a') as f:
                f.write('\n]')
            
            logger.info(f"Data saved to: {self.output_file}")
            
        except Exception as e:
            logger.error(f"Error finalizing output file: {e}")
    
    def update_progress(self, year, month, records_processed, completed_months, total_months):
        """Callback to update progress"""
        progress_percent = int((completed_months / total_months) * 100) if total_months > 0 else 0
        
        StatusManager.update_status({
            'current_month': f"{year}-{month:02d}",
            'records_processed': records_processed,
            'completed_months': completed_months,
            'progress_percent': progress_percent
        })


class CloudantExtractorWithCallback(CloudantExtractorAsync):
    """Extended CloudantExtractorAsync with progress callbacks and data storage"""
    
    def __init__(self, *args, status_callback=None, data_storage_callback=None, total_months=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.status_callback = status_callback
        self.data_storage_callback = data_storage_callback
        self.total_months_expected = total_months
    
    async def extract_year(self, year, start_month=1, end_month=12):
        """Override to add progress tracking (async)"""
        logger.info(f"=" * 80)
        logger.info(f"Starting extraction for year {year}")
        logger.info(f"Months: {start_month} to {end_month}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"=" * 80)
        
        start_time = time.time()
        
        for month in range(start_month, end_month + 1):
            month_start_time = time.time()
            
            try:
                # Process month data in batches (async)
                async for batch in self._extract_month_data(year, month):
                    # Store data if callback provided
                    if self.data_storage_callback:
                        self.data_storage_callback(batch)
                    
                    # Process the batch immediately (streaming approach)
                    processed = self.process_batch(batch)
                    
                    self.total_batches_processed += 1
                    self.total_records_processed += processed
                
                self.months_processed += 1
                
                # Callback for progress update
                if self.status_callback:
                    self.status_callback(
                        year=year,
                        month=month,
                        records_processed=self.total_records_processed,
                        completed_months=self.months_processed,
                        total_months=self.total_months_expected
                    )
                
                month_duration = time.time() - month_start_time
                logger.info(
                    f"Month {year}-{month:02d} completed in "
                    f"{month_duration:.2f} seconds"
                )
                
            except InterruptedError:
                # Re-raise to stop the extraction
                raise
            except Exception as e:
                logger.error(f"Failed to process {year}-{month:02d}: {e}")
                continue
        
        total_duration = time.time() - start_time
        
        logger.info(f"=" * 80)
        logger.info(f"Extraction completed for year {year}")
        logger.info(f"Total months processed: {self.months_processed}")
        logger.info(f"Total batches processed: {self.total_batches_processed}")
        logger.info(f"Total records processed: {self.total_records_processed}")
        logger.info(f"Total duration: {total_duration:.2f} seconds")
        if total_duration > 0:
            logger.info(f"Average records/second: {self.total_records_processed / total_duration:.2f}")
        logger.info(f"=" * 80)


# Import required modules for the extended class
import time
import logging
logger = logging.getLogger(__name__)


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current job status"""
    status = StatusManager.load_status()
    return jsonify(status)



@app.route('/api/filters', methods=['GET'])
def get_filters():
    """Get list of available filters"""
    try:
        # Create a temporary filter manager to get available filters
        temp_manager = FilterManager()
        filters = temp_manager.get_available_filters()
        
        return jsonify({
            'success': True,
            'filters': filters
        })
        
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/retrieve', methods=['POST'])
def start_retrieval():
    """Start data retrieval job"""
    try:
        # Check current status
        current_status = StatusManager.load_status()
        
        if current_status['status'] == 'under_processing':
            return jsonify({
                'success': False,
                'error': 'A job is already running. Please wait for it to complete.'
            }), 400
        
        # Get request data
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        filters = data.get('filters', {})  # Get filter configuration
        batch_size = data.get('batch_size', 3000)  # Get batch size, default 3000
        
        # Validate batch size
        try:
            batch_size = int(batch_size)
            if batch_size < 100 or batch_size > 10000:
                return jsonify({
                    'success': False,
                    'error': 'Batch size must be between 100 and 10000'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid batch size'
            }), 400
        
        # Validate input
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'start_date and end_date are required'
            }), 400
        
        # Validate date format (supports YYYY-MM-DD, YYYY-MM-DD HH:MM, and YYYY-MM-DD HH:MM:SS)
        try:
            # Try parsing with full timestamp first
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # Try HH:MM format (append :00 for seconds)
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M')
                    # Update the date strings to include seconds for consistency
                    start_date = start_dt.strftime('%Y-%m-%d %H:%M:%S')
                    end_date = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Fall back to date-only format
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD, YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS'
            }), 400
        
        # Create extractor wrapper with filter configuration and batch size
        wrapper = ExtractorWrapper(start_date, end_date, filter_config=filters, batch_size=batch_size)
        
        # Store reference to wrapper for stop functionality
        global current_extractor
        with current_extractor_lock:
            current_extractor = wrapper
        
        # Start extraction in background thread
        thread = threading.Thread(target=wrapper.run, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Data retrieval started successfully',
            'start_date': start_date,
            'end_date': end_date
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reset', methods=['POST'])
def reset_status():
    """Reset job status to not_started"""
    try:
        current_status = StatusManager.load_status()
        
        if current_status['status'] == 'under_processing':
            return jsonify({
                'success': False,
                'error': 'Cannot reset while a job is running'
            }), 400
        
        # Reset status
        StatusManager.save_status({
            'status': 'not_started',
            'current_month': None,
            'records_processed': 0,
            'progress_percent': 0,
            'start_date': None,
            'end_date': None,
            'total_months': 0,
            'completed_months': 0,
            'error': None,
            'last_updated': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Status reset successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stop', methods=['POST'])
def stop_extraction():
    """Stop the currently running extraction"""
    try:
        global current_extractor
        
        with current_extractor_lock:
            if current_extractor is None:
                return jsonify({
                    'success': False,
                    'error': 'No extraction is currently running'
                }), 400
            
            if current_extractor.extractor is None:
                return jsonify({
                    'success': False,
                    'error': 'Extractor not initialized yet'
                }), 400
            
            # Request stop
            current_extractor.extractor.request_stop()
        
        return jsonify({
            'success': True,
            'message': 'Stop requested. Extraction will stop after current batch.'
        })
        
    except Exception as e:
        logger.error(f"Error stopping extraction: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _get_extraction_file_path(filename):
    """Helper function to get extraction file path with validation"""
    # Security: Only allow JSON files
    if not filename.endswith('.json'):
        return None, 'Invalid file type'
    
    # Check extraction directory
    file_path = os.path.join('backend', 'extractions', filename)
    
    if not os.path.exists(file_path):
        return None, 'File not found'
    
    return file_path, None


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download extraction file"""
    try:
        file_path, error = _get_extraction_file_path(filename)
        
        if error or not file_path:
            return jsonify({
                'success': False,
                'error': error or 'File not found'
            }), 404 if error == 'File not found' else 400
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/view/<filename>', methods=['GET'])
def view_file(filename):
    """View extraction file with pagination"""
    try:
        file_path, error = _get_extraction_file_path(filename)
        
        if error or not file_path:
            return jsonify({
                'success': False,
                'error': error or 'File not found'
            }), 404 if error == 'File not found' else 400
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 100, type=int)
        
        # Validate pagination parameters
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 1000:
            page_size = 100
        
        # Read and parse JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Calculate pagination
        total_records = len(data)
        total_pages = (total_records + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get page data
        page_data = data[start_idx:end_idx]
        
        return jsonify({
            'success': True,
            'data': page_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total_records,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        })
        
    except Exception as e:
        logger.error(f"Error viewing file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/extractions', methods=['GET'])
def list_extractions():
    """List all available extraction files"""
    try:
        extractions = []
        extraction_dir = os.path.join('backend', 'extractions')
        
        if os.path.exists(extraction_dir):
            for filename in os.listdir(extraction_dir):
                if filename.endswith('.json') and filename.startswith('extraction_'):
                    file_path = os.path.join(extraction_dir, filename)
                    file_stats = os.stat(file_path)
                    
                    extractions.append({
                        'filename': filename,
                        'size': file_stats.st_size,
                        'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                        'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                    })
        
        # Sort by creation time (newest first)
        extractions.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'extractions': extractions,
            'count': len(extractions)
        })
        
    except Exception as e:
        logger.error(f"Error listing extractions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'Cloudant Extractor API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'status': '/api/status',
            'retrieve': '/api/retrieve',
            'reset': '/api/reset',
            'history': '/api/history',
            'health': '/api/health'
        },
        'documentation': 'See SETUP.md for API documentation'
    })


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get extraction history"""
    history = HistoryManager.load_history()
    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Initialize status file if it doesn't exist
    if not os.path.exists(STATUS_FILE):
        StatusManager.save_status({
            'status': 'not_started',
            'current_month': None,
            'records_processed': 0,
            'progress_percent': 0,
            'start_date': None,
            'end_date': None,
            'total_months': 0,
            'completed_months': 0,
            'error': None,
            'last_updated': None
        })
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

# Made with Bob
