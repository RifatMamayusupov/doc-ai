'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Edit, Check, ChevronDown } from 'lucide-react';
import { useUIStore } from '@/lib/store';
import TemplateDropdown from './TemplateDropdown';
import ProcessStatus from './ProcessStatus';

interface PreviewPanelProps {
    isOpen: boolean;
}

export default function PreviewPanel({ isOpen }: PreviewPanelProps) {
    const {
        suggestedTemplates,
        processStatus,
        hitlRequest,
        setPreviewPanelOpen,
        setSuggestedTemplates,
        setHITLRequest,
    } = useUIStore();

    const handleClose = () => {
        setPreviewPanelOpen(false);
        setSuggestedTemplates([]);
        setHITLRequest(null);
    };

    const handleHITLApprove = () => {
        // Will be connected to wsClient
        setHITLRequest(null);
    };

    const handleHITLReject = () => {
        setHITLRequest(null);
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.aside
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 400, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="bg-dark-900 border-l border-dark-700 flex flex-col overflow-hidden"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b border-dark-700">
                        <h3 className="font-semibold text-white">
                            {suggestedTemplates.length > 0
                                ? 'Shablonlar'
                                : processStatus
                                    ? 'Jarayon'
                                    : hitlRequest
                                        ? 'Tasdiqlash'
                                        : 'Preview'}
                        </h3>
                        <button
                            onClick={handleClose}
                            className="p-1 text-dark-400 hover:text-white transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-4">
                        {/* Templates */}
                        {suggestedTemplates.length > 0 && (
                            <TemplateDropdown templates={suggestedTemplates} />
                        )}

                        {/* Process status */}
                        {processStatus && <ProcessStatus status={processStatus} />}

                        {/* HITL Request */}
                        {hitlRequest && (
                            <div className="space-y-4">
                                <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
                                    <div className="flex items-center gap-2 mb-3">
                                        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
                                        <span className="text-sm font-medium text-yellow-400">
                                            Tasdiqlash kerak
                                        </span>
                                    </div>

                                    <h4 className="font-medium text-white mb-2">
                                        {hitlRequest.tool_name}
                                    </h4>
                                    <p className="text-sm text-dark-300 mb-4">
                                        {hitlRequest.description}
                                    </p>

                                    <div className="flex gap-2">
                                        <button
                                            onClick={handleHITLApprove}
                                            className="flex-1 flex items-center justify-center gap-2 bg-primary hover:bg-primary-hover text-white py-2 rounded-lg transition-colors"
                                        >
                                            <Check className="w-4 h-4" />
                                            <span>Tasdiqlash</span>
                                        </button>
                                        <button
                                            onClick={handleHITLReject}
                                            className="flex-1 flex items-center justify-center gap-2 bg-dark-700 hover:bg-dark-600 text-white py-2 rounded-lg transition-colors"
                                        >
                                            <X className="w-4 h-4" />
                                            <span>Bekor qilish</span>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer with actions */}
                    {(suggestedTemplates.length > 0 || processStatus?.status === 'complete') && (
                        <div className="p-4 border-t border-dark-700 space-y-2">
                            <button className="w-full flex items-center justify-center gap-2 btn-primary">
                                <Download className="w-4 h-4" />
                                <span>Yuklab olish</span>
                            </button>
                            <button className="w-full flex items-center justify-center gap-2 btn-secondary">
                                <Edit className="w-4 h-4" />
                                <span>Tahrirlash</span>
                            </button>
                        </div>
                    )}
                </motion.aside>
            )}
        </AnimatePresence>
    );
}
