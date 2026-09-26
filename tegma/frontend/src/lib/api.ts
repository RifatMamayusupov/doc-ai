/**
 * API client for backend communication
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
    private accessToken: string | null = null;
    private refreshToken: string | null = null;

    constructor() {
        // Load tokens from localStorage
        if (typeof window !== 'undefined') {
            this.accessToken = localStorage.getItem('access_token');
            this.refreshToken = localStorage.getItem('refresh_token');
        }
    }

    setTokens(access: string, refresh: string) {
        this.accessToken = access;
        this.refreshToken = refresh;
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    }

    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    }

    getAccessToken() {
        return this.accessToken;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...(options.headers as Record<string, string>),
        };

        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401 && this.refreshToken) {
            // Try refresh
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${this.accessToken}`;
                const retryResponse = await fetch(`${API_URL}${endpoint}`, {
                    ...options,
                    headers,
                });
                if (!retryResponse.ok) {
                    throw new Error(`HTTP error! status: ${retryResponse.status}`);
                }
                return retryResponse.json();
            } else {
                this.clearTokens();
                window.location.href = '/';
                throw new Error('Session expired');
            }
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }

        return response.json();
    }

    private async refreshAccessToken(): Promise<boolean> {
        try {
            const response = await fetch(`${API_URL}/api/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshToken }),
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return true;
            }
            return false;
        } catch {
            return false;
        }
    }

    // Auth endpoints
    async register(email: string, username: string, password: string) {
        return this.request<{ message: string }>('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password }),
        });
    }

    async login(username: string, password: string) {
        const data = await this.request<{
            access_token: string;
            refresh_token: string;
            user: any;
        }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
        });
        this.setTokens(data.access_token, data.refresh_token);
        return data;
    }

    async getCurrentUser() {
        return this.request<any>('/api/auth/me');
    }

    // Chat endpoints
    async getChats(page = 1, perPage = 20) {
        return this.request<{ chats: any[]; total: number }>(
            `/api/chats?page=${page}&per_page=${perPage}`
        );
    }

    async createChat(title?: string) {
        return this.request<any>('/api/chats', {
            method: 'POST',
            body: JSON.stringify({ title }),
        });
    }

    async getChat(chatId: string) {
        return this.request<any>(`/api/chats/${chatId}`);
    }

    async deleteChat(chatId: string) {
        return this.request<void>(`/api/chats/${chatId}`, { method: 'DELETE' });
    }

    async updateChat(chatId: string, data: { title?: string; is_archived?: boolean }) {
        return this.request<any>(`/api/chats/${chatId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    async getChatMessages(chatId: string) {
        return this.request<any[]>(`/api/chats/${chatId}/messages`);
    }

    // File endpoints
    async uploadFile(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_URL}/api/files/upload`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${this.accessToken}`,
            },
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }
        return response.json();
    }

    // Template endpoints
    async getTemplates(organization?: string) {
        const params = organization ? `?organization=${organization}` : '';
        return this.request<{ templates: any[] }>(`/api/templates${params}`);
    }
}

export const api = new ApiClient();
