/**
 * Universal Document Preview Component
 * 
 * Supports all document types:
 * - Images (PNG, JPG, GIF, WebP, SVG)
 * - PDF (with page navigation)
 * - Word documents (rendered as HTML)
 * - Excel/CSV (rendered as tables)
 * - PowerPoint (slide navigation)
 * - Text/Code (with syntax highlighting)
 * - JSON (pretty printed)
 */

import React, { useState, useEffect, useCallback } from 'react';
import './DocumentPreview.css';

interface PreviewData {
  success: boolean;
  preview_type: 'image' | 'pdf' | 'html' | 'text' | 'json' | 'binary' | 'error';
  content: string | null;
  content_url: string | null;
  pages: number;
  metadata: Record<string, any>;
  error: string | null;
}

interface DocumentPreviewProps {
  filePath?: string;
  fileId?: string;
  fileUrl?: string;
  initialPage?: number;
  maxWidth?: number;
  maxHeight?: number;
  editable?: boolean;
  onEdit?: (content: any) => void;
  onSave?: (content: any) => Promise<boolean>;
  className?: string;
}

export function DocumentPreview({
  filePath,
  fileId,
  fileUrl,
  initialPage = 1,
  maxWidth = 1200,
  maxHeight = 1600,
  editable = false,
  onEdit,
  onSave,
  className = '',
}: DocumentPreviewProps) {
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState<string>('');
  const [zoom, setZoom] = useState(100);

  // Fetch preview
  const fetchPreview = useCallback(async (page: number) => {
    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch('/api/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          file_path: filePath,
          file_id: fileId,
          page,
          max_width: maxWidth,
          max_height: maxHeight,
        }),
      });

      if (!response.ok) {
        throw new Error('Preview generation failed');
      }

      const data: PreviewData = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Preview failed');
      }

      setPreview(data);
      
      // Set edit content for text types
      if (data.preview_type === 'text' || data.preview_type === 'json') {
        setEditContent(data.content || '');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [filePath, fileId, maxWidth, maxHeight]);

  useEffect(() => {
    if (filePath || fileId) {
      fetchPreview(currentPage);
    }
  }, [filePath, fileId, currentPage, fetchPreview]);

  // Handle page navigation
  const goToPage = (page: number) => {
    if (preview && page >= 1 && page <= preview.pages) {
      setCurrentPage(page);
    }
  };

  // Handle zoom
  const handleZoomIn = () => setZoom(z => Math.min(z + 25, 200));
  const handleZoomOut = () => setZoom(z => Math.max(z - 25, 50));
  const handleZoomReset = () => setZoom(100);

  // Handle edit save
  const handleSave = async () => {
    if (onSave) {
      const success = await onSave({
        type: preview?.preview_type === 'json' ? 'json' : 'text',
        content: editContent,
      });
      
      if (success) {
        setIsEditing(false);
        fetchPreview(currentPage);
      }
    }
  };

  // Render based on preview type
  const renderPreview = () => {
    if (!preview) return null;

    switch (preview.preview_type) {
      case 'image':
        return (
          <div className="preview-image-container" style={{ transform: `scale(${zoom / 100})` }}>
            <img 
              src={preview.content || preview.content_url || ''} 
              alt="Document preview"
              className="preview-image"
            />
          </div>
        );

      case 'pdf':
        return (
          <div className="preview-pdf-container" style={{ transform: `scale(${zoom / 100})` }}>
            <img 
              src={preview.content || ''} 
              alt={`Page ${currentPage}`}
              className="preview-pdf-page"
            />
          </div>
        );

      case 'html':
        return (
          <div 
            className="preview-html-container"
            style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
            dangerouslySetInnerHTML={{ __html: preview.content || '' }}
          />
        );

      case 'text':
        return isEditing ? (
          <textarea
            className="preview-text-editor"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            spellCheck={false}
          />
        ) : (
          <pre className="preview-text-container" style={{ fontSize: `${zoom}%` }}>
            {preview.content}
          </pre>
        );

      case 'json':
        return isEditing ? (
          <textarea
            className="preview-json-editor"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            spellCheck={false}
          />
        ) : (
          <pre className="preview-json-container" style={{ fontSize: `${zoom}%` }}>
            {preview.content}
          </pre>
        );

      case 'binary':
        return (
          <div className="preview-binary">
            <div className="binary-icon">📄</div>
            <p>Binary fayl - preview mavjud emas</p>
            <p className="binary-size">
              {preview.metadata?.size ? formatFileSize(preview.metadata.size) : 'Unknown size'}
            </p>
            {preview.metadata?.mime_type && (
              <p className="binary-type">{preview.metadata.mime_type}</p>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="preview-error">
            <div className="error-icon">⚠️</div>
            <p>{preview.error || 'Preview failed'}</p>
          </div>
        );

      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className={`document-preview loading ${className}`}>
        <div className="preview-spinner"></div>
        <p>Preview yuklanmoqda...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`document-preview error ${className}`}>
        <div className="error-icon">❌</div>
        <p>{error}</p>
        <button onClick={() => fetchPreview(currentPage)}>Qayta urinish</button>
      </div>
    );
  }

  return (
    <div className={`document-preview ${className}`}>
      {/* Toolbar */}
      <div className="preview-toolbar">
        <div className="toolbar-left">
          {/* Navigation for multi-page docs */}
          {preview && preview.pages > 1 && (
            <div className="page-navigation">
              <button 
                onClick={() => goToPage(currentPage - 1)}
                disabled={currentPage <= 1}
                title="Oldingi sahifa"
              >
                ←
              </button>
              <span className="page-info">
                {currentPage} / {preview.pages}
              </span>
              <button 
                onClick={() => goToPage(currentPage + 1)}
                disabled={currentPage >= preview.pages}
                title="Keyingi sahifa"
              >
                →
              </button>
            </div>
          )}
        </div>

        <div className="toolbar-center">
          {/* Zoom controls */}
          <div className="zoom-controls">
            <button onClick={handleZoomOut} title="Kichiklashtirish">−</button>
            <span className="zoom-level">{zoom}%</span>
            <button onClick={handleZoomIn} title="Kattalashtirish">+</button>
            <button onClick={handleZoomReset} title="Reset">↺</button>
          </div>
        </div>

        <div className="toolbar-right">
          {/* Edit controls */}
          {editable && (preview?.preview_type === 'text' || preview?.preview_type === 'json') && (
            <>
              {isEditing ? (
                <>
                  <button onClick={handleSave} className="save-btn">
                    💾 Saqlash
                  </button>
                  <button onClick={() => setIsEditing(false)} className="cancel-btn">
                    ✕ Bekor
                  </button>
                </>
              ) : (
                <button onClick={() => setIsEditing(true)} className="edit-btn">
                  ✏️ Tahrirlash
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Preview content */}
      <div className="preview-content">
        {renderPreview()}
      </div>

      {/* Metadata footer */}
      {preview?.metadata && Object.keys(preview.metadata).length > 0 && (
        <div className="preview-footer">
          {preview.metadata.lines && (
            <span>{preview.metadata.lines} qator</span>
          )}
          {preview.metadata.language && (
            <span className="language-badge">{preview.metadata.language}</span>
          )}
          {preview.metadata.sheets && (
            <span>{preview.metadata.sheets} sheet</span>
          )}
        </div>
      )}
    </div>
  );
}

// Helper function
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export default DocumentPreview;
