import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Clock, Camera, Hash, Calendar } from 'lucide-react';

interface SessionItem {
  id: number;
  started_at: string;
  ended_at: string | null;
  photo_count: number;
  barcode_count: number;
  is_active: boolean;
}

export function SessionsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.get<{ data: SessionItem[] }>('/api/sessions'),
  });
  const sessions = data?.data || [];

  return (
    <div className="p-5 lg:p-7 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">ประวัติเซสชัน</h1>
        <p className="text-sm text-muted-foreground mt-1">ดูประวัติการทำงานย้อนหลัง</p>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-card p-5 animate-pulse">
              <div className="flex gap-4">
                <div className="h-4 bg-muted rounded w-24" />
                <div className="h-4 bg-muted rounded w-32" />
                <div className="h-4 bg-muted rounded w-16" />
              </div>
            </div>
          ))}
        </div>
      ) : sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="size-16 rounded-2xl bg-muted flex items-center justify-center mb-5">
            <Clock className="size-7 text-muted-foreground/60" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">ยังไม่มีเซสชัน</h3>
          <p className="text-sm text-muted-foreground">เริ่มถ่ายรูปเพื่อสร้างเซสชันแรก</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`rounded-xl border bg-card overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 ${
                s.is_active ? 'border-emerald-500/30' : 'border-border'
              }`}
            >
              <div className="p-5 relative">
                {/* Left border */}
                <div className={`absolute inset-y-0 left-0 w-1 rounded-l-xl ${s.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/20'}`} />

                <div className="pl-3 flex items-center gap-6 flex-wrap">
                  <div className="flex items-center gap-2.5">
                    <span className="text-sm font-bold text-foreground">#{s.id}</span>
                    {s.is_active && (
                      <span className="text-2xs font-semibold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        กำลังทำงาน
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <Calendar className="size-3.5" />
                    {new Date(s.started_at).toLocaleString('th-TH', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    {s.ended_at && ` — ${new Date(s.ended_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}`}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <div className="size-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
                      <Camera className="size-3.5 text-blue-500" />
                    </div>
                    <span className="text-sm font-semibold text-foreground">{s.photo_count}</span>
                    <span className="text-2xs text-muted-foreground">รูป</span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <div className="size-7 rounded-lg bg-violet-500/10 flex items-center justify-center">
                      <Hash className="size-3.5 text-violet-500" />
                    </div>
                    <span className="text-sm font-semibold text-foreground">{s.barcode_count}</span>
                    <span className="text-2xs text-muted-foreground">บาร์โค้ด</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
