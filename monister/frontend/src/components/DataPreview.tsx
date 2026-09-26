/**
 * Data Preview Component - Right zone
 * Shows file uploads and data previews with real-time updates
 */

import { useState, useCallback } from 'react';
import { Upload, FileText, X, Eye, FolderOpen } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';
import { useWebSocket } from '../hooks/useWebSocket';

export function DataPreview() {
    const [activeTab, setActiveTab] = useState<'preview' | 'templates'>('preview');
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);

    const { uploadedFiles, templates, previewData, addUploadedFile, removeUploadedFile } = useMonisterStore();
    const { sendFileUpload } = useWebSocket();

    // Handle file upload
    const handleUpload = useCallback(async (files: FileList | null) => {
        if (!files || files.length === 0) return;

        setIsUploading(true);

        for (const file of Array.from(files)) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const token = localStorage.getItem('token');
                const response = await fetch('http://localhost:8000/api/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();

                    // Add to local state
                    addUploadedFile({
                        id: data.file_id,
                        name: data.filename,
                        path: data.path,
                        size: data.size,
                        type: data.type || 'application/octet-stream',
                        status: 'uploaded',
                    });

                    // Notify backend via WebSocket (so agent knows about the file)
                    sendFileUpload({
                        file_id: data.file_id,
                        filename: data.filename,
                        path: data.path,
                        size: data.size,
                        file_type: data.type,
                    });
                }
            } catch (error) {
                console.error('Upload failed:', error);
            }
        }

        setIsUploading(false);
    }, [addUploadedFile, sendFileUpload]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        handleUpload(e.dataTransfer.files);
    }, [handleUpload]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setIsDragging(false);
    }, []);

    // Format file size
    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <div className="data-preview">
            {/* Tab Header */}
            <div className="preview-tabs">
                <button
                    className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('preview')}
                >
                    <Eye size={16} />
                    Preview
                </button>
                <button
                    className={`tab ${activeTab === 'templates' ? 'active' : ''}`}
                    onClick={() => setActiveTab('templates')}
                >
                    <FolderOpen size={16} />
                    Templates
                </button>
            </div>

            {/* Content */}
            <div className="preview-content">
                {activeTab === 'preview' && (
                    <>
                        {/* Upload Zone */}
                        <div
                            className={`upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onClick={() => document.getElementById('file-input')?.click()}
                        >
                            <input
                                id="file-input"
                                type="file"
                                multiple
                                hidden
                                onChange={(e) => handleUpload(e.target.files)}
                            />
                            <Upload size={24} />
                            <span>{isUploading ? 'Uploading...' : 'Drop files or click to upload'}</span>
                            <small>PDF, Excel, Images, Word</small>
                        </div>

                        {/* Uploaded Files */}
                        {uploadedFiles.length > 0 && (
                            <div className="uploaded-files">
                                <h4>📁 Uploaded Files</h4>
                                {uploadedFiles.map((file) => (
                                    <div key={file.id} className="file-item">
                                        <FileText size={16} />
                                        <div className="file-info">
                                            <span className="file-name">{file.name}</span>
                                            <span className="file-size">{formatSize(file.size)}</span>
                                        </div>
                                        <button
                                            className="remove-btn"
                                            onClick={() => removeUploadedFile(file.id)}
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Data Preview from Agent */}
                        <div className="data-output">
                            <h4>📊 Ma'lumotlar yuklanmagan</h4>
                            {previewData ? (
                                <div className="preview-box">
                                    <div className="preview-header">
                                        <span>🔧 {String(previewData.tool || 'Tool')}</span>
                                        <small>{String(previewData.timestamp || '')}</small>
                                    </div>
                                    <pre className="preview-content-text">
                                        {String(previewData.content || '').slice(0, 500)}
                                        {String(previewData.content || '').length > 500 && '...'}
                                    </pre>
                                </div>
                            ) : (
                                <p className="no-data">
                                    Agent ma'lumotlarni qayta ishlaganda bu yerda ko'rsatiladi
                                </p>
                            )}
                        </div>
                    </>
                )}

                {activeTab === 'templates' && (
                    <div className="templates-list">
                        {templates.length === 0 ? (
                            <p className="no-templates">No templates available</p>
                        ) : (
                            <>
                                {/* Group by category */}
                                {Object.entries(
                                    templates.reduce((acc, t) => {
                                        if (!acc[t.category]) acc[t.category] = [];
                                        acc[t.category].push(t);
                                        return acc;
                                    }, {} as Record<string, typeof templates>)
                                ).map(([category, categoryTemplates]) => (
                                    <div key={category} className="template-category">
                                        <h4>{category}</h4>
                                        {categoryTemplates.map((template) => (
                                            <div key={template.id} className="template-item">
                                                <FileText size={16} />
                                                <span>{template.name}</span>
                                            </div>
                                        ))}
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
