import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Download, FileText, Package, Image, BarChart3, ClipboardCheck, Check, X as XIcon, Store, ShoppingBag, Facebook } from 'lucide-react';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';

const QC_ANGLES = ['front', 'back', 'left', 'right', 'top', 'bottom', 'detail', 'package'];

interface Summary {
  barcode: string;
  name: string;
  category: string;
  total_photos: number;
  angles: Record<string, number>;
}

export function ReportsPage() {
  const [showQC, setShowQC] = useState(false);
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
    <>
      <Toolbar>
        <ToolbarHeading title="รายงาน" description="สรุปภาพสินค้าทั้งหมด" />
        <ToolbarActions>
          <Button variant={showQC ? 'default' : 'outline'} onClick={() => setShowQC(!showQC)}>
            <ClipboardCheck className="size-4" />
            QC
          </Button>
          <Button variant="outline" asChild>
            <a href="/api/reports/export/csv" target="_blank">
              <Download className="size-4" /> CSV
            </a>
          </Button>
          <Button asChild>
            <a href="/api/reports/export/html" target="_blank">
              <FileText className="size-4" /> HTML
            </a>
          </Button>
        </ToolbarActions>
      </Toolbar>

    <div className="container pb-7 space-y-5">

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

      {/* QC Checklist */}
      {showQC && summary.length > 0 && (
        <div className="rounded-xl border border-primary/20 bg-gradient-to-br from-primary/5 to-card overflow-hidden">
          <div className="flex items-center gap-2 p-4 border-b border-border/50">
            <ClipboardCheck className="size-4.5 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">QC Checklist — ตรวจสอบมุมถ่าย</h2>
            <span className="ml-auto text-2xs text-muted-foreground">
              {summary.filter((r) => QC_ANGLES.every((a) => r.angles[a])).length}/{summary.length} ครบทุกมุม
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 text-left">
                  <th className="px-4 py-2.5 text-2xs font-medium text-muted-foreground uppercase">บาร์โค้ด</th>
                  {QC_ANGLES.map((a) => (
                    <th key={a} className="px-2 py-2.5 text-2xs font-medium text-muted-foreground uppercase text-center w-16">{a}</th>
                  ))}
                  <th className="px-4 py-2.5 text-2xs font-medium text-muted-foreground uppercase text-center">สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((r) => {
                  const done = QC_ANGLES.filter((a) => r.angles[a]).length;
                  const complete = done === QC_ANGLES.length;
                  return (
                    <tr key={r.barcode} className={`border-b border-border/30 ${complete ? 'bg-emerald-500/5' : ''}`}>
                      <td className="px-4 py-2.5 font-mono font-semibold text-foreground">{r.barcode}</td>
                      {QC_ANGLES.map((a) => (
                        <td key={a} className="px-2 py-2.5 text-center">
                          {r.angles[a] ? (
                            <Check className="size-4 text-emerald-500 mx-auto" />
                          ) : (
                            <XIcon className="size-4 text-muted-foreground/30 mx-auto" />
                          )}
                        </td>
                      ))}
                      <td className="px-4 py-2.5 text-center">
                        {complete ? (
                          <span className="text-2xs font-semibold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">ครบ</span>
                        ) : (
                          <span className="text-2xs font-semibold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded-full">{done}/{QC_ANGLES.length}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

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
      {/* Marketplace Export */}
      {summary.length > 0 && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="flex items-center gap-2 p-5 border-b border-border/50">
            <Store className="size-4.5 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">ส่งออกสำหรับ Marketplace</h2>
          </div>
          <div className="p-5 grid sm:grid-cols-3 gap-4">
            {[
              { name: 'Shopee', icon: ShoppingBag, color: 'orange', spec: 'JPG 800×800, พื้นหลังขาว, max 2MB', size: 'M', variant: 'cutout' },
              { name: 'Lazada', icon: Store, color: 'blue', spec: 'JPG 1000×1000, พื้นหลังขาว, max 3MB', size: 'L', variant: 'cutout' },
              { name: 'Facebook', icon: Facebook, color: 'sky', spec: 'JPG 1200×1200, ต้นฉบับ + ลายน้ำ', size: 'L', variant: 'watermarked_original' },
            ].map((mp) => (
              <button
                key={mp.name}
                onClick={async () => {
                  toast.info(`กำลังสร้าง ZIP สำหรับ ${mp.name}...`);
                  try {
                    const allPhotos = await api.get<{ data: { id: number }[] }>(`/api/gallery?limit=200`);
                    const ids = allPhotos.data.map((p) => p.id);
                    const blob = await api.postBlob('/api/photos/download-zip', {
                      photo_ids: ids, variant: mp.variant, size: mp.size,
                    });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = `${mp.name.toLowerCase()}-export.zip`; a.click();
                    URL.revokeObjectURL(url);
                    toast.success(`ส่งออก ${mp.name} สำเร็จ`);
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : 'ส่งออกไม่สำเร็จ');
                  }
                }}
                className={`group rounded-xl border border-${mp.color}-500/20 bg-gradient-to-br from-${mp.color}-50/30 to-card dark:from-card dark:to-${mp.color}-950/10 p-5 text-left hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 relative overflow-hidden`}
              >
                <div className={`absolute inset-y-0 left-0 w-1 bg-${mp.color}-500 rounded-l-xl`} />
                <div className="pl-2">
                  <div className={`size-10 rounded-xl bg-${mp.color}-500/10 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
                    <mp.icon className={`size-5 text-${mp.color}-500`} />
                  </div>
                  <h3 className="text-sm font-semibold text-foreground">{mp.name}</h3>
                  <p className="text-2xs text-muted-foreground mt-1">{mp.spec}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
    </>
  );
}
