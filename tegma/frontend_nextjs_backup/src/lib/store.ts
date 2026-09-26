/**
 * Zustand stores for global state management
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types
export interface User {
    id: string;
    email: string;
    username: string;
    full_name: string | null;
}

export interface Chat {
    id: string;
    title: string;
    thread_id: string;
    is_archived: boolean;
    is_pinned: boolean;
    created_at: string;
    updated_at: string;
    message_count: number;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    message_metadata?: Record<string, any>;
    isStreaming?: boolean;
    created_at: string;
}

export interface Template {
    id: string;
    name: string;
    organization: string;
    category: string;
    preview_image: string | null;
}

export interface ProcessStatus {
    type: string;
    status: string;
    progress: number;
    message: string;
    preview_url?: string;
}

export interface HITLRequest {
    request_id: string;
    tool_name: string;
    description: string;
    options: string[];
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
            setUser: (user) => set({ user, isAuthenticated: !!user }),
            logout: () => set({ user: null, isAuthenticated: false }),
        }),
        {
            name: 'auth-storage',
        }
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

export const useChatStore = create<ChatState>((set) => ({
    chats: [],
    currentChatId: null,
    messages: [],
    isLoading: false,
    isStreaming: false,
    streamingContent: '',

    setChats: (chats) => set({ chats }),
    addChat: (chat) => set((state) => ({ chats: [chat, ...state.chats] })),
    setCurrentChatId: (id) => set({ currentChatId: id, messages: [] }),
    setMessages: (messages) => set({ messages }),
    addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
    updateMessage: (id, updates) => set((state) => ({
        messages: state.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),
    appendToStreamingContent: (chunk) => set((state) => ({
        streamingContent: state.streamingContent + chunk,
    })),
    clearStreamingContent: () => set({ streamingContent: '' }),
    setIsLoading: (loading) => set({ isLoading: loading }),
    setIsStreaming: (streaming) => set({ isStreaming: streaming }),
}));

// UI Store
interface UIState {
    sidebarOpen: boolean;
    previewPanelOpen: boolean;
    templates: Template[];
    suggestedTemplates: Template[];
    processStatus: ProcessStatus | null;
    hitlRequest: HITLRequest | null;

    toggleSidebar: () => void;
    setSidebarOpen: (open: boolean) => void;
    setPreviewPanelOpen: (open: boolean) => void;
    setTemplates: (templates: Template[]) => void;
    setSuggestedTemplates: (templates: Template[]) => void;
    setProcessStatus: (status: ProcessStatus | null) => void;
    setHITLRequest: (request: HITLRequest | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
    sidebarOpen: true,
    previewPanelOpen: false,
    templates: [],
    suggestedTemplates: [],
    processStatus: null,
    hitlRequest: null,

    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
    setPreviewPanelOpen: (open) => set({ previewPanelOpen: open }),
    setTemplates: (templates) => set({ templates }),
    setSuggestedTemplates: (templates) => set({ suggestedTemplates: templates, previewPanelOpen: templates.length > 0 }),
    setProcessStatus: (status) => set({ processStatus: status, previewPanelOpen: !!status }),
    setHITLRequest: (request) => set({ hitlRequest: request, previewPanelOpen: !!request }),
}));
