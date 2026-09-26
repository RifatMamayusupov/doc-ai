/**
 * Admin Dashboard - Statistics and overview
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import {
    Users, FileText, Database,
    ArrowLeft, Settings, LogOut,
    Folder, BarChart3
} from 'lucide-react';

interface Stats {
    users: {
        total: number;
        active: number;
        admins: number;
        new_this_week: number;
    };
    files: {
        total: number;
        storage_bytes: number;
        storage_formatted: string;
        new_this_week: number;
        by_type: Array<{ type: string; count: number; size_formatted: string }>;
    };
    recent_files: Array<any>;
    recent_users: Array<any>;
}

interface DashboardProps {
    onNavigate: (page: 'dashboard' | 'users' | 'files' | 'settings' | 'main') => void;
}

export function AdminDashboard({ onNavigate }: DashboardProps) {
    const { user, logout, token } = useAuth();
    const [stats, setStats] = useState<Stats | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetchStats();
    }, []);

    const fetchStats = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/admin/stats', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) throw new Error('Failed to fetch stats');

            const data = await response.json();
            setStats(data);
        } catch (err) {
            console.error('Error loading stats:', err);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) {
        return (
            <div className="admin-loading">
                <div className="spinner"></div>
                <p>Yuklanmoqda...</p>
            </div>
        );
    }

    return (
        <div className="admin-container">
            {/* Header */}
            <header className="admin-header">
                <div className="admin-header-left">
                    <button className="admin-back-btn" onClick={() => onNavigate('main')}>
                        <ArrowLeft size={20} />
                    </button>
                    <h1>🎛️ Admin Panel</h1>
                </div>
                <div className="admin-header-right">
                    <span className="admin-user">👤 {user?.username}</span>
                    <button className="admin-logout-btn" onClick={logout}>
                        <LogOut size={18} />
                    </button>
                </div>
            </header>

            {/* Navigation */}
            <nav className="admin-nav">
                <button className="admin-nav-btn active">
                    <BarChart3 size={18} />
                    Dashboard
                </button>
                <button className="admin-nav-btn" onClick={() => onNavigate('users')}>
                    <Users size={18} />
                    Foydalanuvchilar
                </button>
                <button className="admin-nav-btn" onClick={() => onNavigate('files')}>
                    <Folder size={18} />
                    Fayllar
                </button>
                <button className="admin-nav-btn" onClick={() => onNavigate('settings')}>
                    <Settings size={18} />
                    Sozlamalar
                </button>
            </nav>

            {/* Stats Grid */}
            <div className="admin-stats-grid">
                <div className="stat-card users">
                    <div className="stat-icon"><Users size={24} /></div>
                    <div className="stat-info">
                        <h3>{stats?.users.total || 0}</h3>
                        <p>Jami foydalanuvchilar</p>
                        <span className="stat-badge">+{stats?.users.new_this_week || 0} bu hafta</span>
                    </div>
                </div>

                <div className="stat-card files">
                    <div className="stat-icon"><FileText size={24} /></div>
                    <div className="stat-info">
                        <h3>{stats?.files.total || 0}</h3>
                        <p>Jami fayllar</p>
                        <span className="stat-badge">+{stats?.files.new_this_week || 0} bu hafta</span>
                    </div>
                </div>

                <div className="stat-card storage">
                    <div className="stat-icon"><Database size={24} /></div>
                    <div className="stat-info">
                        <h3>{stats?.files.storage_formatted || '0 B'}</h3>
                        <p>Umumiy hajm</p>
                    </div>
                </div>

                <div className="stat-card admins">
                    <div className="stat-icon"><Settings size={24} /></div>
                    <div className="stat-info">
                        <h3>{stats?.users.admins || 0}</h3>
                        <p>Adminlar</p>
                    </div>
                </div>
            </div>

            {/* File Types */}
            <div className="admin-section">
                <h2>📊 Fayl turlari</h2>
                <div className="file-types-grid">
                    {stats?.files.by_type.map((item) => (
                        <div key={item.type} className="file-type-card">
                            <span className="file-type-icon">
                                {item.type === 'images' && '🖼️'}
                                {item.type === 'documents' && '📄'}
                                {item.type === 'spreadsheets' && '📊'}
                                {item.type === 'code' && '💻'}
                                {item.type === 'other' && '📁'}
                            </span>
                            <div className="file-type-info">
                                <h4>{item.type}</h4>
                                <p>{item.count} ta fayl • {item.size_formatted}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Recent Activity */}
            <div className="admin-grid-2">
                <div className="admin-section">
                    <h2>👥 Yangi foydalanuvchilar</h2>
                    <div className="recent-list">
                        {stats?.recent_users.map((u) => (
                            <div key={u.id} className="recent-item">
                                <span className="recent-icon">👤</span>
                                <div className="recent-info">
                                    <strong>{u.username}</strong>
                                    <span>{u.email}</span>
                                </div>
                                <span className="recent-time">
                                    {new Date(u.created_at).toLocaleDateString('uz')}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="admin-section">
                    <h2>📁 Oxirgi fayllar</h2>
                    <div className="recent-list">
                        {stats?.recent_files.slice(0, 5).map((f) => (
                            <div key={f.id} className="recent-item">
                                <span className="recent-icon">
                                    {f.file_type === 'images' && '🖼️'}
                                    {f.file_type === 'documents' && '📄'}
                                    {f.file_type === 'spreadsheets' && '📊'}
                                    {f.file_type === 'code' && '💻'}
                                    {f.file_type === 'other' && '📁'}
                                </span>
                                <div className="recent-info">
                                    <strong>{f.original_name}</strong>
                                    <span>{f.username}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
