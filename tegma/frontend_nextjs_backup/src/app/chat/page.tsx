'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { wsClient, WSMessage } from '@/lib/websocket';
import { useAuthStore, useChatStore, useUIStore, Message } from '@/lib/store';
import ChatSidebar from '@/components/chat/ChatSidebar';
import MessageList from '@/components/chat/MessageList';
import ChatInput from '@/components/chat/ChatInput';
import PreviewPanel from '@/components/preview/PreviewPanel';
import ThinkingIndicator from '@/components/ui/ThinkingIndicator';

export default function ChatPage() {
    const router = useRouter();
    const { user, isAuthenticated, logout } = useAuthStore();
    const {
        chats,
        currentChatId,
        messages,
        isLoading,
        isStreaming,
        streamingContent,
        setChats,
        addChat,
        setCurrentChatId,
        setMessages,
        addMessage,
        updateMessage,
        appendToStreamingContent,
        clearStreamingContent,
        setIsLoading,
        setIsStreaming,
    } = useChatStore();
    const {
        sidebarOpen,
        previewPanelOpen,
        setSuggestedTemplates,
        setProcessStatus,
        setHITLRequest,
    } = useUIStore();

    const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);

    // Auth check
    useEffect(() => {
        if (!isAuthenticated) {
            router.push('/');
        }
    }, [isAuthenticated, router]);

    // Load chats on mount
    useEffect(() => {
        const loadChats = async () => {
            try {
                const data = await api.getChats();
                setChats(data.chats);
                // Auto-select first chat or create new one
                if (data.chats.length > 0) {
                    setCurrentChatId(data.chats[0].id);
                }
            } catch (error) {
                console.error('Failed to load chats:', error);
            }
        };

        if (isAuthenticated) {
            loadChats();
        }
    }, [isAuthenticated, setChats, setCurrentChatId]);

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

    // WebSocket connection and event handling
    useEffect(() => {
        if (!currentChatId) return;

        wsClient.connect(currentChatId);

        const handleWSMessage = (message: WSMessage) => {
            switch (message.event) {
                case 'agent_thinking':
                    setIsLoading(true);
                    break;

                case 'agent_step':
                    // Update status
                    break;

                case 'message_chunk':
                    if (!streamingMessageId) {
                        const newId = message.data.message_id;
                        setStreamingMessageId(newId);
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
                    if (streamingMessageId) {
                        updateMessage(streamingMessageId, {
                            content: message.data.content,
                            isStreaming: false,
                        });
                    }
                    setStreamingMessageId(null);
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
                        status: message.data.status,
                        progress: 100,
                        message: 'Complete',
                    });
                    setTimeout(() => setProcessStatus(null), 3000);
                    break;

                case 'code_execute_start':
                    setProcessStatus({
                        type: 'code',
                        status: 'running',
                        progress: 0,
                        message: 'Executing code...',
                    });
                    break;

                case 'code_execute_output':
                    setProcessStatus({
                        type: 'code',
                        status: 'running',
                        progress: 50,
                        message: message.data.output,
                    });
                    break;

                case 'code_execute_complete':
                    setProcessStatus({
                        type: 'code',
                        status: message.data.status,
                        progress: 100,
                        message: message.data.output || 'Complete',
                    });
                    break;

                case 'template_suggest':
                    setSuggestedTemplates(message.data.templates);
                    break;

                case 'hitl_request':
                    setHITLRequest({
                        request_id: message.data.request_id,
                        tool_name: message.data.tool_name,
                        description: message.data.description,
                        options: message.data.options || ['approve', 'reject'],
                    });
                    break;

                case 'error':
                    console.error('WebSocket error:', message.data);
                    setIsLoading(false);
                    setIsStreaming(false);
                    break;
            }
        };

        const unsubscribe = wsClient.on('*', handleWSMessage);

        return () => {
            unsubscribe();
            wsClient.disconnect();
        };
    }, [currentChatId]);

    // Send message handler
    const handleSendMessage = useCallback(async (content: string, attachments?: string[]) => {
        if (!currentChatId || !content.trim()) return;

        // Add user message immediately
        const userMessage: Message = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content,
            created_at: new Date().toISOString(),
        };
        addMessage(userMessage);

        // Send via WebSocket
        wsClient.sendMessage(content, attachments);
        setIsLoading(true);
    }, [currentChatId, addMessage, setIsLoading]);

    // Create new chat
    const handleNewChat = useCallback(async () => {
        try {
            const chat = await api.createChat();
            addChat(chat as any);
            setCurrentChatId(chat.id);
        } catch (error) {
            console.error('Failed to create chat:', error);
        }
    }, [addChat, setCurrentChatId]);

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="h-screen flex bg-dark-950 overflow-hidden">
            {/* Sidebar */}
            <ChatSidebar
                chats={chats}
                currentChatId={currentChatId}
                onSelectChat={setCurrentChatId}
                onNewChat={handleNewChat}
                user={user}
                onLogout={logout}
                isOpen={sidebarOpen}
            />

            {/* Main chat area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Messages */}
                <div className="flex-1 overflow-y-auto">
                    {currentChatId ? (
                        <MessageList
                            messages={messages}
                            streamingContent={streamingContent}
                            isStreaming={isStreaming}
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center">
                            <div className="text-center">
                                <h2 className="text-2xl font-bold gradient-text mb-2">
                                    Xush kelibsiz!
                                </h2>
                                <p className="text-dark-400 mb-4">
                                    Yangi chat boshlang yoki mavjud chatni tanlang
                                </p>
                                <button onClick={handleNewChat} className="btn-primary">
                                    Yangi Chat
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Thinking indicator */}
                    {isLoading && !isStreaming && <ThinkingIndicator />}
                </div>

                {/* Input */}
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={!currentChatId || isLoading || isStreaming}
                />
            </div>

            {/* Preview panel */}
            <PreviewPanel isOpen={previewPanelOpen} />
        </div>
    );
}
