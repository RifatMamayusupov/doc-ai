/**
 * Sidebar Component - ChatGPT-style chat history
 */

import { useState } from 'react';
import { Plus, MessageSquare, Trash2, ChevronLeft, ChevronRight, Edit2, Shield, ShieldAlert, Wand2 } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';
import { API_URL } from '../config';

export function Sidebar() {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState('');

    const {
        sessions: rawSessions,
        activeSessionId,
        createSession,
        setActiveSession,
        deleteSession,
        updateSessionTitle,
        autoApprove,
        setAutoApprove,
    } = useMonisterStore();

    const sessions = rawSessions ?? [];

    const handleNewChat = () => {
        createSession();
    };

    const handleSelectSession = (sessionId: string) => {
        setActiveSession(sessionId);
    };

    const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
        e.stopPropagation();
        deleteSession(sessionId);
    };

    const handleStartEdit = (e: React.MouseEvent, sessionId: string, currentTitle: string) => {
        e.stopPropagation();
        setEditingId(sessionId);
        setEditTitle(currentTitle);
    };

    const handleSaveEdit = (sessionId: string) => {
        if (editTitle.trim()) {
            updateSessionTitle(sessionId, editTitle.trim());
        }
        setEditingId(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
        if (e.key === 'Enter') {
            handleSaveEdit(sessionId);
        } else if (e.key === 'Escape') {
            setEditingId(null);
        }
    };

    if (isCollapsed) {
        return (
            <div className="sidebar collapsed">
                <button
                    className="sidebar-toggle"
                    onClick={() => setIsCollapsed(false)}
                    title="Expand sidebar"
                >
                    <ChevronRight size={20} />
                </button>
                <button
                    className="new-chat-icon"
                    onClick={handleNewChat}
                    title="New chat"
                >
                    <Plus size={20} />
                </button>
            </div>
        );
    }

    return (
        <div className="sidebar">
            {/* Header */}
            <div className="sidebar-header">
                <button className="new-chat-btn" onClick={handleNewChat}>
                    <Plus size={18} />
                    <span>Yangi chat</span>
                </button>
                <button
                    className="sidebar-toggle"
                    onClick={() => setIsCollapsed(true)}
                    title="Collapse sidebar"
                >
                    <ChevronLeft size={20} />
                </button>
            </div>

            {/* Chat History */}
            <div className="chat-history">
                {sessions.length === 0 ? (
                    <div className="empty-history">
                        <MessageSquare size={32} />
                        <p>Hech qanday chat yo'q</p>
                        <p className="hint">Yangi chat boshlang</p>
                    </div>
                ) : (
                    sessions.map((session) => (
                        <div
                            key={session.id}
                            className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
                            onClick={() => handleSelectSession(session.id)}
                        >
                            <MessageSquare size={16} />

                            {editingId === session.id ? (
                                <input
                                    className="edit-title-input"
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onBlur={() => handleSaveEdit(session.id)}
                                    onKeyDown={(e) => handleKeyDown(e, session.id)}
                                    autoFocus
                                    onClick={(e) => e.stopPropagation()}
                                />
                            ) : (
                                <span className="session-title">{session.title}</span>
                            )}

                            <div className="session-actions">
                                <button
                                    className="action-btn"
                                    onClick={async (e) => {
                                        e.stopPropagation();
                                        try {
                                            const res = await fetch(`${API_URL}/api/sessions/${session.id}/title/generate`, { method: 'POST' });
                                            const data = await res.json();
                                            if (data.title) updateSessionTitle(session.id, data.title);
                                        } catch (err) { console.error(err); }
                                    }}
                                    title="AI Title"
                                >
                                    <Wand2 size={14} />
                                </button>
                                <button
                                    className="action-btn"
                                    onClick={(e) => handleStartEdit(e, session.id, session.title)}
                                    title="Rename"
                                >
                                    <Edit2 size={14} />
                                </button>
                                <button
                                    className="action-btn delete"
                                    onClick={(e) => handleDeleteSession(e, session.id)}
                                    title="Delete"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Footer */}
            <div className="sidebar-footer">
                <div className="hitl-toggle">
                    <button
                        className={`toggle-btn ${autoApprove ? 'auto' : 'manual'}`}
                        onClick={() => setAutoApprove(!autoApprove)}
                        title={autoApprove ? "Auto-approve mode: ON" : "Human-in-the-Loop mode: ON"}
                    >
                        {autoApprove ? <Shield size={16} /> : <ShieldAlert size={16} />}
                        <span className="mode-label">
                            {autoApprove ? 'Auto Mode' : 'HITL Mode'}
                        </span>
                    </button>
                </div>
                <div className="app-info">
                    <span className="version">Monister AI v2.0</span>
                </div>
            </div>
        </div>
    );
}
