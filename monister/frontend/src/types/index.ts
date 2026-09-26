/**
 * Monister Types - Extended with Industry, Workflow, and Deadline types
 */

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    toolCalls?: ToolCall[];
}

export interface ChatSession {
    id: string;
    title: string;
    createdAt: Date;
    updatedAt: Date;
    messages: Message[];
}

export interface ToolCall {
    id: string;
    name: string;
    inputs: Record<string, unknown>;
    output?: string;
    status: 'pending' | 'running' | 'complete' | 'error';
}

export interface Tool {
    name: string;
    description: string;
    icon?: string;
}

export interface PipelineNode {
    id: string;
    type: 'input' | 'tool' | 'output';
    label: string;
    status: 'idle' | 'running' | 'complete' | 'error';
    data?: Record<string, unknown>;
    dataPreview?: string;
    rowCount?: number;
    summary?: string;
}

export interface Template {
    id: string;
    name: string;
    category: string;
    path: string;
    fields?: string[];
}

export interface HITLRequest {
    id: string;
    message: string;
    options: string[];
    timestamp: Date;
}

export interface LogEntry {
    id: string;
    level: 'info' | 'warn' | 'error';
    message: string;
    timestamp: Date;
}

export interface UploadedFile {
    id: string;
    name: string;
    path: string;
    size: number;
    type: string;
    status?: 'uploaded' | 'processing' | 'ready';
}

// WebSocket message types
export type WSMessageType =
    | 'connected'
    | 'message'
    | 'token'
    | 'tool_start'
    | 'tool_end'
    | 'pipeline_update'
    | 'hitl_request'
    | 'hitl_response'
    | 'complete'
    | 'error'
    | 'log'
    | 'status'
    | 'data_preview'
    | 'file_upload'
    | 'file_ready'
    | 'files'
    | 'deadline_alert';

export interface WSMessage {
    type: WSMessageType;
    [key: string]: unknown;
}

// ============== Data Preview ==============
export interface DataPreviewEvent {
    type: 'data_preview';
    tool_name: string;
    data: string;
    node_id: string;
    url?: string;
    file_type?: string;
    description?: string;
    auto_open?: boolean;
}

// ============== Preview Queue Item ==============
export interface PreviewQueueItem {
    id: string;
    url: string;
    fileType: string;
    toolName: string;
    description: string;
    timestamp: number;
}

// ============== Industry Module ==============
export interface IndustryModule {
    id: string;
    name: string;
    name_uz: string;
    icon: string;
    description: string;
    description_uz: string;
    document_count: number;
    keywords: string[];
}

export interface IndustryDocument {
    id: string;
    name: string;
    name_uz: string;
    description: string;
    required_fields: string[];
    optional_fields: string[];
    template_file: string;
    has_template: boolean;
    deadline_days: number;
    compliance_rules: string[];
}

// ============== Workflow ==============
export interface WorkflowStep {
    id: string;
    name: string;
    name_uz: string;
    step_type: string;
    tool_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'waiting_hitl' | 'skipped';
    output?: string;
    error?: string;
    requires_hitl: boolean;
    started_at?: string;
    completed_at?: string;
}

export interface Workflow {
    id: string;
    name: string;
    name_uz: string;
    description: string;
    industry_module: string;
    steps: WorkflowStep[];
    status: 'draft' | 'running' | 'completed' | 'failed' | 'paused';
    current_step: number;
    created_at: string;
    updated_at: string;
    output_files: string[];
}

// ============== Deadline ==============
export interface Deadline {
    id: string;
    title: string;
    title_uz: string;
    description: string;
    document_type: string;
    industry_module: string;
    due_date: string;
    status: 'active' | 'upcoming' | 'overdue' | 'completed' | 'cancelled';
    priority: 'low' | 'medium' | 'high' | 'critical';
    days_remaining: number;
    is_overdue: boolean;
    tags: string[];
}

export interface DeadlineAlert {
    type: 'overdue' | 'urgent' | 'warning' | 'reminder';
    level: 'critical' | 'high' | 'medium' | 'low';
    message: string;
    deadline: Deadline;
}
