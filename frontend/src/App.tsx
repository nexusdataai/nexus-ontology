import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { ThemeProvider } from "./hooks/use-theme";
import { EnterpriseAuthProvider, useEnterpriseAuth } from "./context/EnterpriseAuthContext";
import { ChatProvider } from "./context/ChatContext";
import { ConfirmHost } from "./components/ds/confirm";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import AuthCallback from "./pages/AuthCallback";
import NotFound from "./pages/NotFound";
import Settings from "./pages/Settings";
import UserManagement from "./pages/UserManagement";
import HomePage from "./pages/HomePage";

import DataPlaneCreatePage from "./pages/DataPlaneCreatePage";
import DataPlaneExplorer from "./pages/DataPlaneExplorer";
import DataPlanePage from "./pages/ai-stack/DataPlanePage";
import ControlPlanePage from "./pages/ai-stack/ControlPlanePage";
import ReasoningPage from "./pages/ai-stack/ReasoningPage";
import ToolsCataloguePage from "./pages/workspace/ToolsCataloguePage";
import AppCataloguePage from "./pages/workspace/AppCataloguePage";
import AIAutomationPage from "./pages/workspace/AIAutomationPage";
import AppPage from "./pages/apps/AppPage";
import DiagnosticsPage from "./pages/DiagnosticsPage";
import Operations from "./pages/Operations";
import DashboardListPage from "./pages/dashboard/DashboardListPage";
import DashboardBuilderPage from "./pages/dashboard/DashboardBuilderPage";
import DashboardViewerPage from "./pages/dashboard/DashboardViewerPage";
import ViewListPage from "./pages/views/ViewListPage";
import ViewBuilderPage from "./pages/views/ViewBuilderPage";
import ViewRuntimePage from "./pages/views/ViewRuntimePage";
import AIAnalyticsPage from "./pages/AIAnalyticsPage";
import DesignSystemPage from "./pages/DesignSystemPage";
import { AssistantDock } from '@/components/assistant/AssistantDock';
import HelpPage from './pages/HelpPage';
import SimulatorPage from './pages/SimulatorPage';

const queryClient = new QueryClient();

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useEnterpriseAuth();
  if (loading) return <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const P = ({ children }: { children: React.ReactNode }) => (
  <ProtectedRoute>{children}</ProtectedRoute>
);

const AuthRoutes = () => {
  const { user, loading, profile } = useEnterpriseAuth();

  if (user && !loading && (window.location.pathname === '/login' || window.location.pathname === '/signup')) {
    return <Navigate to="/" replace />;
  }

  return (
    <ChatProvider profileName={profile?.full_name}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/auth/callback" element={<AuthCallback />} />

        <Route path="/" element={<P><HomePage /></P>} />

        {/* AI Stack */}
        <Route path="/ai-stack/data-plane" element={<P><DataPlanePage /></P>} />
        <Route path="/ai-stack/data-plane/create" element={<P><DataPlaneCreatePage /></P>} />
        <Route path="/ai-stack/data-plane/:id" element={<P><DataPlaneExplorer /></P>} />
        <Route path="/ai-stack/control-plane" element={<P><ControlPlanePage /></P>} />
        <Route path="/ai-stack/reasoning" element={<P><ReasoningPage /></P>} />

        {/* Workspace */}
        <Route path="/workspace/apps" element={<P><AppCataloguePage /></P>} />
        <Route path="/apps/:appId" element={<P><AppPage /></P>} />
        <Route path="/workspace/automation" element={<P><AIAutomationPage /></P>} />
        <Route path="/workspace/tools" element={<P><ToolsCataloguePage /></P>} />
        {/* Legacy /tools shortcut -> Reasoning page's Tool Builder tab */}
        <Route path="/tools" element={<Navigate to="/ai-stack/reasoning?tab=builder" replace />} />
        <Route path="/tools/:toolId" element={<Navigate to="/ai-stack/reasoning?tab=builder" replace />} />
        {/* AI Analytics (combined Dashboards + Views) */}
        <Route path="/ai-analytics" element={<P><AIAnalyticsPage /></P>} />

        {/* Dashboards */}
        <Route path="/dashboards" element={<P><DashboardListPage /></P>} />
        <Route path="/dashboard/builder" element={<P><DashboardBuilderPage /></P>} />
        <Route path="/dashboard/builder/:uid" element={<P><DashboardBuilderPage /></P>} />
        <Route path="/dashboard/view/:uid" element={<P><DashboardViewerPage /></P>} />

        {/* Views (tabbed dashboards) */}
        <Route path="/views" element={<P><ViewListPage /></P>} />
        <Route path="/views/builder" element={<P><ViewBuilderPage /></P>} />
        <Route path="/views/builder/:viewId" element={<P><ViewBuilderPage /></P>} />
        <Route path="/views/:viewId" element={<P><ViewRuntimePage /></P>} />

        {/* Operations (AI Ops) */}
        <Route path="/operations" element={<Navigate to="/operations/diagnostics" replace />} />
        <Route path="/operations/journeys" element={<Navigate to="/workspace/automation?tab=journeys" replace />} />
        <Route path="/operations/diagnostics" element={<P><DiagnosticsPage /></P>} />
        <Route path="/operations/jobs" element={<Navigate to="/operations/health?tab=jobs" replace />} />
        <Route path="/operations/audit" element={<Navigate to="/operations/health?tab=audit" replace />} />
        <Route path="/operations/health" element={<P><Operations /></P>} />

        {/* User Management & Settings */}
        <Route path="/user-management" element={<P><UserManagement /></P>} />
        <Route path="/settings" element={<P><Settings /></P>} />
        <Route path="/help" element={<P><HelpPage /></P>} />
        <Route path="/simulator" element={<P><SimulatorPage /></P>} />
        {/* Design system reference (not in the sidebar; open via search) */}
        <Route path="/design-system" element={<P><DesignSystemPage /></P>} />
        {/* Sign-in screen preview for design review (no sign-out needed) */}
        <Route path="/design-system/login" element={<P><Login /></P>} />
        {/* Legacy redirects */}
        <Route path="/analytics/*" element={<Navigate to="/" replace />} />
        <Route path="/backbone/*" element={<Navigate to="/ai-stack/control-plane" replace />} />
        <Route path="/data-plane" element={<Navigate to="/ai-stack/data-plane" replace />} />
        <Route path="/copilot" element={<Navigate to="/ai-stack/reasoning" replace />} />
        <Route path="/rag-playground" element={<Navigate to="/ai-stack/control-plane" replace />} />
        <Route path="/operations/schedules" element={<Navigate to="/operations/jobs" replace />} />

        <Route path="*" element={<NotFound />} />
      </Routes>
      {user && !loading && !/^\/(login|signup|design-system\/login)/.test(window.location.pathname) && <AssistantDock userName={profile?.full_name} />}
    </ChatProvider>
  );
};

const App = () => {
  useEffect(() => {
    // Theme is handled by ThemeProvider -- just clean up any old key
    const old = localStorage.getItem('theme');
    if (old) {
      localStorage.setItem('app-theme', old);
      localStorage.removeItem('theme');
    }
  }, []);

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <ConfirmHost />
          <BrowserRouter>
            <EnterpriseAuthProvider>
              <AuthRoutes />
            </EnterpriseAuthProvider>
          </BrowserRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
};

export default App;
