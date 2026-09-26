/**
 * File Upload Component - Drag & Drop + Click to upload
 * Supports all file types including video
 */

import { useState, useRef, useCallback } from 'react';
import { Upload, File, X, FileText, Image, Video, FileSpreadsheet, Loader2 } from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';

interface FileUploadProps {
    onFilesUploaded?: (files: File[]) => void;
}

const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) return <Image size={18} />;
    if (type.startsWith('video/')) return <Video size={18} />;
    if (type.includes('spreadsheet') || type.includes('excel') || type.includes('csv')) return <FileSpreadsheet size={18} />;
    if (type.includes('pdf') || type.includes('document') || type.includes('word')) return <FileText size={18} />;
    return <File size={18} />;
};

const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export function FileUpload({ onFilesUploaded }: FileUploadProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { uploadedFiles, addUploadedFile, removeUploadedFile, updateUploadedFile } = useMonisterStore();

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const uploadFile = async (file: File) => {
        const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        // Add to store immediately with 'uploading' status
        addUploadedFile({
            id: fileId,
            name: file.name,
            path: '',
            size: file.size,
            type: file.type,
            status: 'processing',
        });

        try {
            const formData = new FormData();
            formData.append('file', file);

            const token = localStorage.getItem('token');
            const response = await fetch('http://localhost:8000/api/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();
                updateUploadedFile(fileId, {
                    path: result.path,
                    status: 'ready',
                });
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            updateUploadedFile(fileId, { status: 'uploaded' });
        }
    };

    const handleDrop = useCallback(async (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            setIsUploading(true);
            for (const file of files) {
                await uploadFile(file);
            }
            setIsUploading(false);
            onFilesUploaded?.(files);
        }
    }, [onFilesUploaded]);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
            setIsUploading(true);
            for (const file of files) {
                await uploadFile(file);
            }
            setIsUploading(false);
            onFilesUploaded?.(files);
        }
    };

    const handleClick = () => {
        fileInputRef.current?.click();
    };

    const handleRemove = (fileId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        removeUploadedFile(fileId);
    };

    return (
        <div className="file-upload">
            {/* Drop Zone */}
            <div
                className={`upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleClick}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    onChange={handleFileSelect}
                    className="hidden"
                    accept="*/*"
                />

                {isUploading ? (
                    <>
                        <Loader2 size={32} className="spinner" />
                        <p>Yuklanmoqda...</p>
                    </>
                ) : (
                    <>
                        <Upload size={32} />
                        <p>Fayllarni bu yerga tashlang</p>
                        <span className="hint">yoki bosib tanlang</span>
                    </>
                )}
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
                <div className="uploaded-files-list">
                    {uploadedFiles.map((file) => (
                        <div key={file.id} className={`uploaded-file ${file.status}`}>
                            <div className="file-icon">
                                {getFileIcon(file.type)}
                            </div>
                            <div className="file-info">
                                <span className="file-name">{file.name}</span>
                                <span className="file-size">{formatFileSize(file.size)}</span>
                            </div>
                            {file.status === 'processing' ? (
                                <Loader2 size={16} className="spinner" />
                            ) : (
                                <button
                                    className="remove-file"
                                    onClick={(e) => handleRemove(file.id, e)}
                                    title="O'chirish"
                                >
                                    <X size={16} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
