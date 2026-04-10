import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Camera, Image, Package, Clock, Loader } from 'lucide-react';

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
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get<Stats>('/api/stats'),
    refetchInterval: 10_000,
  });

  const { data: daily } = useQuery({
    queryKey: ['stats-daily'],
    queryFn: () => api.get<DailyItem[]>('/api/stats/daily?days=7'),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  const cards = [
    { label: 'สินค้าทั้งหมด', value: stats?.total_products || 0, icon: Package, color: 'text-blue-500' },
    { label: 'รูปทั้งหมด', value: stats?.total_photos || 0, icon: Image, color: 'text-green-500' },
    { label: 'รูปวันนี้', value: stats?.photos_today || 0, icon: Camera, color: 'text-yellow-500' },
    { label: 'กำลังประมวลผล', value: stats?.pending_processing || 0, icon: Loader, color: 'text-orange-500' },
    { label: 'เซสชันที่ทำงาน', value: stats?.active_sessions || 0, icon: Clock, color: 'text-purple-500' },
  ];

  const maxDaily = Math.max(...(daily || []).map((d) => d.count), 1);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-foreground">แดชบอร์ด</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center gap-3 mb-3">
              <card.icon className={`w-5 h-5 ${card.color}`} />
              <span className="text-sm text-muted-foreground">{card.label}</span>
            </div>
            <p className="text-3xl font-bold text-foreground">{card.value.toLocaleString()}</p>
          </div>
        ))}
      </div>

      {/* Daily Upload Chart (simple bar) */}
      {daily && daily.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-sm font-semibold text-muted-foreground mb-4">อัปโหลดรายวัน (7 วัน)</h2>
          <div className="flex items-end gap-2 h-40">
            {daily.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-xs text-muted-foreground">{d.count}</span>
                <div
                  className="w-full bg-primary rounded-t transition-all"
                  style={{ height: `${(d.count / maxDaily) * 100}%`, minHeight: d.count > 0 ? '4px' : '0' }}
                />
                <span className="text-[10px] text-muted-foreground">
                  {new Date(d.date).toLocaleDateString('th-TH', { day: '2-digit', month: 'short' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
