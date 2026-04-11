import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Save, Upload } from 'lucide-react';
import { UsersSection } from './users-section';
import { EmployeeDashboard } from './employee-dashboard';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Slider, SliderThumb } from '@/components/ui/slider';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

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
    <>
      <Toolbar>
        <ToolbarHeading title="ตั้งค่า" description="ตั้งค่าระบบประมวลผลภาพ" />
        <ToolbarActions>
          <Button
            onClick={() => saveMutation.mutate(config)}
            disabled={saveMutation.isPending}
          >
            <Save className="size-4" />
            {saveMutation.isPending ? 'กำลังบันทึก...' : 'บันทึก'}
          </Button>
        </ToolbarActions>
      </Toolbar>

    <div className="container pb-7 max-w-3xl space-y-6">

      {/* Pipeline */}
      <section className="rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-50/50 to-card dark:from-card dark:to-blue-950/10 p-5 space-y-5 relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-blue-500 rounded-l-xl" />
        <h2 className="text-sm font-semibold text-foreground pl-2 flex items-center gap-2">
          <span className="text-blue-500">⚡</span> ขั้นตอนประมวลผล
        </h2>
        <div className="space-y-4 pl-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="cutout" className="text-sm cursor-pointer">ลบพื้นหลัง (rembg)</Label>
            <Switch id="cutout" checked={!!config.enable_cutout}
              onCheckedChange={(v) => update('enable_cutout', v)} />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="wm" className="text-sm cursor-pointer">ลายน้ำบนภาพลบพื้นหลัง</Label>
            <Switch id="wm" checked={!!config.enable_watermark}
              onCheckedChange={(v) => update('enable_watermark', v)} />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="wm-orig" className="text-sm cursor-pointer">ลายน้ำบนภาพต้นฉบับ</Label>
            <Switch id="wm-orig" checked={!!config.enable_wm_original}
              onCheckedChange={(v) => update('enable_wm_original', v)} />
          </div>
        </div>
      </section>

      {/* Watermark */}
      <section className="rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-50/50 to-card dark:from-card dark:to-violet-950/10 p-5 space-y-5 relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-violet-500 rounded-l-xl" />
        <h2 className="text-sm font-semibold text-foreground pl-2 flex items-center gap-2">
          <span className="text-violet-500">💧</span> ลายน้ำ
        </h2>
        <div className="pl-2 space-y-5">
          {data?.watermark_url && (
            <img src={data.watermark_url} alt="watermark" className="h-16 object-contain bg-muted rounded-lg p-2" />
          )}
          <label className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-dashed border-border cursor-pointer hover:border-primary transition-colors w-fit">
            <Upload className="size-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">อัปโหลดไฟล์ PNG</span>
            <input type="file" accept=".png" className="hidden"
              onChange={(e) => e.target.files?.[0] && uploadWmMutation.mutate(e.target.files[0])} />
          </label>

          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">ความโปร่งใส</Label>
                <span className="text-xs font-mono text-primary font-bold">{String(config.watermark_opacity || 40)}%</span>
              </div>
              <Slider
                value={[Number(config.watermark_opacity || 40)]}
                min={10} max={100} step={5}
                onValueChange={([v]) => update('watermark_opacity', v)}
              >
                <SliderThumb />
              </Slider>
            </div>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs">ขนาด</Label>
                <span className="text-xs font-mono text-primary font-bold">{String(config.watermark_scale || 20)}%</span>
              </div>
              <Slider
                value={[Number(config.watermark_scale || 20)]}
                min={5} max={50} step={5}
                onValueChange={([v]) => update('watermark_scale', v)}
              >
                <SliderThumb />
              </Slider>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="space-y-1.5">
              <Label className="text-xs">ตำแหน่ง</Label>
              <Select
                value={String(config.watermark_position || 'bottom-right')}
                onValueChange={(v) => update('watermark_position', v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bottom-right">ขวาล่าง</SelectItem>
                  <SelectItem value="bottom-left">ซ้ายล่าง</SelectItem>
                  <SelectItem value="top-right">ขวาบน</SelectItem>
                  <SelectItem value="top-left">ซ้ายบน</SelectItem>
                  <SelectItem value="center">ตรงกลาง</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">ระยะขอบ (px)</Label>
              <Input
                type="number" min={0} max={500}
                value={Number(config.watermark_margin || 30)}
                onChange={(e) => update('watermark_margin', Number(e.target.value))}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Background Color */}
      <section className="rounded-xl border border-emerald-500/20 bg-gradient-to-br from-emerald-50/50 to-card dark:from-card dark:to-emerald-950/10 p-5 space-y-4 relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-emerald-500 rounded-l-xl" />
        <h2 className="text-sm font-semibold text-foreground pl-2 flex items-center gap-2">
          <span className="text-emerald-500">🎨</span> สีพื้นหลัง
        </h2>
        <div className="flex gap-3 pl-2 items-end">
          {['R', 'G', 'B'].map((ch, i) => (
            <div key={ch} className="space-y-1.5">
              <Label className="text-xs">{ch}</Label>
              <Input
                type="number" min={0} max={255}
                className="w-20"
                value={Array.isArray(config.bg_color) ? (config.bg_color as number[])[i] : 255}
                onChange={(e) => {
                  const bg = Array.isArray(config.bg_color) ? [...(config.bg_color as number[])] : [255, 255, 255];
                  bg[i] = Number(e.target.value);
                  update('bg_color', bg);
                }}
              />
            </div>
          ))}
          <div className="size-9 rounded-lg border border-border shrink-0" style={{
            backgroundColor: Array.isArray(config.bg_color)
              ? `rgb(${(config.bg_color as number[]).join(',')})`
              : '#ffffff',
          }} />
        </div>
      </section>

      {/* 360 */}
      <section className="rounded-xl border border-orange-500/20 bg-gradient-to-br from-orange-50/50 to-card dark:from-card dark:to-orange-950/10 p-5 space-y-4 relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 w-1 bg-orange-500 rounded-l-xl" />
        <h2 className="text-sm font-semibold text-foreground pl-2 flex items-center gap-2">
          <span className="text-orange-500">🔄</span> 360°
        </h2>
        <div className="pl-2 space-y-1.5">
          <Label className="text-xs">จำนวนเฟรมเริ่มต้น</Label>
          <Select
            value={String(config.spin360_total || 24)}
            onValueChange={(v) => update('spin360_total', Number(v))}
          >
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="12">12 เฟรม</SelectItem>
              <SelectItem value="24">24 เฟรม</SelectItem>
              <SelectItem value="36">36 เฟรม</SelectItem>
              <SelectItem value="72">72 เฟรม</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </section>

      {/* Employee Dashboard */}
      <EmployeeDashboard />

      {/* Users */}
      <UsersSection />
    </div>
    </>
  );
}
