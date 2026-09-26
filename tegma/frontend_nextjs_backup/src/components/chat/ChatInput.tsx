'use client';

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Paperclip, X, FileText, Image, File } from 'lucide-react';
import { api } from '@/lib/api';

interface ChatInputProps {
    onSend: (content: string, attachments?: string[]) => void;
    disabled?: boolean;
}

interface UploadedFile {
    id: string;
    name: string;
    type: string;
    size: number;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
    const [message, setMessage] = useState('');
    const [files, setFiles] = useState<UploadedFile[]>([]);
    const [uploading, setUploading] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!message.trim() && files.length === 0) return;
        if (disabled) return;

        onSend(message, files.map((f) => f.id));
        setMessage('');
        setFiles([]);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setMessage(e.target.value);
        // Auto-resize
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    };

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFiles = Array.from(e.target.files || []);
        if (selectedFiles.length === 0) return;

        setUploading(true);

        try {
            for (const file of selectedFiles) {
                const result = await api.uploadFile(file);
                setFiles((prev) => [
                    ...prev,
                    {
                        id: result.id,
                        name: file.name,
                        type: result.type,
                        size: result.size,
                    },
                ]);
            }
        } catch (error) {
            console.error('Upload failed:', error);
        } finally {
            setUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const removeFile = (id: string) => {
        setFiles((prev) => prev.filter((f) => f.id !== id));
    };

    const getFileIcon = (type: string) => {
        if (type.startsWith('image') || ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(type)) {
            return <Image className="w-4 h-4" />;
        }
        if (['pdf', 'doc', 'docx', 'txt'].includes(type)) {
            return <FileText className="w-4 h-4" />;
        }
        return <File className="w-4 h-4" />;
    };

    return (
        <div className="border-t border-dark-700 bg-dark-900/50 backdrop-blur-sm p-4">
            <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                {/* Attached files */}
                <AnimatePresence>
                    {files.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="flex flex-wrap gap-2 mb-3"
                        >
                            {files.map((file) => (
                                <div
                                    key={file.id}
                                    className="flex items-center gap-2 bg-dark-800 border border-dark-600 rounded-lg px-3 py-2"
                                >
                                    {getFileIcon(file.type)}
                                    <span className="text-sm text-dark-200 truncate max-w-[150px]">
                                        {file.name}
                                    </span>
                                    <button
                                        type="button"
                                        onClick={() => removeFile(file.id)}
                                        className="text-dark-400 hover:text-red-400"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Input area */}
                <div className="flex items-end gap-3">
                    {/* File upload button */}
                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        onChange={handleFileSelect}
                        className="hidden"
                        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.json,.jpg,.jpeg,.png,.gif,.webp"
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading || disabled}
                        className="p-3 text-dark-400 hover:text-white hover:bg-dark-800 rounded-xl transition-colors disabled:opacity-50"
                    >
                        {uploading ? (
                            <div className="w-5 h-5 border-2 border-dark-400 border-t-white rounded-full animate-spin" />
                        ) : (
                            <Paperclip className="w-5 h-5" />
                        )}
                    </button>

                    {/* Text input */}
                    <div className="flex-1 relative">
                        <textarea
                            ref={textareaRef}
                            value={message}
                            onChange={handleTextChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Xabar yozing..."
                            disabled={disabled}
                            rows={1}
                            className="w-full bg-dark-800 border border-dark-600 rounded-xl px-4 py-3 text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none disabled:opacity-50"
                            style={{ maxHeight: '200px' }}
                        />
                    </div>

                    {/* Send button */}
                    <button
                        type="submit"
                        disabled={disabled || (!message.trim() && files.length === 0)}
                        className="p-3 bg-primary hover:bg-primary-hover text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Send className="w-5 h-5" />
                    </button>
                </div>

                {/* Helper text */}
                <p className="text-xs text-dark-500 mt-2 text-center">
                    Enter - yuborish, Shift+Enter - yangi qator
                </p>
            </form>
        </div>
    );
}
