/**
 * WebSocket Hook for real-time communication with Monister backend
 */

import { useEffect, useRef, useCallback } from 'react';
import { useMonisterStore } from '../stores/monisterStore';
import { WS_URL } from '../config';
import type { WSMessage, PipelineNode } from '../types';

export function useWebSocket() {
    const wsRef = useRef<WebSocket | null>(null);
    const clientIdRef = useRef<string>(`client-${Date.now()}`);
    const retryCountRef = useRef<number>(0);
    const MAX_RETRIES = 10;

    const {
        setConnected,
        addMessage,
        appendToCurrentResponse,
        setStreaming,
        setAvailableTools,
        addPipelineNode,
        updatePipelineNode,
        updatePipelineNodeData,
        setHITLRequest,
        addLog,
        setPreviewData,
        updateUploadedFile,
        addToPreviewQueue,
        setDeadlineAlerts,
    } = useMonisterStore();

    // Handle incoming messages
    const handleMessage = useCallback((data: WSMessage) => {
        switch (data.type) {
            case 'connected':
                setAvailableTools(data.tools as any[]);
                break;

            case 'token':
                appendToCurrentResponse(data.content as string);
                break;

            case 'tool_start':
                addPipelineNode({
                    id: data.name as string,
                    type: 'tool',
                    label: data.name as string,
                    status: 'running',
                    data: data.inputs as Record<string, unknown>,
                });
                addLog({ level: 'info', message: `Running tool: ${data.name}` });
                break;

            case 'tool_end':
                updatePipelineNode(data.name as string, 'complete');
                addLog({ level: 'info', message: `Tool completed: ${data.name}` });
                break;

            // Handle data preview with queue-based conflict-free display
            case 'data_preview': {
                const previewData = data.data as string;
                const nodeId = data.node_id as string;
                const fileUrl = (data as any).url;
                const fileType = (data as any).file_type;
                const description = (data as any).description || '';
                const autoOpen = (data as any).auto_open ?? true;

                // Update pipeline node
                updatePipelineNodeData(nodeId, {
                    dataPreview: previewData?.slice(0, 200),
                    summary: description || `${(previewData || '').length} chars processed`,
                });

                // Only open preview for actual files with URL
                if (fileUrl && fileType) {
                    // Add to preview queue (conflict-free FIFO)
                    addToPreviewQueue({
                        id: `pq-${Date.now()}`,
                        url: fileUrl,
                        fileType,
                        toolName: data.tool_name as string,
                        description,
                        timestamp: Date.now(),
                    });

                    // Set as active preview
                    setPreviewData({
                        tool: data.tool_name,
                        content: previewData,
                        url: fileUrl,
                        type: fileType,
                        description,
                        timestamp: new Date().toISOString(),
                    });

                    useMonisterStore.getState().setPreviewType(fileType);
                    if (autoOpen) {
                        useMonisterStore.getState().setPreviewOpen(true);
                    }
                    const fileName = fileUrl.split('/').pop() || 'file';
                    addLog({ level: 'info', message: `📄 Fayl tayyor: ${fileName}` });
                } else if (previewData) {
                    addLog({ level: 'info', message: `Tool completed: ${nodeId}` });
                }
                break;
            }

            // NEW: Handle file ready notification
            case 'file_ready':
                addLog({ level: 'info', message: data.message as string });
                break;

            case 'pipeline_update':
                const nodes = data.nodes as PipelineNode[];
                nodes.forEach((node) => {
                    updatePipelineNode(node.id, node.status);
                });
                break;

            case 'hitl_request':
                const autoApprove = useMonisterStore.getState().autoApprove;

                if (autoApprove) {
                    addLog({ level: 'info', message: 'Auto-approving agent request...' });
                    // Send approval immediately
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(JSON.stringify({
                            type: 'hitl_response',
                            interrupt_id: data.interrupt_id,
                            decision: 'approve',
                        }));
                        addLog({ level: 'info', message: 'Decision: approve (Auto)' });
                    }
                } else {
                    setHITLRequest({
                        id: data.interrupt_id as string,
                        message: data.message as string,
                        options: ['approve', 'reject'],
                        timestamp: new Date(),
                    });
                    addLog({ level: 'warn', message: 'Agent awaiting approval' });
                }
                break;

            case 'complete':
                const response = data.response as string;
                const currentResponse = useMonisterStore.getState().currentResponse;

                addMessage({
                    id: `msg-${Date.now()}`,
                    role: 'assistant',
                    content: currentResponse || response,
                    timestamp: new Date(),
                });
                setStreaming(false);
                addLog({ level: 'info', message: 'Response complete' });
                break;

            case 'error':
                addLog({ level: 'error', message: data.message as string });
                setStreaming(false);
                break;

            case 'log':
                addLog({
                    level: data.level as 'info' | 'warn' | 'error',
                    message: data.message as string,
                });
                break;

            case 'status':
                addLog({ level: 'info', message: `Status: ${data.status}` });
                break;

            // Handle deadline alerts from backend
            case 'deadline_alert' as any:
                const alerts = (data as any).alerts;
                if (Array.isArray(alerts)) {
                    setDeadlineAlerts(alerts);
                    alerts.forEach((a: any) => {
                        addLog({ level: a.level === 'critical' ? 'error' : 'warn', message: a.message });
                    });
                }
                break;
        }
    }, [
        setAvailableTools,
        appendToCurrentResponse,
        addPipelineNode,
        updatePipelineNode,
        updatePipelineNodeData,
        setHITLRequest,
        addMessage,
        setStreaming,
        addLog,
        setPreviewData,
        updateUploadedFile,
        addToPreviewQueue,
        setDeadlineAlerts,
    ]);

    // Connect to WebSocket
    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const token = localStorage.getItem('token');
        const wsUrl = `${WS_URL}/${clientIdRef.current}${token ? `?token=${token}` : ''}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            setConnected(true, clientIdRef.current);
            addLog({ level: 'info', message: 'Connected to Monister AI' });
            retryCountRef.current = 0; // Reset retry counter on success
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            setConnected(false);
            addLog({ level: 'warn', message: 'Disconnected from server' });

            // Reconnect with exponential backoff, max 10 retries
            if (retryCountRef.current < MAX_RETRIES) {
                const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
                retryCountRef.current += 1;
                console.log(`Reconnecting in ${delay}ms (attempt ${retryCountRef.current}/${MAX_RETRIES})`);
                setTimeout(connect, delay);
            } else {
                addLog({ level: 'error', message: 'Max reconnection attempts reached. Please refresh the page.' });
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addLog({ level: 'error', message: 'Connection error' });
        };

        ws.onmessage = (event) => {
            try {
                const data: WSMessage = JSON.parse(event.data);
                handleMessage(data);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };

        wsRef.current = ws;
    }, [setConnected, addLog, handleMessage]);

    // Send message to server
    const sendMessage = useCallback((content: string, activeTools?: string[]) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            addLog({ level: 'error', message: 'Not connected to server' });
            return;
        }

        // Add user message
        addMessage({
            id: `msg-${Date.now()}`,
            role: 'user',
            content,
            timestamp: new Date(),
        });

        setStreaming(true);

        // Send to server
        wsRef.current.send(JSON.stringify({
            type: 'message',
            content,
            active_tools: activeTools,
        }));

        addLog({ level: 'info', message: 'Message sent' });
    }, [addMessage, setStreaming, addLog]);

    // NEW: Send file upload notification
    const sendFileUpload = useCallback((fileInfo: {
        file_id: string;
        filename: string;
        path: string;
        size: number;
        file_type: string;
    }) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            addLog({ level: 'error', message: 'Not connected to server' });
            return;
        }

        wsRef.current.send(JSON.stringify({
            type: 'file_upload',
            ...fileInfo,
        }));

        addLog({ level: 'info', message: `File registered: ${fileInfo.filename}` });
    }, [addLog]);

    // Send HITL response
    const sendHITLResponse = useCallback((interruptId: string, decision: 'approve' | 'reject') => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            return;
        }

        wsRef.current.send(JSON.stringify({
            type: 'hitl_response',
            interrupt_id: interruptId,
            decision,
        }));

        setHITLRequest(null);
        addLog({ level: 'info', message: `Decision: ${decision}` });
    }, [setHITLRequest, addLog]);

    // Stop generation
    const stopGeneration = useCallback(() => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            return;
        }

        // Send stop command to server
        wsRef.current.send(JSON.stringify({
            type: 'stop',
        }));

        // Reset streaming state locally
        setStreaming(false);

        // Add current response as message if exists
        const currentResponse = useMonisterStore.getState().currentResponse;
        if (currentResponse) {
            addMessage({
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: currentResponse + '\n\n[⏹️ To\'xtatildi]',
                timestamp: new Date(),
            });
            useMonisterStore.getState().setCurrentResponse('');
        }

        addLog({ level: 'warn', message: 'Generation stopped by user' });
    }, [setStreaming, addMessage, addLog]);

    // Connect on mount
    useEffect(() => {
        connect();

        return () => {
            wsRef.current?.close();
        };
    }, [connect]);

    return {
        sendMessage,
        sendFileUpload,
        sendHITLResponse,
        stopGeneration,
        reconnect: connect,
    };
}

