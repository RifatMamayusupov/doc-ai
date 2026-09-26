/**
 * Real-time Sync Status Dashboard Component
 * 
 * Shows live status of connector syncs with progress indicators
 */

import React, { useState, useEffect, useCallback } from 'react';
import './SyncDashboard.css';

interface SyncJob {
    connector_id: string;
    connector_name: string;
    connector_type: string;
    status: 'scheduled' | 'running' | 'paused' | 'error';
    next_run: string | null;
    last_run: string | null;
    files_synced: number;
    progress?: number;
    current_file?: string;
    error?: string;
}

interface SyncDashboardProps {
    className?: string;
}

export function SyncDashboard({ className = '' }: SyncDashboardProps) {
    const [jobs, setJobs] = useState<SyncJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [ws, setWs] = useState<WebSocket | null>(null);

    // Fetch initial jobs
    useEffect(() => {
        fetchJobs();
        setupWebSocket();

        return () => {
            ws?.close();
        };
    }, []);

    const fetchJobs = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/api/connectors', {
                headers: { 'Authorization': `Bearer ${token}` },
            });

            if (response.ok) {
                const connectors = await response.json();

                // Convert to SyncJob format
                const syncJobs: SyncJob[] = connectors
                    .filter((c: any) => c.schedule)
                    .map((c: any) => ({
                        connector_id: c.id,
                        connector_name: c.name,
                        connector_type: c.connector_type,
                        status: c.is_active ? 'scheduled' : 'paused',
                        next_run: null,
                        last_run: c.last_sync_at,
                        files_synced: c.files_synced,
                    }));

                setJobs(syncJobs);
            }
        } catch (err) {
            console.error('Failed to fetch jobs:', err);
        } finally {
            setLoading(false);
        }
    };

    const setupWebSocket = () => {
        const token = localStorage.getItem('token');
        const wsUrl = `ws://${window.location.host}/ws?token=${token}`;

        const websocket = new WebSocket(wsUrl);

        websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWsEvent(message);
            } catch (err) {
                console.error('WebSocket parse error:', err);
            }
        };

        websocket.onclose = () => {
            // Reconnect after delay
            setTimeout(setupWebSocket, 5000);
        };

        setWs(websocket);
    };

    const handleWsEvent = useCallback((message: any) => {
        const { event, data } = message;

        switch (event) {
            case 'sync_started':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? { ...job, status: 'running', progress: 0 }
                        : job
                ));
                break;

            case 'sync_progress':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? {
                            ...job,
                            progress: data.percent,
                            current_file: data.filename,
                        }
                        : job
                ));
                break;

            case 'sync_completed':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? {
                            ...job,
                            status: 'scheduled',
                            progress: undefined,
                            current_file: undefined,
                            files_synced: data.files_synced,
                            last_run: data.completed_at,
                        }
                        : job
                ));
                break;

            case 'sync_error':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? {
                            ...job,
                            status: 'error',
                            progress: undefined,
                            error: data.error,
                        }
                        : job
                ));
                break;

            case 'sync_job_paused':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? { ...job, status: 'paused' }
                        : job
                ));
                break;

            case 'sync_job_resumed':
                setJobs(prev => prev.map(job =>
                    job.connector_id === data.connector_id
                        ? { ...job, status: 'scheduled' }
                        : job
                ));
                break;
        }
    }, []);

    const triggerSync = (connectorId: string) => {
        ws?.send(JSON.stringify({
            event: 'trigger_sync',
            data: { connector_id: connectorId },
        }));
    };

    const pauseSync = (connectorId: string) => {
        ws?.send(JSON.stringify({
            event: 'pause_sync',
            data: { connector_id: connectorId },
        }));
    };

    const resumeSync = (connectorId: string) => {
        ws?.send(JSON.stringify({
            event: 'resume_sync',
            data: { connector_id: connectorId },
        }));
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running': return 'var(--accent, #7c3aed)';
            case 'scheduled': return 'var(--success, #10b981)';
            case 'paused': return 'var(--warning, #f59e0b)';
            case 'error': return 'var(--error, #ef4444)';
            default: return 'var(--text-secondary)';
        }
    };

    const getConnectorIcon = (type: string) => {
        switch (type) {
            case 'sharepoint': return '📁';
            case 'google_drive': return '🔵';
            case 's3': return '☁️';
            case 'azure_blob': return '🔷';
            case 'database': return '🗄️';
            default: return '📂';
        }
    };

    const formatTime = (dateStr: string | null) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
    };

    if (loading) {
        return (
            <div className={`sync-dashboard loading ${className}`}>
                <div className="spinner"></div>
                <p>Yuklanmoqda...</p>
            </div>
        );
    }

    if (jobs.length === 0) {
        return (
            <div className={`sync-dashboard empty ${className}`}>
                <p>Jadval bo'yicha sinxronlash yo'q</p>
                <a href="/settings/connectors">Connector qo'shish →</a>
            </div>
        );
    }

    return (
        <div className={`sync-dashboard ${className}`}>
            <div className="dashboard-header">
                <h3>🔄 Sinxronlash holati</h3>
                <span className="job-count">{jobs.length} ta jadval</span>
            </div>

            <div className="jobs-list">
                {jobs.map(job => (
                    <div key={job.connector_id} className={`job-card ${job.status}`}>
                        <div className="job-header">
                            <span className="connector-icon">
                                {getConnectorIcon(job.connector_type)}
                            </span>
                            <div className="connector-info">
                                <span className="connector-name">{job.connector_name}</span>
                                <span className="connector-type">{job.connector_type}</span>
                            </div>
                            <div
                                className="status-indicator"
                                style={{ backgroundColor: getStatusColor(job.status) }}
                            >
                                {job.status === 'running' && '⟳'}
                                {job.status === 'scheduled' && '✓'}
                                {job.status === 'paused' && '⏸'}
                                {job.status === 'error' && '!'}
                            </div>
                        </div>

                        {/* Progress bar for running jobs */}
                        {job.status === 'running' && job.progress !== undefined && (
                            <div className="progress-section">
                                <div className="progress-bar">
                                    <div
                                        className="progress-fill"
                                        style={{ width: `${job.progress}%` }}
                                    />
                                </div>
                                <div className="progress-info">
                                    <span className="progress-percent">{job.progress}%</span>
                                    {job.current_file && (
                                        <span className="current-file">{job.current_file}</span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Error message */}
                        {job.status === 'error' && job.error && (
                            <div className="error-message">
                                ⚠️ {job.error}
                            </div>
                        )}

                        {/* Stats and actions */}
                        <div className="job-footer">
                            <div className="job-stats">
                                <span className="stat">
                                    📄 {job.files_synced} fayl
                                </span>
                                {job.last_run && (
                                    <span className="stat">
                                        🕐 {formatTime(job.last_run)}
                                    </span>
                                )}
                            </div>

                            <div className="job-actions">
                                {job.status === 'paused' ? (
                                    <button
                                        onClick={() => resumeSync(job.connector_id)}
                                        className="action-btn resume"
                                        title="Davom ettirish"
                                    >
                                        ▶
                                    </button>
                                ) : job.status !== 'running' && (
                                    <button
                                        onClick={() => pauseSync(job.connector_id)}
                                        className="action-btn pause"
                                        title="To'xtatish"
                                    >
                                        ⏸
                                    </button>
                                )}

                                {job.status !== 'running' && (
                                    <button
                                        onClick={() => triggerSync(job.connector_id)}
                                        className="action-btn sync"
                                        title="Hozir sinxronlash"
                                    >
                                        🔄
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default SyncDashboard;
