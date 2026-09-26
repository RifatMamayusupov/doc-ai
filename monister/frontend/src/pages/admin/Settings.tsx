/**
 * Admin Settings Page — Platform konfiguratsiya
 * Telegram bot, soha modullari, agent sozlamalari
 */

import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Send, RefreshCw, Check, X, Bot, Cpu, Building2 } from 'lucide-react';

interface TelegramConfig {
    bot_token: string;
    default_caption: string;
    enabled: boolean;
}

interface AgentConfig {
    model_name: string;
    auto_approve: boolean;
    max_recursion: number;
    system_prompt_override: string;
}

interface IndustryItem {
    id: string;
    name: string;
    description: string;
    document_count: number;
    enabled: boolean;
}

export default function AdminSettings() {
    const [activeTab, setActiveTab] = useState<'telegram' | 'industries' | 'agent'>('telegram');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    // Telegram state
    const [telegramConfig, setTelegramConfig] = useState<TelegramConfig>({
        bot_token: '',
        default_caption: 'Monister AI orqali yuborildi',
        enabled: false,
    });
    const [botInfo, setBotInfo] = useState<{ bot_name?: string; bot_username?: string } | null>(null);

    // Agent state
    const [agentConfig, setAgentConfig] = useState<AgentConfig>({
        model_name: '',
        auto_approve: false,
        max_recursion: 50,
        system_prompt_override: '',
    });

    // Industries state
    const [industries, setIndustries] = useState<IndustryItem[]>([]);

    const token = localStorage.getItem('token');
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };

    // Load config on mount
    useEffect(() => {
        loadConfig();
        loadIndustries();
    }, []);

    const loadConfig = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/admin/config', { headers });
            if (res.ok) {
                const data = await res.json();
                if (data.config?.telegram) {
                    setTelegramConfig(prev => ({
                        ...prev,
                        ...data.config.telegram,
                        bot_token: '', // Don't load token — show masked
                    }));
                }
                if (data.config?.agent) {
                    setAgentConfig(prev => ({ ...prev, ...data.config.agent }));
                }
            }
        } catch (err) {
            console.error('Config load error:', err);
        }
    };

    const loadIndustries = async () => {
        try {
            const res = await fetch('http://localhost:8000/api/admin/config/industries', { headers });
            if (res.ok) {
                const data = await res.json();
                if (data.industries) setIndustries(data.industries);
            }
        } catch (err) {
            console.error('Industries load error:', err);
        }
    };

    const showMessage = (text: string, type: 'success' | 'error') => {
        setMessage({ text, type });
        setTimeout(() => setMessage(null), 3000);
    };

    // ===== Telegram handlers =====
    const saveTelegramConfig = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/api/admin/config/telegram', {
                method: 'PUT',
                headers,
                body: JSON.stringify(telegramConfig),
            });
            const data = await res.json();
            showMessage(data.message || 'Saqlandi', res.ok ? 'success' : 'error');
        } catch {
            showMessage('Xatolik yuz berdi', 'error');
        }
        setLoading(false);
    };

    const testTelegramToken = async () => {
        setLoading(true);
        setBotInfo(null);
        try {
            const res = await fetch('http://localhost:8000/api/admin/config/telegram/test', {
                method: 'POST',
                headers,
                body: JSON.stringify(telegramConfig),
            });
            const data = await res.json();
            if (data.status === 'success') {
                setBotInfo({ bot_name: data.bot_name, bot_username: data.bot_username });
                showMessage(`✅ Bot topildi: @${data.bot_username}`, 'success');
            } else {
                showMessage(data.message || 'Token noto\'g\'ri', 'error');
            }
        } catch {
            showMessage('Test xatolik', 'error');
        }
        setLoading(false);
    };

    // ===== Agent handlers =====
    const saveAgentConfig = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/api/admin/config/agent', {
                method: 'PUT',
                headers,
                body: JSON.stringify(agentConfig),
            });
            const data = await res.json();
            showMessage(data.message || 'Saqlandi', res.ok ? 'success' : 'error');
        } catch {
            showMessage('Xatolik yuz berdi', 'error');
        }
        setLoading(false);
    };

    // ===== Industry handlers =====
    const toggleIndustry = (id: string) => {
        setIndustries(prev =>
            prev.map(ind => ind.id === id ? { ...ind, enabled: !ind.enabled } : ind)
        );
    };

    const saveIndustries = async () => {
        setLoading(true);
        try {
            const payload = industries.map(i => ({
                industry_id: i.id,
                enabled: i.enabled,
            }));
            const res = await fetch('http://localhost:8000/api/admin/config/industries', {
                method: 'PUT',
                headers,
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            showMessage(data.message || 'Saqlandi', res.ok ? 'success' : 'error');
        } catch {
            showMessage('Xatolik yuz berdi', 'error');
        }
        setLoading(false);
    };

    return (
        <div className="admin-settings">
            <div className="settings-header">
                <SettingsIcon size={24} />
                <h2>Platform Sozlamalari</h2>
            </div>

            {/* Status message */}
            {message && (
                <div className={`settings-message ${message.type}`}>
                    {message.type === 'success' ? <Check size={16} /> : <X size={16} />}
                    {message.text}
                </div>
            )}

            {/* Tab navigation */}
            <div className="settings-tabs">
                <button
                    className={`settings-tab ${activeTab === 'telegram' ? 'active' : ''}`}
                    onClick={() => setActiveTab('telegram')}
                >
                    <Send size={16} /> Telegram Bot
                </button>
                <button
                    className={`settings-tab ${activeTab === 'industries' ? 'active' : ''}`}
                    onClick={() => setActiveTab('industries')}
                >
                    <Building2 size={16} /> Soha Modullari
                </button>
                <button
                    className={`settings-tab ${activeTab === 'agent' ? 'active' : ''}`}
                    onClick={() => setActiveTab('agent')}
                >
                    <Cpu size={16} /> Agent Sozlamalari
                </button>
            </div>

            {/* Tab content */}
            <div className="settings-content">

                {/* ===== TELEGRAM TAB ===== */}
                {activeTab === 'telegram' && (
                    <div className="settings-section">
                        <h3><Bot size={18} /> Telegram Bot Konfiguratsiya</h3>
                        <p className="section-desc">
                            Bot token orqali tayyor hujjatlarni Telegram foydalanuvchilariga yuboring.
                        </p>

                        <div className="settings-field">
                            <label>Bot Token</label>
                            <input
                                type="password"
                                placeholder="123456:ABC-DEF1234ghIkl-..."
                                value={telegramConfig.bot_token}
                                onChange={e => setTelegramConfig(prev => ({ ...prev, bot_token: e.target.value }))}
                            />
                        </div>

                        <div className="settings-field">
                            <label>Standart Caption</label>
                            <input
                                type="text"
                                value={telegramConfig.default_caption}
                                onChange={e => setTelegramConfig(prev => ({ ...prev, default_caption: e.target.value }))}
                            />
                        </div>

                        <div className="settings-field checkbox-field">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={telegramConfig.enabled}
                                    onChange={e => setTelegramConfig(prev => ({ ...prev, enabled: e.target.checked }))}
                                />
                                Telegram integratsiyani yoqish
                            </label>
                        </div>

                        {botInfo && (
                            <div className="bot-info-card">
                                <span className="bot-icon">🤖</span>
                                <div>
                                    <strong>{botInfo.bot_name}</strong>
                                    <span className="bot-username">@{botInfo.bot_username}</span>
                                </div>
                            </div>
                        )}

                        <div className="settings-actions">
                            <button className="btn-test" onClick={testTelegramToken} disabled={loading || !telegramConfig.bot_token}>
                                <RefreshCw size={14} className={loading ? 'spin' : ''} /> Test
                            </button>
                            <button className="btn-save" onClick={saveTelegramConfig} disabled={loading}>
                                <Check size={14} /> Saqlash
                            </button>
                        </div>
                    </div>
                )}

                {/* ===== INDUSTRIES TAB ===== */}
                {activeTab === 'industries' && (
                    <div className="settings-section">
                        <h3><Building2 size={18} /> Soha Modullari</h3>
                        <p className="section-desc">
                            Qaysi soha modullari agent uchun mavjud bo'lishini boshqaring.
                        </p>

                        <div className="industry-grid">
                            {industries.map(ind => (
                                <div
                                    key={ind.id}
                                    className={`industry-card ${ind.enabled ? 'enabled' : 'disabled'}`}
                                    onClick={() => toggleIndustry(ind.id)}
                                >
                                    <div className="industry-card-header">
                                        <span className="industry-name">{ind.name}</span>
                                        <span className={`toggle-indicator ${ind.enabled ? 'on' : 'off'}`}>
                                            {ind.enabled ? '✓' : '✕'}
                                        </span>
                                    </div>
                                    <p className="industry-desc">{ind.description}</p>
                                    <span className="doc-count">{ind.document_count || 0} hujjat</span>
                                </div>
                            ))}
                        </div>

                        {industries.length > 0 && (
                            <div className="settings-actions">
                                <button className="btn-save" onClick={saveIndustries} disabled={loading}>
                                    <Check size={14} /> Saqlash
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* ===== AGENT TAB ===== */}
                {activeTab === 'agent' && (
                    <div className="settings-section">
                        <h3><Cpu size={18} /> Agent Sozlamalari</h3>

                        <div className="settings-field">
                            <label>AI Model nomi</label>
                            <input
                                type="text"
                                placeholder="gemini-2.0-flash (default)"
                                value={agentConfig.model_name}
                                onChange={e => setAgentConfig(prev => ({ ...prev, model_name: e.target.value }))}
                            />
                        </div>

                        <div className="settings-field">
                            <label>Max Recursion Limit</label>
                            <input
                                type="number"
                                min={5}
                                max={200}
                                value={agentConfig.max_recursion}
                                onChange={e => setAgentConfig(prev => ({ ...prev, max_recursion: parseInt(e.target.value) || 50 }))}
                            />
                        </div>

                        <div className="settings-field checkbox-field">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={agentConfig.auto_approve}
                                    onChange={e => setAgentConfig(prev => ({ ...prev, auto_approve: e.target.checked }))}
                                />
                                Auto-approve (HITL o'chiriladi — ehtiyot bo'ling!)
                            </label>
                        </div>

                        <div className="settings-field">
                            <label>System Prompt Override (bo'sh = default)</label>
                            <textarea
                                rows={6}
                                placeholder="Agentga qo'shimcha ko'rsatmalar..."
                                value={agentConfig.system_prompt_override}
                                onChange={e => setAgentConfig(prev => ({ ...prev, system_prompt_override: e.target.value }))}
                            />
                        </div>

                        <div className="settings-actions">
                            <button className="btn-save" onClick={saveAgentConfig} disabled={loading}>
                                <Check size={14} /> Saqlash
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
