'use client';

import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { User, Bot, Wrench } from 'lucide-react';
import { Message } from '@/lib/store';

interface MessageListProps {
    messages: Message[];
    streamingContent: string;
    isStreaming: boolean;
}

export default function MessageList({
    messages,
    streamingContent,
    isStreaming,
}: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamingContent]);

    return (
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
            {messages.map((message, index) => (
                <MessageBubble
                    key={message.id}
                    message={message}
                    streamingContent={message.isStreaming ? streamingContent : undefined}
                    isNew={index === messages.length - 1}
                />
            ))}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
        </div>
    );
}

function MessageBubble({
    message,
    streamingContent,
    isNew,
}: {
    message: Message;
    streamingContent?: string;
    isNew?: boolean;
}) {
    const isUser = message.role === 'user';
    const isTool = message.role === 'tool';
    const displayContent = streamingContent || message.content;

    return (
        <motion.div
            initial={isNew ? { opacity: 0, y: 10 } : false}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}
        >
            {/* Avatar */}
            <div
                className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser
                    ? 'bg-primary/20'
                    : isTool
                        ? 'bg-yellow-500/20'
                        : 'bg-dark-700'
                    }`}
            >
                {isUser ? (
                    <User className="w-4 h-4 text-primary" />
                ) : isTool ? (
                    <Wrench className="w-4 h-4 text-yellow-500" />
                ) : (
                    <Bot className="w-4 h-4 text-white" />
                )}
            </div>

            {/* Content */}
            <div
                className={`flex-1 max-w-[80%] ${isUser ? 'text-right' : 'text-left'
                    }`}
            >
                <div
                    className={`inline-block px-4 py-3 rounded-2xl ${isUser
                        ? 'bg-primary text-white rounded-tr-sm'
                        : isTool
                            ? 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-100 rounded-tl-sm'
                            : 'bg-dark-800 text-white rounded-tl-sm'
                        }`}
                >
                    {isUser ? (
                        <p className="whitespace-pre-wrap">{displayContent}</p>
                    ) : (
                        <div className="prose prose-invert prose-sm max-w-none">
                            <ReactMarkdown>{displayContent}</ReactMarkdown>
                        </div>
                    )}

                    {/* Streaming cursor */}
                    {streamingContent && (
                        <span className="inline-block w-2 h-4 bg-primary ml-1 animate-pulse" />
                    )}
                </div>

                {/* Metadata */}
                {message.message_metadata && (
                    <div className="mt-2 text-xs text-dark-400">
                        {message.message_metadata.tool_name && (
                            <span className="bg-dark-700 px-2 py-0.5 rounded">
                                {message.message_metadata.tool_name}
                            </span>
                        )}
                    </div>
                )}
            </div>
        </motion.div>
    );
}
