/**
 * API client for backend communication
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiError {
    detail: string;
}

class ApiClient {
    private baseUrl: string;
    private accessToken: string | null = null;
    private refreshToken: string | null = null;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
        // Load tokens from localStorage on init
        if (typeof window !== 'undefined') {
            this.accessToken = localStorage.getItem('access_token');
            this.refreshToken = localStorage.getItem('refresh_token');
        }
    }

    setTokens(accessToken: string, refreshToken: string) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;
        if (typeof window !== 'undefined') {
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('refresh_token', refreshToken);
        }
    }

    clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
        }
    }

    getAccessToken() {
        return this.accessToken;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.accessToken) {
            (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
        }

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (response.status === 401 && this.refreshToken) {
            // Try to refresh token
            const refreshed = await this.refreshAccessToken();
            if (refreshed) {
                // Retry original request
                (headers as Record<string, string>)['Authorization'] = `Bearer ${this.accessToken}`;
                const retryResponse = await fetch(url, { ...options, headers });
                if (!retryResponse.ok) {
                    throw new Error('Request failed after token refresh');
                }
                return retryResponse.json();
            }
        }

        if (!response.ok) {
            const error: ApiError = await response.json().catch(() => ({ detail: 'An error occurred' }));
            throw new Error(error.detail);
        }

        // Handle 204 No Content
        if (response.status === 204) {
            return {} as T;
        }

        return response.json();
    }

    private async refreshAccessToken(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshToken }),
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return true;
            }
        } catch {
            // Refresh failed
        }
        this.clearTokens();
        return false;
    }

    // Auth endpoints
    async register(email: string, username: string, password: string, fullName?: string) {
        const data = await this.request<{ access_token: string; refresh_token: string }>('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password, full_name: fullName }),
        });
        this.setTokens(data.access_token, data.refresh_token);
        return data;
    }

    async login(email: string, password: string) {
        const data = await this.request<{ access_token: string; refresh_token: string }>('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        this.setTokens(data.access_token, data.refresh_token);
        return data;
    }

    async logout() {
        await this.request('/api/auth/logout', { method: 'POST' });
        this.clearTokens();
    }

    async getCurrentUser() {
        return this.request<{
            id: string;
            email: string;
            username: string;
            full_name: string | null;
        }>('/api/auth/me');
    }

    // Chat endpoints
    async getChats(page = 1, perPage = 20) {
        return this.request<{
            chats: Array<{
                id: string;
                title: string;
                thread_id: string;
                is_archived: boolean;
                is_pinned: boolean;
                created_at: string;
                updated_at: string;
                message_count: number;
            }>;
            total: number;
            page: number;
            per_page: number;
            has_next: boolean;
        }>(`/api/chats?page=${page}&per_page=${perPage}`);
    }

    async createChat(title = 'New Chat') {
        return this.request<{
            id: string;
            title: string;
            thread_id: string;
        }>('/api/chats', {
            method: 'POST',
            body: JSON.stringify({ title }),
        });
    }

    async getChat(chatId: string) {
        return this.request<{
            id: string;
            title: string;
            thread_id: string;
            messages: Array<{
                id: string;
                role: string;
                content: string;
                created_at: string;
            }>;
        }>(`/api/chats/${chatId}`);
    }

    async getChatMessages(chatId: string) {
        return this.request<Array<{
            id: string;
            role: string;
            content: string;
            message_metadata: any;
            created_at: string;
        }>>(`/api/chats/${chatId}/messages`);
    }

    async updateChat(chatId: string, data: { title?: string; is_archived?: boolean; is_pinned?: boolean }) {
        return this.request(`/api/chats/${chatId}`, {
            method: 'PATCH',
            body: JSON.stringify(data),
        });
    }

    async deleteChat(chatId: string) {
        return this.request(`/api/chats/${chatId}`, { method: 'DELETE' });
    }

    // File endpoints
    async uploadFile(file: File) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/api/files/upload`, {
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
    async getTemplates(organization?: string, category?: string) {
        let url = '/api/templates';
        const params = new URLSearchParams();
        if (organization) params.set('organization', organization);
        if (category) params.set('category', category);
        if (params.toString()) url += `?${params.toString()}`;

        return this.request<{
            templates: Array<{
                id: string;
                name: string;
                organization: string;
                category: string;
                preview_image: string | null;
            }>;
            organizations: string[];
            categories: string[];
        }>(url);
    }
}

export const api = new ApiClient(API_URL);
