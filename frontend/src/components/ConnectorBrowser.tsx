/**
 * Connector Browser Component
 * 
 * Modal for browsing files from connected data sources
 */

import React, { useState, useEffect, useCallback } from 'react';
import './ConnectorBrowser.css';

interface ConnectorInfo {
    id: string;
    name: string;
    connector_type: string;
    is_active: boolean;
    last_sync_at: string | null;
    files_synced: number;
}

interface FileItem {
    id: string;
    name: string;
    path: string;
    size: number;
    is_folder: boolean;
    mime_type: string | null;
    modified_at: string | null;
}

interface ConnectorBrowserProps {
    isOpen: boolean;
    onClose: () => void;
    onSelectFiles: (files: FileItem[]) => void;
    allowMultiple?: boolean;
    fileTypes?: string[];
}

export function ConnectorBrowser({
    isOpen,
    onClose,
    onSelectFiles,
    allowMultiple = true,
    fileTypes,
}: ConnectorBrowserProps) {
    const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
    const [selectedConnector, setSelectedConnector] = useState<string | null>(null);
    const [currentPath, setCurrentPath] = useState('/');
    const [files, setFiles] = useState<FileItem[]>([]);
    const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [breadcrumbs, setBreadcrumbs] = useState<string[]>(['/']);

    // Fetch connectors
    useEffect(() => {
        if (isOpen) {
            fetchConnectors();
        }
    }, [isOpen]);

    // Fetch files when connector or path changes
    useEffect(() => {
        if (selectedConnector) {
            fetchFiles(selectedConnector, currentPath);
        }
    }, [selectedConnector, currentPath]);

    const fetchConnectors = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch('/api/connectors', {
                headers: { 'Authorization': `Bearer ${token}` },
            });

            if (response.ok) {
                const data = await response.json();
                setConnectors(data);

                // Auto-select first active connector
                const active = data.find((c: ConnectorInfo) => c.is_active);
                if (active) {
                    setSelectedConnector(active.id);
                }
            }
        } catch (err) {
            setError('Connectorlarni yuklashda xatolik');
        }
    };

    const fetchFiles = async (connectorId: string, path: string) => {
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(
                `/api/connectors/${connectorId}/files?path=${encodeURIComponent(path)}`,
                { headers: { 'Authorization': `Bearer ${token}` } }
            );

            if (response.ok) {
                const data = await response.json();
                let fileList = data.files || [];

                // Filter by file types if specified
                if (fileTypes && fileTypes.length > 0) {
                    fileList = fileList.filter((f: FileItem) => {
                        if (f.is_folder) return true;
                        const ext = f.name.split('.').pop()?.toLowerCase();
                        return ext && fileTypes.includes(`.${ext}`);
                    });
                }

                setFiles(fileList);
            } else {
                setError('Fayllarni yuklashda xatolik');
            }
        } catch (err) {
            setError('Serverga ulanishda xatolik');
        } finally {
            setLoading(false);
        }
    };

    // Navigate to folder
    const navigateToFolder = (folder: FileItem) => {
        const newPath = folder.path;
        setCurrentPath(newPath);
        setBreadcrumbs(prev => [...prev, newPath]);
        setSelectedFiles(new Set());
    };

    // Navigate to breadcrumb
    const navigateToBreadcrumb = (index: number) => {
        const targetPath = breadcrumbs[index];
        setCurrentPath(targetPath);
        setBreadcrumbs(prev => prev.slice(0, index + 1));
        setSelectedFiles(new Set());
    };

    // Toggle file selection
    const toggleFileSelection = (file: FileItem) => {
        if (file.is_folder) {
            navigateToFolder(file);
            return;
        }

        setSelectedFiles(prev => {
            const newSet = new Set(prev);

            if (newSet.has(file.id)) {
                newSet.delete(file.id);
            } else {
                if (!allowMultiple) {
                    newSet.clear();
                }
                newSet.add(file.id);
            }

            return newSet;
        });
    };

    // Handle confirm
    const handleConfirm = () => {
        const selected = files.filter(f => selectedFiles.has(f.id));
        onSelectFiles(selected);
        onClose();
    };

    // Get connector icon
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

    // Format file size
    const formatSize = (bytes: number) => {
        if (bytes === 0) return '-';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    // Format date
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        return new Date(dateStr).toLocaleDateString('uz-UZ');
    };

    if (!isOpen) return null;

    return (
        <div className="connector-browser-overlay" onClick={onClose}>
            <div className="connector-browser" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="browser-header">
                    <h3>Ma'lumot manbalaridan tanlang</h3>
                    <button className="close-btn" onClick={onClose}>✕</button>
                </div>

                {/* Main content */}
                <div className="browser-content">
                    {/* Connector sidebar */}
                    <div className="connector-sidebar">
                        <h4>Ma'lumot manbalari</h4>
                        <div className="connector-list">
                            {connectors.map(connector => (
                                <button
                                    key={connector.id}
                                    className={`connector-item ${selectedConnector === connector.id ? 'active' : ''}`}
                                    onClick={() => {
                                        setSelectedConnector(connector.id);
                                        setCurrentPath('/');
                                        setBreadcrumbs(['/']);
                                    }}
                                >
                                    <span className="connector-icon">
                                        {getConnectorIcon(connector.connector_type)}
                                    </span>
                                    <div className="connector-info">
                                        <span className="connector-name">{connector.name}</span>
                                        <span className="connector-type">{connector.connector_type}</span>
                                    </div>
                                    {connector.is_active && (
                                        <span className="active-indicator" title="Aktiv">●</span>
                                    )}
                                </button>
                            ))}

                            {connectors.length === 0 && (
                                <div className="no-connectors">
                                    <p>Hech qanday connector ulanmagan</p>
                                    <a href="/settings/connectors">Yangi qo'shish →</a>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* File browser */}
                    <div className="file-browser">
                        {/* Breadcrumbs */}
                        <div className="breadcrumbs">
                            {breadcrumbs.map((path, index) => (
                                <React.Fragment key={path}>
                                    {index > 0 && <span className="separator">/</span>}
                                    <button
                                        className="breadcrumb-item"
                                        onClick={() => navigateToBreadcrumb(index)}
                                    >
                                        {index === 0 ? '🏠' : path.split('/').pop() || path}
                                    </button>
                                </React.Fragment>
                            ))}
                        </div>

                        {/* File list */}
                        <div className="file-list">
                            {loading ? (
                                <div className="loading-state">
                                    <div className="spinner"></div>
                                    <p>Yuklanmoqda...</p>
                                </div>
                            ) : error ? (
                                <div className="error-state">
                                    <p>⚠️ {error}</p>
                                </div>
                            ) : files.length === 0 ? (
                                <div className="empty-state">
                                    <p>Bu papka bo'sh</p>
                                </div>
                            ) : (
                                <table className="files-table">
                                    <thead>
                                        <tr>
                                            <th></th>
                                            <th>Nom</th>
                                            <th>Hajm</th>
                                            <th>O'zgartirilgan</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {files.map(file => (
                                            <tr
                                                key={file.id}
                                                className={`file-row ${file.is_folder ? 'folder' : ''} ${selectedFiles.has(file.id) ? 'selected' : ''}`}
                                                onClick={() => toggleFileSelection(file)}
                                            >
                                                <td className="checkbox-cell">
                                                    {!file.is_folder && (
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedFiles.has(file.id)}
                                                            onChange={() => { }}
                                                        />
                                                    )}
                                                </td>
                                                <td className="name-cell">
                                                    <span className="file-icon">
                                                        {file.is_folder ? '📁' : '📄'}
                                                    </span>
                                                    <span className="file-name">{file.name}</span>
                                                </td>
                                                <td className="size-cell">{formatSize(file.size)}</td>
                                                <td className="date-cell">{formatDate(file.modified_at)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="browser-footer">
                    <div className="selection-info">
                        {selectedFiles.size > 0 && (
                            <span>{selectedFiles.size} ta fayl tanlandi</span>
                        )}
                    </div>
                    <div className="action-buttons">
                        <button className="cancel-btn" onClick={onClose}>
                            Bekor qilish
                        </button>
                        <button
                            className="confirm-btn"
                            disabled={selectedFiles.size === 0}
                            onClick={handleConfirm}
                        >
                            Tanlash
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ConnectorBrowser;
