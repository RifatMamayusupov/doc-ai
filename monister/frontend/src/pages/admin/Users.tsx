/**
 * Admin Users - User management
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import {
    Users, ArrowLeft, Search, Trash2, Shield,
    ShieldOff, Folder, BarChart3, Settings
} from 'lucide-react';

interface UserData {
    id: number;
    username: string;
    email: string;
    is_admin: boolean;
    is_active: boolean;
    created_at: string;
    files_count: number;
    storage_used: number;
    storage_formatted: string;
}

interface AdminUsersProps {
    onNavigate: (page: 'dashboard' | 'users' | 'files' | 'settings' | 'main') => void;
}

export function AdminUsers({ onNavigate }: AdminUsersProps) {
    const { token } = useAuth();
    const [users, setUsers] = useState<UserData[]>([]);
    const [total, setTotal] = useState(0);
    const [search, setSearch] = useState('');
    const [, setIsLoading] = useState(true);

    useEffect(() => {
        fetchUsers();
    }, [search]);

    const fetchUsers = async () => {
        try {
            const params = new URLSearchParams();
            if (search) params.append('search', search);

            const response = await fetch(`http://localhost:8000/api/admin/users?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });

            const data = await response.json();
            setUsers(data.users);
            setTotal(data.total);
        } catch (err) {
            console.error('Error fetching users:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleToggleAdmin = async (userId: number) => {
        try {
            await fetch(`http://localhost:8000/api/admin/users/${userId}/toggle-admin`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            fetchUsers();
        } catch (err) {
            alert('Xatolik yuz berdi');
        }
    };

    const handleDeleteUser = async (userId: number, username: string) => {
        if (!confirm(`"${username}" foydalanuvchisini o'chirmoqchimisiz? Barcha fayllari ham o'chiriladi!`)) {
            return;
        }

        try {
            await fetch(`http://localhost:8000/api/admin/users/${userId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            fetchUsers();
        } catch (err) {
            alert('Xatolik yuz berdi');
        }
    };

    return (
        <div className="admin-container">
            <header className="admin-header">
                <div className="admin-header-left">
                    <button className="admin-back-btn" onClick={() => onNavigate('dashboard')}>
                        <ArrowLeft size={20} />
                    </button>
                    <h1>👥 Foydalanuvchilar</h1>
                    <span className="admin-count">{total} ta</span>
                </div>
            </header>

            <nav className="admin-nav">
                <button className="admin-nav-btn" onClick={() => onNavigate('dashboard')}>
                    <BarChart3 size={18} />
                    Dashboard
                </button>
                <button className="admin-nav-btn active">
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

            <div className="admin-toolbar">
                <div className="admin-search">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Qidirish..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            <div className="admin-table-container">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>Foydalanuvchi</th>
                            <th>Email</th>
                            <th>Rol</th>
                            <th>Fayllar</th>
                            <th>Hajm</th>
                            <th>Sana</th>
                            <th>Amallar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map((u) => (
                            <tr key={u.id}>
                                <td>
                                    <span className="user-avatar">
                                        {u.username.charAt(0).toUpperCase()}
                                    </span>
                                    {u.username}
                                </td>
                                <td>{u.email}</td>
                                <td>
                                    <span className={`role-badge ${u.is_admin ? 'admin' : 'user'}`}>
                                        {u.is_admin ? '👑 Admin' : '👤 User'}
                                    </span>
                                </td>
                                <td>{u.files_count}</td>
                                <td>{u.storage_formatted}</td>
                                <td>{new Date(u.created_at).toLocaleDateString('uz')}</td>
                                <td>
                                    <div className="action-buttons">
                                        <button
                                            className="action-btn toggle"
                                            onClick={() => handleToggleAdmin(u.id)}
                                            title={u.is_admin ? 'Admin olib tashlash' : 'Admin qilish'}
                                        >
                                            {u.is_admin ? <ShieldOff size={16} /> : <Shield size={16} />}
                                        </button>
                                        {u.username !== 'admin' && u.username !== 'system' && (
                                            <button
                                                className="action-btn delete"
                                                onClick={() => handleDeleteUser(u.id, u.username)}
                                                title="O'chirish"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
