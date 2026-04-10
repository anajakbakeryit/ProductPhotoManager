import { lazy, Suspense, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useNavigate } from 'react-router';
import {
  Camera, Image, Package, Loader2, Clock,
  ArrowRight, TrendingUp, Zap, ScanBarcode, RotateCcw,
} from 'lucide-react';
import { useShootingStore } from '@/store/shootingStore';
import { Input } from '@/components/ui/input';
import {
  Toolbar,
  ToolbarActions,
  ToolbarHeading,
} from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';

const DailyChart = lazy(() => import('./daily-chart').then((m) => ({ default: m.DailyChart })));
type DailyItem = import('./daily-chart').DailyItem;

interface Stats {
  total_products: number;
  total_photos: number;
  photos_today: number;
  pending_processing: number;
  active_sessions: number;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [quickBarcode, setQuickBarcode] = useState('');
  const lastBarcode = useShootingStore((s) => s.currentBarcode);
  const setBarcode = useShootingStore((s) => s.setBarcode);

  const handleQuickScan = () => {
    const bc = quickBarcode.trim();
    if (!bc) return;
    setBarcode(bc);
    navigate('/shooting');
  };

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<Stats>('/api/stats'),
    refetchInterval: 10_000,
  });

  const { data: daily } = useQuery({
    queryKey: ['stats-daily'],
    queryFn: () => api.get<DailyItem[]>('/api/stats/daily?days=7'),
  });

  const { data: recentData } = useQuery({
    queryKey: ['recent-photos'],
    queryFn: () => api.get<{ data: { id: number; barcode: string; angle: string; thumbnail_url: string; status: string; created_at: string }[] }>('/api/gallery?limit=8&page=1'),
  });
  const recent = recentData?.data || [];

  const cards = [
    {
      label: 'รูปวันนี้', value: stats?.photos_today || 0, icon: Camera,
      borderColor: 'bg-blue-500', iconBg: 'bg-blue-500/10', iconColor: 'text-blue-500',
      cardBg: 'bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-card dark:to-blue-950/20',
    },
    {
      label: 'รูปทั้งหมด', value: stats?.total_photos || 0, icon: Image,
      borderColor: 'bg-emerald-500', iconBg: 'bg-emerald-500/10', iconColor: 'text-emerald-500',
      cardBg: 'bg-gradient-to-br from-emerald-50 to-emerald-100/50 dark:from-card dark:to-emerald-950/20',
    },
    {
      label: 'สินค้า', value: stats?.total_products || 0, icon: Package,
      borderColor: 'bg-amber-500', iconBg: 'bg-amber-500/10', iconColor: 'text-amber-500',
      cardBg: 'bg-gradient-to-br from-amber-50 to-amber-100/50 dark:from-card dark:to-amber-950/20',
    },
    {
      label: 'กำลังประมวลผล', value: stats?.pending_processing || 0, icon: Zap,
      borderColor: 'bg-rose-500', iconBg: 'bg-rose-500/10', iconColor: 'text-rose-500',
      cardBg: 'bg-gradient-to-br from-rose-50 to-rose-100/50 dark:from-card dark:to-rose-950/20',
    },
    {
      label: 'เซสชัน', value: stats?.active_sessions || 0, icon: Clock,
      borderColor: 'bg-violet-500', iconBg: 'bg-violet-500/10', iconColor: 'text-violet-500',
      cardBg: 'bg-gradient-to-br from-violet-50 to-violet-100/50 dark:from-card dark:to-violet-950/20',
    },
  ];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      {/* Demo 9 style toolbar */}
      <Toolbar>
        <ToolbarHeading title="แดชบอร์ด" description="ภาพรวมการถ่ายภาพสินค้า" />
        <ToolbarActions>
          <Button onClick={() => navigate('/shooting')}>
            <Camera className="size-4" />
            เริ่มถ่ายรูป
          </Button>
        </ToolbarActions>
      </Toolbar>

      <div className="container space-y-5 lg:space-y-7 pb-7">
        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-5">
          {cards.map((card) => (
            <div
              key={card.label}
              className={`group cursor-pointer rounded-xl border border-border overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 ${card.cardBg}`}
            >
              <div className="p-5 relative">
                <div className={`absolute inset-y-0 left-0 w-1 ${card.borderColor} rounded-l-xl`} />

                <div className="pl-2">
                  <div className="flex items-center justify-between mb-3">
                    <div className={`size-10 rounded-xl ${card.iconBg} flex items-center justify-center group-hover:scale-110 transition-transform`}>
                      <card.icon className={`size-5 ${card.iconColor}`} />
                    </div>
                  </div>

                  <p className="text-2xl lg:text-3xl font-bold text-foreground tabular-nums">
                    {card.value.toLocaleString()}
                  </p>
                  <p className="text-xs font-medium text-muted-foreground mt-1.5 uppercase tracking-wider">
                    {card.label}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Chart + Quick Actions */}
        <div className="grid lg:grid-cols-3 gap-5 lg:gap-7">
          {/* Chart */}
          <div className="lg:col-span-2 rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border/50">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4.5 h-4.5 text-primary" />
                <h2 className="text-sm font-semibold text-foreground">อัปโหลดรายวัน</h2>
              </div>
              <span className="text-2xs font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                7 วันล่าสุด
              </span>
            </div>

            <div className="p-5">
              <Suspense fallback={
                <div className="h-[200px] flex items-center justify-center">
                  <Loader2 className="size-6 animate-spin text-primary" />
                </div>
              }>
                <DailyChart data={daily || []} />
              </Suspense>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-4">
            {/* Quick Scan */}
            <div className="rounded-xl border border-primary/20 bg-gradient-to-r from-primary/5 to-card p-5 relative overflow-hidden">
              <div className="absolute inset-y-0 left-0 w-1 bg-primary rounded-l-xl" />
              <div className="pl-2">
                <div className="flex items-center gap-2 mb-3">
                  <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <ScanBarcode className="size-4 text-primary" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">Quick Scan</h3>
                </div>
                <form onSubmit={(e) => { e.preventDefault(); handleQuickScan(); }} className="flex gap-2">
                  <Input
                    value={quickBarcode}
                    onChange={(e) => setQuickBarcode(e.target.value)}
                    placeholder="สแกนหรือพิมพ์บาร์โค้ด..."
                    className="font-mono text-sm"
                  />
                  <Button type="submit" size="sm" disabled={!quickBarcode.trim()}>
                    ไป
                  </Button>
                </form>
              </div>
            </div>

            {/* Resume Last Session */}
            {lastBarcode && (
              <button
                onClick={() => navigate('/shooting')}
                className="w-full group rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-50/50 to-card dark:from-card dark:to-card p-4 text-left overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative"
              >
                <div className="absolute inset-y-0 left-0 w-1 bg-amber-500 rounded-l-xl" />
                <div className="flex items-center justify-between pl-2">
                  <div className="flex items-center gap-3">
                    <RotateCcw className="size-4 text-amber-500" />
                    <div>
                      <p className="text-sm font-semibold text-foreground">ถ่ายต่อ: {lastBarcode}</p>
                      <p className="text-2xs text-muted-foreground">กลับไปถ่ายรูปต่อจากที่ค้างไว้</p>
                    </div>
                  </div>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-amber-500 transition-colors" />
                </div>
              </button>
            )}

            <button
              onClick={() => navigate('/gallery')}
              className="w-full group rounded-xl border border-border bg-gradient-to-r from-emerald-50/50 to-card dark:from-card dark:to-card p-5 text-left overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative"
            >
              <div className="absolute inset-y-0 left-0 w-1 bg-emerald-500 rounded-l-xl" />
              <div className="flex items-center justify-between pl-2">
                <div>
                  <div className="size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3 group-hover:bg-emerald-500/20 transition-colors">
                    <Image className="size-5 text-emerald-500" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">ดูแกลเลอรี่</h3>
                  <p className="text-2xs text-muted-foreground mt-1">ดูรูปทั้งหมด ค้นหา กรอง ดาวน์โหลด</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground group-hover:text-emerald-500 transition-colors" />
              </div>
            </button>

            <button
              onClick={() => navigate('/reports')}
              className="w-full group rounded-xl border border-border bg-gradient-to-r from-amber-50/50 to-card dark:from-card dark:to-card p-5 text-left overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative"
            >
              <div className="absolute inset-y-0 left-0 w-1 bg-amber-500 rounded-l-xl" />
              <div className="flex items-center justify-between pl-2">
                <div>
                  <div className="size-10 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3 group-hover:bg-amber-500/20 transition-colors">
                    <TrendingUp className="size-5 text-amber-500" />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">ดูรายงาน</h3>
                  <p className="text-2xs text-muted-foreground mt-1">สรุปภาพรวม ส่งออก HTML/CSV</p>
                </div>
                <ArrowRight className="size-4 text-muted-foreground group-hover:text-amber-500 transition-colors" />
              </div>
            </button>
          </div>
        </div>

        {/* Recent Uploads */}
        {recent.length > 0 && (
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border/50">
              <div className="flex items-center gap-2">
                <Image className="size-4.5 text-emerald-500" />
                <h2 className="text-sm font-semibold text-foreground">อัปโหลดล่าสุด</h2>
              </div>
              <button onClick={() => navigate('/gallery')} className="text-xs text-primary hover:underline font-medium">
                ดูทั้งหมด →
              </button>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-4 lg:grid-cols-8 gap-3">
                {recent.map((p) => (
                  <div key={p.id} onClick={() => navigate('/gallery')}
                    className="group cursor-pointer rounded-lg border border-border overflow-hidden hover:shadow-md transition-all">
                    <div className="aspect-square bg-muted relative">
                      <img src={p.thumbnail_url} alt={p.barcode} className="w-full h-full object-cover group-hover:scale-105 transition-transform" loading="lazy" />
                      <div className={`absolute top-1 right-1 size-2 rounded-full ring-1 ring-card ${
                        p.status === 'done' ? 'bg-emerald-500' : p.status === 'processing' ? 'bg-amber-500 animate-pulse' : 'bg-muted-foreground'
                      }`} />
                    </div>
                    <div className="px-2 py-1.5">
                      <p className="text-2xs font-mono font-semibold text-foreground truncate">{p.barcode}</p>
                      <p className="text-2xs text-muted-foreground">{p.angle}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
