/**
 * Zustand Store for Monister State Management
 * Extended with preview queue, industry modules, and deadline tracking
 */

import { create } from 'zustand';
import type {
    Message, Tool, PipelineNode, Template, LogEntry, HITLRequest,
    UploadedFile, ChatSession, DataPreviewEvent,
    PreviewQueueItem, IndustryModule, Deadline, DeadlineAlert
} from '../types';

interface MonisterState {
    // Connection
    isConnected: boolean;
    clientId: string | null;

    // Sessions
    sessions: ChatSession[];
    activeSessionId: string | null;

    // Messages
    messages: Message[];
    isStreaming: boolean;
    currentResponse: string;

    // Tools
    availableTools: Tool[];
    activeTools: string[];

    // Pipeline
    pipelineNodes: PipelineNode[];

    // Templates
    templates: Template[];
    selectedTemplate: Template | null;

    // HITL
    hitlRequest: HITLRequest | null;
    autoApprove: boolean;

    // Logs
    logs: LogEntry[];

    // Files
    uploadedFiles: UploadedFile[];

    // Data Preview
    previewData: Record<string, unknown> | null;
    previewOpen: boolean;
    previewType: 'none' | 'excel' | 'pdf' | 'image' | 'text' | 'json' | 'video' | 'spreadsheet' | 'code' | 'docx' | 'word' | 'html' | 'audio' | 'archive' | 'presentation' | 'file';
    dataPreview: DataPreviewEvent | null;

    // Preview Queue (NEW)
    previewQueue: PreviewQueueItem[];

    // Industry Modules (NEW)
    industries: IndustryModule[];
    activeIndustry: string | null;

    // Deadlines (NEW)
    deadlines: Deadline[];
    deadlineAlerts: DeadlineAlert[];

    // Sidebar
    sidebarCollapsed: boolean;

    // Actions
    setConnected: (connected: boolean, clientId?: string) => void;
    createSession: () => void;
    setActiveSession: (sessionId: string) => void;
    deleteSession: (sessionId: string) => void;
    updateSessionTitle: (sessionId: string, title: string) => void;
    addMessage: (message: Message) => void;
    updateLastMessage: (content: string) => void;
    setStreaming: (streaming: boolean) => void;
    setCurrentResponse: (response: string) => void;
    appendToCurrentResponse: (token: string) => void;
    setAvailableTools: (tools: Tool[]) => void;
    toggleTool: (toolName: string) => void;
    updatePipelineNode: (nodeId: string, status: PipelineNode['status']) => void;
    updatePipelineNodeData: (nodeId: string, data: { dataPreview?: string; summary?: string }) => void;
    addPipelineNode: (node: PipelineNode) => void;
    clearPipeline: () => void;
    setTemplates: (templates: Template[]) => void;
    selectTemplate: (template: Template | null) => void;
    setHITLRequest: (request: HITLRequest | null) => void;
    setAutoApprove: (auto: boolean) => void;
    addLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
    clearLogs: () => void;
    addUploadedFile: (file: UploadedFile) => void;
    updateUploadedFile: (fileId: string, updates: Partial<UploadedFile>) => void;
    removeUploadedFile: (fileId: string) => void;
    setPreviewData: (data: Record<string, unknown> | null) => void;
    setPreviewOpen: (open: boolean) => void;
    setPreviewType: (type: MonisterState['previewType']) => void;
    setDataPreview: (data: DataPreviewEvent | null) => void;
    setSidebarCollapsed: (collapsed: boolean) => void;

    // Preview Queue Actions (NEW)
    addToPreviewQueue: (item: PreviewQueueItem) => void;
    removeFromPreviewQueue: (id: string) => void;
    clearPreviewQueue: () => void;

    // Industry Actions (NEW)
    setIndustries: (industries: IndustryModule[]) => void;
    setActiveIndustry: (id: string | null) => void;

    // Deadline Actions (NEW)
    setDeadlines: (deadlines: Deadline[]) => void;
    setDeadlineAlerts: (alerts: DeadlineAlert[]) => void;
    addDeadline: (deadline: Deadline) => void;

    reset: () => void;
}

const initialState = {
    isConnected: false,
    clientId: null,
    sessions: [] as ChatSession[],
    activeSessionId: null as string | null,
    messages: [] as Message[],
    isStreaming: false,
    currentResponse: '',
    availableTools: [] as Tool[],
    activeTools: [] as string[],
    pipelineNodes: [] as PipelineNode[],
    templates: [] as Template[],
    selectedTemplate: null as Template | null,
    hitlRequest: null as HITLRequest | null,
    autoApprove: false,
    logs: [] as LogEntry[],
    uploadedFiles: [] as UploadedFile[],
    previewData: null as Record<string, unknown> | null,
    previewOpen: false,
    previewType: 'none' as MonisterState['previewType'],
    dataPreview: null as DataPreviewEvent | null,
    previewQueue: [] as PreviewQueueItem[],
    industries: [] as IndustryModule[],
    activeIndustry: null as string | null,
    deadlines: [] as Deadline[],
    deadlineAlerts: [] as DeadlineAlert[],
    sidebarCollapsed: false,
};

