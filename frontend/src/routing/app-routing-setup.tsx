import { Route, Routes, Navigate } from 'react-router';
import { Layout1 } from '@/components/layouts/layout-1';
import { LoginPage } from '@/pages/login/page';
import { ShootingPage } from '@/pages/shooting/page';
import { useAuthStore } from '@/store/authStore';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function AppRoutingSetup() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes with sidebar layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout1 />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<ShootingPage />} />
        <Route path="/gallery" element={<div className="p-6 text-foreground">แกลเลอรี่ (เร็วๆ นี้)</div>} />
        <Route path="/360" element={<div className="p-6 text-foreground">360° (เร็วๆ นี้)</div>} />
        <Route path="/sessions" element={<div className="p-6 text-foreground">เซสชัน (เร็วๆ นี้)</div>} />
        <Route path="/reports" element={<div className="p-6 text-foreground">รายงาน (เร็วๆ นี้)</div>} />
        <Route path="/settings" element={<div className="p-6 text-foreground">ตั้งค่า (เร็วๆ นี้)</div>} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
