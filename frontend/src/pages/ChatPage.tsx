/**
 * Chat Page - Main chat interface
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    MessageSquare, Plus, Send, Paperclip, LogOut,
    Menu, ChevronLeft, ChevronDown, ChevronUp, Bot, User, Loader2, X, Check,
    Sparkles, Settings, MoreVertical, Trash2, Download, Edit2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import * as XLSX from 'xlsx';
import { api } from '../lib/api';
import { wsClient, WSMessage } from '../lib/websocket';
import { useAuthStore, useChatStore, useUIStore, Message } from '../lib/store';

export default function ChatPage() {
    const navigate = useNavigate();
    const { user, isAuthenticated, logout } = useAuthStore();
    const {
        chats, currentChatId, messages, isLoading, isStreaming, streamingContent,
        setChats, addChat, setCurrentChatId, setMessages, addMessage, updateMessage,
        appendToStreamingContent, clearStreamingContent, setIsLoading, setIsStreaming,
    } = useChatStore();
    const { sidebarOpen, setSidebarOpen, hitlRequest, setHITLRequest, processStatus, setProcessStatus } = useUIStore();

    const [inputValue, setInputValue] = useState('');
    const [attachments, setAttachments] = useState<any[]>([]);
    const [previewFile, setPreviewFile] = useState<any>(null);
    const [previewWidth, setPreviewWidth] = useState(450);
    const [isResizing, setIsResizing] = useState(false);
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const fileInputRef = useRef<HTMLInputElement>(null);
    const streamingMessageIdRef = useRef<string | null>(null);

    // Resize handlers
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (isResizing) {
                const newWidth = window.innerWidth - e.clientX;
                if (newWidth > 300 && newWidth < 800) setPreviewWidth(newWidth);
            }
        };
        const handleMouseUp = () => setIsResizing(false);
        if (isResizing) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isResizing]);

    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            try {
                // Show loading state if needed
                const uploadedFile = await api.uploadFile(file);
                setAttachments(prev => [...prev, uploadedFile]);
                // Reset input
                if (fileInputRef.current) fileInputRef.current.value = '';
            } catch (error) {
                console.error('File upload failed:', error);
                alert('Fayl yuklashda xatolik yuz berdi');
            }
        }
    };

    const removeAttachment = (id: string) => {
        setAttachments(prev => prev.filter(a => a.id !== id));
    };

    // Auth check
    useEffect(() => {
        if (!isAuthenticated) {
            navigate('/');
        }
    }, [isAuthenticated, navigate]);

    // Load chats on mount
    useEffect(() => {
        const loadChats = async () => {
            try {
                const data = await api.getChats();
                setChats(data.chats);
                if (data.chats.length > 0 && !currentChatId) {
                    setCurrentChatId(data.chats[0].id);
                }
            } catch (error) {
                console.error('Failed to load chats:', error);
            }
        };
        if (isAuthenticated) loadChats();
    }, [isAuthenticated, setChats, setCurrentChatId, currentChatId]);

    // Load messages when chat changes
    useEffect(() => {
        const loadMessages = async () => {
            if (!currentChatId) return;
            try {
                const msgs = await api.getChatMessages(currentChatId);
                setMessages(msgs as Message[]);
            } catch (error) {
                console.error('Failed to load messages:', error);
            }
        };
        loadMessages();
    }, [currentChatId, setMessages]);

    // WebSocket handling
    useEffect(() => {
        if (!currentChatId) return;

        wsClient.connect(currentChatId);

        const handleWSMessage = (message: WSMessage) => {
            switch (message.event) {
                case 'agent_thinking':
                    setIsLoading(true);
                    break;

                case 'message_chunk':
                    if (!streamingMessageIdRef.current) {
                        const newId = message.data.message_id;
                        streamingMessageIdRef.current = newId;
                        addMessage({
                            id: newId,
                            role: 'assistant',
                            content: '',
                            isStreaming: true,
                            created_at: new Date().toISOString(),
                        });
                    }
                    setIsStreaming(true);
                    appendToStreamingContent(message.data.chunk);
                    break;

                case 'message_complete':
                    setIsStreaming(false);
                    setIsLoading(false);
                    if (streamingMessageIdRef.current) {
                        updateMessage(streamingMessageIdRef.current, {
                            content: message.data.content,
                            isStreaming: false,
                        });
                    }
                    streamingMessageIdRef.current = null;
                    clearStreamingContent();
                    break;

                case 'tool_call_start':
                    setProcessStatus({
                        type: message.data.tool_name,
                        status: 'running',
                        progress: 0,
                        message: message.data.description || 'Executing...',
                    });
                    break;

                case 'tool_call_result':
                    setProcessStatus({
                        type: message.data.tool_name,
                        status: message.data.status === 'success' ? 'success' : 'error',
                        progress: 100,
                        message: 'Complete',
                    });
                    setTimeout(() => setProcessStatus(null), 3000);
                    break;

                case 'hitl_request':
                    setHITLRequest({
                        request_id: message.data.request_id,
                        tool_name: message.data.tool_name,
                        description: message.data.description,
                        arguments: message.data.arguments,
                        options: message.data.options || ['approve', 'reject'],
                    });
                    break;

                case 'code_execute_start':
                    setProcessStatus({
                        type: 'Python Sandbox',
                        status: 'running',
                        progress: 0,
                        message: message.data.description || 'Executing code...',
                    });
                    break;

                case 'code_execute_complete':
                    // Check for artifacts
                    if (message.data.artifacts && message.data.artifacts.length > 0) {
                        setPreviewFile(message.data.artifacts[0]);
                    }

                    setProcessStatus({
                        type: 'Python Sandbox',
                        status: message.data.status === 'success' ? 'success' : 'error',
                        progress: 100,
                        message: message.data.status === 'success' ? 'Completed successfully' : 'Execution failed',
                    });
                    setTimeout(() => setProcessStatus(null), 5000);
                    break;

                case 'document_ready':
                    // Show document preview inline
                    if (message.data.content) {
                        const previewMessageId = `doc-preview-${Date.now()}`;
                        addMessage({
                            id: previewMessageId,
                            role: 'assistant',
                            content: message.data.content,
                            created_at: new Date().toISOString(),
                            message_metadata: {
                                type: 'document_preview',
                                file_path: message.data.file_path,
                                preview_type: message.data.preview_type,
                            }
                        });
                    }
                    break;

                case 'document_generated':
                    // Handle generated document
                    if (message.data.success) {
                        setProcessStatus({
                            type: 'Hujjat yaratish',
                            status: 'success',
                            progress: 100,
                            message: message.data.message || 'Hujjat yaratildi!',
                        });

                        // If file path is provided, show in preview panel
                        if (message.data.file_path) {
                            const fileName = message.data.file_path.split('/').pop() || 'document';
                            setPreviewFile({
                                name: fileName,
                                url: `/uploads/${message.data.file_path.split('uploads/')[1] || message.data.file_path}`,
                                type: 'document'
                            });
                        }
                    } else {
                        setProcessStatus({
                            type: 'Hujjat yaratish',
                            status: 'error',
                            progress: 100,
                            message: message.data.error || 'Xatolik yuz berdi',
                        });
                    }
                    setTimeout(() => setProcessStatus(null), 5000);
                    break;

                case 'error':
                    console.error('WebSocket error:', message.data);
                    setIsLoading(false);
                    setIsStreaming(false);
                    setProcessStatus({
                        type: 'Error',
                        status: 'error',
                        progress: 100,
                        message: message.data.message || 'Unknown error',
                    });
                    setTimeout(() => setProcessStatus(null), 5000);
                    break;
            }
        };

        const unsubscribe = wsClient.on('*', handleWSMessage);

        return () => {
            unsubscribe();
            wsClient.disconnect();
        };
    }, [currentChatId]);

    // Send message
    const handleSendMessage = useCallback(async () => {
        if (!currentChatId || (!inputValue.trim() && attachments.length === 0)) return;

        // Add file names to content for visibility if attachments exist
        let displayContent = inputValue;
        if (attachments.length > 0) {
            const fileNames = attachments.map(a => `[📎 ${a.filename}]`).join(' ');
            if (displayContent) displayContent += '\n\n' + fileNames;
            else displayContent = fileNames;
        }

        const userMessage: Message = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: displayContent,
            created_at: new Date().toISOString(),
        };
        addMessage(userMessage);
        setInputValue('');
        const currentAttachments = [...attachments];
        setAttachments([]);

        wsClient.sendMessage(inputValue, currentAttachments);
        setIsLoading(true);
    }, [currentChatId, inputValue, attachments, addMessage, setIsLoading]);

    // Create new chat
    const handleNewChat = useCallback(async () => {
        try {
            const chat = await api.createChat();
            addChat(chat);
            setCurrentChatId(chat.id);
        } catch (error) {
            console.error('Failed to create chat:', error);
        }
    }, [addChat, setCurrentChatId]);

    // Update and Delete handlers
    const handleUpdateChat = async (id: string, data: any) => {
        try {
            await api.updateChat(id, data);
            const updatedChats = chats.map(c => c.id === id ? { ...c, ...data } : c);
            setChats(updatedChats);
        } catch (error) {
            console.error('Failed to update chat:', error);
        }
    };

    const handleDeleteChat = async (id: string) => {
        if (!window.confirm('Haqiqatan ham bu chatni o\'chirmoqchimisiz?')) return;
        try {
            await api.deleteChat(id);
            const updatedChats = chats.filter(c => c.id !== id);
            setChats(updatedChats);
            if (currentChatId === id) {
                setCurrentChatId(null);
                setMessages([]);
            }
        } catch (error) {
            console.error('Failed to delete chat:', error);
        }
    };

    // HITL response
    const handleHITLResponse = (response: 'approve' | 'reject') => {
        if (hitlRequest) {
            wsClient.sendHITLResponse(hitlRequest.request_id, response);
            setHITLRequest(null);
        }
    };

    // Logout
    const handleLogout = () => {
        logout();
        api.clearTokens();
        navigate('/');
    };

    if (!isAuthenticated) return null;

    return (
        <div className="h-screen flex overflow-hidden" style={{ background: 'var(--dark-950)' }}>
            {/* Sidebar */}
            <AnimatePresence>
                {sidebarOpen && (
                    <motion.aside
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        style={{
                            background: 'var(--dark-900)',
                            borderRight: '1px solid var(--dark-700)',
                            display: 'flex',
                            flexDirection: 'column',
                        }}
                    >
                        {/* Sidebar header */}
                        <div style={{ padding: '1rem', borderBottom: '1px solid var(--dark-700)' }}>
                            <button
                                onClick={handleNewChat}
                                className="btn-primary w-full"
                                style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                            >
                                <Plus size={18} />
                                Yangi Chat
                            </button>
                        </div>

                        {/* Chat list */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
                            {chats.map((chat) => (
                                <ChatListItem
                                    key={chat.id}
                                    chat={chat}
                                    active={currentChatId === chat.id}
                                    onSelect={() => setCurrentChatId(chat.id)}
                                    onUpdate={handleUpdateChat}
                                    onDelete={handleDeleteChat}
                                />
                            ))}
                        </div>

                        {/* User section */}
                        <div style={{
                            padding: '1rem',
                            borderTop: '1px solid var(--dark-700)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                        }}>
                            <div style={{
                                width: '36px',
                                height: '36px',
                                borderRadius: '50%',
                                background: 'var(--primary)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}>
                                <User size={18} color="white" />
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>{user?.username}</div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--dark-400)' }}>{user?.email}</div>
                            </div>
                            <button
                                onClick={handleLogout}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--dark-400)',
                                    cursor: 'pointer',
                                    padding: '0.5rem',
                                }}
                            >
                                <LogOut size={18} />
                            </button>
                        </div>
                    </motion.aside>
                )}
            </AnimatePresence>

            {/* Main area */}
            {/* Main Wrapper */}
            <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
                {/* Chat Column */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    {/* Header */}
                    <header style={{
                        padding: '1rem',
                        borderBottom: '1px solid var(--dark-700)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                    }}>
                        <button
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--dark-300)',
                                cursor: 'pointer',
                                padding: '0.5rem',
                            }}
                        >
                            {sidebarOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
                        </button>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Sparkles size={20} style={{ color: 'var(--primary)' }} />
                            <span className="gradient-text font-bold">DocAgent</span>
                        </div>
                    </header>

                    {/* Messages */}
                    <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                        {currentChatId ? (
                            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                                {messages.map((msg) => (
                                    <MessageBubble
                                        key={msg.id}
                                        message={msg}
                                        streamingContent={msg.isStreaming ? streamingContent : undefined}
                                    />
                                ))}

                                {/* Loading indicator */}
                                {isLoading && !isStreaming && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}
                                    >
                                        <div style={{
                                            width: '32px',
                                            height: '32px',
                                            borderRadius: '50%',
                                            background: 'linear-gradient(135deg, var(--primary) 0%, #a855f7 100%)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                        }}>
                                            <Bot size={16} color="white" />
                                        </div>
                                        <div style={{
                                            background: 'var(--dark-800)',
                                            border: '1px solid var(--dark-600)',
                                            borderRadius: '1rem',
                                            padding: '0.75rem 1.25rem',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.75rem',
                                        }}>
                                            <div style={{ display: 'flex', gap: '4px' }}>
                                                <motion.div
                                                    animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                                    transition={{ duration: 1, repeat: Infinity, delay: 0 }}
                                                    style={{ width: '8px', height: '8px', background: 'var(--primary)', borderRadius: '50%' }}
                                                />
                                                <motion.div
                                                    animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                                    transition={{ duration: 1, repeat: Infinity, delay: 0.2 }}
                                                    style={{ width: '8px', height: '8px', background: 'var(--primary)', borderRadius: '50%' }}
                                                />
                                                <motion.div
                                                    animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
                                                    transition={{ duration: 1, repeat: Infinity, delay: 0.4 }}
                                                    style={{ width: '8px', height: '8px', background: 'var(--primary)', borderRadius: '50%' }}
                                                />
                                            </div>
                                            <span style={{ color: 'var(--dark-300)', fontSize: '0.875rem' }}>
                                                AI o'ylayapti...
                                            </span>
                                        </div>
                                    </motion.div>
                                )}

                                {/* Process status */}
                                {processStatus && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        style={{
                                            background: 'var(--dark-800)',
                                            border: '1px solid var(--dark-600)',
                                            borderRadius: '0.75rem',
                                            padding: '1rem',
                                            marginTop: '1rem',
                                        }}
                                    >
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            {processStatus.status === 'running' && <Loader2 size={16} className="animate-spin" style={{ color: 'var(--primary)' }} />}
                                            {processStatus.status === 'success' && <Check size={16} style={{ color: 'var(--success)' }} />}
                                            <span style={{ fontWeight: 500 }}>{processStatus.type}</span>
                                        </div>
                                        <p style={{ fontSize: '0.875rem', color: 'var(--dark-400)', marginTop: '0.5rem' }}>
                                            {processStatus.message}
                                        </p>
                                    </motion.div>
                                )}
                            </div>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <div className="text-center">
                                    <div style={{
                                        width: '80px',
                                        height: '80px',
                                        background: 'linear-gradient(135deg, var(--primary) 0%, #a855f7 100%)',
                                        borderRadius: '1.5rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        margin: '0 auto 1.5rem',
                                    }}>
                                        <Sparkles size={40} color="white" />
                                    </div>
                                    <h2 className="gradient-text" style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                                        Xush kelibsiz!
                                    </h2>
                                    <p style={{ color: 'var(--dark-400)', marginBottom: '1.5rem' }}>
                                        Yangi chat boshlang yoki mavjud chatni tanlang
                                    </p>
                                    <button onClick={handleNewChat} className="btn-primary">
                                        <Plus size={18} style={{ marginRight: '0.5rem' }} />
                                        Yangi Chat
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* HITL Request Modal */}
                    <AnimatePresence>
                        {hitlRequest && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                style={{
                                    position: 'fixed',
                                    inset: 0,
                                    background: 'rgba(0, 0, 0, 0.7)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    zIndex: 100,
                                }}
                            >
                                <motion.div
                                    initial={{ scale: 0.9, opacity: 0 }}
                                    animate={{ scale: 1, opacity: 1 }}
                                    exit={{ scale: 0.9, opacity: 0 }}
                                    className="card"
                                    style={{ maxWidth: '450px', width: '90%' }}
                                >
                                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>
                                        Tasdiqlash kerak
                                    </h3>
                                    <p style={{ color: 'var(--dark-300)', marginBottom: '0.5rem' }}>
                                        <strong>{hitlRequest.tool_name}</strong>
                                    </p>
                                    <p style={{ color: 'var(--dark-400)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
                                        {hitlRequest.description}
                                    </p>
                                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                                        <button
                                            onClick={() => handleHITLResponse('reject')}
                                            className="btn-secondary"
                                            style={{ flex: 1 }}
                                        >
                                            <X size={16} style={{ marginRight: '0.5rem' }} />
                                            Rad etish
                                        </button>
                                        <button
                                            onClick={() => handleHITLResponse('approve')}
                                            className="btn-primary"
                                            style={{ flex: 1 }}
                                        >
                                            <Check size={16} style={{ marginRight: '0.5rem' }} />
                                            Tasdiqlash
                                        </button>
                                    </div>
                                </motion.div>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Input area */}
                    {currentChatId && (
                        <div style={{ padding: '1rem', borderTop: '1px solid var(--dark-700)' }}>
                            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                                {/* Attachments list */}
                                {attachments.length > 0 && (
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem', padding: '0 0.5rem' }}>
                                        {attachments.map((att) => (
                                            <div key={att.id} style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.25rem',
                                                background: 'var(--dark-700)',
                                                padding: '0.25rem 0.5rem',
                                                borderRadius: '0.25rem',
                                                fontSize: '0.75rem',
                                                color: 'var(--dark-200)'
                                            }}>
                                                <span>📎 {att.filename}</span>
                                                <button
                                                    onClick={() => removeAttachment(att.id)}
                                                    style={{ border: 'none', background: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}
                                                >
                                                    <X size={12} color="var(--dark-400)" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div style={{
                                    background: 'var(--dark-800)',
                                    borderRadius: '1rem',
                                    border: '1px solid var(--dark-600)',
                                    display: 'flex',
                                    alignItems: 'flex-end',
                                    padding: '0.75rem',
                                }}>
                                    <input
                                        type="file"
                                        ref={fileInputRef}
                                        style={{ display: 'none' }}
                                        onChange={handleFileSelect}
                                    />
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        style={{
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--dark-300)',
                                            cursor: 'pointer',
                                            padding: '0.5rem',
                                            marginRight: '0.5rem',
                                        }}
                                        title="Fayl yuklash"
                                    >
                                        <Paperclip size={20} />
                                    </button>

                                    <textarea
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && !e.shiftKey) {
                                                e.preventDefault();
                                                handleSendMessage();
                                            }
                                        }}
                                        placeholder="Xabar yozing... (yoki fayl yuklang)"
                                        rows={1}
                                        style={{
                                            flex: 1,
                                            background: 'none',
                                            border: 'none',
                                            color: 'var(--dark-100)',
                                            fontSize: '1rem',
                                            resize: 'none',
                                            outline: 'none',
                                            maxHeight: '150px',
                                        }}
                                    />
                                    <button
                                        onClick={handleSendMessage}
                                        disabled={(!inputValue.trim() && attachments.length === 0) || isLoading}
                                        style={{
                                            background: (inputValue.trim() || attachments.length > 0) ? 'var(--primary)' : 'var(--dark-600)',
                                            border: 'none',
                                            borderRadius: '0.5rem',
                                            padding: '0.5rem',
                                            cursor: (inputValue.trim() || attachments.length > 0) ? 'pointer' : 'not-allowed',
                                            marginLeft: '0.5rem',
                                        }}
                                    >
                                        <Send size={18} color="white" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Preview Column */}
                <AnimatePresence>
                    {previewFile && (
                        <motion.div
                            initial={{ width: 0, opacity: 0 }}
                            animate={{ width: previewWidth, opacity: 1 }}
                            exit={{ width: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            style={{
                                borderLeft: '1px solid var(--dark-700)',
                                background: 'var(--dark-800)',
                                display: 'flex',
                                flexDirection: 'column',
                                boxShadow: '-4px 0 12px rgba(0,0,0,0.2)',
                                zIndex: 10,
                                position: 'relative',
                                width: previewWidth
                            }}
                        >
                            {/* Resize Handle */}
                            <div
                                onMouseDown={(e) => { e.preventDefault(); setIsResizing(true); }}
                                style={{
                                    position: 'absolute',
                                    left: '-6px',
                                    top: 0,
                                    bottom: 0,
                                    width: '12px',
                                    cursor: 'col-resize',
                                    zIndex: 50,
                                    background: 'transparent',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center'
                                }}
                            >
                                <div style={{ width: '4px', height: '40px', background: 'var(--dark-600)', borderRadius: '2px' }} />
                            </div>

                            {/* Header */}
                            <div style={{
                                padding: '1rem',
                                borderBottom: '1px solid var(--dark-700)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                background: 'var(--dark-900)'
                            }}>
                                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--dark-100)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '300px' }}>
                                    {previewFile.name}
                                </span>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <a
                                        href={API_URL + previewFile.url}
                                        download
                                        target="_blank"
                                        style={{ color: 'var(--dark-400)', cursor: 'pointer' }}
                                        title="Yuklab olish"
                                    >
                                        <Download size={20} />
                                    </a>
                                    <button
                                        onClick={() => setPreviewFile(null)}
                                        style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--dark-400)', display: 'flex' }}
                                    >
                                        <X size={20} />
                                    </button>
                                </div>
                            </div>

                            {/* Content */}
                            <div style={{ flex: 1, overflow: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--dark-800)' }}>
                                {previewFile.type === 'image' || previewFile.name.match(/\.(png|jpg|jpeg|gif)$/i) ? (
                                    <img
                                        src={API_URL + previewFile.url}
                                        alt="Preview"
                                        style={{ maxWidth: '100%', maxHeight: '100%', borderRadius: '0.5rem', boxShadow: '0 4px 6px rgba(0,0,0,0.3)' }}
                                    />
                                ) : previewFile.name.match(/\.(xlsx|csv|xls)$/i) ? (
                                    <ExcelPreview url={API_URL + previewFile.url} />
                                ) : previewFile.name.match(/\.pdf$/i) ? (
                                    <iframe
                                        src={API_URL + previewFile.url}
                                        style={{
                                            width: '100%',
                                            height: '100%',
                                            border: 'none',
                                            background: 'white',
                                            borderRadius: '0.5rem',
                                            pointerEvents: isResizing ? 'none' : 'auto'
                                        }}
                                    />
                                ) : (
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>📄</div>
                                        <p style={{ color: 'var(--dark-300)', marginBottom: '1rem' }}>Fayl ko'rinishi mavjud emas</p>
                                        <a
                                            href={API_URL + previewFile.url}
                                            download
                                            target="_blank"
                                            style={{
                                                display: 'inline-block',
                                                padding: '0.5rem 1rem',
                                                background: 'var(--primary)',
                                                color: 'white',
                                                borderRadius: '0.5rem',
                                                textDecoration: 'none',
                                                fontWeight: 500
                                            }}
                                        >
                                            Yuklab olish
                                        </a>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div >
    );
}

// Custom Code Block Component
const CodeBlock = ({ inline, className, children, ...props }: any) => {
    // ... code block logic ...
    const match = /language-(\w+)/.exec(className || '');
    const [isCollapsed, setIsCollapsed] = useState(false);

    if (!inline && match) {
        return (
            <div style={{ margin: '0.75rem 0', borderRadius: '0.5rem', border: '1px solid var(--dark-700)', overflow: 'hidden' }}>
                <div
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    style={{
                        background: 'var(--dark-800)',
                        padding: '0.5rem 1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        color: 'var(--dark-300)',
                        borderBottom: isCollapsed ? 'none' : '1px solid var(--dark-700)',
                        userSelect: 'none'
                    }}
                >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--primary)', textTransform: 'uppercase' }}>{match[1]}</span>
                    </div>
                    {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                </div>
                {!isCollapsed && (
                    <div style={{ padding: '0.75rem', background: 'var(--dark-900)', overflowX: 'auto' }}>
                        <code className={className} {...props}>
                            {children}
                        </code>
                    </div>
                )}
            </div>
        );
    }
    return <code className={className} {...props}>{children}</code>;
};

// Excel Preview Component
const ExcelPreview = ({ url }: { url: string }) => {
    const [data, setData] = useState<any[]>([]);
    const [columns, setColumns] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        setError(null);
        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error('Failed to fetch file');
                return res.arrayBuffer();
            })
            .then(ab => {
                try {
                    const wb = XLSX.read(ab, { type: 'array' });
                    const wsname = wb.SheetNames[0];
                    const ws = wb.Sheets[wsname];
                    const jsonData = XLSX.utils.sheet_to_json(ws, { header: 1 }); // Array of arrays
                    if (jsonData && jsonData.length > 0) {
                        setColumns(jsonData[0] as string[] || []);
                        setData(jsonData.slice(1));
                    }
                } catch (e) {
                    console.error('Excel parse error:', e);
                    setError('Failed to parse Excel file');
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setError(err.message);
                setLoading(false);
            });
    }, [url]);

    if (loading) return (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--dark-400)' }}>
            <Loader2 className="animate-spin" style={{ margin: '0 auto 1rem' }} />
            Loading spreadsheet...
        </div>
    );

    if (error) return <div style={{ color: 'var(--error)', padding: '1rem' }}>Error: {error}</div>;

    return (
        <div style={{ overflow: 'auto', maxHeight: '100%', width: '100%', padding: '0.5rem' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                <thead>
                    <tr>
                        {columns.map((col, i) => (
                            <th key={i} style={{
                                border: '1px solid var(--dark-600)',
                                padding: '8px 12px',
                                background: 'var(--dark-700)',
                                color: 'var(--dark-100)',
                                textAlign: 'left',
                                fontWeight: 600
                            }}>
                                {col || `Col ${i + 1}`}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map((row: any[], i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'var(--dark-800)' : 'var(--dark-850)' }}>
                            {columns.map((_, colIndex) => (
                                <td key={colIndex} style={{
                                    border: '1px solid var(--dark-700)',
                                    padding: '6px 12px',
                                    color: 'var(--dark-200)'
                                }}>
                                    {row[colIndex] !== undefined ? String(row[colIndex]) : ''}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

// Message bubble component
function MessageBubble({ message, streamingContent }: { message: Message; streamingContent?: string }) {
    const isUser = message.role === 'user';
    const content = streamingContent || message.content;

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
                display: 'flex',
                gap: '0.75rem',
                marginBottom: '1rem',
                flexDirection: isUser ? 'row-reverse' : 'row',
            }}
        >
            <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: isUser ? 'var(--primary)' : 'var(--dark-700)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
            }}>
                {isUser ? <User size={16} color="white" /> : <Bot size={16} />}
            </div>
            <div style={{
                maxWidth: '80%',
                background: isUser ? 'var(--primary)' : 'var(--dark-800)',
                borderRadius: isUser ? '1rem 1rem 0 1rem' : '1rem 1rem 1rem 0',
                padding: '0.75rem 1rem',
                overflowWrap: 'break-word',
            }}>
                {isUser ? (
                    <p style={{ whiteSpace: 'pre-wrap' }}>{content}</p>
                ) : message.message_metadata?.type === 'document_preview' ? (
                    <div className="document-preview">
                        <div style={{
                            marginBottom: '1rem',
                            paddingBottom: '0.5rem',
                            borderBottom: '1px solid #eee',
                            fontWeight: '600',
                            fontSize: '1rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            color: '#333'
                        }}>
                            <span style={{ fontSize: '1.2rem' }}>📄</span>
                            Hujjat Ko'rinishi
                        </div>
                        <div dangerouslySetInnerHTML={{ __html: content }} />
                    </div>
                ) : (
                    <div className="prose prose-invert prose-sm">
                        <ReactMarkdown components={{
                            code: CodeBlock
                        }}>{content}</ReactMarkdown>
                    </div>
                )}
                {streamingContent && (
                    <span style={{
                        display: 'inline-block',
                        width: '8px',
                        height: '16px',
                        background: 'var(--primary)',
                        marginLeft: '2px',
                        animation: 'pulse 1s infinite',
                    }} />
                )}
            </div>
        </motion.div>
    );
}

// Chat List Item Component with Edit/Delete support
const ChatListItem = ({ chat, active, onSelect, onUpdate, onDelete }: any) => {
    const [isEditing, setIsEditing] = useState(false);
    const [title, setTitle] = useState(chat.title || '');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isEditing]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (title.trim() !== chat.title) {
            await onUpdate(chat.id, { title });
        }
        setIsEditing(false);
    };

    const handleStartEdit = (e: React.MouseEvent) => {
        e.stopPropagation();
        setTitle(chat.title || '');
        setIsEditing(true);
    };

    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        onDelete(chat.id);
    };

    return (
        <div
            onClick={!isEditing ? onSelect : undefined}
            style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: active ? 'var(--dark-700)' : 'transparent',
                color: active ? 'white' : 'var(--dark-300)',
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.25rem',
                transition: 'all 0.2s',
                position: 'relative',
            }}
            className="group"
        >
            <MessageSquare size={16} />

            {isEditing ? (
                <form onSubmit={handleSave} style={{ flex: 1, display: 'flex', gap: '4px' }}>
                    <input
                        ref={inputRef}
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        onBlur={() => setIsEditing(false)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            background: 'var(--dark-800)',
                            border: '1px solid var(--primary)',
                            color: 'white',
                            borderRadius: '4px',
                            padding: '2px 4px',
                            width: '100%',
                            fontSize: '0.875rem'
                        }}
                    />
                </form>
            ) : (
                <>
                    <span style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        flex: 1,
                        fontSize: '0.875rem',
                        marginRight: '32px'
                    }}>
                        {chat.title || 'Untitled Chat'}
                    </span>

                    {/* Action Buttons */}
                    <div
                        className="hidden group-hover:flex items-center gap-1"
                        style={{
                            position: 'absolute',
                            right: '8px',
                            background: active ? 'var(--dark-700)' : 'var(--dark-900)',
                            paddingLeft: '8px'
                        }}
                    >
                        <button onClick={handleStartEdit} title="Tahrirlash" className="p-1 hover:text-white rounded hover:bg-dark-600" style={{ color: 'var(--dark-400)' }}>
                            <Edit2 size={12} />
                        </button>
                        <button onClick={handleDelete} title="O'chirish" className="p-1 hover:text-red-400 rounded hover:bg-dark-600" style={{ color: 'var(--dark-400)' }}>
                            <Trash2 size={12} />
                        </button>
                    </div>
                </>
            )}
        </div>
    );
};
