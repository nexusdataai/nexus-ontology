import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense, useEffect } from "react";
import Layout from "./components/Layout";
import { Skeleton } from "./components/ui/skeleton";
import { ThemeProvider } from "./hooks/use-theme";
import { EnterpriseAuthProvider, useEnterpriseAuth } from "./context/EnterpriseAuthContext";
import { ChatProvider } from "./context/ChatContext";
import { ConfirmHost } from "./components/ds/confirm";
// The assistant loads after the page: it is not needed for the first paint.
const AssistantDock = lazyPage(() => import('@/components/assistant/AssistantDock').then(m => ({ default: m.AssistantDock })));

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import AuthCallback from "./pages/AuthCallback";
import NotFound from "./pages/NotFound";
/**
 * Pages are separate files in the build. After a new release, a tab opened
 * before it may ask for a file that no longer exists; reload once to pick up
 * the new release instead of showing a broken page.
 */
function lazyPage<T extends React.ComponentType<any>>(load: () => Promise<{ default: T }>) {
  return lazy(() =>
    load().then(
      (m) => { sessionStorage.removeItem('page-reload'); return m; },
      (err) => {
        if (!sessionStorage.getItem('page-reload')) {
          sessionStorage.setItem('page-reload', '1');
          window.location.reload();
          return new Promise<{ default: T }>(() => {});
        }
        throw err;
      },
    ),
  );
}

const Settings = lazyPage(() => import("./pages/Settings"));
const UserManagement = lazyPage(() => import("./pages/UserManagement"));
const HomePage = lazyPage(() => import("./pages/HomePage"));

const DataPlaneCreatePage = lazyPage(() => import("./pages/DataPlaneCreatePage"));
const DataPlaneExplorer = lazyPage(() => import("./pages/DataPlaneExplorer"));
const DataPlanePage = lazyPage(() => import("./pages/ai-stack/DataPlanePage"));
const ControlPlanePage = lazyPage(() => import("./pages/ai-stack/ControlPlanePage"));
const ReasoningPage = lazyPage(() => import("./pages/ai-stack/ReasoningPage"));
const ToolsCataloguePage = lazyPage(() => import("./pages/workspace/ToolsCataloguePage"));
const AppCataloguePage = lazyPage(() => import("./pages/workspace/AppCataloguePage"));
const AIAutomationPage = lazyPage(() => import("./pages/workspace/AIAutomationPage"));
const AppPage = lazyPage(() => import("./pages/apps/AppPage"));
const DiagnosticsPage = lazyPage(() => import("./pages/DiagnosticsPage"));
const Operations = lazyPage(() => import("./pages/Operations"));
const DashboardListPage = lazyPage(() => import("./pages/dashboard/DashboardListPage"));
const DashboardBuilderPage = lazyPage(() => import("./pages/dashboard/DashboardBuilderPage"));
const DashboardViewerPage = lazyPage(() => import("./pages/dashboard/DashboardViewerPage"));
const ViewListPage = lazyPage(() => import("./pages/views/ViewListPage"));
const ViewBuilderPage = lazyPage(() => import("./pages/views/ViewBuilderPage"));
const ViewRuntimePage = lazyPage(() => import("./pages/views/ViewRuntimePage"));
const AIAnalyticsPage = lazyPage(() => import("./pages/AIAnalyticsPage"));
const DesignSystemPage = lazyPage(() => import("./pages/DesignSystemPage"));
const HelpPage = lazyPage(() => import("./pages/HelpPage"));
const SimulatorPage = lazyPage(() => import("./pages/SimulatorPage"));

const queryClient = new QueryClient();

/**
 * Shown while a page's code is fetched (each page is its own file in the
 * build). The app shell stays, so only the content area waits.
 */
const PageLoading = () => {
  const path = window.location.pathname;
  if (/^\/(login|signup|auth\/)/.test(path)) return null;
  return (
    <Layout>
      <div className="mx-auto w-full max-w-[1400px] space-y-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-8" aria-busy="true" aria-label="Loading page">
        <Skeleton className="h-8 w-64 max-w-full" />
        <Skeleton className="h-4 w-96 max-w-full" />
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    </Layout>
  );
};

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
      <Suspense fallback={<PageLoading />}>
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
      </Suspense>
      {user && !loading && !/^\/(login|signup|design-system\/login)/.test(window.location.pathname) && <Suspense fallback={null}><AssistantDock userName={profile?.full_name} /></Suspense>}
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
