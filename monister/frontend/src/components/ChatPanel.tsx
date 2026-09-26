/**
 * Chat Panel Component - Main chat interface
 * Includes messages, input, file upload, tool selector, and template dropdown
 * Renders markdown in assistant messages via react-markdown
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Wrench, Loader2, Paperclip, X, Square } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useMonisterStore } from '../stores/monisterStore';
import { API_URL } from '../config';
import { useWebSocket } from '../hooks/useWebSocket';
import { TemplateDropdown } from './TemplateDropdown';

export function ChatPanel() {
    const [input, setInput] = useState('');
    const [showTools, setShowTools] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const { sendMessage, stopGeneration } = useWebSocket();

    const {
        messages: rawMessages,
        isStreaming,
        currentResponse,
        availableTools: rawAvailableTools,
        activeTools: rawActiveTools,
        toggleTool,
        uploadedFiles: rawUploadedFiles,
        addUploadedFile,
        removeUploadedFile,
        updateUploadedFile,
        updateSessionTitle,
        activeSessionId,
    } = useMonisterStore();

    // Defensive defaults — prevent crashes if store returns undefined during HMR
    const messages = rawMessages ?? [];
    const availableTools = rawAvailableTools ?? [];
    const activeTools = rawActiveTools ?? [];
    const uploadedFiles = rawUploadedFiles ?? [];

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, currentResponse]);

    // Update session title based on first user message
    useEffect(() => {
        if (activeSessionId && messages.length === 1 && messages[0].role === 'user') {
            const firstMessage = messages[0].content;
            const title = firstMessage.length > 40
                ? firstMessage.substring(0, 40) + '...'
                : firstMessage;
            updateSessionTitle(activeSessionId, title);
        }
    }, [messages, activeSessionId, updateSessionTitle]);

    // Handle file upload
    const handleFileUpload = async (files: FileList | File[]) => {
        const fileArray = Array.from(files);

        for (const file of fileArray) {
            const fileId = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

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
                const response = await fetch(`${API_URL}/api/upload`, {
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
                }
            } catch (error) {
                updateUploadedFile(fileId, { status: 'ready' });
                console.error('Upload error:', error);
            }
        }
    };

    // Drag and drop handlers
    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files);
        }
    };

    // Handle send
    const handleSend = () => {
        if (!input.trim() || isStreaming) return;

        // Include file paths in message if files are uploaded
        let messageContent = input;
        if (uploadedFiles.length > 0) {
            const filePaths = uploadedFiles
                .filter(f => f.status === 'ready')
                .map(f => f.path)
                .join(', ');
            if (filePaths) {
                messageContent = `[FILES: ${filePaths}]\n${input}`;
            }
        }

        sendMessage(messageContent, activeTools.length > 0 ? activeTools : undefined);
        setInput('');
    };

    // Handle slash commands
    const handleInputChange = (value: string) => {
        setInput(value);

        // Show tool picker on /
        if (value.endsWith('/')) {
            setShowTools(true);
        } else if (!value.includes('/')) {
            setShowTools(false);
        }
    };

    // Insert tool command
    const insertTool = (toolName: string) => {
        setInput((prev) => prev.replace(/\/$/, '') + `/${toolName} `);
        setShowTools(false);
    };

    return (
        <div
            className={`chat-panel ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            {/* Header */}
            <div className="chat-header">
                <h2>💬 Chat</h2>
                <div className="chat-header-actions">
                    <TemplateDropdown />
                </div>
            </div>

            {/* Drag Overlay */}
            {dragActive && (
                <div className="drag-overlay">
                    <div className="drag-content">
                        <Paperclip size={48} />
                        <p>Fayllarni bu yerga tashlang</p>
                    </div>
                </div>
            )}

            {/* Messages */}
            <div className="messages-container">
                {messages.length === 0 && (
                    <div className="welcome-message">
                        <h3>👋 Salom! Men Monister AI.</h3>
                        <p>Hujjatlar, Big Data va preprocessing bilan yordam beraman.</p>
                        <p className="hint">/ bosib toollarni ko'ring yoki fayl yuklang</p>
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} className={`message ${msg.role}`}>
                        <div className="message-avatar">
                            {msg.role === 'user' ? '👤' : '🤖'}
                        </div>
                        <div className="message-content">
                            {msg.role === 'assistant' ? (
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {msg.content}
                                </ReactMarkdown>
                            ) : (
                                msg.content
                            )}
                        </div>
                    </div>
                ))}

                {/* Streaming response */}
                {isStreaming && currentResponse && (
                    <div className="message assistant streaming">
                        <div className="message-avatar">🤖</div>
                        <div className="message-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {currentResponse}
                            </ReactMarkdown>
                            <span className="cursor">▊</span>
                        </div>
                    </div>
                )}

                {isStreaming && !currentResponse && (
                    <div className="message assistant thinking">
                        <div className="message-avatar">🤖</div>
                        <div className="message-content">
                            <Loader2 className="spinner" />
                            O'ylamoqda...
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Uploaded Files */}
            {uploadedFiles.length > 0 && (
                <div className="uploaded-files-bar">
                    {uploadedFiles.map((file) => (
                        <div key={file.id} className={`file-chip ${file.status}`}>
                            <span className="file-chip-name">{file.name}</span>
                            {file.status === 'processing' ? (
                                <Loader2 size={14} className="spinner" />
                            ) : (
                                <button
                                    className="remove-file-chip"
                                    onClick={() => removeUploadedFile(file.id)}
                                >
                                    <X size={14} />
                                </button>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Active Tools */}
            {activeTools.length > 0 && (
                <div className="active-tools">
                    <span className="label">Active tools:</span>
                    {activeTools.map((tool) => (
                        <span key={tool} className="tool-chip active" onClick={() => toggleTool(tool)}>
                            {tool} ×
                        </span>
                    ))}
                </div>
            )}

            {/* Tool Picker */}
            {showTools && (
                <div className="tool-picker">
                    <div className="tool-picker-header">🛠️ Tool tanlang:</div>
                    {availableTools.map((tool) => (
                        <div
                            key={tool.name}
                            className="tool-option"
                            onClick={() => insertTool(tool.name)}
                        >
                            <span className="tool-name">/{tool.name}</span>
                            <span className="tool-desc">{tool.description}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Input */}
            <div className="chat-input-container">
                <button
                    className="tools-button"
                    onClick={() => fileInputRef.current?.click()}
                    title="Fayl yuklash"
                >
                    <Paperclip size={20} />
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                />

                <button
                    className="tools-button"
                    onClick={() => setShowTools(!showTools)}
                    title="Toollar"
                >
                    <Wrench size={20} />
                </button>

                <input
                    type="text"
                    className="chat-input"
                    placeholder="Xabar yozing... (/ - toollar)"
                    value={input}
                    onChange={(e) => handleInputChange(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    disabled={isStreaming}
                />

                {isStreaming ? (
                    <button
                        className="send-button stop"
                        onClick={stopGeneration}
                        title="To'xtatish"
                    >
                        <Square size={20} />
                    </button>
                ) : (
                    <button
                        className="send-button"
                        onClick={handleSend}
                        disabled={!input.trim()}
                    >
                        <Send size={20} />
                    </button>
                )}
            </div>
        </div>
    );
}
