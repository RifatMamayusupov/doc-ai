/**
 * Monister Agentic AI - Main Application
 * Redesigned with Auth, Admin Panel, and flexible layout
 */

import { useEffect, useState } from 'react';
import { Sidebar, ChatPanel, PipelineCanvas, PreviewPanel, LogsPanel, HITLModal, IndustryPanel, DeadlinePanel } from './components';
import { useWebSocket } from './hooks/useWebSocket';
import { useMonisterStore } from './stores/monisterStore';
import { API_URL } from './config';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { AdminDashboard } from './pages/admin/Dashboard';
import { AdminUsers } from './pages/admin/Users';
import { AdminFiles } from './pages/admin/Files';
import AdminSettings from './pages/admin/Settings';
import './App.css';

type AuthView = 'login' | 'register';
type AdminView = 'dashboard' | 'users' | 'files' | 'settings' | 'main';

function MainApp() {
  const { isAuthenticated, isAdmin, user, logout } = useAuth();
  const {
    isConnected,
    sidebarCollapsed,
    previewOpen,
    createSession,
    sessions: rawSessions,
  } = useMonisterStore();

  const sessions = rawSessions ?? [];

  const [authView, setAuthView] = useState<AuthView>('login');
  const [adminView, setAdminView] = useState<AdminView>('main');

  // Initialize WebSocket connection
  useWebSocket();

  // Create initial session if none exists
  useEffect(() => {
    if (sessions.length === 0) {
      createSession();
    }
  }, [sessions.length, createSession]);

  // Fetch templates on mount
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await fetch(`${API_URL}/api/templates`);
        if (response.ok) {
          const data = await response.json();
          useMonisterStore.getState().setTemplates(data.templates);
        }
      } catch (error) {
        console.error('Failed to fetch templates:', error);
      }
    };

    fetchTemplates();
  }, []);

  // Fetch industries on mount
  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const response = await fetch(`${API_URL}/api/industries`);
        if (response.ok) {
          const data = await response.json();
          useMonisterStore.getState().setIndustries(data.industries);
        }
      } catch (error) {
        console.error('Failed to fetch industries:', error);
      }
    };
    fetchIndustries();
  }, []);

  // Layout state
  const [chatWidth, setChatWidth] = useState(400);
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = () => {
    setIsResizing(true);
  };

  const stopResizing = () => {
    setIsResizing(false);
  };

  const resize = (mouseMoveEvent: MouseEvent) => {
    if (isResizing) {
      const newWidth = mouseMoveEvent.clientX - (sidebarCollapsed ? 60 : 250);
      if (newWidth > 300 && newWidth < 800) {
        setChatWidth(newWidth);
      }
    }
  };

  useEffect(() => {
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [isResizing]);

  // Show login/register if not authenticated
  if (!isAuthenticated) {
    if (authView === 'login') {
      return <LoginPage onNavigateToRegister={() => setAuthView('register')} />;
    }
    return <RegisterPage onNavigateToLogin={() => setAuthView('login')} />;
  }

  // Show admin panel if requested
  if (adminView !== 'main') {
    const handleAdminNavigate = (page: AdminView) => setAdminView(page);

    switch (adminView) {
      case 'dashboard':
        return <AdminDashboard onNavigate={handleAdminNavigate} />;
      case 'users':
        return <AdminUsers onNavigate={handleAdminNavigate} />;
      case 'files':
        return <AdminFiles onNavigate={handleAdminNavigate} />;
      case 'settings':
        return <AdminSettings />;
    }
  }

  return (
    <div className="app">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className={`app-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {/* Header */}
        <header className="app-header">
          <div className="logo">
            <span className="logo-icon">🤖</span>
            <span className="logo-text">Monister AI</span>
          </div>
          <div className="header-right">
            <div className="header-status">
              <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
              <span>{isConnected ? 'Connected' : 'Connecting...'}</span>
            </div>

            {/* User info and actions */}
            <div className="header-user">
              <span className="user-name">👤 {user?.username}</span>
              {isAdmin && (
                <button
                  className="admin-panel-btn"
                  onClick={() => setAdminView('dashboard')}
                >
                  🎛️ Admin
                </button>
              )}
              <button className="logout-btn" onClick={logout}>
                Chiqish
              </button>
            </div>
          </div>
        </header>

        {/* Main Layout */}
        <main className={`app-main ${previewOpen ? 'with-preview' : ''}`} style={{ display: 'flex' }}>
          {/* Chat Zone - Resizable */}
          <section className="zone-chat" style={{ width: previewOpen ? chatWidth : '100%', flex: previewOpen ? 'none' : 1 }}>
            <ChatPanel />
            {/* Industry module browser (collapsible, inside chat zone) */}
            <IndustryPanel />
          </section>

          {/* Resizer Handle (only visible when preview is open) */}
          {previewOpen && (
            <div
              className="resizer-handle"
              onMouseDown={startResizing}
            />
          )}

          {/* Preview Zone (conditional) */}
          {previewOpen && (
            <section className="zone-preview" style={{ flex: 1 }}>
              <PreviewPanel />
            </section>
          )}

          {/* Pipeline Zone (hidden when preview is open) */}
          {!previewOpen && (
            <section className="zone-pipeline" style={{ display: 'none' }}>
              <PipelineCanvas />
            </section>
          )}
        </main>

        {/* Deadline Widget (above logs) */}
        <DeadlinePanel />

        {/* Bottom - Logs */}
        <footer className="zone-bottom">
          <LogsPanel />
        </footer>
      </div>

      {/* HITL Modal */}
      <HITLModal />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
