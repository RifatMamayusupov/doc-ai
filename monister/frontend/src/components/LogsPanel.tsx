/**
 * Logs Panel Component - Bottom zone
 * Real-time streaming logs and system status
 */

import { useEffect, useRef } from 'react';
import { Terminal, Trash2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';

export function LogsPanel() {
    const logsEndRef = useRef<HTMLDivElement>(null);
    const { logs, clearLogs, isConnected } = useMonisterStore();

    // Auto-scroll to bottom
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const getIcon = (level: string) => {
        switch (level) {
            case 'error':
                return <AlertCircle size={14} className="log-icon error" />;
            case 'warn':
                return <AlertTriangle size={14} className="log-icon warn" />;
            default:
                return <Info size={14} className="log-icon info" />;
        }
    };

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        });
    };

    return (
        <div className="logs-panel">
            {/* Header */}
            <div className="logs-header">
                <div className="logs-title">
                    <Terminal size={16} />
                    <span>System Logs</span>
                    <span className={`connection-dot ${isConnected ? 'connected' : 'disconnected'}`} />
                </div>

                <div className="logs-actions">
                    <span className="log-count">{logs.length} entries</span>
                    <button
                        className="clear-logs-btn"
                        onClick={clearLogs}
                        title="Clear logs"
                    >
                        <Trash2 size={14} />
                    </button>
                </div>
            </div>

            {/* Log entries */}
            <div className="logs-container">
                {logs.length === 0 ? (
                    <div className="logs-empty">
                        <Terminal size={24} />
                        <span>Logs will appear here...</span>
                    </div>
                ) : (
                    logs.map((log) => (
                        <div key={log.id} className={`log-entry ${log.level}`}>
                            <span className="log-time">{formatTime(log.timestamp)}</span>
                            {getIcon(log.level)}
                            <span className="log-message">{log.message}</span>
                        </div>
                    ))
                )}
                <div ref={logsEndRef} />
            </div>
        </div>
    );
}
