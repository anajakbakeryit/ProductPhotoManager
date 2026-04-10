import { Route, Routes, Navigate } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout1 } from '@/components/layouts/layout-1';
import { LoginPage } from '@/pages/login/page';
import { ShootingPage } from '@/pages/shooting/page';
import { GalleryPage } from '@/pages/gallery/page';
import { SettingsPage } from '@/pages/settings/page';
import { SessionsPage } from '@/pages/sessions/page';
import { ReportsPage } from '@/pages/reports/page';
import { Spin360Page } from '@/pages/spin360/page';
import { useAuthStore } from '@/store/authStore';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const [devMode, setDevMode] = useState<boolean | null>(null);

  useEffect(() => {
    // Check if backend is in dev mode (no login required)
    api.get<{ dev_mode?: boolean }>('/api/health')
      .then((res) => {
        if (res.dev_mode) {
          setDevMode(true);
          // Set a dummy user so app works
          useAuthStore.setState({
            user: { id: 1, username: 'admin', display_name: 'ผู้ดูแลระบบ', role: 'admin' },
          });
        } else {
          setDevMode(false);
        }
      })
      .catch(() => setDevMode(false));
  }, []);

  // Loading while checking dev mode
  if (devMode === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user && !devMode) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function AppRoutingSetup() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <ProtectedRoute>
              <Layout1 />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<ShootingPage />} />
          <Route path="/gallery" element={<GalleryPage />} />
          <Route path="/360" element={<Spin360Page />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </QueryClientProvider>
  );
}
