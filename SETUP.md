# Setup Instructions - Cloudant Extractor Control System

Complete setup guide for the backend + UI control system.

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- IBM Cloudant credentials

## 🚀 Quick Start

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp ../.env.example ../.env

# Edit .env with your Cloudant credentials
# Required variables:
# - CLOUDANT_USERNAME
# - CLOUDANT_PASSWORD
# - CLOUDANT_URL

# Start Flask server
python app.py
```

The backend will start on `http://localhost:5000`

### 2. Frontend Setup

```bash
# Open a new terminal
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Start React development server
npm start
```

The frontend will start on `http://localhost:3000`

## 📁 Project Structure

```
dormant_id_/
├── backend/
│   ├── app.py                 # Flask backend server
│   ├── requirements.txt       # Python dependencies
│   └── status.json           # Job status (auto-created)
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.scss          # Styles
│   │   ├── index.js          # Entry point
│   │   └── index.scss        # Global styles
│   ├── package.json
│   └── .env.example
├── cloudant_extractor.py     # Core extraction logic
├── .env                      # Cloudant credentials
└── status.json              # Job status persistence
```

## 🔧 Configuration

### Backend Configuration (.env)

```bash
# Cloudant Authentication
CLOUDANT_USERNAME=your_username
CLOUDANT_PASSWORD=your_password
CLOUDANT_URL=https://your-instance.cloudant.com/db/_design/view/_view/name

# Extraction Configuration
BATCH_SIZE=1000
START_YEAR=2007
START_MONTH=1
END_YEAR=2026
END_MONTH=12
```

### Frontend Configuration (frontend/.env)

```bash
# API Base URL
REACT_APP_API_URL=http://localhost:5000/api
```

## 🌐 API Endpoints

### GET /api/status
Get current job status

**Response:**
```json
{
  "status": "not_started|under_processing|finished",
  "current_month": "2024-03",
  "records_processed": 150000,
  "progress_percent": 45,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "total_months": 12,
  "completed_months": 5,
  "error": null,
  "last_updated": "2024-03-20T10:30:00"
}
```

### POST /api/retrieve
Start data extraction job

**Request:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Data retrieval started successfully",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

**Error Response (if job already running):**
```json
{
  "success": false,
  "error": "A job is already running. Please wait for it to complete."
}
```

### POST /api/reset
Reset job status to not_started

**Response:**
```json
{
  "success": true,
  "message": "Status reset successfully"
}
```

### GET /api/health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-20T10:30:00"
}
```

## 🎨 UI Features

### Date Range Configuration Panel
- **Start Date Picker**: Select extraction start date
- **End Date Picker**: Select extraction end date
- **Start Extraction Button**: Initiates the extraction job
  - Disabled when job is running
  - Shows "Starting..." during initialization
- **Reset Button**: Resets status to not_started
  - Disabled when job is running

### Status Panel
- **Status Tag**: Visual indicator of current status
  - Gray: Not Started
  - Blue with spinner: Processing
  - Green with checkmark: Completed
  - Red with error icon: Failed

- **Progress Information** (shown during processing):
  - Current month being processed
  - Total records processed
  - Months completed / Total months
  - Progress bar with percentage

- **Completion Information** (shown after finish):
  - Total records processed
  - Date range processed
  - Error message (if failed)
  - Last updated timestamp

### Auto-Polling
- Automatically polls status every 5 seconds when job is running
- Stops polling when job completes
- Updates UI in real-time

## 🔒 System Rules

1. **Single Job Execution**: Only one extraction job can run at a time
2. **Status Persistence**: Status survives server restarts (stored in status.json)
3. **Background Processing**: Extraction runs in background thread, doesn't block server
4. **Button State Management**: Send button automatically disabled during processing
5. **Error Handling**: Errors are captured and displayed in UI

## 🧪 Testing the System

### 1. Test Basic Flow

```bash
# 1. Start backend
cd backend
python app.py

# 2. Start frontend (new terminal)
cd frontend
npm start

