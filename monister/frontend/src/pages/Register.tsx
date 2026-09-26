/**
 * Register Page - User registration
 */

import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Lock, User, Mail, ArrowRight, ArrowLeft } from 'lucide-react';

interface RegisterPageProps {
    onNavigateToLogin: () => void;
}

export function RegisterPage({ onNavigateToLogin }: RegisterPageProps) {
    const { register } = useAuth();
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Parollar mos kelmaydi');
            return;
        }

        if (password.length < 6) {
            setError('Parol kamida 6 ta belgidan iborat bo\'lishi kerak');
            return;
        }

        setIsLoading(true);

        try {
            await register(username, email, password);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed');
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
                    <h1>Ro'yxatdan o'tish</h1>
                    <p>Yangi hisob yarating</p>
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
                            minLength={3}
                        />
                    </div>

                    <div className="auth-input-group">
                        <Mail size={18} />
                        <input
                            type="email"
                            placeholder="Email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
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
                            minLength={6}
                        />
                    </div>

                    <div className="auth-input-group">
                        <Lock size={18} />
                        <input
                            type="password"
                            placeholder="Parolni tasdiqlang"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="auth-button primary"
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>⏳ Ro'yxatdan o'tish...</>
                        ) : (
                            <>
                                Ro'yxatdan o'tish
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
                    onClick={onNavigateToLogin}
                >
                    <ArrowLeft size={18} />
                    Tizimga kirish
                </button>
            </div>
        </div>
    );
}
