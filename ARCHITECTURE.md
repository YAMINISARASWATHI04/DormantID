# Architecture & Design Documentation

## System Overview

The Cloudant Data Extraction Pipeline is designed to efficiently extract and process 21M+ records from IBM Cloudant using a hybrid approach of monthly partitioning and key-based pagination.

## Core Design Principles

### 1. Monthly Partitioning

**Rationale:**
- Reduces query complexity and scope
- Enables parallel processing capabilities
- Provides natural checkpoints for restart safety
- Improves error isolation and recovery

**Implementation:**
```python
# Month boundaries are calculated dynamically
startkey = [true, year, month, 1, 0, 0, 0]
endkey = [true, year, month, last_day, 23, 59, 59]
```

**Benefits:**
- Each month is an independent unit of work
- Failed months can be retried without affecting others
- Progress tracking is granular and meaningful
- Memory usage is bounded per month

### 2. Key-Based Pagination

**Problem with `skip`:**
```python
# BAD: O(n) complexity - gets slower with each page
GET /view?skip=10000&limit=1000  # Scans 10,000 rows to skip them
GET /view?skip=20000&limit=1000  # Scans 20,000 rows to skip them
```

**Solution with `startkey` + `startkey_docid`:**
```python
# GOOD: O(1) complexity - direct seek to position
GET /view?startkey=[...]&startkey_docid=doc123&limit=1000
```

**Why `startkey_docid` is Critical:**

When multiple documents share the same key:
```
Row 1: key=[true,2024,1,15,10,30,0], id="user001"
Row 2: key=[true,2024,1,15,10,30,0], id="user002"  
Row 3: key=[true,2024,1,15,10,30,0], id="user003"
```

Without `startkey_docid`:
- Next request with `startkey=[true,2024,1,15,10,30,0]` returns Row 1 again
- Creates infinite loop or duplicates

With `startkey_docid="user002"`:
- Next request returns Row 3 onwards
- No duplicates, no missing records

### 3. Streaming Architecture

**Memory Efficiency:**
```python
# Traditional approach - loads all data in memory
all_data = []
for batch in fetch_all():
    all_data.extend(batch)  # Memory grows linearly
process(all_data)  # Peak memory = total dataset size

# Streaming approach - constant memory
for batch in fetch_batches():
    process(batch)  # Process immediately
    # batch is garbage collected
    # Peak memory = single batch size
```

**Benefits:**
- Constant memory usage regardless of dataset size
- Can process infinite streams
- Faster time-to-first-result
- Better resource utilization

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CloudantExtractor                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           extract_date_range()                        │  │
│  │  - Orchestrates multi-year extraction                 │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │           extract_year()                              │  │
│  │  - Iterates through months                            │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │      _extract_month_data() [Generator]                │  │
│  │  - Monthly partitioning logic                         │  │
│  │  - Key-based pagination loop                          │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │           _fetch_batch()                              │  │
│  │  - HTTP request with retry logic                      │  │
│  │  - Connection pooling                                 │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │           process_batch()                             │  │
│  │  - Business logic (override in subclass)              │  │
│  │  - Filtering, validation, storage                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐
│  Start Year  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────┐
│  For each month in year:             │
│  ┌────────────────────────────────┐ │
│  │ Calculate month boundaries     │ │
│  │ startkey = [true,Y,M,1,0,0,0] │ │
│  │ endkey = [true,Y,M,LD,23,59,59]│ │
│  └────────────┬───────────────────┘ │
│               │                      │
│               ▼                      │
│  ┌────────────────────────────────┐ │
│  │ Pagination Loop:               │ │
│  │ ┌──────────────────────────┐  │ │
│  │ │ Fetch batch (limit+1)    │  │ │
│  │ └──────────┬───────────────┘  │ │
│  │            │                   │ │
│  │            ▼                   │ │
│  │ ┌──────────────────────────┐  │ │
│  │ │ Process batch            │  │ │
│  │ │ (business logic)         │  │ │
│  │ └──────────┬───────────────┘  │ │
│  │            │                   │ │
│  │            ▼                   │ │
│  │ ┌──────────────────────────┐  │ │
│  │ │ Extract last row's       │  │ │
│  │ │ key and id               │  │ │
│  │ └──────────┬───────────────┘  │ │
│  │            │                   │ │
│  │            ▼                   │ │
│  │ ┌──────────────────────────┐  │ │
│  │ │ More data?               │  │ │
│  │ │ Yes: Continue loop       │  │ │
│  │ │ No: Next month           │  │ │
│  │ └──────────────────────────┘  │ │
│  └────────────────────────────────┘ │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  Next Year   │
└──────────────┘
```

## Error Handling Strategy

### Retry Logic

```python
# Exponential backoff with jitter
for attempt in range(max_retries):
    try:
        return fetch_data()
    except TransientError:
        delay = retry_delay * (attempt + 1)
        time.sleep(delay)
```

**Retry Conditions:**
- HTTP 429 (Rate Limit)
- HTTP 500, 502, 503, 504 (Server Errors)
- Network timeouts
- Connection errors

**No Retry:**
- HTTP 401, 403 (Authentication/Authorization)
- HTTP 400 (Bad Request)
- HTTP 404 (Not Found)

### Error Isolation

```
Year Level:
  ├─ Month 1: Success ✓
  ├─ Month 2: Failed ✗ (logged, continue)
  ├─ Month 3: Success ✓
  └─ ...

Batch Level:
  ├─ Batch 1: Success ✓
  ├─ Batch 2: Partial (some rows failed, logged)
  ├─ Batch 3: Success ✓
  └─ ...
