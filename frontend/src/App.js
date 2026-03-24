import React, { useState, useEffect, useCallback } from 'react';
import {
  Accordion,
  AccordionItem,
  Button,
  DatePicker,
  DatePickerInput,
  ProgressBar,
  InlineNotification,
  Loading,
  Tag
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import axios from 'axios';
import './App.scss';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

function App() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const [polling, setPolling] = useState(false);

  // Fetch status from API
  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status`);
      setStatus(response.data);
      
      // Start polling if under processing
      if (response.data.status === 'under_processing' && !polling) {
        setPolling(true);
      } else if (response.data.status !== 'under_processing' && polling) {
        setPolling(false);
      }
    } catch (error) {
      console.error('Error fetching status:', error);
      setNotification({
        kind: 'error',
        title: 'Error',
        subtitle: 'Failed to fetch status from server'
      });
    }
  }, [polling]);

  // Fetch history from API
  const fetchHistory = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/history`);
      if (response.data.success) {
        setHistory(response.data.history);
      }
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  }, []);

  // Initial status and history fetch
  useEffect(() => {
    fetchStatus();
    fetchHistory();
  }, [fetchStatus, fetchHistory]);

  // Polling effect
  useEffect(() => {
    let interval;
    if (polling) {
      interval = setInterval(() => {
        fetchStatus();
      }, 5000); // Poll every 5 seconds
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [polling, fetchStatus]);

  // Handle form submission
  const handleSubmit = async () => {
    if (!startDate || !endDate) {
      setNotification({
        kind: 'error',
        title: 'Validation Error',
        subtitle: 'Please select both start and end dates'
      });
      return;
    }

    setLoading(true);
    setNotification(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/retrieve`, {
        start_date: startDate,
        end_date: endDate
      });

      if (response.data.success) {
        setNotification({
          kind: 'success',
          title: 'Success',
          subtitle: 'Data retrieval started successfully'
        });
        setPolling(true);
        fetchStatus();
        fetchHistory(); // Refresh history
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Failed to start data retrieval';
      setNotification({
        kind: 'error',
        title: 'Error',
        subtitle: errorMessage
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle reset
  const handleReset = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/reset`);
      if (response.data.success) {
        setNotification({
          kind: 'success',
          title: 'Success',
          subtitle: 'Status reset successfully'
        });
        fetchStatus();
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Failed to reset status';
      setNotification({
        kind: 'error',
        title: 'Error',
        subtitle: errorMessage
      });
    }
  };

  // Get status tag
  const getStatusTag = () => {
    if (!status) return null;

    const statusConfig = {
      not_started: { type: 'gray', text: 'Not Started' },
      under_processing: { type: 'blue', text: 'Processing' },
      finished: {
        type: status.error ? 'red' : 'green',
        text: status.error ? 'Failed' : 'Completed'
      }
    };

    const config = statusConfig[status.status] || statusConfig.not_started;

    return (
      <Tag type={config.type}>
        {config.text}
      </Tag>
    );
  };

  const isProcessing = status?.status === 'under_processing';
  const isDisabled = isProcessing || loading;

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>Cloudant Data Extraction Control Panel</h1>
        <p>Manage and monitor data extraction jobs</p>
      </div>

      {notification && (
        <InlineNotification
          kind={notification.kind}
          title={notification.title}
          subtitle={notification.subtitle}
          onCloseButtonClick={() => setNotification(null)}
          style={{ marginBottom: '1rem', maxWidth: '100%' }}
        />
      )}

      <Accordion>
        <AccordionItem title="Date Range Configuration" open>
          <div className="date-picker-container">
            <DatePicker
              datePickerType="single"
              onChange={(dates) => {
                if (dates && dates.length > 0) {
                  const date = dates[0];
                  // Format date in local timezone to avoid UTC conversion issues
                  const year = date.getFullYear();
                  const month = String(date.getMonth() + 1).padStart(2, '0');
                  const day = String(date.getDate()).padStart(2, '0');
                  const formatted = `${year}-${month}-${day}`;
                  setStartDate(formatted);
                }
              }}
            >
              <DatePickerInput
                id="start-date"
                placeholder="yyyy-mm-dd"
                labelText="Start Date"
                disabled={isDisabled}
              />
            </DatePicker>

            <DatePicker
              datePickerType="single"
              onChange={(dates) => {
                if (dates && dates.length > 0) {
                  const date = dates[0];
                  // Format date in local timezone to avoid UTC conversion issues
                  const year = date.getFullYear();
                  const month = String(date.getMonth() + 1).padStart(2, '0');
                  const day = String(date.getDate()).padStart(2, '0');
                  const formatted = `${year}-${month}-${day}`;
                  setEndDate(formatted);
                }
              }}
            >
              <DatePickerInput
                id="end-date"
                placeholder="yyyy-mm-dd"
                labelText="End Date"
                disabled={isDisabled}
              />
            </DatePicker>
          </div>

          <div className="button-container">
            <Button
              kind="primary"
              onClick={handleSubmit}
              disabled={isDisabled}
            >
              {loading ? 'Starting...' : 'Start Extraction'}
            </Button>

            <Button
              kind="secondary"
              renderIcon={Renew}
              onClick={handleReset}
              disabled={isProcessing}
            >
              Reset
            </Button>
          </div>
        </AccordionItem>

        <AccordionItem title="Extraction Status" open>
          {status ? (
            <div className="status-container">
              <div className="status-row">
                <span className="status-label">Status:</span>
                {getStatusTag()}
              </div>

              {status.status === 'under_processing' && (
                <>
                  <div className="status-row">
                    <span className="status-label">Current Month:</span>
                    <span className="status-value">{status.current_month || 'N/A'}</span>
                  </div>

                  <div className="status-row">
                    <span className="status-label">Records Processed:</span>
                    <span className="status-value">
                      {status.records_processed?.toLocaleString() || 0}
                    </span>
                  </div>

                  <div className="status-row">
                    <span className="status-label">Months Completed:</span>
                    <span className="status-value">
                      {status.completed_months || 0} / {status.total_months || 0}
                    </span>
                  </div>

                  {status.start_time && (
                    <div className="status-row">
                      <span className="status-label">Elapsed Time:</span>
                      <span className="status-value">
                        {(() => {
                          const elapsed = Math.floor(Date.now() / 1000 - status.start_time);
                          const minutes = Math.floor(elapsed / 60);
                          const seconds = elapsed % 60;
                          return elapsed >= 60 ? `${minutes}m ${seconds}s` : `${seconds}s`;
                        })()}
                      </span>
                    </div>
                  )}

                  <div className="progress-container">
                    <ProgressBar
                      label="Progress"
                      value={status.progress_percent || 0}
                      max={100}
                      helperText={`${status.progress_percent || 0}% complete`}
                    />
                  </div>
                </>
              )}

              {status.status === 'finished' && !status.error && (
                <>
                  <div className="status-row">
                    <span className="status-label">Total Records Processed:</span>
                    <span className="status-value">
                      {status.records_processed?.toLocaleString() || 0}
                    </span>
                  </div>
                  {status.duration_seconds != null && status.duration_seconds > 0 && (
                    <div className="status-row">
                      <span className="status-label">Duration:</span>
                      <span className="status-value">
                        {status.duration_seconds >= 60
                          ? `${Math.floor(status.duration_seconds / 60)}m ${status.duration_seconds % 60}s`
                          : `${status.duration_seconds}s`
                        }
                      </span>
                    </div>
                  )}
                </>
              )}

              {status.error && (
                <InlineNotification
                  kind="error"
                  title="Extraction Error"
                  subtitle={status.error}
                  hideCloseButton
                  lowContrast
                />
              )}

              {status.start_date && status.end_date && (
                <div className="status-row">
                  <span className="status-label">Date Range:</span>
                  <span className="status-value">
                    {status.start_date} to {status.end_date}
                  </span>
                </div>
              )}

              {status.last_updated && (
                <div className="status-row">
                  <span className="status-label">Last Updated:</span>
                  <span className="status-value">
                    {new Date(status.last_updated).toLocaleString()}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <Loading description="Loading status..." />
          )}
        </AccordionItem>

        <AccordionItem title="Extraction History">
          {history.length > 0 ? (
            <div className="history-container">
              <p className="history-description">
                View past extraction jobs. Click on an entry to see details.
              </p>
              <div className="history-list">
                {history.map((entry) => (
                  <div key={entry.id} className="history-item">
                    <div className="history-item-header">
                      <Tag type={entry.status === 'completed' ? 'green' : 'red'}>
                        {entry.status}
                      </Tag>
                      <span className="history-timestamp">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="history-item-details">
                      <div className="history-detail">
                        <span className="history-label">Date Range:</span>
                        <span className="history-value">
                          {entry.start_date} to {entry.end_date}
                        </span>
                      </div>
                      <div className="history-detail">
                        <span className="history-label">Records:</span>
                        <span className="history-value">
                          {entry.records_processed?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div className="history-detail">
                        <span className="history-label">Months:</span>
                        <span className="history-value">
                          {entry.months_processed || 0}
                        </span>
                      </div>
                      {entry.duration_seconds != null && entry.duration_seconds > 0 && (
                        <div className="history-detail">
                          <span className="history-label">Duration:</span>
                          <span className="history-value">
                            {entry.duration_seconds >= 60
                              ? `${Math.floor(entry.duration_seconds / 60)}m ${entry.duration_seconds % 60}s`
                              : `${entry.duration_seconds}s`
                            }
                          </span>
                        </div>
                      )}
                      {entry.error && (
                        <div className="history-detail error">
                          <span className="history-label">Error:</span>
                          <span className="history-value">{entry.error}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-history">
              <p>📋 No extraction history yet</p>
              <p className="empty-history-subtitle">
                Start your first extraction to see it here
              </p>
            </div>
          )}
        </AccordionItem>
      </Accordion>
    </div>
  );
}

export default App;

// Made with Bob
