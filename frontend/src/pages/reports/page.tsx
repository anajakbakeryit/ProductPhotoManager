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
  const totalAngles = summary.reduce((a, r) => a + Object.keys(r.angles).length, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">รายงาน</h1>
          <p className="text-sm text-muted-foreground mt-1">สรุปภาพสินค้าทั้งหมด</p>
        </div>
        <div className="flex gap-2">
          <a href="/api/reports/export/html" target="_blank"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-violet-600 text-white text-sm font-medium shadow-lg shadow-blue-500/25 hover:shadow-xl transition-shadow">
            <FileText className="w-4 h-4" /> HTML
          </a>
          <a href="/api/reports/export/csv" target="_blank"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-500 text-white text-sm font-medium shadow-lg shadow-emerald-500/25 hover:shadow-xl transition-shadow">
            <Download className="w-4 h-4" /> CSV
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl border border-border bg-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <Package className="w-6 h-6 text-white" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">บาร์โค้ด</p>
            <p className="text-2xl font-bold text-foreground">{summary.length}</p>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/25">
            <Image className="w-6 h-6 text-white" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">รูปทั้งหมด</p>
            <p className="text-2xl font-bold text-foreground">{totalPhotos}</p>
          </div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/25">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">มุมถ่าย</p>
            <p className="text-2xl font-bold text-foreground">{totalAngles}</p>
          </div>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="rounded-2xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/50 border-b border-border">
                <th className="text-left p-4 text-muted-foreground font-semibold">บาร์โค้ด</th>
                <th className="text-left p-4 text-muted-foreground font-semibold">ชื่อ</th>
                <th className="text-left p-4 text-muted-foreground font-semibold">หมวดหมู่</th>
                <th className="text-right p-4 text-muted-foreground font-semibold">จำนวนรูป</th>
                <th className="text-left p-4 text-muted-foreground font-semibold">มุมถ่าย</th>
              </tr>
            </thead>
            <tbody>
              {summary.map((r, i) => (
                <tr key={r.barcode} className={`border-b border-border hover:bg-muted/30 transition-colors ${i % 2 === 0 ? '' : 'bg-muted/10'}`}>
                  <td className="p-4">
                    <span className="font-mono font-semibold text-primary">{r.barcode}</span>
                  </td>
                  <td className="p-4 text-foreground">{r.name || '—'}</td>
                  <td className="p-4 text-muted-foreground">{r.category || '—'}</td>
                  <td className="p-4 text-right">
                    <span className="inline-flex items-center justify-center min-w-[32px] h-7 rounded-full bg-primary/10 text-primary text-xs font-bold">
                      {r.total_photos}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(r.angles).map(([angle, count]) => (
                        <span key={angle} className="px-2 py-0.5 rounded-md bg-muted text-xs text-muted-foreground font-medium">
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
      )}
    </div>
  );
}
