# 🚀 Quick Start Guide

Get the Cloudant Extractor Control System running in 5 minutes!

## Prerequisites Check

```bash
# Check Python version (need 3.8+)
python3 --version

# Check Node.js version (need 16+)
node --version

# Check npm
npm --version
```

## Step 1: Clone and Setup Environment (1 min)

```bash
# Navigate to project directory
cd dormant_id_

# Copy environment file
cp .env.example .env

# Edit .env with your Cloudant credentials
nano .env  # or use your preferred editor
```

Required in `.env`:
```
CLOUDANT_USERNAME=your_username
CLOUDANT_PASSWORD=your_password
CLOUDANT_URL=https://your-instance.cloudant.com/db/_design/view/_view/name
```

## Step 2: Start Backend (2 min)

```bash
# Open Terminal 1
cd backend

# Install dependencies
pip3 install -r requirements.txt

# Start Flask server
python3 app.py
```

✅ Backend running at `http://localhost:5000`

## Step 3: Start Frontend (2 min)

```bash
# Open Terminal 2
cd frontend

# Install dependencies (first time only)
npm install

# Copy frontend env file
cp .env.example .env

# Start React app
npm start
```

✅ Frontend opens automatically at `http://localhost:3000`

## Step 4: Use the System

### Start an Extraction Job

1. **Select Date Range**
   - Start Date: `2024-01-01`
   - End Date: `2024-01-31`

2. **Click "Start Extraction"**
   - Button will disable
   - Status changes to "Processing"
   - Progress updates every 5 seconds

3. **Monitor Progress**
   - Watch current month
   - See records processed
   - View progress percentage

4. **Wait for Completion**
   - Status changes to "Completed" (green)
   - Button re-enables
   - View total records processed

### Reset Status

Click **"Reset"** button to clear status and start fresh.

## Verify Everything Works

### Test Backend API

```bash
# Check health
curl http://localhost:5000/api/health

# Check status
curl http://localhost:5000/api/status
```

### Test Frontend

1. Open `http://localhost:3000`
2. You should see:
   - Date Range Configuration panel
   - Extraction Status panel
   - Status showing "Not Started"

## Common Issues

### Backend won't start

```bash
# Missing dependencies?
pip3 install flask flask-cors python-dotenv requests

# Port 5000 in use?
# Edit backend/app.py, change port to 5001
# Update frontend/.env: REACT_APP_API_URL=http://localhost:5001/api
```

### Frontend won't start

```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### Can't connect to backend

```bash
# Check backend is running
curl http://localhost:5000/api/health

# Check frontend .env
cat frontend/.env
# Should show: REACT_APP_API_URL=http://localhost:5000/api
```

## What's Next?

- Read [SETUP.md](SETUP.md) for detailed configuration
- Check [README.md](README.md) for architecture details
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical deep dive

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  React Frontend │ ◄─────► │  Flask Backend   │
│  (Port 3000)    │  REST   │  (Port 5000)     │
└─────────────────┘  API    └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │ Cloudant         │
                            │ Extractor        │
                            │ (Background)     │
                            └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │ status.json      │
                            │ (Persistence)    │
                            └──────────────────┘
```

## Key Features

✅ **Single Job Execution** - Only one job at a time
✅ **Status Persistence** - Survives server restarts
✅ **Real-time Updates** - Auto-polling every 5 seconds
✅ **Background Processing** - Non-blocking server
✅ **Progress Tracking** - Month-by-month updates
✅ **Error Handling** - Graceful error display

## Support

Having issues? Check:
1. Both terminals are running
2. Environment variables are set
3. Cloudant credentials are correct
4. Ports 3000 and 5000 are available

For detailed help, see [SETUP.md](SETUP.md)