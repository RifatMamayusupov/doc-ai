/**
 * Admin Files - File management
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import {
    ArrowLeft, Search, Trash2, Download,
    Folder, Users, BarChart3, Filter, Settings
} from 'lucide-react';

interface FileData {
    id: number;
    user_id: number;
    username: string;
    filename: string;
    original_name: string;
    file_type: string;
    mime_type: string;
    path: string;
    size: number;
    created_at: string;
}

interface AdminFilesProps {
    onNavigate: (page: 'dashboard' | 'users' | 'files' | 'settings' | 'main') => void;
}

const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

export function AdminFiles({ onNavigate }: AdminFilesProps) {
    const { token } = useAuth();
    const [files, setFiles] = useState<FileData[]>([]);
    const [total, setTotal] = useState(0);
    const [search, setSearch] = useState('');
    const [filterType, setFilterType] = useState('');
    const [, setIsLoading] = useState(true);

    useEffect(() => {
        fetchFiles();
    }, [search, filterType]);

    const fetchFiles = async () => {
        try {
            const params = new URLSearchParams();
            if (search) params.append('search', search);
            if (filterType) params.append('file_type', filterType);

            const response = await fetch(`http://localhost:8000/api/admin/files?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });

            const data = await response.json();
            setFiles(data.files);
            setTotal(data.total);
        } catch (err) {
            console.error('Error fetching files:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleDeleteFile = async (fileId: number, fileName: string) => {
        if (!confirm(`"${fileName}" faylini o'chirmoqchimisiz?`)) {
            return;
        }

        try {
            await fetch(`http://localhost:8000/api/admin/files/${fileId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            fetchFiles();
        } catch (err) {
            alert('Xatolik yuz berdi');
        }
    };

    const getFileIcon = (type: string) => {
        switch (type) {
            case 'images': return '🖼️';
            case 'documents': return '📄';
            case 'spreadsheets': return '📊';
            case 'code': return '💻';
            default: return '📁';
        }
    };

    return (
        <div className="admin-container">
            <header className="admin-header">
                <div className="admin-header-left">
                    <button className="admin-back-btn" onClick={() => onNavigate('dashboard')}>
                        <ArrowLeft size={20} />
                    </button>
                    <h1>📁 Fayllar</h1>
                    <span className="admin-count">{total} ta</span>
                </div>
            </header>

            <nav className="admin-nav">
                <button className="admin-nav-btn" onClick={() => onNavigate('dashboard')}>
                    <BarChart3 size={18} />
                    Dashboard
                </button>
                <button className="admin-nav-btn" onClick={() => onNavigate('users')}>
                    <Users size={18} />
                    Foydalanuvchilar
                </button>
                <button className="admin-nav-btn active">
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
                        placeholder="Fayl qidirish..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <div className="admin-filter">
                    <Filter size={18} />
                    <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                        <option value="">Barcha turlar</option>
                        <option value="images">🖼️ Rasmlar</option>
                        <option value="documents">📄 Hujjatlar</option>
                        <option value="spreadsheets">📊 Jadvallar</option>
                        <option value="code">💻 Kod</option>
                        <option value="other">📁 Boshqa</option>
                    </select>
                </div>
            </div>

            <div className="admin-table-container">
                <table className="admin-table">
                    <thead>
                        <tr>
                            <th>Fayl</th>
                            <th>Foydalanuvchi</th>
                            <th>Tur</th>
                            <th>Hajm</th>
                            <th>Sana</th>
                            <th>Amallar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {files.map((f) => (
                            <tr key={f.id}>
                                <td>
                                    <span className="file-icon">{getFileIcon(f.file_type)}</span>
                                    <span className="file-name" title={f.original_name}>
                                        {f.original_name.length > 30
                                            ? f.original_name.slice(0, 30) + '...'
                                            : f.original_name}
                                    </span>
                                </td>
                                <td>
                                    <span className="user-badge">👤 {f.username}</span>
                                </td>
                                <td>
                                    <span className="type-badge">{f.file_type}</span>
                                </td>
                                <td>{formatBytes(f.size)}</td>
                                <td>{new Date(f.created_at).toLocaleDateString('uz')}</td>
                                <td>
                                    <div className="action-buttons">
                                        <a
                                            href={`http://localhost:8000${f.path.includes('/data/') ? f.path.replace(/.*\/data/, '/data') : '/uploads/' + f.filename}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="action-btn download"
                                            title="Yuklab olish"
                                        >
                                            <Download size={16} />
                                        </a>
                                        <button
                                            className="action-btn delete"
                                            onClick={() => handleDeleteFile(f.id, f.original_name)}
                                            title="O'chirish"
                                        >
                                            <Trash2 size={16} />
                                        </button>
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
