import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Download, FileText } from 'lucide-react';

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

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">รายงาน</h1>
        <div className="flex gap-2">
          <a href="/api/reports/export/html" target="_blank"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-accent/10">
            <FileText className="w-4 h-4" /> ส่งออก HTML
          </a>
          <a href="/api/reports/export/csv" target="_blank"
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-accent/10">
            <Download className="w-4 h-4" /> ส่งออก CSV
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">บาร์โค้ดทั้งหมด</p>
          <p className="text-3xl font-bold text-foreground mt-1">{summary.length}</p>
        </div>
        <div className="rounded-xl border border-border bg-card p-5">
          <p className="text-sm text-muted-foreground">รูปทั้งหมด</p>
          <p className="text-3xl font-bold text-foreground mt-1">{totalPhotos}</p>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3 text-muted-foreground font-medium">บาร์โค้ด</th>
                <th className="text-left p-3 text-muted-foreground font-medium">ชื่อ</th>
                <th className="text-left p-3 text-muted-foreground font-medium">หมวดหมู่</th>
                <th className="text-right p-3 text-muted-foreground font-medium">จำนวนรูป</th>
                <th className="text-left p-3 text-muted-foreground font-medium">มุมถ่าย</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((r) => (
                <tr key={r.barcode} className="border-t border-border hover:bg-muted/20">
                  <td className="p-3 font-mono text-foreground">{r.barcode}</td>
                  <td className="p-3 text-foreground">{r.name || '-'}</td>
                  <td className="p-3 text-muted-foreground">{r.category || '-'}</td>
                  <td className="p-3 text-right font-semibold text-foreground">{r.total_photos}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(r.angles).map(([angle, count]) => (
                        <span key={angle} className="px-1.5 py-0.5 rounded bg-muted text-xs text-muted-foreground">
                          {angle}: {count}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
