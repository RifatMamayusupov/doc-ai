/**
 * Global state management with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types
export interface User {
    id: string;
    email: string;
    username: string;
}

export interface Chat {
    id: string;
    title: string;
    thread_id?: string;
    is_pinned?: boolean;
    is_archived?: boolean;
    created_at: string;
    updated_at: string;
    message_count?: number;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    message_metadata?: Record<string, any>;
    isStreaming?: boolean;
    created_at: string;
}

export interface ProcessStatus {
    type: string;
    status: 'pending' | 'running' | 'success' | 'error';
    progress: number;
    message: string;
}

export interface HITLRequest {
    request_id: string;
    tool_name: string;
    description: string;
    arguments?: Record<string, any>;
    options: string[];
}

export interface Template {
    id: string;
    name: string;
    description: string;
    organization?: string;
    category?: string;
}

// Auth Store
interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    setUser: (user: User | null) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            isAuthenticated: false,
            setUser: (user: User | null) => set({ user, isAuthenticated: !!user }),
            logout: () => set({ user: null, isAuthenticated: false }),
        }),
        { name: 'auth-storage' }
    )
);

// Chat Store
interface ChatState {
    chats: Chat[];
    currentChatId: string | null;
    messages: Message[];
    isLoading: boolean;
    isStreaming: boolean;
    streamingContent: string;
    setChats: (chats: Chat[]) => void;
    addChat: (chat: Chat) => void;
    setCurrentChatId: (id: string | null) => void;
    setMessages: (messages: Message[]) => void;
    addMessage: (message: Message) => void;
    updateMessage: (id: string, updates: Partial<Message>) => void;
    appendToStreamingContent: (chunk: string) => void;
    clearStreamingContent: () => void;
    setIsLoading: (loading: boolean) => void;
    setIsStreaming: (streaming: boolean) => void;
}

export const useChatStore = create<ChatState>()((set) => ({
    chats: [],
    currentChatId: null,
    messages: [],
    isLoading: false,
    isStreaming: false,
    streamingContent: '',
    setChats: (chats: Chat[]) => set({ chats }),
    addChat: (chat: Chat) => set((state) => ({ chats: [chat, ...state.chats] })),
    setCurrentChatId: (id: string | null) => set({ currentChatId: id, messages: [] }),
    setMessages: (messages: Message[]) => set({ messages }),
    addMessage: (message: Message) => set((state) => ({ messages: [...state.messages, message] })),
    updateMessage: (id: string, updates: Partial<Message>) =>
        set((state) => ({
            messages: state.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
        })),
    appendToStreamingContent: (chunk: string) =>
        set((state) => ({ streamingContent: state.streamingContent + chunk })),
    clearStreamingContent: () => set({ streamingContent: '' }),
    setIsLoading: (loading: boolean) => set({ isLoading: loading }),
    setIsStreaming: (streaming: boolean) => set({ isStreaming: streaming }),
}));

// UI Store
interface UIState {
    sidebarOpen: boolean;
    previewPanelOpen: boolean;
    suggestedTemplates: Template[];
    processStatus: ProcessStatus | null;
    hitlRequest: HITLRequest | null;
    setSidebarOpen: (open: boolean) => void;
    setPreviewPanelOpen: (open: boolean) => void;
    setSuggestedTemplates: (templates: Template[]) => void;
    setProcessStatus: (status: ProcessStatus | null) => void;
    setHITLRequest: (request: HITLRequest | null) => void;
}

export const useUIStore = create<UIState>()((set) => ({
    sidebarOpen: true,
    previewPanelOpen: false,
    suggestedTemplates: [],
    processStatus: null,
    hitlRequest: null,
    setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
    setPreviewPanelOpen: (open: boolean) => set({ previewPanelOpen: open }),
    setSuggestedTemplates: (templates: Template[]) => set({ suggestedTemplates: templates, previewPanelOpen: templates.length > 0 }),
    setProcessStatus: (status: ProcessStatus | null) => set({ processStatus: status, previewPanelOpen: !!status }),
    setHITLRequest: (request: HITLRequest | null) => set({ hitlRequest: request, previewPanelOpen: !!request }),
}));
