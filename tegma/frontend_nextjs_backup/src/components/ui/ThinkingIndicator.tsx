'use client';

import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

export default function ThinkingIndicator() {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-4xl mx-auto px-4 py-3"
        >
            <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dark-700 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                </div>

                <div className="bg-dark-800 rounded-2xl rounded-tl-sm px-4 py-3">
                    <div className="flex items-center gap-2">
                        <span className="text-dark-300">O'ylayapman</span>
                        <div className="thinking-dots flex gap-1">
                            <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                            <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                            <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
