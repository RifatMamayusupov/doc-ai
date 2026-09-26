/**
 * Login Page - User authentication
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Lock, User, ArrowRight, UserPlus } from 'lucide-react';

interface LoginPageProps {
    onNavigateToRegister: () => void;
}

export function LoginPage({ onNavigateToRegister }: LoginPageProps) {
    const { login } = useAuth();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            await login(username, password);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card">
                <div className="auth-header">
                    <div className="auth-logo">
                        <span className="logo-icon">🤖</span>
                        <span className="logo-text">Monister</span>
                    </div>
                    <h1>Tizimga kirish</h1>
                    <p>Hujjatlar bilan ishlash uchun kiring</p>
                </div>

                <form className="auth-form" onSubmit={handleSubmit}>
                    {error && (
                        <div className="auth-error">
                            ❌ {error}
                        </div>
                    )}

                    <div className="auth-input-group">
                        <User size={18} />
                        <input
                            type="text"
                            placeholder="Foydalanuvchi nomi"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>

                    <div className="auth-input-group">
                        <Lock size={18} />
                        <input
                            type="password"
                            placeholder="Parol"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="auth-button primary"
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>⏳ Kirish...</>
                        ) : (
                            <>
                                Kirish
                                <ArrowRight size={18} />
                            </>
                        )}
                    </button>
                </form>

                <div className="auth-divider">
                    <span>yoki</span>
                </div>

                <button
                    className="auth-button secondary"
                    onClick={onNavigateToRegister}
                >
                    <UserPlus size={18} />
                    Ro'yxatdan o'tish
                </button>

                <div className="auth-footer">
                    <p>Admin: admin / admin123</p>
                </div>
            </div>
        </div>
    );
}
