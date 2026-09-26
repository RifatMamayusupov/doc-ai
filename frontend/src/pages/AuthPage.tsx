/**
 * Auth Page - Login/Register
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, Loader2, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { useAuthStore } from '../lib/store';

export default function AuthPage() {
    const navigate = useNavigate();
    const { setUser } = useAuthStore();
    const [isLogin, setIsLogin] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [formData, setFormData] = useState({
        email: '',
        username: '',
        password: '',
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            if (isLogin) {
                await api.login(formData.username, formData.password);
                // Fetch user info after login
                const user = await api.getCurrentUser();
                setUser(user);
                navigate('/chat');
            } else {
                await api.register(formData.email, formData.username, formData.password);
                // Auto login after register
                await api.login(formData.username, formData.password);
                const user = await api.getCurrentUser();
                setUser(user);
                navigate('/chat');
            }
        } catch (err: any) {
            setError(err.message || 'Something went wrong');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-screen flex items-center justify-center" style={{ background: 'var(--dark-950)' }}>
            {/* Background effects */}
            <div style={{
                position: 'absolute',
                inset: 0,
                overflow: 'hidden',
                pointerEvents: 'none',
            }}>
                <div style={{
                    position: 'absolute',
                    top: '10%',
                    left: '20%',
                    width: '400px',
                    height: '400px',
                    background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
                    filter: 'blur(60px)',
                }} />
                <div style={{
                    position: 'absolute',
                    bottom: '20%',
                    right: '15%',
                    width: '300px',
                    height: '300px',
                    background: 'radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, transparent 70%)',
                    filter: 'blur(60px)',
                }} />
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="card-glass"
                style={{
                    width: '100%',
                    maxWidth: '420px',
                    padding: '2.5rem',
                    margin: '1rem',
                }}
            >
                {/* Logo */}
                <div className="text-center" style={{ marginBottom: '2rem' }}>
                    <div style={{
                        width: '64px',
                        height: '64px',
                        background: 'linear-gradient(135deg, var(--primary) 0%, #a855f7 100%)',
                        borderRadius: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 1rem',
                    }}>
                        <Sparkles size={32} color="white" />
                    </div>
                    <h1 className="gradient-text" style={{ fontSize: '1.75rem', fontWeight: 700 }}>
                        DocAgent
                    </h1>
                    <p style={{ color: 'var(--dark-400)', marginTop: '0.5rem' }}>
                        AI-powered document processing
                    </p>
                </div>

                {/* Tabs */}
                <div style={{
                    display: 'flex',
                    background: 'var(--dark-800)',
                    borderRadius: '0.75rem',
                    padding: '4px',
                    marginBottom: '1.5rem',
                }}>
                    <button
                        onClick={() => setIsLogin(true)}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            borderRadius: '0.5rem',
                            border: 'none',
                            background: isLogin ? 'var(--primary)' : 'transparent',
                            color: isLogin ? 'white' : 'var(--dark-400)',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        Kirish
                    </button>
                    <button
                        onClick={() => setIsLogin(false)}
                        style={{
                            flex: 1,
                            padding: '0.75rem',
                            borderRadius: '0.5rem',
                            border: 'none',
                            background: !isLogin ? 'var(--primary)' : 'transparent',
                            color: !isLogin ? 'white' : 'var(--dark-400)',
                            fontWeight: 500,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                    >
                        Ro'yxatdan o'tish
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit}>
                    {!isLogin && (
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ position: 'relative' }}>
                                <Mail
                                    size={18}
                                    style={{
                                        position: 'absolute',
                                        left: '1rem',
                                        top: '50%',
                                        transform: 'translateY(-50%)',
                                        color: 'var(--dark-400)',
                                    }}
                                />
                                <input
                                    type="email"
                                    placeholder="Email"
                                    className="input-field"
                                    style={{ paddingLeft: '2.75rem' }}
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required={!isLogin}
                                />
                            </div>
                        </div>
                    )}

                    <div style={{ marginBottom: '1rem' }}>
                        <div style={{ position: 'relative' }}>
                            <User
                                size={18}
                                style={{
                                    position: 'absolute',
                                    left: '1rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--dark-400)',
                                }}
                            />
                            <input
                                type="text"
                                placeholder="Username"
                                className="input-field"
                                style={{ paddingLeft: '2.75rem' }}
                                value={formData.username}
                                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <div style={{ position: 'relative' }}>
                            <Lock
                                size={18}
                                style={{
                                    position: 'absolute',
                                    left: '1rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--dark-400)',
                                }}
                            />
                            <input
                                type="password"
                                placeholder="Parol"
                                className="input-field"
                                style={{ paddingLeft: '2.75rem' }}
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                required
                            />
                        </div>
                    </div>

                    {error && (
                        <div style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            borderRadius: '0.5rem',
                            padding: '0.75rem',
                            marginBottom: '1rem',
                            color: 'var(--error)',
                            fontSize: '0.875rem',
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn-primary w-full"
                        disabled={loading}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                        }}
                    >
                        {loading && <Loader2 size={18} className="animate-spin" />}
                        {isLogin ? 'Kirish' : 'Ro\'yxatdan o\'tish'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
}
