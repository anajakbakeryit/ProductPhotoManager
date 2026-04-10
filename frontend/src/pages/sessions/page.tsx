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
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">ประวัติเซสชัน</h1>
        <p className="text-sm text-muted-foreground mt-1">ดูประวัติการทำงานย้อนหลัง</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-16">
          <Clock className="w-12 h-12 text-muted-foreground/20 mx-auto mb-4" />
          <p className="text-muted-foreground">ยังไม่มีเซสชัน</p>
        </div>
      ) : (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[19px] top-0 bottom-0 w-0.5 bg-border" />

          <div className="space-y-4">
            {sessions.map((s) => (
              <div key={s.id} className="relative flex gap-5">
                {/* Timeline dot */}
                <div className={`relative z-10 mt-5 w-[10px] h-[10px] rounded-full ring-4 ring-background shrink-0 ${
                  s.is_active ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse' : 'bg-muted-foreground/30'
                }`} style={{ marginLeft: '14px' }} />

                {/* Card */}
                <div className={`flex-1 rounded-2xl border bg-card p-5 transition-all hover:shadow-md ${
                  s.is_active ? 'border-emerald-500/30 shadow-lg shadow-emerald-500/5' : 'border-border'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-foreground">เซสชัน #{s.id}</span>
                      {s.is_active && (
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 text-xs font-semibold">
                          กำลังทำงาน
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(s.started_at).toLocaleDateString('th-TH', { day: '2-digit', month: 'short', year: '2-digit' })}
                    </div>
                  </div>

                  <div className="flex gap-6">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Camera className="w-4 h-4 text-blue-500" />
                      </div>
                      <div>
                        <p className="text-lg font-bold text-foreground">{s.photo_count}</p>
                        <p className="text-[10px] text-muted-foreground">รูป</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
                        <Hash className="w-4 h-4 text-violet-500" />
                      </div>
                      <div>
                        <p className="text-lg font-bold text-foreground">{s.barcode_count}</p>
                        <p className="text-[10px] text-muted-foreground">บาร์โค้ด</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
                        <Clock className="w-4 h-4 text-amber-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">
                          {new Date(s.started_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}
                          {s.ended_at && ` — ${new Date(s.ended_at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' })}`}
                        </p>
                        <p className="text-[10px] text-muted-foreground">เวลา</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