# 3. Open browser to http://localhost:3000
# 4. Select date range (e.g., 2024-01-01 to 2024-01-31)
# 5. Click "Start Extraction"
# 6. Watch status update in real-time
```

### 2. Test Status Persistence

```bash
# 1. Start a job
# 2. Stop the backend server (Ctrl+C)
# 3. Restart the backend
# 4. Refresh the frontend
# 5. Status should be preserved
```

### 3. Test Concurrent Job Prevention

```bash
# 1. Start a job
# 2. Try to start another job
# 3. Should see error: "A job is already running"
# 4. Send button should be disabled
```

### 4. Test Reset Functionality

```bash
# 1. Complete a job (or let it fail)
# 2. Click "Reset" button
# 3. Status should return to "Not Started"
# 4. All counters should reset to 0
```

## 🐛 Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'flask'`
```bash
# Solution: Install dependencies
pip install -r backend/requirements.txt
```

**Problem**: `Missing required environment variables`
```bash
# Solution: Create and configure .env file
cp .env.example .env
# Edit .env with your credentials
```

**Problem**: `Port 5000 already in use`
```bash
# Solution: Change port in backend/app.py
app.run(debug=True, host='0.0.0.0', port=5001)
# Update frontend/.env accordingly
```

### Frontend Issues

**Problem**: `Cannot find module '@carbon/react'`
```bash
# Solution: Install dependencies
cd frontend
npm install
```

**Problem**: `Network Error` when calling API
```bash
# Solution: Check backend is running
# Verify REACT_APP_API_URL in frontend/.env
# Check CORS is enabled in backend
```

**Problem**: Date picker not working
```bash
# Solution: Clear browser cache
# Restart development server
npm start
```

### Status File Issues

**Problem**: Status not persisting
```bash
# Solution: Check file permissions
chmod 644 status.json

# Or delete and let it recreate
rm status.json
# Restart backend
```

## 📊 Performance Considerations

### Backend
- Runs extraction in background thread
- Non-blocking Flask server
- Status updates after each month completion
- Efficient JSON file I/O with locking

### Frontend
- Polling interval: 5 seconds (configurable)
- Automatic polling start/stop
- Efficient React state management
- Responsive Carbon Design System components

## 🔐 Security Notes

1. **Never commit .env files** - Contains sensitive credentials
2. **Use HTTPS in production** - Secure API communication
3. **Implement authentication** - Add auth layer for production
4. **Rate limiting** - Consider adding rate limits to API endpoints
5. **Input validation** - Backend validates all inputs

## 🚀 Production Deployment

### Backend Deployment

```bash
# Use production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

### Frontend Deployment

```bash
# Build production bundle
cd frontend
npm run build

# Serve with nginx or any static server
# Build output is in frontend/build/
```

### Environment Variables

```bash
# Production backend
export FLASK_ENV=production
export CLOUDANT_USERNAME=xxx
export CLOUDANT_PASSWORD=xxx
export CLOUDANT_URL=xxx

# Production frontend
export REACT_APP_API_URL=https://your-api-domain.com/api
```

## 📝 Development Tips

### Backend Development

```bash
# Enable debug mode (auto-reload)
# Already enabled in app.py for development

# View logs
tail -f cloudant_extraction.log

# Test API with curl
curl http://localhost:5000/api/status
curl -X POST http://localhost:5000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2024-01-01","end_date":"2024-01-31"}'
```

### Frontend Development

```bash
# Hot reload is enabled by default
# Changes reflect immediately

# Build for production
npm run build

# Test production build locally
npm install -g serve
serve -s build
```

## 🎯 Next Steps

1. **Add Authentication**: Implement user authentication
2. **Add Logging Dashboard**: Visualize extraction logs
3. **Add Email Notifications**: Notify on job completion
4. **Add Job History**: Track past extraction jobs
5. **Add Data Preview**: Preview extracted data
6. **Add Export Options**: Export data in various formats

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs (cloudant_extraction.log)
3. Check status.json for current state
4. Verify environment variables are set correctly

## 📄 License

[Your License Here]