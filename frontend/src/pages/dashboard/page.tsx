import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useNavigate } from 'react-router';
import {
  Camera, Image, Package, Loader2, Clock,
  ArrowRight, TrendingUp, Zap,
} from 'lucide-react';

interface Stats {
  total_products: number;
  total_photos: number;
  photos_today: number;
  pending_processing: number;
  active_sessions: number;
}

interface DailyItem {
  date: string;
  count: number;
}

export function DashboardPage() {
  const navigate = useNavigate();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<Stats>('/api/stats'),
    refetchInterval: 10_000,
  });

  const { data: daily } = useQuery({
    queryKey: ['stats-daily'],
    queryFn: () => api.get<DailyItem[]>('/api/stats/daily?days=7'),
  });

  const maxDaily = Math.max(...(daily || []).map((d) => d.count), 1);

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
    <div className="p-5 lg:p-7 space-y-5 lg:space-y-7">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">แดชบอร์ด</h1>
        <p className="text-sm text-muted-foreground mt-1">ภาพรวมการถ่ายภาพสินค้า</p>
      </div>

      {/* KPI Cards — BESTCHOICE style with left border */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className={`group cursor-pointer rounded-xl border border-border overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 ${card.cardBg}`}
          >
            <div className="p-5 relative">
              {/* Left color border */}
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
        <div className="lg:col-span-2 rounded-xl border border-border bg-card dark:bg-card overflow-hidden">
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
            {daily && daily.length > 0 ? (
              <div className="flex items-end gap-3 h-44">
                {daily.map((d) => (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-2">
                    <span className="text-xs font-bold text-foreground tabular-nums">{d.count}</span>
                    <div className="w-full relative rounded-t-lg bg-muted/50 overflow-hidden">
                      <div
                        className="w-full bg-gradient-to-t from-primary to-primary/70 rounded-t-lg transition-all duration-700 ease-out"
                        style={{ height: `${Math.max((d.count / maxDaily) * 140, d.count > 0 ? 8 : 0)}px` }}
                      />
                    </div>
                    <span className="text-2xs text-muted-foreground whitespace-nowrap">
                      {new Date(d.date).toLocaleDateString('th-TH', { day: '2-digit', month: 'short' })}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-44 flex flex-col items-center justify-center">
                <div className="size-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
                  <TrendingUp className="size-5 text-muted-foreground/60" />
                </div>
                <p className="text-sm text-muted-foreground">ยังไม่มีข้อมูล</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="space-y-4">
          <button
            onClick={() => navigate('/shooting')}
            className="w-full group rounded-xl border border-border bg-gradient-to-r from-blue-50/50 to-card dark:from-card dark:to-card p-5 text-left overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative"
          >
            <div className="absolute inset-y-0 left-0 w-1 bg-primary rounded-l-xl" />
            <div className="flex items-center justify-between pl-2">
              <div>
                <div className={`size-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors`}>
                  <Camera className="size-5 text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-foreground">เริ่มถ่ายรูป</h3>
                <p className="text-2xs text-muted-foreground mt-1">สแกนบาร์โค้ด → เลือกมุม → อัปโหลด</p>
              </div>
              <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </button>

          <button
            onClick={() => navigate('/gallery')}
            className="w-full group rounded-xl border border-border bg-gradient-to-r from-emerald-50/50 to-card dark:from-card dark:to-card p-5 text-left overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative"
          >
            <div className="absolute inset-y-0 left-0 w-1 bg-emerald-500 rounded-l-xl" />
            <div className="flex items-center justify-between pl-2">
              <div>
                <div className={`size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3 group-hover:bg-emerald-500/20 transition-colors`}>
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
                <div className={`size-10 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3 group-hover:bg-amber-500/20 transition-colors`}>
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
    </div>
  );
}
