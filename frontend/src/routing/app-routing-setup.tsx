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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
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
