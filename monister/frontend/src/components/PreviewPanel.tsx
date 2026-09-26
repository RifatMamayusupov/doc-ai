/**
 * Preview Panel Component - Real-time file preview with editing, download, and PDF export
 * Supports multiple file formats with format-specific renderers
 */

import { useState, useEffect, useRef } from 'react';
import mammoth from 'mammoth';
import html2canvas from 'html2canvas';
import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx';
import {
    X,
    Maximize2,
    Minimize2,
    FileSpreadsheet,
    FileText,
    Image,
    Video,
    File,
    Code,
    Download,
    Edit3,
    Save,
    XCircle,
    FileDown
} from 'lucide-react';
import { useMonisterStore } from '../stores/monisterStore';

interface PreviewPanelProps {
    onClose?: () => void;
}

export function PreviewPanel({ onClose }: PreviewPanelProps) {
    const [isMaximized, setIsMaximized] = useState(false);
    const [activeTab, setActiveTab] = useState<'preview' | 'code' | 'data'>('preview');
    const [docxHtml, setDocxHtml] = useState<string>('');
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState<string>('');
    const [isSaving, setIsSaving] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [excelData, setExcelData] = useState<string[][] | null>(null);
    const [editedExcelData, setEditedExcelData] = useState<string[][] | null>(null);
    const [excelSheets, setExcelSheets] = useState<string[]>([]);
    const [activeSheet, setActiveSheet] = useState<string>('');
    const [editingCell, setEditingCell] = useState<{ row: number, col: number } | null>(null);
    const editorRef = useRef<HTMLTextAreaElement>(null);
    const previewContentRef = useRef<HTMLDivElement>(null);
    const cellInputRef = useRef<HTMLInputElement>(null);

    const {
        previewData,
        previewType,
        previewOpen,
        setPreviewOpen,
        dataPreview,
    } = useMonisterStore();

    const handleClose = () => {
        setIsEditing(false);
        setEditContent('');
        setPreviewOpen(false);
        onClose?.();
    };

    // Helper to get URL (safe)
    const getUrl = (): string => {
        if (previewData && typeof previewData === 'object' && 'url' in previewData) {
            return String(previewData.url) || '';
        }
        return '';
    };

    // Helper to get filename
    const getFilename = (): string => {
        const url = getUrl();
        if (url) {
            return url.split('/').pop() || 'document';
        }
        return 'document';
    };

    // Helper to get content
    const getContent = (): string => {
        if (previewData && typeof previewData === 'object' && 'content' in previewData) {
            const content = previewData.content;
            if (typeof content === 'string') return content;
            return JSON.stringify(content, null, 2);
        }
        if (dataPreview?.data) return dataPreview.data;
        return '';
    };

    // Check if file type is editable (exclude images and videos)
    const isEditable = (): boolean => {
        const nonEditable = ['image', 'video', 'pdf'];
        return !nonEditable.includes(previewType || '');
    };

    // Load DOCX content
    useEffect(() => {
        const isDocx = previewType === 'docx' || previewType === 'word' ||
            (previewData && typeof previewData === 'object' && 'type' in previewData && (previewData as any).type === 'docx');

        if (isDocx) {
            const url = getUrl();
            if (url) {
                fetch(url)
                    .then(res => res.arrayBuffer())
                    .then(buffer => mammoth.convertToHtml({ arrayBuffer: buffer }))
                    .then(result => setDocxHtml(result.value))
                    .catch(err => console.error("Mammoth error", err));
            }
        }
    }, [previewData, previewType]);

    // Load Excel content
    useEffect(() => {
        const isExcel = previewType === 'excel' || previewType === 'spreadsheet' ||
            (previewData && typeof previewData === 'object' && 'type' in previewData &&
                ['excel', 'spreadsheet'].includes((previewData as any).type));

        if (isExcel) {
            const url = getUrl();
            if (url) {
                fetch(url)
                    .then(res => res.arrayBuffer())
                    .then(buffer => {
                        const workbook = XLSX.read(buffer, { type: 'array' });
                        const sheetNames = workbook.SheetNames;
                        setExcelSheets(sheetNames);

                        // Load first sheet by default
                        if (sheetNames.length > 0) {
                            const firstSheet = sheetNames[0];
                            setActiveSheet(firstSheet);
                            const worksheet = workbook.Sheets[firstSheet];
                            const data = XLSX.utils.sheet_to_json<string[]>(worksheet, { header: 1 });
                            setExcelData(data as string[][]);
                        }
                    })
                    .catch(err => console.error("Excel parse error:", err));
            }
        } else {
            // Clear excel data when switching to non-excel type
            setExcelData(null);
            setExcelSheets([]);
            setActiveSheet('');
        }
    }, [previewData, previewType]);

    // Start editing mode
    const handleStartEdit = () => {
        const isExcel = previewType === 'excel' || previewType === 'spreadsheet';

        if (isExcel && excelData) {
            // For Excel, create a deep copy of the data for editing
            setEditedExcelData(excelData.map(row => [...row]));
            setIsEditing(true);
        } else {
            // For other file types, use text editing
            const content = getContent();
            setEditContent(content);
            setIsEditing(true);

            // Focus editor after render
            setTimeout(() => {
                editorRef.current?.focus();
            }, 100);
        }
    };

    // Cancel editing
    const handleCancelEdit = () => {
        setIsEditing(false);
        setEditContent('');
        setEditedExcelData(null);
        setEditingCell(null);
    };

    // Update Excel cell value
    const handleCellChange = (rowIndex: number, colIndex: number, value: string) => {
        if (!editedExcelData) return;

        const newData = editedExcelData.map((row, i) => {
            if (i === rowIndex) {
                const newRow = [...row];
                // Ensure the row has enough columns
                while (newRow.length <= colIndex) {
                    newRow.push('');
                }
                newRow[colIndex] = value;
                return newRow;
            }
            return row;
        });
        setEditedExcelData(newData);
    };

    // Start editing a specific cell
    const handleCellClick = (rowIndex: number, colIndex: number) => {
        if (!isEditing) return;
        setEditingCell({ row: rowIndex, col: colIndex });
        // Focus the input after render
        setTimeout(() => {
            cellInputRef.current?.focus();
            cellInputRef.current?.select();
        }, 50);
    };

    // Finish editing cell (on blur or Enter)
    const handleCellBlur = () => {
        setEditingCell(null);
    };

    // Save edited content
    const handleSaveEdit = async () => {
        const isExcel = previewType === 'excel' || previewType === 'spreadsheet';

        if (isExcel && editedExcelData) {
            // For Excel, create a new workbook and download
            try {
                setIsSaving(true);

                // Create new workbook
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.aoa_to_sheet(editedExcelData);
                XLSX.utils.book_append_sheet(wb, ws, activeSheet || 'Sheet1');

                // Generate file
                const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
                const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

                // Download
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                const originalName = getFilename().replace(/\.[^/.]+$/, '');
                link.href = url;
                link.download = `${originalName}_edited.xlsx`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);

                // Update the displayed data with edited version
                setExcelData(editedExcelData);
                setIsEditing(false);
                setEditedExcelData(null);
                setEditingCell(null);

            } catch (error) {
                console.error('Excel save error:', error);
                alert("❌ Excel saqlashda xatolik yuz berdi");
            } finally {
                setIsSaving(false);
            }
        } else {
            // For other file types, upload to server
            const url = getUrl();
            if (!url) {
                alert("Fayl URL mavjud emas");
                return;
            }

            setIsSaving(true);

            try {
                const filename = url.split('/').pop() || 'file.txt';
                const blob = new Blob([editContent], { type: 'text/plain' });
                const formData = new FormData();
                formData.append('file', blob, filename);

                const token = localStorage.getItem('token');
                const response = await fetch('http://localhost:8000/api/upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                    },
                    body: formData,
                });

                if (response.ok) {
                    alert("✅ Fayl muvaffaqiyatli saqlandi!");
                    setIsEditing(false);

                    if (previewData && typeof previewData === 'object') {
                        useMonisterStore.getState().setPreviewData({
                            ...previewData,
                            content: editContent,
                        });
                    }
                } else {
                    throw new Error('Failed to save');
                }
            } catch (error) {
                console.error('Save error:', error);
                alert("❌ Saqlashda xatolik yuz berdi");
            } finally {
                setIsSaving(false);
            }
        }
    };

    // Download original file
    const handleDownload = () => {
        const url = getUrl();
        const content = getContent();

        if (url) {
            const link = document.createElement('a');
            link.href = url;
            link.download = url.split('/').pop() || 'download';
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else if (content) {
            const blob = new Blob([content], { type: 'text/plain' });
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = 'preview-content.txt';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);
        }
    };

    // Export to PDF - captures preview exactly as it looks
    const handleExportPDF = async () => {
        if (!previewContentRef.current) return;

        setIsExporting(true);

        try {
            const element = previewContentRef.current;

            // Create canvas from the preview content
            const canvas = await html2canvas(element, {
                scale: 2, // Higher quality
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff',
                allowTaint: true,
            });

            // Get canvas dimensions
            const imgWidth = 210; // A4 width in mm
            const pageHeight = 297; // A4 height in mm
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            // Create PDF
            const pdf = new jsPDF('p', 'mm', 'a4');

            // If content is longer than one page, add multiple pages
            let heightLeft = imgHeight;
            let position = 0;

            // Add first page
            pdf.addImage(
                canvas.toDataURL('image/png'),
                'PNG',
                0,
                position,
                imgWidth,
                imgHeight
            );
            heightLeft -= pageHeight;

            // Add additional pages if needed
            while (heightLeft > 0) {
                position = heightLeft - imgHeight;
                pdf.addPage();
                pdf.addImage(
                    canvas.toDataURL('image/png'),
                    'PNG',
                    0,
                    position,
                    imgWidth,
                    imgHeight
                );
                heightLeft -= pageHeight;
            }

            // Download PDF
            const filename = getFilename().replace(/\.[^/.]+$/, '') + '.pdf';
            pdf.save(filename);

        } catch (error) {
            console.error('PDF export error:', error);
            alert("❌ PDF yaratishda xatolik yuz berdi");
        } finally {
            setIsExporting(false);
        }
    };

    const getFileTypeIcon = (type: string) => {
        if (type.includes('spreadsheet') || type.includes('excel') || type.includes('csv')) {
            return <FileSpreadsheet size={20} />;
        }
        if (type.includes('pdf')) {
            return <FileText size={20} />;
        }
        if (type.includes('word') || type.includes('docx')) {
            return <FileText size={20} />;
        }
        if (type.startsWith('image')) {
            return <Image size={20} />;
        }
        if (type.startsWith('video')) {
            return <Video size={20} />;
        }
        if (type.includes('json') || type.includes('code')) {
            return <Code size={20} />;
        }
        return <File size={20} />;
    };

    const renderEditor = () => {
        return (
            <div className="preview-editor">
                <textarea
                    ref={editorRef}
                    className="editor-textarea"
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    spellCheck={false}
                />
            </div>
        );
    };

    const renderContent = () => {
        const isExcel = previewType === 'excel' || previewType === 'spreadsheet';

        // Show text editor if in editing mode (but NOT for Excel - Excel has inline editing)
        if (isEditing && !isExcel) {
            return renderEditor();
        }

        if (!previewData && !dataPreview) {
            return (
                <div className="preview-empty">
                    <File size={48} />
                    <p>Ko'rish uchun fayl tanlanmagan</p>
                    <span className="hint">Fayl yuklang yoki agent orqali yarating</span>
                </div>
            );
        }

        // Render based on preview type
        switch (previewType) {
            case 'image':
                return (
                    <div className="preview-image">
                        <img src={getUrl()} alt="Preview" />
                    </div>
                );

            case 'video':
                return (
                    <div className="preview-video">
                        <video controls src={getUrl()}>
                            Your browser does not support video.
                        </video>
                    </div>
                );

            case 'pdf':
                return (
                    <div className="preview-pdf">
                        <iframe
                            src={getUrl()}
                            title="PDF Preview"
                            width="100%"
                            height="100%"
                        />
                    </div>
                );

            case 'word':
            case 'docx':
                return (
                    <div className="preview-docx">
                        <div
                            className="docx-content typo"
                            dangerouslySetInnerHTML={{ __html: docxHtml }}
                        />
                    </div>
                );

            case 'html':
                return (
                    <div className="preview-html">
                        <iframe
                            src={getUrl()}
                            title="HTML Preview"
                            width="100%"
                            height="100%"
                            style={{ border: 'none', background: 'white' }}
                        />
                    </div>
                );

            case 'spreadsheet':
            case 'excel':
                return (
                    <div className="preview-spreadsheet">
                        {/* Sheet tabs */}
                        {excelSheets.length > 1 && (
                            <div className="sheet-tabs">
                                {excelSheets.map((sheet) => (
                                    <button
                                        key={sheet}
                                        className={`sheet-tab ${activeSheet === sheet ? 'active' : ''}`}
                                        onClick={() => {
                                            setActiveSheet(sheet);
                                            // Reload sheet data
                                            const url = getUrl();
                                            if (url) {
                                                fetch(url)
                                                    .then(res => res.arrayBuffer())
                                                    .then(buffer => {
                                                        const workbook = XLSX.read(buffer, { type: 'array' });
                                                        const worksheet = workbook.Sheets[sheet];
                                                        const data = XLSX.utils.sheet_to_json<string[]>(worksheet, { header: 1 });
                                                        setExcelData(data as string[][]);
                                                    });
                                            }
                                        }}
                                    >
                                        {sheet}
                                    </button>
                                ))}
                            </div>
                        )}

                        {(() => {
                            // Use editedExcelData when editing, otherwise use excelData
                            const displayData = isEditing && editedExcelData ? editedExcelData : excelData;

                            if (!displayData || displayData.length === 0) {
                                return (
                                    <div className="spreadsheet-placeholder">
                                        <FileSpreadsheet size={48} />
                                        <p>Excel yuklanmoqda...</p>
                                    </div>
                                );
                            }

                            return (
                                <div className={`excel-table-container ${isEditing ? 'editing' : ''}`}>
                                    {isEditing && (
                                        <div className="excel-edit-notice">
                                            ✏️ Tahrirlash rejimi - hujayralarni bosib o'zgartiring
                                        </div>
                                    )}
                                    <table className="excel-table">
                                        <thead>
                                            {displayData[0] && (
                                                <tr>
                                                    <th className="row-number">#</th>
                                                    {displayData[0].map((cell, j) => (
                                                        <th
                                                            key={j}
                                                            className={isEditing ? 'editable-header' : ''}
                                                            onClick={() => isEditing && handleCellClick(0, j)}
                                                        >
                                                            {editingCell?.row === 0 && editingCell?.col === j ? (
                                                                <input
                                                                    ref={cellInputRef}
                                                                    type="text"
                                                                    className="cell-input"
                                                                    value={cell !== undefined ? String(cell) : ''}
                                                                    onChange={(e) => handleCellChange(0, j, e.target.value)}
                                                                    onBlur={handleCellBlur}
                                                                    onKeyDown={(e) => {
                                                                        if (e.key === 'Enter') handleCellBlur();
                                                                        if (e.key === 'Escape') {
                                                                            handleCellBlur();
                                                                        }
                                                                    }}
                                                                />
                                                            ) : (
                                                                cell !== undefined ? String(cell) : ''
                                                            )}
                                                        </th>
                                                    ))}
                                                </tr>
                                            )}
                                        </thead>
                                        <tbody>
                                            {displayData.slice(1, 100).map((row, i) => {
                                                const actualRowIndex = i + 1;
                                                return (
                                                    <tr key={i}>
                                                        <td className="row-number">{i + 2}</td>
                                                        {row.map((cell, j) => (
                                                            <td
                                                                key={j}
                                                                className={isEditing ? 'editable-cell' : ''}
                                                                onClick={() => handleCellClick(actualRowIndex, j)}
                                                            >
                                                                {editingCell?.row === actualRowIndex && editingCell?.col === j ? (
                                                                    <input
                                                                        ref={cellInputRef}
                                                                        type="text"
                                                                        className="cell-input"
                                                                        value={cell !== undefined ? String(cell) : ''}
                                                                        onChange={(e) => handleCellChange(actualRowIndex, j, e.target.value)}
                                                                        onBlur={handleCellBlur}
                                                                        onKeyDown={(e) => {
                                                                            if (e.key === 'Enter') {
                                                                                handleCellBlur();
                                                                                // Move to next row
                                                                                if (actualRowIndex < displayData.length - 1) {
                                                                                    handleCellClick(actualRowIndex + 1, j);
                                                                                }
                                                                            }
                                                                            if (e.key === 'Tab') {
                                                                                e.preventDefault();
                                                                                handleCellBlur();
                                                                                // Move to next column
                                                                                if (j < row.length - 1) {
                                                                                    handleCellClick(actualRowIndex, j + 1);
                                                                                }
                                                                            }
                                                                            if (e.key === 'Escape') handleCellBlur();
                                                                        }}
                                                                    />
                                                                ) : (
                                                                    cell !== undefined ? String(cell) : ''
                                                                )}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                    {displayData.length > 100 && (
                                        <div className="excel-overflow-notice">
                                            + {displayData.length - 100} ta qator ko'rsatilmagan
                                        </div>
                                    )}
                                </div>
                            );
                        })()}
                    </div>
                );

            case 'code':
            case 'json':
                return (
                    <div className="preview-code">
                        <pre>
                            <code>{getContent()}</code>
                        </pre>
                    </div>
                );

            case 'audio':
                return (
                    <div className="preview-audio">
                        <audio controls src={getUrl()}>
                            Your browser does not support audio.
                        </audio>
                    </div>
                );

            case 'archive':
            case 'presentation':
            case 'file':
                return (
                    <div className="preview-file">
                        <File size={64} />
                        <p>{getFilename()}</p>
                        <span>Bu fayl turini ko'rish imkoni yo'q</span>
                        <button className="download-btn" onClick={handleDownload}>
                            <Download size={16} /> Yuklab olish
                        </button>
                    </div>
                );

            case 'text':
            default:
                return (
                    <div className="preview-text">
                        <div className="text-content">
                            {getContent() || 'Ko\'rish mavjud emas'}
                        </div>
                    </div>
                );
        }
    };

    if (!previewOpen) return null;

    return (
        <div className={`preview-panel ${isMaximized ? 'maximized' : ''}`}>
            <div className="preview-header">
                <div className="preview-title">
                    {getFileTypeIcon(previewType || 'file')}
                    <span>Ko'rish</span>
                    {getUrl() && (
                        <span className="preview-filename">
                            - {getFilename()}
                        </span>
                    )}
                </div>
                <div className="preview-actions">
                    {/* Edit button (only for editable types) */}
                    {isEditable() && !isEditing && (previewData || dataPreview) && (
                        <button
                            className="preview-action edit"
                            onClick={handleStartEdit}
                            title="Tahrirlash"
                        >
                            <Edit3 size={16} />
                        </button>
                    )}

                    {/* Save/Cancel buttons (when editing) */}
                    {isEditing && (
                        <>
                            <button
                                className="preview-action save"
                                onClick={handleSaveEdit}
                                disabled={isSaving}
                                title="Saqlash"
                            >
                                <Save size={16} />
                            </button>
                            <button
                                className="preview-action cancel"
                                onClick={handleCancelEdit}
                                title="Bekor qilish"
                            >
                                <XCircle size={16} />
                            </button>
                        </>
                    )}

                    {/* PDF Export button - captures preview as PDF */}
                    {!isEditing && (previewData || dataPreview) && previewType !== 'pdf' && (
                        <button
                            className="preview-action pdf-export"
                            onClick={handleExportPDF}
                            disabled={isExporting}
                            title="PDF sifatida saqlash"
                        >
                            <FileDown size={16} />
                        </button>
                    )}

                    {/* Download button */}
                    {(getUrl() || getContent()) && !isEditing && (
                        <button
                            className="preview-action download"
                            onClick={handleDownload}
                            title="Asl faylni yuklab olish"
                        >
                            <Download size={16} />
                        </button>
                    )}

                    {/* Maximize/Minimize */}
                    <button
                        className="preview-action"
                        onClick={() => setIsMaximized(!isMaximized)}
                        title={isMaximized ? "Kichiklashtirish" : "Kattalashtirish"}
                    >
                        {isMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                    </button>

                    {/* Close */}
                    <button
                        className="preview-action close"
                        onClick={handleClose}
                        title="Yopish"
                    >
                        <X size={16} />
                    </button>
                </div>
            </div>

            <div className="preview-tabs" style={{ display: 'none' }}>
                <button
                    className={`preview-tab ${activeTab === 'preview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('preview')}
                >
                    Ko'rish
                </button>
            </div>

            <div className="preview-content" ref={previewContentRef}>
                {renderContent()}
            </div>
        </div>
    );
}
