import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Camera, Star, AlertTriangle, TrendingUp } from 'lucide-react';

interface EmployeeStats {
  user_id: number;
  display_name: string;
  photo_count: number;
  barcode_count: number;
  avg_quality: number | null;
  issues_count: number;
}

export function EmployeeDashboard() {
  const { data } = useQuery({
    queryKey: ['employee-stats'],
    queryFn: () => api.get<EmployeeStats[]>('/api/stats/employees'),
    refetchInterval: 30_000,
  });

  const employees = data || [];

  if (employees.length === 0) {
    return (
      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-3">
          <TrendingUp className="size-4 text-primary" /> ผลงานพนักงาน
        </h2>
        <p className="text-sm text-muted-foreground">ยังไม่มีข้อมูล</p>
      </section>
    );
  }

  const maxPhotos = Math.max(...employees.map((e) => e.photo_count), 1);

  return (
    <section className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="p-5 border-b border-border/50">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <TrendingUp className="size-4 text-primary" /> ผลงานพนักงาน
        </h2>
      </div>
      <div className="divide-y divide-border/50">
        {employees.map((emp) => (
          <div key={emp.user_id} className="p-4 flex items-center gap-4">
            <div className="size-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <span className="text-sm font-bold text-primary">
                {emp.display_name?.charAt(0) || '?'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">{emp.display_name || `User #${emp.user_id}`}</span>
                {emp.avg_quality && (
                  <span className="inline-flex items-center gap-0.5 text-2xs text-amber-500">
                    <Star className="size-3 fill-amber-500" />
                    {emp.avg_quality.toFixed(1)}
                  </span>
                )}
                {emp.issues_count > 0 && (
                  <span className="inline-flex items-center gap-0.5 text-2xs text-red-500">
                    <AlertTriangle className="size-3" />
                    {emp.issues_count}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3 mt-1">
                <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${(emp.photo_count / maxPhotos) * 100}%` }} />
                </div>
                <span className="text-2xs text-muted-foreground shrink-0 w-16 text-right">
                  <Camera className="size-3 inline mr-1" />{emp.photo_count} รูป
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
