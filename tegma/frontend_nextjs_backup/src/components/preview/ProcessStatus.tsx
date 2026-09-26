'use client';

import { motion } from 'framer-motion';
import {
    FileSpreadsheet,
    FileText,
    Image,
    Code,
    CheckCircle,
    XCircle,
    Loader2
} from 'lucide-react';
import { ProcessStatus as ProcessStatusType } from '@/lib/store';

interface ProcessStatusProps {
    status: ProcessStatusType;
}

export default function ProcessStatus({ status }: ProcessStatusProps) {
    const getIcon = () => {
        switch (status.type) {
            case 'excel':
                return <FileSpreadsheet className="w-5 h-5 text-green-400" />;
            case 'pdf':
                return <FileText className="w-5 h-5 text-red-400" />;
            case 'image':
                return <Image className="w-5 h-5 text-blue-400" />;
            case 'code':
                return <Code className="w-5 h-5 text-purple-400" />;
            default:
                return <FileText className="w-5 h-5 text-dark-400" />;
        }
    };

    const getStatusIcon = () => {
        switch (status.status) {
            case 'running':
            case 'processing':
                return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
            case 'success':
            case 'complete':
                return <CheckCircle className="w-4 h-4 text-green-400" />;
            case 'error':
                return <XCircle className="w-4 h-4 text-red-400" />;
            default:
                return null;
        }
    };

    const isRunning = ['running', 'processing'].includes(status.status);

    return (
        <div className="space-y-4">
            {/* Status card */}
            <div className="bg-dark-800 rounded-xl p-4 border border-dark-600">
                {/* Header */}
                <div className="flex items-center gap-3 mb-4">
                    {getIcon()}
                    <div className="flex-1">
                        <h4 className="font-medium text-white capitalize">
                            {status.type} qayta ishlash
                        </h4>
                        <div className="flex items-center gap-2 mt-0.5">
                            {getStatusIcon()}
                            <span className="text-xs text-dark-400 capitalize">
                                {status.status}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="relative h-2 bg-dark-700 rounded-full overflow-hidden mb-2">
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${status.progress}%` }}
                        className={`absolute left-0 top-0 h-full rounded-full ${status.status === 'error'
                                ? 'bg-red-500'
                                : status.status === 'complete' || status.status === 'success'
                                    ? 'bg-green-500'
                                    : 'bg-primary'
                            }`}
                    />
                    {isRunning && (
                        <motion.div
                            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
                            animate={{ x: ['-100%', '100%'] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                        />
                    )}
                </div>

                {/* Progress text */}
                <div className="flex items-center justify-between text-xs">
                    <span className="text-dark-400">{status.message}</span>
                    <span className="text-dark-300">{status.progress}%</span>
                </div>
            </div>

            {/* Preview (if available) */}
            {status.preview_url && (
                <div className="bg-dark-800 rounded-xl overflow-hidden border border-dark-600">
                    <div className="p-3 border-b border-dark-600">
                        <span className="text-sm text-dark-300">Ko'rish</span>
                    </div>
                    <div className="p-4">
                        <img
                            src={status.preview_url}
                            alt="Preview"
                            className="w-full rounded-lg"
                        />
                    </div>
                </div>
            )}

            {/* Output display for code execution */}
            {status.type === 'code' && status.message && status.message.length > 20 && (
                <div className="bg-dark-950 rounded-xl p-4 border border-dark-700">
                    <p className="text-xs text-dark-400 mb-2">Output:</p>
                    <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                        {status.message}
                    </pre>
                </div>
            )}
        </div>
    );
}
