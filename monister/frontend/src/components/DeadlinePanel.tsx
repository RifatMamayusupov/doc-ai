/**
 * DeadlinePanel - Deadline alerts and tracking widget
 * Shows upcoming/overdue deadlines with priority indicators
 */

import { useState, useEffect } from 'react';
import { useMonisterStore } from '../stores/monisterStore';


const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function DeadlinePanel() {
    const { deadlines, setDeadlines, deadlineAlerts, setDeadlineAlerts } = useMonisterStore();

    const [expanded, setExpanded] = useState(true);

    // Fetch deadlines on mount and periodically
    useEffect(() => {
        const fetchDeadlines = async () => {
            try {
                const [dlRes, alertRes] = await Promise.all([
                    fetch(`${API_BASE}/api/deadlines/upcoming?days=30`),
                    fetch(`${API_BASE}/api/deadlines/alerts`),
                ]);
                if (dlRes.ok) {
                    const data = await dlRes.json();
                    setDeadlines(data.deadlines || []);
                }
                if (alertRes.ok) {
                    const data = await alertRes.json();
                    setDeadlineAlerts(data.alerts || []);
                }
            } catch (err) {
                console.error('Deadline fetch error:', err);
            }
        };

        fetchDeadlines();
        const interval = setInterval(fetchDeadlines, 60000); // Refresh every minute
        return () => clearInterval(interval);
    }, []);

    const completeDeadline = async (id: string) => {
        try {
            const res = await fetch(`${API_BASE}/api/deadlines/${id}/complete`, { method: 'PUT' });
            if (res.ok) {
                setDeadlines(deadlines.filter(d => d.id !== id));
            }
        } catch (err) {
            console.error('Complete deadline error:', err);
        }
    };

    const priorityColors: Record<string, string> = {
        critical: '#ff4444',
        high: '#ff8800',
        medium: '#ffcc00',
        low: '#44aaff',
    };

    const statusIcons: Record<string, string> = {
        overdue: '🔴',
        upcoming: '🟡',
        active: '🟢',
    };

    if (deadlines.length === 0 && deadlineAlerts.length === 0) {
        return null; // Don't render if no deadlines
    }

    return (
        <div className="deadline-panel">
            <div
                className="deadline-panel-header"
                onClick={() => setExpanded(!expanded)}
            >
                <span className="deadline-panel-title">
                    ⏰ Muddatlar
                    {deadlineAlerts.length > 0 && (
                        <span className="deadline-alert-badge">{deadlineAlerts.length}</span>
                    )}
                </span>
                <span className={`expand-arrow ${expanded ? 'expanded' : ''}`}>▼</span>
            </div>

            {expanded && (
                <div className="deadline-panel-content">
                    {/* Alerts first */}
                    {deadlineAlerts.map((alert, i) => (
                        <div
                            key={i}
                            className={`deadline-alert deadline-alert-${alert.level}`}
                            style={{ borderLeftColor: priorityColors[alert.level] || '#666' }}
                        >
                            <span className="alert-message">{alert.message}</span>
                        </div>
                    ))}

                    {/* Deadline list */}
                    {deadlines.map((dl) => (
                        <div
                            key={dl.id}
                            className={`deadline-item deadline-${dl.status}`}
                        >
                            <div className="deadline-item-header">
                                <span className="deadline-status-icon">
                                    {statusIcons[dl.status] || '📋'}
                                </span>
                                <span className="deadline-title">{dl.title_uz || dl.title}</span>
                                <span
                                    className="deadline-priority"
                                    style={{ color: priorityColors[dl.priority] }}
                                >
                                    {dl.priority}
                                </span>
                            </div>
                            <div className="deadline-item-meta">
                                <span className="deadline-days">
                                    {dl.is_overdue
                                        ? `${Math.abs(dl.days_remaining)} kun o'tgan`
                                        : `${dl.days_remaining} kun qoldi`
                                    }
                                </span>
                                {dl.tags.length > 0 && (
                                    <div className="deadline-tags">
                                        {dl.tags.map(t => (
                                            <span key={t} className="deadline-tag">{t}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <button
                                className="deadline-complete-btn"
                                onClick={() => completeDeadline(dl.id)}
                                title="Bajarildi"
                            >
                                ✓
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
