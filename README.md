# Cloudant Data Extraction Pipeline

A production-ready, scalable data extraction pipeline for IBM Cloudant with monthly partitioning and key-based pagination, designed to handle 21M+ records efficiently.

## 🎯 Key Features

- **Monthly Partitioning**: Divides data extraction by month for better manageability
- **Key-Based Pagination**: Avoids expensive `skip` operations using `startkey_docid`
- **Incremental Data Storage**: Saves extracted data to timestamped JSON files
- **Fault Tolerance**: Built-in retry logic with exponential backoff
- **Low Memory Footprint**: Streaming approach with incremental file writing
- **Production Ready**: Comprehensive logging, error handling, and monitoring
- **Restart Safe**: Idempotent design allows safe restarts
- **Web UI**: React-based control panel with real-time progress tracking

## 🏗️ Architecture

### Monthly Partitioning Strategy

The pipeline divides the extraction into monthly chunks:

```
Year 2024:
  ├── January (2024-01-01 to 2024-01-31)
  ├── February (2024-02-01 to 2024-02-29)
  └── ... (continues for all months)
```

**Benefits:**
- Reduces query scope and complexity
- Enables parallel processing (future enhancement)
- Easier to track progress and resume
- Better error isolation

### Key-Based Pagination

Within each month, pagination uses `startkey` and `startkey_docid`:

```python
# First request
startkey = [true, 2024, 1, 1, 0, 0, 0]
endkey = [true, 2024, 1, 31, 23, 59, 59]
limit = 1000

# Subsequent requests use last row's key and id
startkey = last_row['key']
startkey_docid = last_row['id']
```

**Why `startkey_docid` is MANDATORY:**

1. **Prevents Duplicates**: When multiple documents share the same key, `startkey` alone would return the same documents again
2. **Ensures Completeness**: Guarantees no records are skipped
3. **Deterministic Ordering**: Provides consistent pagination across requests

Example scenario:
```
Records with same timestamp:
- key: [true, 2024, 1, 15, 10, 30, 0], id: "doc1"
- key: [true, 2024, 1, 15, 10, 30, 0], id: "doc2"
- key: [true, 2024, 1, 15, 10, 30, 0], id: "doc3"

Without startkey_docid: Would return doc1, doc2, doc3 repeatedly
With startkey_docid="doc2": Returns doc3 onwards (correct pagination)
```

## 📋 Prerequisites

- Python 3.8+
- IBM Cloudant database access
- Basic Authentication credentials

## 🚀 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd dormant_id_
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required
CLOUDANT_USERNAME=your_username
CLOUDANT_PASSWORD=your_password
CLOUDANT_URL=https://your-instance.cloudant.com/db/_design/view/_view/name

# Optional (with defaults)
BATCH_SIZE=1000          # Records per batch
START_YEAR=2024          # Starting year
START_MONTH=1            # Starting month (1-12)
END_YEAR=2026            # Ending year
END_MONTH=12             # Ending month (1-12)
```

### Using python-dotenv (Recommended)

```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file

# Then run the extractor
python cloudant_extractor.py
```

### Direct Environment Variables

```bash
export CLOUDANT_USERNAME="your_username"
export CLOUDANT_PASSWORD="your_password"
export CLOUDANT_URL="https://..."
python cloudant_extractor.py
```

## 📖 Usage

### Basic Usage

```python
from cloudant_extractor import CloudantExtractor

# Initialize
extractor = CloudantExtractor(
    base_url="https://your-instance.cloudant.com/db/_design/view/_view/name",
    username="your_username",
    password="your_password",
    batch_size=1000
)

# Extract data for a specific year
extractor.extract_year(2024)

# Extract data for a date range
extractor.extract_date_range(
    start_year=2024,
    start_month=1,
    end_year=2026,
    end_month=12
)

# Clean up
extractor.close()
```

### Command Line Usage

```bash
# Using environment variables
python cloudant_extractor.py

# With custom configuration
BATCH_SIZE=500 START_YEAR=2025 python cloudant_extractor.py
```

### Custom Processing Logic

Override the `process_batch` method to implement your business logic:

```python
class CustomExtractor(CloudantExtractor):
    def process_batch(self, rows):
        processed_count = 0
        
        for row in rows:
            key = row.get('key', [])
            value = row.get('value', {})
            doc_id = row.get('id', '')
            
            # Your custom logic here
            if self.is_dormant(key, value):
                self.store_dormant_record(doc_id, key, value)
                processed_count += 1
        
        return processed_count
    
    def is_dormant(self, key, value):
        # Implement dormancy check
        pass
    
    def store_dormant_record(self, doc_id, key, value):
        # Store to database, file, queue, etc.
        pass

## 💾 Data Storage

### Automatic File Storage

Extracted data is automatically saved to timestamped JSON files:

```
backend/extractions/extraction_20260323_133045.json
```

**Features:**
- **Incremental Writing**: Data is written every 10,000 records to avoid memory issues
- **Timestamped Filenames**: Each extraction creates a unique file
- **Valid JSON Format**: Files maintain proper JSON array structure
- **Partial Results**: Data is preserved even if extraction fails mid-way

### File Format

```json
[
  {
    "id": "document_id",
    "key": [true, 2026, 3, 18, 0, 0, 0],
    "value": {
      "field1": "value1",
      "field2": "value2"
    }
  },
  ...
]
```

### Managing Extracted Files

```bash
# View extracted files
ls -lh backend/extractions/

# Compress old files to save space
gzip backend/extractions/extraction_20260320_*.json

# Remove old extractions (be careful!)
rm backend/extractions/extraction_2026032[0-2]_*.json
```

