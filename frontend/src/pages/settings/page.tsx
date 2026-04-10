import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Save, Upload } from 'lucide-react';
import { UsersSection } from './users-section';

export function SettingsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<{ config: Record<string, unknown>; watermark_url: string | null }>('/api/settings'),
  });

  const [config, setConfig] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (data?.config) setConfig(data.config);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (cfg: Record<string, unknown>) => api.put('/api/settings', { config: cfg }),
    onSuccess: () => {
      toast.success('บันทึกการตั้งค่าแล้ว');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const uploadWmMutation = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append('file', file);
      return api.upload('/api/settings/watermark', fd);
    },
    onSuccess: () => {
      toast.success('อัปโหลดลายน้ำแล้ว');
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const update = (key: string, value: unknown) => setConfig((prev) => ({ ...prev, [key]: value }));

  if (isLoading) return <div className="p-6 text-muted-foreground">กำลังโหลด...</div>;

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">ตั้งค่า</h1>
        <button
          onClick={() => saveMutation.mutate(config)}
          disabled={saveMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {saveMutation.isPending ? 'กำลังบันทึก...' : 'บันทึก'}
        </button>
      </div>

      {/* Pipeline */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">ขั้นตอนประมวลผล</h2>
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={!!config.enable_cutout}
            onChange={(e) => update('enable_cutout', e.target.checked)}
            className="w-4 h-4 rounded border-border" />
          <span className="text-sm text-foreground">ลบพื้นหลัง (rembg)</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={!!config.enable_watermark}
            onChange={(e) => update('enable_watermark', e.target.checked)}
            className="w-4 h-4 rounded border-border" />
          <span className="text-sm text-foreground">ลายน้ำบนภาพลบพื้นหลัง</span>
        </label>
        <label className="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={!!config.enable_wm_original}
            onChange={(e) => update('enable_wm_original', e.target.checked)}
            className="w-4 h-4 rounded border-border" />
          <span className="text-sm text-foreground">ลายน้ำบนภาพต้นฉบับ</span>
        </label>
      </section>

      {/* Watermark */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">ลายน้ำ</h2>
        {data?.watermark_url && (
          <img src={data.watermark_url} alt="watermark" className="h-16 object-contain bg-muted rounded p-2" />
        )}
        <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-dashed border-border cursor-pointer hover:border-primary transition-colors w-fit">
          <Upload className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">อัปโหลดไฟล์ PNG</span>
          <input type="file" accept=".png" className="hidden"
            onChange={(e) => e.target.files?.[0] && uploadWmMutation.mutate(e.target.files[0])} />
        </label>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">ความโปร่งใส (%)</label>
            <input type="range" min={10} max={100} value={Number(config.watermark_opacity || 40)}
              onChange={(e) => update('watermark_opacity', Number(e.target.value))}
              className="w-full" />
            <span className="text-xs text-muted-foreground">{String(config.watermark_opacity || 40)}%</span>
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">ขนาด (%)</label>
            <input type="range" min={5} max={50} value={Number(config.watermark_scale || 20)}
              onChange={(e) => update('watermark_scale', Number(e.target.value))}
              className="w-full" />
            <span className="text-xs text-muted-foreground">{String(config.watermark_scale || 20)}%</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-muted-foreground mb-1">ตำแหน่ง</label>
            <select value={String(config.watermark_position || 'bottom-right')}
              onChange={(e) => update('watermark_position', e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm">
              <option value="bottom-right">ขวาล่าง</option>
              <option value="bottom-left">ซ้ายล่าง</option>
              <option value="top-right">ขวาบน</option>
              <option value="top-left">ซ้ายบน</option>
              <option value="center">ตรงกลาง</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-muted-foreground mb-1">ระยะขอบ (px)</label>
            <input type="number" min={0} max={500} value={Number(config.watermark_margin || 30)}
              onChange={(e) => update('watermark_margin', Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm" />
          </div>
        </div>
      </section>

      {/* Background Color */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">สีพื้นหลัง (สำหรับ flatten)</h2>
        <div className="flex gap-3">
          {['R', 'G', 'B'].map((ch, i) => (
            <div key={ch}>
              <label className="block text-xs text-muted-foreground mb-1">{ch}</label>
              <input type="number" min={0} max={255}
                value={Array.isArray(config.bg_color) ? (config.bg_color as number[])[i] : 255}
                onChange={(e) => {
                  const bg = Array.isArray(config.bg_color) ? [...(config.bg_color as number[])] : [255, 255, 255];
                  bg[i] = Number(e.target.value);
                  update('bg_color', bg);
                }}
                className="w-20 px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm" />
            </div>
          ))}
          <div className="flex items-end">
            <div className="w-10 h-10 rounded border border-border" style={{
              backgroundColor: Array.isArray(config.bg_color)
                ? `rgb(${(config.bg_color as number[]).join(',')})`
                : '#ffffff',
            }} />
          </div>
        </div>
      </section>

      {/* 360 */}
      <section className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">360°</h2>
        <div>
          <label className="block text-xs text-muted-foreground mb-1">จำนวนเฟรมเริ่มต้น</label>
          <select value={String(config.spin360_total || 24)}
            onChange={(e) => update('spin360_total', Number(e.target.value))}
            className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm">
            <option value="12">12</option>
            <option value="24">24</option>
            <option value="36">36</option>
            <option value="72">72</option>
          </select>
        </div>
      </section>

      {/* Users */}
      <UsersSection />
    </div>
  );
}