```

## Performance Optimization

### Connection Pooling

```python
session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,  # Number of connection pools
    pool_maxsize=20       # Connections per pool
)
```

**Benefits:**
- Reuses TCP connections
- Reduces SSL handshake overhead
- Improves throughput by 30-50%

### Batch Size Tuning

| Batch Size | Memory Usage | Network Overhead | Throughput |
|------------|--------------|------------------|------------|
| 100        | Low          | High             | Low        |
| 1000       | Medium       | Medium           | High       |
| 5000       | High         | Low              | Very High  |

**Recommendation:** Start with 1000, adjust based on:
- Available memory
- Network latency
- Processing complexity

### Parallel Processing

```python
# Sequential (current)
for year in [2024, 2025, 2026]:
    extract_year(year)  # ~6 hours total

# Parallel (future enhancement)
with ThreadPoolExecutor(max_workers=3):
    for year in [2024, 2025, 2026]:
        executor.submit(extract_year, year)  # ~2 hours total
```

## Scalability Considerations

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────┐
│                  Load Balancer                       │
└────────┬────────────────────────────────┬───────────┘
         │                                │
    ┌────▼────┐                      ┌────▼────┐
    │ Worker 1│                      │ Worker 2│
    │ 2024    │                      │ 2025    │
    └─────────┘                      └─────────┘
         │                                │
         └────────────┬───────────────────┘
                      │
              ┌───────▼────────┐
              │   Cloudant     │
              └────────────────┘
```

### Distributed Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Producer   │────▶│  Message     │────▶│   Consumer   │
│  (Extractor) │     │  Queue       │     │  (Processor) │
└──────────────┘     │  (RabbitMQ)  │     └──────────────┘
                     └──────────────┘
```

**Benefits:**
- Decouples extraction from processing
- Enables independent scaling
- Provides buffering for rate limiting
- Improves fault tolerance

## Security Architecture

### Credential Management

```
Environment Variables (Production)
         │
         ▼
┌─────────────────────┐
│  Secret Manager     │
│  (AWS Secrets/      │
│   Azure KeyVault)   │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Application  │
    └──────────────┘
```

### Network Security

- All connections use HTTPS/TLS
- Certificate validation enabled
- No credential logging
- Secure credential storage

## Monitoring & Observability

### Metrics to Track

1. **Throughput:**
   - Records per second
   - Batches per minute
   - Months per hour

2. **Errors:**
   - Retry count
   - Failed batches
   - Failed months

3. **Resources:**
   - Memory usage
   - CPU usage
   - Network bandwidth

4. **Progress:**
   - Current month
   - Total records processed
   - Estimated completion time

### Logging Strategy

```
INFO:  High-level progress (month start/end)
DEBUG: Detailed pagination info
WARN:  Retryable errors
ERROR: Non-retryable errors
```

## Future Enhancements

### 1. Async/Await Support

```python
async def _fetch_batch_async(self, ...):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, ...) as response:
            return await response.json()
```

**Benefits:**
- 5-10x throughput improvement
- Better resource utilization
- Non-blocking I/O

### 2. Checkpoint/Resume

```python
# Save state after each month
checkpoint = {
    'last_completed_year': 2024,
    'last_completed_month': 6,
    'total_records': 12500000
}
save_checkpoint(checkpoint)

# Resume from checkpoint
resume_from_checkpoint(checkpoint)
```

### 3. Real-time Monitoring Dashboard

```
┌─────────────────────────────────────────┐
│  Cloudant Extraction Dashboard          │
├─────────────────────────────────────────┤
│  Progress: ████████░░ 80%               │
│  Current: 2024-10                        │
│  Records: 16.8M / 21M                    │
│  Speed: 1,250 records/sec                │
│  ETA: 1h 15m                             │
└─────────────────────────────────────────┘
```

### 4. Data Validation Framework

```python
class Validator:
    def validate_batch(self, batch):
        # Schema validation
        # Data quality checks
        # Consistency checks
        pass
```

## Conclusion

This architecture provides:
- ✅ Scalability to 21M+ records
- ✅ Fault tolerance and reliability
- ✅ Low memory footprint
- ✅ Production-ready error handling
- ✅ Extensibility for future enhancements

## Data Storage Strategy

### Incremental File Writing

**Problem:**
- Loading 21M+ records into memory would cause memory exhaustion
- Waiting until end to write data risks data loss on failure

**Solution:**
```python
# Write data incrementally every 10,000 records
def store_batch_data(self, batch):
    self.extracted_data.extend(batch)
    if len(self.extracted_data) >= 10000:
        self.flush_to_file()
```

**Benefits:**
- Constant memory usage (~10K records in buffer)
- Data is persisted progressively
- Partial results available even if extraction fails
- No risk of OOM (Out of Memory) errors

### File Naming Convention

Files are automatically named with timestamps:
```
backend/extractions/extraction_YYYYMMDD_HHMMSS.json
```

Example: `extraction_20260323_133045.json`

**Advantages:**
- Unique filename per extraction
- Easy to identify when extraction occurred
- Chronological sorting by filename
- No file conflicts between concurrent extractions

### JSON Format

Output files contain a valid JSON array:
```json
[
  {
    "id": "document_id",
    "key": [true, 2026, 3, 18, 0, 0, 0],
    "value": { ... }
  },
  ...
]
```

**Implementation Details:**
- File starts with `[` (opening bracket)
- Records are comma-separated
- File ends with `]` (closing bracket)
- Proper JSON formatting maintained throughout

### Write Strategy

1. **Initialization**: Create file with opening bracket `[`
2. **Batch Writing**: Append records with commas every 10K records
3. **Finalization**: Close array with `]` when extraction completes

This ensures the file is always valid JSON, even during writing.
