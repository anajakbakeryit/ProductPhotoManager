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
      gradient: 'from-blue-500 to-violet-600', shadow: 'shadow-blue-500/25',
    },
    {
      label: 'รูปทั้งหมด', value: stats?.total_photos || 0, icon: Image,
      gradient: 'from-emerald-400 to-teal-500', shadow: 'shadow-emerald-500/25',
    },
    {
      label: 'สินค้า', value: stats?.total_products || 0, icon: Package,
      gradient: 'from-amber-400 to-orange-500', shadow: 'shadow-amber-500/25',
    },
    {
      label: 'กำลังประมวลผล', value: stats?.pending_processing || 0, icon: Zap,
      gradient: 'from-rose-400 to-red-500', shadow: 'shadow-rose-500/25',
    },
    {
      label: 'เซสชัน', value: stats?.active_sessions || 0, icon: Clock,
      gradient: 'from-fuchsia-400 to-purple-600', shadow: 'shadow-fuchsia-500/25',
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
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">แดชบอร์ด</h1>
          <p className="text-muted-foreground text-sm mt-1">ภาพรวมการถ่ายภาพสินค้า</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className={`relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br ${card.gradient} text-white shadow-lg ${card.shadow} transition-transform hover:scale-[1.02]`}
          >
            <div className="absolute top-3 right-3 opacity-20">
              <card.icon className="w-12 h-12" />
            </div>
            <p className="text-sm text-white/80 font-medium">{card.label}</p>
            <p className="text-3xl font-bold mt-2">{card.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Chart + Quick Actions row */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Daily Chart */}
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold text-foreground">อัปโหลดรายวัน</h2>
            </div>
            <span className="text-xs text-muted-foreground">7 วันล่าสุด</span>
          </div>

          {daily && daily.length > 0 ? (
            <div className="flex items-end gap-3 h-48">
              {daily.map((d) => (
                <div key={d.date} className="flex-1 flex flex-col items-center gap-2">
                  <span className="text-xs font-semibold text-foreground">{d.count}</span>
                  <div className="w-full relative overflow-hidden rounded-t-lg bg-muted">
                    <div
                      className="w-full bg-gradient-to-t from-blue-500 to-violet-500 rounded-t-lg transition-all duration-500"
                      style={{ height: `${Math.max((d.count / maxDaily) * 160, d.count > 0 ? 8 : 0)}px` }}
                    />
                  </div>
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(d.date).toLocaleDateString('th-TH', { day: '2-digit', month: 'short' })}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-muted-foreground">
              ยังไม่มีข้อมูล
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="space-y-4">
          <button
            onClick={() => navigate('/shooting')}
            className="w-full group rounded-2xl border border-border bg-card p-6 text-left hover:border-primary hover:shadow-lg hover:shadow-primary/10 transition-all"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center mb-3">
                  <Camera className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-base font-semibold text-foreground">เริ่มถ่ายรูป</h3>
                <p className="text-sm text-muted-foreground mt-1">สแกนบาร์โค้ด → เลือกมุม → อัปโหลด</p>
              </div>
              <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
          </button>

          <button
            onClick={() => navigate('/gallery')}
            className="w-full group rounded-2xl border border-border bg-card p-6 text-left hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/10 transition-all"
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center mb-3">
                  <Image className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-base font-semibold text-foreground">ดูแกลเลอรี่</h3>
                <p className="text-sm text-muted-foreground mt-1">ดูรูปทั้งหมด ค้นหา กรอง ดาวน์โหลด</p>
              </div>
              <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-emerald-500 transition-colors" />
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
