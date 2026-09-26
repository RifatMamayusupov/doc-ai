/**
 * Document Workflow Panel Component
 * 
 * Real-time document generation workflow UI with WebSocket integration
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { DocumentPreview } from './DocumentPreview';
import { TemplateGallery } from './TemplateGallery';
import './WorkflowPanel.css';

type WorkflowState =
    | 'idle'
    | 'analyzing'
    | 'matching_templates'
    | 'waiting_selection'
    | 'generating'
    | 'previewing'
    | 'editing'
    | 'finalizing'
    | 'completed'
    | 'error';

interface WorkflowTemplate {
    id: string;
    name: string;
    description?: string;
    category: string;
    match_score?: number;
    matched_fields?: string[];
    missing_fields?: string[];
    preview_image?: string;
}

interface GeneratedDocument {
    id: string;
    template_id: string;
    template_name: string;
    preview?: any;
    editable_fields?: Array<{
        field_id: string;
        label: string;
        value: any;
        type: string;
        editable: boolean;
        options?: string[];
    }>;
    status: 'draft' | 'approved' | 'skipped' | 'error';
    error?: string;
}

interface WorkflowPanelProps {
    chatId: string;
    ws: WebSocket | null;
    onComplete?: (documents: GeneratedDocument[]) => void;
    className?: string;
}

export function WorkflowPanel({
    chatId,
    ws,
    onComplete,
    className = '',
}: WorkflowPanelProps) {
    const [state, setState] = useState<WorkflowState>('idle');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [extractedData, setExtractedData] = useState<Record<string, any>>({});
    const [suggestedTemplates, setSuggestedTemplates] = useState<WorkflowTemplate[]>([]);
    const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
    const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
    const [currentDocIndex, setCurrentDocIndex] = useState(0);
    const [progress, setProgress] = useState({ current: 0, total: 0 });
    const [error, setError] = useState<string | null>(null);

    const stateRef = useRef(state);
    stateRef.current = state;

    // WebSocket event handling
    useEffect(() => {
        if (!ws) return;

        const handleMessage = (event: MessageEvent) => {
            try {
                const message = JSON.parse(event.data);
                handleWsEvent(message);
            } catch (err) {
                console.error('Parse error:', err);
            }
        };

        ws.addEventListener('message', handleMessage);
        return () => ws.removeEventListener('message', handleMessage);
    }, [ws]);

    const handleWsEvent = useCallback((message: any) => {
        const { event, data } = message;

        switch (event) {
            case 'workflow_started':
                setSessionId(data.session_id);
                setState('analyzing');
                setError(null);
                break;

            case 'analysis_started':
                setState('analyzing');
                break;

            case 'analysis_completed':
                setExtractedData(data.extracted_fields || {});
                setState('matching_templates');
                break;

            case 'template_suggestions':
                // Ensure templates have required category field
                const templates = (data.templates || []).map((t: any) => ({
                    ...t,
                    category: t.category || 'Umumiy',
                }));
                setSuggestedTemplates(templates);
                setExtractedData(data.extracted_data || {});
                setState('waiting_selection');
                break;

            case 'templates_selected':
                setState('generating');
                setProgress({ current: 0, total: data.count });
                break;

            case 'generation_started':
                setState('generating');
                setProgress({ current: 0, total: data.total });
                break;

            case 'generation_progress':
                setProgress({ current: data.current, total: data.total });
                break;

            case 'document_ready':
                setDocuments(prev => {
                    const existing = prev.find(d => d.id === data.document.id);
                    if (existing) {
                        return prev.map(d => d.id === data.document.id ? data.document : d);
                    }
                    return [...prev, data.document];
                });
                break;

            case 'all_documents_ready':
                setState('previewing');
                setCurrentDocIndex(0);
                break;

            case 'document_regenerated':
                setDocuments(prev =>
                    prev.map(d => d.id === data.document.id ? data.document : d)
                );
                break;

            case 'document_approved':
                setDocuments(prev =>
                    prev.map(d => d.id === data.document_id ? { ...d, status: 'approved' } : d)
                );
                // Auto-advance to next
                if (stateRef.current === 'previewing') {
                    setCurrentDocIndex(prev => Math.min(prev + 1, documents.length - 1));
                }
                break;

            case 'document_skipped':
                setDocuments(prev =>
                    prev.map(d => d.id === data.document_id ? { ...d, status: 'skipped' } : d)
                );
                // Auto-advance to next
                if (stateRef.current === 'previewing') {
                    setCurrentDocIndex(prev => Math.min(prev + 1, documents.length - 1));
                }
                break;

            case 'finalizing_started':
                setState('finalizing');
                break;

            case 'workflow_completed':
                setState('completed');
                onComplete?.(documents);
                break;

            case 'workflow_cancelled':
                setState('idle');
                resetWorkflow();
                break;

            case 'workflow_error':
                setError(data.error);
                setState('error');
                break;
        }
    }, [documents, onComplete]);

    // Send WebSocket event
    const sendEvent = (eventType: string, data: any = {}) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ event: eventType, data }));
        }
    };

    // Reset workflow
    const resetWorkflow = () => {
        setSessionId(null);
        setExtractedData({});
        setSuggestedTemplates([]);
        setSelectedTemplateIds([]);
        setDocuments([]);
        setCurrentDocIndex(0);
        setProgress({ current: 0, total: 0 });
        setError(null);
    };

    // Handle template selection
    const handleTemplateSelect = (templateId: string) => {
        setSelectedTemplateIds(prev => {
            if (prev.includes(templateId)) {
                return prev.filter(id => id !== templateId);
            }
            return [...prev, templateId];
        });
    };

    // Confirm template selection
    const confirmTemplateSelection = () => {
        if (selectedTemplateIds.length === 0) return;

        sendEvent('template_selected', {
            template_ids: selectedTemplateIds,
        });
    };

    // Handle field update
    const handleFieldUpdate = (documentId: string, fieldId: string, value: any) => {
        sendEvent('update_field', {
            document_id: documentId,
            field_id: fieldId,
            value,
        });

        // Optimistic update
        setDocuments(prev =>
            prev.map(d => {
                if (d.id === documentId && d.editable_fields) {
                    return {
                        ...d,
                        editable_fields: d.editable_fields.map(f =>
                            f.field_id === fieldId ? { ...f, value } : f
                        ),
                    };
                }
                return d;
            })
        );
    };

    // Approve current document
    const approveDocument = () => {
        const doc = documents[currentDocIndex];
        if (doc) {
            sendEvent('approve_doc', { document_id: doc.id });
        }
    };

    // Skip current document
    const skipDocument = () => {
        const doc = documents[currentDocIndex];
        if (doc) {
            sendEvent('skip_doc', { document_id: doc.id });
        }
    };

    // Regenerate current document
    const regenerateDocument = () => {
        const doc = documents[currentDocIndex];
        if (doc) {
            sendEvent('regenerate_doc', { document_id: doc.id });
        }
    };

    // Finalize workflow
    const finalizeWorkflow = () => {
        const approvedIds = documents
            .filter(d => d.status === 'approved')
            .map(d => d.id);

        sendEvent('finalize_workflow', {
            approved_document_ids: approvedIds,
        });
    };

    // Cancel workflow
    const cancelWorkflow = () => {
        sendEvent('cancel_workflow', {});
        setState('idle');
        resetWorkflow();
    };

    // Get state description
    const getStateDescription = () => {
        switch (state) {
            case 'idle': return '';
            case 'analyzing': return "Ma'lumotlar tahlil qilinmoqda...";
            case 'matching_templates': return 'Mos shablonlar qidirilmoqda...';
            case 'waiting_selection': return 'Shablon tanlang';
            case 'generating': return `Hujjatlar yaratilmoqda (${progress.current}/${progress.total})`;
            case 'previewing': return "Hujjatlarni ko'rib chiqing";
            case 'editing': return 'Tahrirlash';
            case 'finalizing': return 'Yakunlanmoqda...';
            case 'completed': return 'Tayyor!';
            case 'error': return 'Xatolik yuz berdi';
            default: return '';
        }
    };

    const currentDoc = documents[currentDocIndex];
    const approvedCount = documents.filter(d => d.status === 'approved').length;
    const skippedCount = documents.filter(d => d.status === 'skipped').length;

    // Don't render if idle
    if (state === 'idle') return null;

    return (
        <div className={`workflow-panel ${className}`}>
            {/* Header */}
            <div className="workflow-header">
                <div className="workflow-status">
                    <div className={`status-indicator ${state}`}></div>
                    <span className="status-text">{getStateDescription()}</span>
                </div>

                <button className="cancel-btn" onClick={cancelWorkflow}>
                    ✕
                </button>
            </div>

            {/* Main Content */}
            <div className="workflow-content">
                {/* Analyzing State */}
                {(state === 'analyzing' || state === 'matching_templates') && (
                    <div className="analyzing-state">
                        <div className="loading-animation">
                            <div className="pulse-ring"></div>
                            <div className="pulse-core">📄</div>
                        </div>
                        <p>{getStateDescription()}</p>
                    </div>
                )}

                {/* Template Selection State */}
                {state === 'waiting_selection' && (
                    <div className="template-selection">
                        <TemplateGallery
                            templates={suggestedTemplates}
                            preselected={selectedTemplateIds}
                            onSelect={(ids) => setSelectedTemplateIds(ids)}
                            showMatchScores
                        />

                        <div className="selection-footer">
                            <span className="selection-count">
                                {selectedTemplateIds.length} ta tanlandi
                            </span>
                            <button
                                className="confirm-btn"
                                disabled={selectedTemplateIds.length === 0}
                                onClick={confirmTemplateSelection}
                            >
                                Davom etish →
                            </button>
                        </div>
                    </div>
                )}

                {/* Generating State */}
                {state === 'generating' && (
                    <div className="generating-state">
                        <div className="progress-container">
                            <div className="progress-bar">
                                <div
                                    className="progress-fill"
                                    style={{ width: `${(progress.current / progress.total) * 100}%` }}
                                />
                            </div>
                            <span className="progress-text">
                                {progress.current} / {progress.total}
                            </span>
                        </div>
                        <p>Hujjatlar yaratilmoqda...</p>
                    </div>
                )}

                {/* Preview State */}
                {state === 'previewing' && currentDoc && (
                    <div className="preview-state">
                        {/* Document navigation */}
                        <div className="doc-navigation">
                            <button
                                className="nav-btn prev"
                                disabled={currentDocIndex === 0}
                                onClick={() => setCurrentDocIndex(prev => prev - 1)}
                            >
                                ←
                            </button>

                            <div className="doc-counter">
                                <span className="current">{currentDocIndex + 1}</span>
                                <span className="separator">/</span>
                                <span className="total">{documents.length}</span>
                            </div>

                            <button
                                className="nav-btn next"
                                disabled={currentDocIndex === documents.length - 1}
                                onClick={() => setCurrentDocIndex(prev => prev + 1)}
                            >
                                →
                            </button>
                        </div>

                        {/* Document preview */}
                        <div className="preview-area">
                            <div className="document-preview-wrapper">
                                {currentDoc.preview?.content ? (
                                    <img
                                        src={currentDoc.preview.content}
                                        alt={currentDoc.template_name}
                                        style={{ maxWidth: '100%', height: 'auto' }}
                                    />
                                ) : (
                                    <div className="preview-placeholder">
                                        <span>📄</span>
                                        <p>{currentDoc.template_name}</p>
                                    </div>
                                )}
                            </div>

                            {/* Editable fields sidebar */}
                            {currentDoc.editable_fields && currentDoc.editable_fields.length > 0 && (
                                <div className="fields-sidebar">
                                    <h4>Maydonlar</h4>
                                    {currentDoc.editable_fields.map(field => (
                                        <div key={field.field_id} className="field-item">
                                            <label>{field.label}</label>
                                            {field.type === 'select' && field.options ? (
                                                <select
                                                    value={field.value || ''}
                                                    onChange={e => handleFieldUpdate(currentDoc.id, field.field_id, e.target.value)}
                                                >
                                                    {field.options.map(opt => (
                                                        <option key={opt} value={opt}>{opt}</option>
                                                    ))}
                                                </select>
                                            ) : field.type === 'date' ? (
                                                <input
                                                    type="date"
                                                    value={field.value || ''}
                                                    onChange={e => handleFieldUpdate(currentDoc.id, field.field_id, e.target.value)}
                                                />
                                            ) : (
                                                <input
                                                    type="text"
                                                    value={field.value || ''}
                                                    onChange={e => handleFieldUpdate(currentDoc.id, field.field_id, e.target.value)}
                                                />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Document actions */}
                        <div className="doc-actions">
                            <button className="action-btn skip" onClick={skipDocument}>
                                O'tkazib yuborish
                            </button>
                            <button className="action-btn regenerate" onClick={regenerateDocument}>
                                Qayta yaratish
                            </button>
                            <button className="action-btn approve" onClick={approveDocument}>
                                ✓ Tasdiqlash
                            </button>
                        </div>

                        {/* Progress summary */}
                        <div className="doc-summary">
                            <span className="approved">✓ {approvedCount} tasdiqlangan</span>
                            <span className="skipped">↷ {skippedCount} o'tkazilgan</span>
                        </div>

                        {/* Finalize button */}
                        {approvedCount > 0 && currentDocIndex === documents.length - 1 && (
                            <button className="finalize-btn" onClick={finalizeWorkflow}>
                                Yakunlash va yuklab olish
                            </button>
                        )}
                    </div>
                )}

                {/* Completed State */}
                {state === 'completed' && (
                    <div className="completed-state">
                        <div className="success-icon">✓</div>
                        <h3>Muvaffaqiyatli yakunlandi!</h3>
                        <p>{approvedCount} ta hujjat tayyor</p>
                        <button className="close-btn" onClick={() => { setState('idle'); resetWorkflow(); }}>
                            Yopish
                        </button>
                    </div>
                )}

                {/* Error State */}
                {state === 'error' && (
                    <div className="error-state">
                        <div className="error-icon">⚠️</div>
                        <h3>Xatolik yuz berdi</h3>
                        <p>{error}</p>
                        <button className="retry-btn" onClick={() => { setState('idle'); resetWorkflow(); }}>
                            Qayta urinish
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default WorkflowPanel;
