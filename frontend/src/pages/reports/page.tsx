import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Download, FileText, Package, Image, BarChart3 } from 'lucide-react';

interface Summary {
  barcode: string;
  name: string;
  category: string;
  total_photos: number;
  angles: Record<string, number>;
}

export function ReportsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['reports-summary'],
    queryFn: () => api.get<Summary[]>('/api/reports/summary'),
  });
  const summary = data || [];
  const totalPhotos = summary.reduce((a, r) => a + r.total_photos, 0);

  const statCards = [
    { label: 'บาร์โค้ด', value: summary.length, icon: Package, borderColor: 'bg-blue-500', iconBg: 'bg-blue-500/10', iconColor: 'text-blue-500' },
    { label: 'รูปทั้งหมด', value: totalPhotos, icon: Image, borderColor: 'bg-emerald-500', iconBg: 'bg-emerald-500/10', iconColor: 'text-emerald-500' },
    { label: 'มุมถ่าย', value: summary.reduce((a, r) => a + Object.keys(r.angles).length, 0), icon: BarChart3, borderColor: 'bg-amber-500', iconBg: 'bg-amber-500/10', iconColor: 'text-amber-500' },
  ];

  return (
    <div className="p-5 lg:p-7 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">รายงาน</h1>
          <p className="text-sm text-muted-foreground mt-1">สรุปภาพสินค้าทั้งหมด</p>
        </div>
        <div className="flex gap-2">
          <a href="/api/reports/export/html" target="_blank"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 shadow-sm transition-colors">
            <FileText className="size-4" /> HTML
          </a>
          <a href="/api/reports/export/csv" target="_blank"
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
            <Download className="size-4" /> CSV
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {statCards.map((card) => (
          <div key={card.label} className="rounded-xl border border-border bg-card overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
            <div className="p-5 relative">
              <div className={`absolute inset-y-0 left-0 w-1 ${card.borderColor} rounded-l-xl`} />
              <div className="pl-2 flex items-center gap-4">
                <div className={`size-10 rounded-xl ${card.iconBg} flex items-center justify-center shrink-0`}>
                  <card.icon className={`size-5 ${card.iconColor}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground tabular-nums">{card.value}</p>
                  <p className="text-2xs text-muted-foreground font-medium uppercase tracking-wider">{card.label}</p>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="rounded-xl border border-border bg-card p-5 animate-pulse">
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-muted rounded" />
            ))}
          </div>
        </div>
      ) : summary.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="size-16 rounded-2xl bg-muted flex items-center justify-center mb-5">
            <BarChart3 className="size-7 text-muted-foreground/60" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">ยังไม่มีข้อมูล</h3>
          <p className="text-sm text-muted-foreground">อัปโหลดรูปภาพก่อนเพื่อดูรายงาน</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/40 border-b border-border/60 text-left">
                  <th className="px-5 pb-3 pt-4 font-medium text-2xs text-muted-foreground uppercase tracking-wider">บาร์โค้ด</th>
                  <th className="px-5 pb-3 pt-4 font-medium text-2xs text-muted-foreground uppercase tracking-wider">ชื่อ</th>
                  <th className="px-5 pb-3 pt-4 font-medium text-2xs text-muted-foreground uppercase tracking-wider">หมวดหมู่</th>
                  <th className="px-5 pb-3 pt-4 font-medium text-2xs text-muted-foreground uppercase tracking-wider text-right">จำนวนรูป</th>
                  <th className="px-5 pb-3 pt-4 font-medium text-2xs text-muted-foreground uppercase tracking-wider">มุมถ่าย</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((r) => (
                  <tr key={r.barcode} className="border-b border-border/40 transition-colors hover:bg-muted/50">
                    <td className="px-5 py-3.5">
                      <span className="font-mono font-semibold text-primary">{r.barcode}</span>
                    </td>
                    <td className="px-5 py-3.5 text-foreground">{r.name || '—'}</td>
                    <td className="px-5 py-3.5 text-muted-foreground">{r.category || '—'}</td>
                    <td className="px-5 py-3.5 text-right">
                      <span className="inline-flex items-center justify-center min-w-[28px] h-6 rounded-md bg-primary/10 text-primary text-xs font-bold">
                        {r.total_photos}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(r.angles).map(([angle, count]) => (
                          <span key={angle} className="px-2 py-0.5 rounded-md bg-muted text-2xs text-muted-foreground font-medium">
                            {angle}:{count}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
