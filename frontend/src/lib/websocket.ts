/**
 * WebSocket client for real-time communication
 */

import { api } from './api';

export type WSEventType =
    | 'connected'
    | 'disconnected'
    | 'error'
    | 'agent_thinking'
    | 'agent_step'
    | 'agent_complete'
    | 'message_chunk'
    | 'message_complete'
    | 'tool_call_start'
    | 'tool_call_progress'
    | 'tool_call_result'
    | 'code_execute_start'
    | 'code_execute_output'
    | 'code_execute_complete'
    | 'hitl_request'
    | 'hitl_response'
    | 'template_suggest'
    | 'template_selected'
    | 'document_ready'
    | 'document_generated'
    | 'process_status';

export interface WSMessage {
    event: WSEventType;
    chat_id?: string;
    data: Record<string, any>;
    timestamp?: string;
}

export type WSEventHandler = (message: WSMessage) => void;

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

class WebSocketClient {
    private ws: WebSocket | null = null;
    private chatId: string | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private eventHandlers: Map<WSEventType | '*', Set<WSEventHandler>> = new Map();
    private messageQueue: Array<{ event: string; data: any }> = [];

    connect(chatId: string): void {
        const token = api.getAccessToken();
        if (!token) {
            console.error('No access token available');
            return;
        }

        this.chatId = chatId;
        const url = `${WS_URL}/ws/chat/${chatId}/${token}`;

        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            // Send queued messages
            while (this.messageQueue.length > 0) {
                const msg = this.messageQueue.shift();
                if (msg) this.send(msg.event, msg.data);
            }
            this.emit({ event: 'connected', data: { chatId } });
        };

        this.ws.onmessage = (event) => {
            try {
                const message: WSMessage = JSON.parse(event.data);
                this.emit(message);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.emit({ event: 'error', data: { error: 'Connection error' } });
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit({ event: 'disconnected', data: {} });
            this.attemptReconnect();
        };
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.chatId = null;
        this.reconnectAttempts = 0;
    }

    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }

        if (!this.chatId) return;

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

        setTimeout(() => {
            if (this.chatId) {
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                this.connect(this.chatId);
            }
        }, delay);
    }

    send(event: string, data: Record<string, any>): void {
        const message = { event, data };

        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            this.messageQueue.push(message);
        }
    }

    sendMessage(content: string, attachments?: any[]): void {
        this.send('send_message', { content, attachments });
    }

    sendHITLResponse(requestId: string, response: 'approve' | 'reject' | 'modify', modifications?: any): void {
        this.send('hitl_response', { request_id: requestId, response, modifications });
    }

    selectTemplate(templateId: string): void {
        this.send('template_selected', { template_id: templateId });
    }

    cancelGeneration(): void {
        this.send('cancel_generation', {});
    }

    on(event: WSEventType | '*', handler: WSEventHandler): () => void {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event)!.add(handler);

        // Return unsubscribe function
        return () => {
            this.eventHandlers.get(event)?.delete(handler);
        };
    }

    off(event: WSEventType | '*', handler: WSEventHandler): void {
        this.eventHandlers.get(event)?.delete(handler);
    }

    private emit(message: WSMessage): void {
        this.eventHandlers.get(message.event)?.forEach((handler) => handler(message));
        this.eventHandlers.get('*')?.forEach((handler) => handler(message));
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

export const wsClient = new WebSocketClient();
