/**
 * Document Carousel Component
 * 
 * Displays generated documents one by one with navigation,
 * preview, edit, and download capabilities.
 */

import React, { useState, useCallback } from 'react';
import DocumentPreview from './DocumentPreview';
import './DocumentCarousel.css';

interface GeneratedDocument {
    id: string;
    template_id: string;
    template_name: string;
    preview_url: string;
    format: string;
    editable_fields: EditableField[];
    pages: number;
    status: 'draft' | 'approved' | 'skipped';
}

interface EditableField {
    field_id: string;
    label: string;
    value: any;
    type: 'text' | 'number' | 'date' | 'select';
    editable: boolean;
    options?: string[];
}

interface DocumentCarouselProps {
    documents: GeneratedDocument[];
    onApprove: (documentId: string, fieldUpdates?: Record<string, any>) => void;
    onSkip: (documentId: string) => void;
    onRegenerate: (documentId: string) => void;
    onFinalize: (approvedDocumentIds: string[]) => void;
    onCancel?: () => void;
}

export function DocumentCarousel({
    documents,
    onApprove,
    onSkip,
    onRegenerate,
    onFinalize,
    onCancel,
}: DocumentCarouselProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [documentStates, setDocumentStates] = useState<Record<string, GeneratedDocument['status']>>({});
    const [fieldValues, setFieldValues] = useState<Record<string, Record<string, any>>>({});
    const [isEditing, setIsEditing] = useState(false);

    const currentDoc = documents[currentIndex];
    const currentStatus = documentStates[currentDoc?.id] || currentDoc?.status || 'draft';
    const currentFields = fieldValues[currentDoc?.id] || {};

    // Navigation
    const goToPrevious = () => setCurrentIndex(i => Math.max(0, i - 1));
    const goToNext = () => setCurrentIndex(i => Math.min(documents.length - 1, i + 1));
    const goToIndex = (index: number) => setCurrentIndex(index);

    // Handle field change
    const handleFieldChange = (fieldId: string, value: any) => {
        setFieldValues(prev => ({
            ...prev,
            [currentDoc.id]: {
                ...(prev[currentDoc.id] || {}),
                [fieldId]: value,
            },
        }));
    };

    // Handle approve
    const handleApprove = () => {
        setDocumentStates(prev => ({
            ...prev,
            [currentDoc.id]: 'approved',
        }));

        onApprove(currentDoc.id, fieldValues[currentDoc.id]);

        // Auto-advance to next
        if (currentIndex < documents.length - 1) {
            setCurrentIndex(currentIndex + 1);
        }

        setIsEditing(false);
    };

    // Handle skip
    const handleSkip = () => {
        setDocumentStates(prev => ({
            ...prev,
            [currentDoc.id]: 'skipped',
        }));

        onSkip(currentDoc.id);

        // Auto-advance
        if (currentIndex < documents.length - 1) {
            setCurrentIndex(currentIndex + 1);
        }
    };

    // Handle regenerate
    const handleRegenerate = () => {
        onRegenerate(currentDoc.id);
    };

    // Handle finalize
    const handleFinalize = () => {
        const approvedIds = documents
            .filter(doc => (documentStates[doc.id] || doc.status) === 'approved')
            .map(doc => doc.id);

        onFinalize(approvedIds);
    };

    // Count approved documents
    const approvedCount = documents.filter(
        doc => (documentStates[doc.id] || doc.status) === 'approved'
    ).length;

    if (!currentDoc) {
        return (
            <div className="document-carousel empty">
                <p>Hujjatlar mavjud emas</p>
            </div>
        );
    }

    return (
        <div className="document-carousel">
            {/* Header with progress */}
            <div className="carousel-header">
                <div className="progress-info">
                    <span className="current">
                        Hujjat {currentIndex + 1}
                    </span>
                    <span className="separator">/</span>
                    <span className="total">{documents.length}</span>
                </div>

                <div className="progress-dots">
                    {documents.map((doc, i) => {
                        const status = documentStates[doc.id] || doc.status || 'draft';
                        return (
                            <button
                                key={doc.id}
                                className={`progress-dot ${status} ${i === currentIndex ? 'active' : ''}`}
                                onClick={() => goToIndex(i)}
                                title={doc.template_name}
                            >
                                {status === 'approved' && '✓'}
                                {status === 'skipped' && '–'}
                            </button>
                        );
                    })}
                </div>

                <div className="approved-count">
                    <span className="count">{approvedCount}</span>
                    <span className="label">tasdiqlangan</span>
                </div>
            </div>

            {/* Document info */}
            <div className="document-info">
                <h3 className="document-title">{currentDoc.template_name}</h3>
                <div className="document-meta">
                    <span className={`status-badge ${currentStatus}`}>
                        {currentStatus === 'draft' && 'Ko\'rib chiqilmagan'}
                        {currentStatus === 'approved' && 'Tasdiqlangan'}
                        {currentStatus === 'skipped' && 'O\'tkazib yuborilgan'}
                    </span>
                    <span className="format-badge">{currentDoc.format.toUpperCase()}</span>
                    {currentDoc.pages > 1 && (
                        <span className="pages-info">{currentDoc.pages} sahifa</span>
                    )}
                </div>
            </div>

            {/* Main content area */}
            <div className="carousel-content">
                {/* Preview pane */}
                <div className="preview-pane">
                    <DocumentPreview
                        fileUrl={currentDoc.preview_url}
                        editable={false}
                    />
                </div>

                {/* Editable fields sidebar */}
                {currentDoc.editable_fields.length > 0 && (
                    <div className="fields-pane">
                        <div className="fields-header">
                            <h4>Maydonlar</h4>
                            <button
                                className={`edit-toggle ${isEditing ? 'active' : ''}`}
                                onClick={() => setIsEditing(!isEditing)}
                            >
                                {isEditing ? '✓ Tugatish' : '✏️ Tahrirlash'}
                            </button>
                        </div>

                        <div className="fields-list">
                            {currentDoc.editable_fields.map(field => (
                                <div key={field.field_id} className="field-item">
                                    <label className="field-label">{field.label}</label>

                                    {isEditing && field.editable ? (
                                        <FieldInput
                                            field={field}
                                            value={currentFields[field.field_id] ?? field.value}
                                            onChange={(value) => handleFieldChange(field.field_id, value)}
                                        />
                                    ) : (
                                        <div className="field-value">
                                            {currentFields[field.field_id] ?? field.value}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Navigation and actions */}
            <div className="carousel-footer">
                <div className="navigation-buttons">
                    <button
                        onClick={goToPrevious}
                        disabled={currentIndex === 0}
                        className="nav-btn prev"
                    >
                        ← Oldingi
                    </button>
                    <button
                        onClick={goToNext}
                        disabled={currentIndex === documents.length - 1}
                        className="nav-btn next"
                    >
                        Keyingi →
                    </button>
                </div>

                <div className="action-buttons">
                    <button onClick={handleSkip} className="action-btn skip">
                        O'tkazib yuborish
                    </button>
                    <button onClick={handleRegenerate} className="action-btn regenerate">
                        🔄 Qayta yaratish
                    </button>
                    <button
                        onClick={handleApprove}
                        className="action-btn approve"
                        disabled={currentStatus === 'approved'}
                    >
                        ✓ Tasdiqlash
                    </button>
                </div>
            </div>

            {/* Finalize button */}
            {approvedCount > 0 && (
                <div className="finalize-section">
                    <button onClick={handleFinalize} className="finalize-btn">
                        📥 {approvedCount} ta hujjatni yuklab olish
                    </button>
                    {onCancel && (
                        <button onClick={onCancel} className="cancel-all-btn">
                            Bekor qilish
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

// Field Input Component
interface FieldInputProps {
    field: EditableField;
    value: any;
    onChange: (value: any) => void;
}

function FieldInput({ field, value, onChange }: FieldInputProps) {
    switch (field.type) {
        case 'select':
            return (
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="field-input select"
                >
                    {field.options?.map(opt => (
                        <option key={opt} value={opt}>{opt}</option>
                    ))}
                </select>
            );

        case 'number':
            return (
                <input
                    type="number"
                    value={value}
                    onChange={(e) => onChange(parseFloat(e.target.value))}
                    className="field-input number"
                />
            );

        case 'date':
            return (
                <input
                    type="date"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="field-input date"
                />
            );

        default:
            return (
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="field-input text"
                />
            );
    }
}

export default DocumentCarousel;
