import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Clock, Camera, Hash } from 'lucide-react';

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
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-foreground">ประวัติเซสชัน</h1>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : sessions.length === 0 ? (
        <p className="text-muted-foreground py-8 text-center">ยังไม่มีเซสชัน</p>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <div key={s.id} className="rounded-xl border border-border bg-card p-4 flex items-center gap-6">
              <div className="flex items-center gap-2">
                {s.is_active ? (
                  <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
                ) : (
                  <span className="w-2.5 h-2.5 rounded-full bg-muted" />
                )}
                <span className="text-sm font-medium text-foreground">
                  #{s.id}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Clock className="w-3.5 h-3.5" />
                {new Date(s.started_at).toLocaleString('th-TH')}
                {s.ended_at && ` — ${new Date(s.ended_at).toLocaleTimeString('th-TH')}`}
              </div>
              <div className="flex items-center gap-1.5 text-sm text-foreground">
                <Camera className="w-3.5 h-3.5 text-muted-foreground" />
                {s.photo_count} รูป
              </div>
              <div className="flex items-center gap-1.5 text-sm text-foreground">
                <Hash className="w-3.5 h-3.5 text-muted-foreground" />
                {s.barcode_count} บาร์โค้ด
              </div>
              {s.is_active && (
                <span className="ml-auto px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-semibold">
                  กำลังทำงาน
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
