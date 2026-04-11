import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import {
  Package, Camera, RotateCw, CheckCircle, Search, ArrowRight,
  Star, AlertTriangle, Copy, Clock,
} from 'lucide-react';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useShootingStore } from '@/store/shootingStore';

interface PipelineStats {
  pending: number;
  shooting: number;
  spin360: number;
  completed: number;
  total: number;
}

interface Product {
  id: number;
  barcode: string;
  name: string;
  category: string;
  photo_count: number;
  color: string;
  priority: string;
  photo_status: string;
  has_spin360: boolean;
  quality_score: number | null;
  created_at: string;
}

const STATUS_CONFIG = {
  pending: { label: 'รอถ่าย', icon: Package, color: 'text-muted-foreground', bg: 'bg-muted', border: 'border-border' },
  shooting: { label: 'กำลังถ่าย', icon: Camera, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-500/20' },
  spin360: { label: 'รอทำ 360°', icon: RotateCw, color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-500/20' },
  completed: { label: 'เสร็จแล้ว', icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' },
} as const;

const PRIORITY_COLORS = {
  urgent: 'bg-red-500',
  normal: 'bg-blue-500',
  low: 'bg-muted-foreground',
};

export function PipelinePage() {
  const navigate = useNavigate();
  const setBarcode = useShootingStore((s) => s.setBarcode);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<string>('all');

  const { data: stats } = useQuery({
    queryKey: ['pipeline-stats'],
    queryFn: () => api.get<PipelineStats>('/api/products/pipeline-stats'),
    refetchInterval: 10_000,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['pipeline-products', activeTab, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (activeTab !== 'all') params.set('status', activeTab);
      if (search) params.set('search', search);
      params.set('limit', '100');
      return api.get<{ data: Product[]; total: number }>(`/api/products?${params}`);
    },
  });
  const products = data?.data || [];

  const handleStartShooting = (barcode: string) => {
    setBarcode(barcode);
    navigate('/shooting');
  };

  const tabs = [
    { key: 'all', label: 'ทั้งหมด', count: stats?.total || 0 },
    { key: 'pending', label: 'รอถ่าย', count: stats?.pending || 0 },
    { key: 'shooting', label: 'กำลังถ่าย', count: stats?.shooting || 0 },
    { key: 'spin360', label: 'รอ 360°', count: stats?.spin360 || 0 },
    { key: 'completed', label: 'เสร็จ', count: stats?.completed || 0 },
  ];

  return (
    <>
      <Toolbar>
        <ToolbarHeading title="Pipeline" description="รายการสินค้าที่ต้องถ่ายรูป" />
        <ToolbarActions>
          <Button onClick={() => navigate('/shooting')}>
            <Camera className="size-4" />
            เริ่มถ่ายรูป
          </Button>
        </ToolbarActions>
      </Toolbar>

      <div className="container pb-7 space-y-5">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {(['pending', 'shooting', 'spin360', 'completed'] as const).map((key) => {
            const cfg = STATUS_CONFIG[key];
            const count = stats?.[key] || 0;
            return (
              <button key={key} onClick={() => setActiveTab(key)}
                className={`rounded-xl border ${activeTab === key ? cfg.border + ' ring-2 ring-offset-2 ring-offset-background ring-primary/20' : 'border-border'} ${cfg.bg} p-5 text-left transition-all hover:shadow-md`}>
                <div className="flex items-center justify-between mb-2">
                  <cfg.icon className={`size-5 ${cfg.color}`} />
                  {key === 'shooting' && count > 0 && (
                    <span className="size-2 rounded-full bg-blue-500 animate-pulse" />
                  )}
                </div>
                <p className="text-2xl font-bold text-foreground">{count}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{cfg.label}</p>
              </button>
            );
          })}
        </div>

        {/* Tabs + Search */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  activeTab === tab.key
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}>
                {tab.label} ({tab.count})
              </button>
            ))}
          </div>
          <div className="relative flex-1 max-w-xs ml-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="ค้นหาบาร์โค้ด..." className="pl-9" />
          </div>
        </div>

        {/* Product List */}
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-5 animate-pulse">
                <div className="flex gap-4">
                  <div className="h-5 bg-muted rounded w-32" />
                  <div className="h-5 bg-muted rounded w-24" />
                  <div className="h-5 bg-muted rounded w-16 ml-auto" />
                </div>
              </div>
            ))}
          </div>
        ) : products.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Package className="size-12 text-muted-foreground/30 mb-4" />
            <h3 className="text-base font-semibold text-foreground mb-1">ไม่มีสินค้า</h3>
            <p className="text-sm text-muted-foreground">เพิ่มสินค้าโดยสแกนบาร์โค้ดที่หน้าถ่ายรูป</p>
          </div>
        ) : (
          <div className="space-y-2">
            {products.map((product) => {
              const cfg = STATUS_CONFIG[product.photo_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending;
              const actionLabel = product.photo_status === 'pending' ? 'เริ่มถ่าย'
                : product.photo_status === 'shooting' ? 'ถ่ายต่อ'
                : product.photo_status === 'spin360' ? 'ทำ 360°'
                : 'ดูรูป';

              return (
                <div key={product.id}
                  className={`group rounded-xl border ${cfg.border} bg-card overflow-hidden hover:shadow-md transition-all`}>
                  <div className="p-4 flex items-center gap-4">
                    {/* Priority dot */}
                    <div className={`size-2 rounded-full shrink-0 ${PRIORITY_COLORS[product.priority as keyof typeof PRIORITY_COLORS] || PRIORITY_COLORS.normal}`} />

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-foreground">{product.barcode}</span>
                        <button onClick={() => { navigator.clipboard.writeText(product.barcode); toast.success('คัดลอกแล้ว'); }}
                          className="text-muted-foreground hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                          <Copy className="size-3" />
                        </button>
                        {product.name && (
                          <span className="text-sm text-muted-foreground truncate">{product.name}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className={`inline-flex items-center gap-1 text-2xs font-medium ${cfg.color}`}>
                          <cfg.icon className="size-3" />
                          {cfg.label}
                        </span>
                        <span className="text-2xs text-muted-foreground">
                          {product.photo_count} รูป
                        </span>
                        {product.quality_score && (
                          <span className="inline-flex items-center gap-0.5 text-2xs text-amber-500">
                            <Star className="size-3 fill-amber-500" />
                            {product.quality_score}
                          </span>
                        )}
                        {product.color && (
                          <span className="text-2xs text-muted-foreground">{product.color}</span>
                        )}
                      </div>
                    </div>

                    {/* Action */}
                    <Button size="sm" variant={product.photo_status === 'completed' ? 'outline' : 'default'}
                      onClick={() => {
                        if (product.photo_status === 'completed') {
                          navigate(`/gallery?search=${product.barcode}`);
                        } else if (product.photo_status === 'spin360') {
                          navigate('/360');
                        } else {
                          handleStartShooting(product.barcode);
                        }
                      }}>
                      {actionLabel}
                      <ArrowRight className="size-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
