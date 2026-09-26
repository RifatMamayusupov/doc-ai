'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    MessageSquarePlus,
    Settings,
    CreditCard,
    LogOut,
    ChevronLeft,
    ChevronRight,
    Search,
    MoreVertical,
    Pin,
    Trash2
} from 'lucide-react';
import { Chat, User } from '@/lib/store';
import { formatDistanceToNow } from 'date-fns';

interface ChatSidebarProps {
    chats: Chat[];
    currentChatId: string | null;
    onSelectChat: (id: string) => void;
    onNewChat: () => void;
    user: User | null;
    onLogout: () => void;
    isOpen: boolean;
}

export default function ChatSidebar({
    chats,
    currentChatId,
    onSelectChat,
    onNewChat,
    user,
    onLogout,
    isOpen,
}: ChatSidebarProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [menuOpen, setMenuOpen] = useState<string | null>(null);

    const filteredChats = chats.filter((chat) =>
        chat.title.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const pinnedChats = filteredChats.filter((c) => c.is_pinned);
    const regularChats = filteredChats.filter((c) => !c.is_pinned);

    return (
        <motion.aside
            initial={false}
            animate={{ width: isOpen ? 280 : 0 }}
            className="bg-dark-900 border-r border-dark-700 flex flex-col overflow-hidden"
        >
            {/* Header */}
            <div className="p-4 border-b border-dark-700">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 btn-primary"
                >
                    <MessageSquarePlus className="w-5 h-5" />
                    <span>Yangi Chat</span>
                </button>
            </div>

            {/* Search */}
            <div className="p-3">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
                    <input
                        type="text"
                        placeholder="Qidirish..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="input w-full pl-10 py-2 text-sm"
                    />
                </div>
            </div>

            {/* Chat list */}
            <div className="flex-1 overflow-y-auto">
                {/* Pinned chats */}
                {pinnedChats.length > 0 && (
                    <div className="px-3 py-2">
                        <p className="text-xs text-dark-400 uppercase font-medium mb-2">
                            Muhim
                        </p>
                        {pinnedChats.map((chat) => (
                            <ChatItem
                                key={chat.id}
                                chat={chat}
                                isActive={chat.id === currentChatId}
                                onSelect={() => onSelectChat(chat.id)}
                                menuOpen={menuOpen === chat.id}
                                onMenuToggle={() => setMenuOpen(menuOpen === chat.id ? null : chat.id)}
                            />
                        ))}
                    </div>
                )}

                {/* Regular chats */}
                <div className="px-3 py-2">
                    {pinnedChats.length > 0 && (
                        <p className="text-xs text-dark-400 uppercase font-medium mb-2">
                            Barcha Chatlar
                        </p>
                    )}
                    {regularChats.map((chat) => (
                        <ChatItem
                            key={chat.id}
                            chat={chat}
                            isActive={chat.id === currentChatId}
                            onSelect={() => onSelectChat(chat.id)}
                            menuOpen={menuOpen === chat.id}
                            onMenuToggle={() => setMenuOpen(menuOpen === chat.id ? null : chat.id)}
                        />
                    ))}
                </div>

                {filteredChats.length === 0 && (
                    <div className="text-center py-8 text-dark-400">
                        <p>Chatlar topilmadi</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="border-t border-dark-700 p-3 space-y-1">
                <button className="w-full flex items-center gap-3 px-3 py-2 text-dark-300 hover:text-white hover:bg-dark-800 rounded-lg transition-colors">
                    <Settings className="w-4 h-4" />
                    <span className="text-sm">Sozlamalar</span>
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2 text-dark-300 hover:text-white hover:bg-dark-800 rounded-lg transition-colors">
                    <CreditCard className="w-4 h-4" />
                    <span className="text-sm">Narxlar</span>
                </button>

                {/* User info */}
                <div className="flex items-center justify-between pt-3 border-t border-dark-700 mt-2">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                            <span className="text-primary text-sm font-medium">
                                {user?.username?.[0]?.toUpperCase() || 'U'}
                            </span>
                        </div>
                        <span className="text-sm text-white truncate max-w-[120px]">
                            {user?.username || 'User'}
                        </span>
                    </div>
                    <button
                        onClick={onLogout}
                        className="p-2 text-dark-400 hover:text-red-400 transition-colors"
                    >
                        <LogOut className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </motion.aside>
    );
}

// Chat item component
function ChatItem({
    chat,
    isActive,
    onSelect,
    menuOpen,
    onMenuToggle,
}: {
    chat: Chat;
    isActive: boolean;
    onSelect: () => void;
    menuOpen: boolean;
    onMenuToggle: () => void;
}) {
    return (
        <div className="relative group">
            <button
                onClick={onSelect}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors mb-1 ${isActive
                        ? 'bg-primary/20 text-primary'
                        : 'text-dark-300 hover:bg-dark-800 hover:text-white'
                    }`}
            >
                <div className="flex items-center justify-between">
                    <span className="truncate text-sm flex-1">{chat.title}</span>
                    {chat.is_pinned && <Pin className="w-3 h-3 text-primary flex-shrink-0" />}
                </div>
                <p className="text-xs text-dark-500 mt-0.5">
                    {formatDistanceToNow(new Date(chat.updated_at), { addSuffix: true })}
                </p>
            </button>

            {/* Menu button */}
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    onMenuToggle();
                }}
                className="absolute right-2 top-2 p-1 opacity-0 group-hover:opacity-100 text-dark-400 hover:text-white transition-opacity"
            >
                <MoreVertical className="w-4 h-4" />
            </button>

            {/* Dropdown menu */}
            <AnimatePresence>
                {menuOpen && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="absolute right-0 top-8 z-10 bg-dark-800 border border-dark-600 rounded-lg shadow-xl py-1 min-w-[120px]"
                    >
                        <button className="w-full px-3 py-2 text-left text-sm text-dark-300 hover:bg-dark-700 hover:text-white flex items-center gap-2">
                            <Pin className="w-4 h-4" />
                            <span>{chat.is_pinned ? 'Olib tashlash' : 'Muhim qilish'}</span>
                        </button>
                        <button className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 flex items-center gap-2">
                            <Trash2 className="w-4 h-4" />
                            <span>O'chirish</span>
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
