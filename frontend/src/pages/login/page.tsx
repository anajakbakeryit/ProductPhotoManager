import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuthStore } from '@/store/authStore';
import { Camera, User, Lock, Loader2, Aperture, Layers, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'เกิดข้อผิดพลาด');
      setShake(true);
      setTimeout(() => setShake(false), 500);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left: Branded Panel */}
      <div className="hidden lg:flex lg:w-[480px] xl:w-[560px] relative overflow-hidden bg-[#1b84ff]">
        {/* Subtle pattern overlay */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 -left-10 w-72 h-72 rounded-full border-[40px] border-white/30" />
          <div className="absolute bottom-20 -right-20 w-96 h-96 rounded-full border-[50px] border-white/20" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full border-[60px] border-white/10" />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between w-full p-10">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="size-9 rounded-lg bg-white/20 flex items-center justify-center">
              <Camera className="size-5 text-white" />
            </div>
            <span className="text-lg font-semibold text-white">Photo Manager</span>
          </div>

          {/* Center content */}
          <div className="space-y-8">
            <div>
              <h1 className="text-3xl font-bold text-white leading-tight">
                ระบบจัดการ<br />ถ่ายภาพสินค้า
              </h1>
              <p className="text-base text-white/70 mt-3 max-w-sm">
                สแกน อัปโหลด ประมวลผลอัตโนมัติ พร้อมส่งออกทุกรูปแบบ
              </p>
            </div>

            {/* Feature highlights */}
            <div className="space-y-4">
              {[
                { icon: Aperture, text: 'ลบพื้นหลังอัตโนมัติด้วย AI' },
                { icon: Layers, text: 'Multi-Resolution (S/M/L/OG)' },
                { icon: Zap, text: '360° Viewer + ลายน้ำอัตโนมัติ' },
              ].map((feat) => (
                <div key={feat.text} className="flex items-center gap-3">
                  <div className="size-8 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
                    <feat.icon className="size-4 text-white/90" />
                  </div>
                  <span className="text-sm text-white/80">{feat.text}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom */}
          <p className="text-xs text-white/40">
            &copy; {new Date().getFullYear()} BESTCHOICE Photo Manager
          </p>
        </div>
      </div>

      {/* Right: Login Form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-[400px]">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-10">
            <div className="inline-flex items-center justify-center size-14 rounded-xl bg-primary/10 mb-3">
              <Camera className="size-7 text-primary" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Photo Manager</h1>
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-foreground">เข้าสู่ระบบ</h2>
            <p className="text-sm text-muted-foreground mt-1.5">ระบุชื่อผู้ใช้และรหัสผ่านเพื่อเริ่มใช้งาน</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className={`p-3.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center gap-2.5 ${shake ? 'animate-[shake_0.5s_ease-in-out]' : ''}`}>
                <div className="size-1.5 rounded-full bg-destructive shrink-0" />
                {error}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">ชื่อผู้ใช้</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10"
                  placeholder="admin"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">รหัสผ่าน</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11"
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  กำลังเข้าสู่ระบบ...
                </>
              ) : (
                'เข้าสู่ระบบ'
              )}
            </Button>
          </form>

          <p className="text-xs text-muted-foreground text-center mt-8 lg:hidden">
            &copy; {new Date().getFullYear()} BESTCHOICE Photo Manager
          </p>
        </div>
      </div>
    </div>
  );
}