**Note:** Extracted files are excluded from git via `.gitignore`.

```

## 🔍 Monitoring

### Logging

The pipeline provides comprehensive logging:

```
2026-03-20 10:00:00 - INFO - Starting extraction for year 2024
2026-03-20 10:00:00 - INFO - Starting extraction for 2024-01
2026-03-20 10:00:05 - INFO -   Batch 1: Fetched 1000 records (Total: 1000)
2026-03-20 10:00:10 - INFO -   Batch 2: Fetched 1000 records (Total: 2000)
2026-03-20 10:05:00 - INFO - Completed 2024-01: 150 batches, 150000 records
2026-03-20 10:05:00 - INFO - Month 2024-01 completed in 300.00 seconds
```

Logs are written to:
- Console (stdout)
- File: `cloudant_extraction.log`

### Statistics

The extractor tracks:
- Total records processed
- Total batches processed
- Months completed
- Processing duration
- Records per second

## 🛡️ Error Handling

### Retry Logic

- Automatic retries for transient failures (3 attempts by default)
- Exponential backoff between retries
- Handles HTTP 429, 500, 502, 503, 504 errors

### Failure Scenarios

1. **Network Failures**: Automatic retry with backoff
2. **Authentication Errors**: Immediate failure with clear error message
3. **Month Processing Failure**: Logs error and continues with next month
4. **Batch Processing Error**: Logs error and continues with next batch

## 📊 Performance Optimization

### Best Practices

1. **Batch Size**: 
   - Default: 1000 records
   - Increase for faster extraction (up to 5000)
   - Decrease if memory constrained (down to 100)

2. **Connection Pooling**:
   - Reuses HTTP connections
   - Reduces connection overhead
   - Configured automatically

3. **Streaming Processing**:
   - Processes batches immediately
   - No in-memory accumulation
   - Constant memory usage

4. **Parallel Processing** (Future Enhancement):
   ```python
   # Process multiple months in parallel
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [
           executor.submit(extractor.extract_year, year)
           for year in range(2024, 2027)
       ]
   ```

### Scaling Considerations

For 21M+ records:

- **Single Instance**: ~6-8 hours (depending on network and processing)
- **Parallel Processing**: Can reduce to 2-3 hours with 4 workers
- **Distributed**: Use message queues (RabbitMQ, Kafka) for horizontal scaling

## 🔒 Security

- ✅ Credentials via environment variables (never hardcoded)
- ✅ HTTPS for all API calls
- ✅ Basic Authentication support
- ✅ No credentials in logs
- ✅ `.env` file in `.gitignore`

## 🧪 Testing

```bash
# Test with a small date range first
START_YEAR=2026 START_MONTH=3 END_YEAR=2026 END_MONTH=3 python cloudant_extractor.py

# Monitor the log file
tail -f cloudant_extraction.log
```

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   Error: 401 Unauthorized
   Solution: Verify CLOUDANT_USERNAME and CLOUDANT_PASSWORD
   ```

2. **Connection Timeout**
   ```
   Error: Connection timeout
   Solution: Check network connectivity, increase timeout in code
   ```

3. **Rate Limiting**
   ```
   Error: 429 Too Many Requests
   Solution: Reduce batch size or add delay between requests
   ```

4. **Memory Issues**
   ```
   Error: MemoryError
   Solution: Reduce BATCH_SIZE to 100-500
   ```

## 📈 Production Deployment

### Recommended Setup

1. **Use a Process Manager**:
   ```bash
   # Using systemd
   sudo systemctl start cloudant-extractor
   
   # Using supervisor
   supervisorctl start cloudant-extractor
   ```

2. **Monitor Resources**:
   - CPU usage
   - Memory usage
   - Network bandwidth
   - Disk I/O (if writing to files)

3. **Set Up Alerts**:
   - Extraction failures
   - Slow processing (< 100 records/sec)
   - High error rates

4. **Backup Strategy**:
   - Regular backups of processed data
   - Checkpoint mechanism for restart safety

## 📝 License

[Your License Here]

## 🤝 Contributing

[Your Contributing Guidelines Here]

## 📧 Support

For issues or questions, please contact [Your Contact Info]

---

## 🎓 Technical Deep Dive

### Why Not Use `skip`?

The `skip` parameter has O(n) complexity in CouchDB/Cloudant:

```python
# BAD: Using skip (O(n) for each request)
for page in range(0, 21000):
    fetch(skip=page*1000, limit=1000)  # Gets slower with each page

# GOOD: Using key-based pagination (O(1) for each request)
while has_more:
    fetch(startkey=last_key, startkey_docid=last_id, limit=1000)
```

### View Key Structure

```javascript
// Cloudant view emit
emit([isActive, year, month, day, hour, minute, second], {
    userId: doc.userId,
    lastLogin: doc.lastLogin
});
```

This structure enables:
- Efficient time-based queries
- Natural sorting by timestamp
- Monthly partitioning without additional indexes

### Memory Efficiency

```python
# Memory usage remains constant regardless of dataset size
# Only one batch (1000 records) in memory at a time

for batch in extractor._extract_month_data(2024, 1):
    process_batch(batch)  # Process immediately
    # batch is garbage collected after processing
```

## 🔮 Future Enhancements

- [ ] Async/await support with `aiohttp`
- [ ] Parallel month processing
- [ ] Checkpoint/resume mechanism
- [ ] Metrics export (Prometheus)
- [ ] Docker containerization
- [ ] Kubernetes deployment manifests
- [ ] Data validation framework
- [ ] Real-time progress dashboard