export const useMonisterStore = create<MonisterState>((set) => ({
    ...initialState,

    setConnected: (connected, clientId) => set({
        isConnected: connected,
        clientId: clientId ?? null
    }),

    // Session management
    createSession: () => set((state) => {
        const newSession: ChatSession = {
            id: `session-${Date.now()}`,
            title: 'Yangi chat',
            createdAt: new Date(),
            updatedAt: new Date(),
            messages: [],
        };
        return {
            sessions: [newSession, ...state.sessions],
            activeSessionId: newSession.id,
            messages: [],
            currentResponse: '',
            pipelineNodes: [],
        };
    }),

    setActiveSession: (sessionId) => set((state) => {
        const sessions = state.sessions.map((s) =>
            s.id === state.activeSessionId
                ? { ...s, messages: state.messages, updatedAt: new Date() }
                : s
        );
        const selectedSession = sessions.find((s) => s.id === sessionId);
        return {
            sessions,
            activeSessionId: sessionId,
            messages: selectedSession?.messages || [],
            currentResponse: '',
            pipelineNodes: [],
        };
    }),

    deleteSession: (sessionId) => set((state) => {
        const sessions = state.sessions.filter((s) => s.id !== sessionId);
        const isActiveDeleted = state.activeSessionId === sessionId;
        return {
            sessions,
            activeSessionId: isActiveDeleted
                ? sessions[0]?.id || null
                : state.activeSessionId,
            messages: isActiveDeleted ? (sessions[0]?.messages || []) : state.messages,
        };
    }),

    updateSessionTitle: (sessionId, title) => set((state) => ({
        sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, title, updatedAt: new Date() } : s
        ),
    })),

    addMessage: (message) => set((state) => ({
        messages: [...state.messages, message],
        currentResponse: '',
    })),

    updateLastMessage: (content) => set((state) => {
        const messages = [...state.messages];
        if (messages.length > 0) {
            messages[messages.length - 1] = {
                ...messages[messages.length - 1],
                content,
            };
        }
        return { messages };
    }),

    setStreaming: (streaming) => set({ isStreaming: streaming }),
    setCurrentResponse: (response) => set({ currentResponse: response }),
    appendToCurrentResponse: (token) => set((state) => ({
        currentResponse: state.currentResponse + token,
    })),
    setAvailableTools: (tools) => set({ availableTools: tools }),

    toggleTool: (toolName) => set((state) => {
        const activeTools = state.activeTools.includes(toolName)
            ? state.activeTools.filter((t) => t !== toolName)
            : [...state.activeTools, toolName];
        return { activeTools };
    }),

    updatePipelineNode: (nodeId, status) => set((state) => ({
        pipelineNodes: state.pipelineNodes.map((node) =>
            node.id === nodeId ? { ...node, status } : node
        ),
    })),

    updatePipelineNodeData: (nodeId, data) => set((state) => ({
        pipelineNodes: state.pipelineNodes.map((node) =>
            node.id === nodeId ? { ...node, ...data } : node
        ),
    })),

    addPipelineNode: (node) => set((state) => ({
        pipelineNodes: [...state.pipelineNodes, node],
    })),

    clearPipeline: () => set({ pipelineNodes: [] }),
    setTemplates: (templates) => set({ templates }),
    selectTemplate: (template) => set({ selectedTemplate: template }),
    setHITLRequest: (request) => set({ hitlRequest: request }),

    addLog: (log) => set((state) => ({
        logs: [
            ...state.logs,
            {
                ...log,
                id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 5)}`,
                timestamp: new Date(),
            },
        ].slice(-100),
    })),

    clearLogs: () => set({ logs: [] }),

    addUploadedFile: (file) => set((state) => ({
        uploadedFiles: [...state.uploadedFiles, file],
    })),

    updateUploadedFile: (fileId, updates) => set((state) => ({
        uploadedFiles: state.uploadedFiles.map((f) =>
            f.id === fileId ? { ...f, ...updates } : f
        ),
    })),

    removeUploadedFile: (fileId) => set((state) => ({
        uploadedFiles: state.uploadedFiles.filter((f) => f.id !== fileId),
    })),

    setPreviewData: (data) => set({ previewData: data }),
    setPreviewOpen: (open) => set({ previewOpen: open }),
    setPreviewType: (type) => set({ previewType: type }),
    setDataPreview: (data) => set({ dataPreview: data }),
    setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
    setAutoApprove: (auto) => set({ autoApprove: auto }),

    // ============== Preview Queue ==============
    addToPreviewQueue: (item) => set((state) => ({
        previewQueue: [...state.previewQueue, item].slice(-20),
    })),

    removeFromPreviewQueue: (id) => set((state) => ({
        previewQueue: state.previewQueue.filter((p) => p.id !== id),
    })),

    clearPreviewQueue: () => set({ previewQueue: [] }),

    // ============== Industries ==============
    setIndustries: (industries) => set({ industries }),
    setActiveIndustry: (id) => set({ activeIndustry: id }),

    // ============== Deadlines ==============
    setDeadlines: (deadlines) => set({ deadlines }),
    setDeadlineAlerts: (alerts) => set({ deadlineAlerts: alerts }),
    addDeadline: (deadline) => set((state) => ({
        deadlines: [...state.deadlines, deadline],
    })),

    reset: () => set(initialState),
}));
