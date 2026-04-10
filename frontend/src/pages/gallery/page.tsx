import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Search, Image as ImageIcon, X, Download, Trash2, Eye, Filter } from 'lucide-react';

interface Photo {
  id: number;
  barcode: string;
  angle: string;
  filename: string;
  status: string;
  has_cutout: boolean;
  has_watermark: boolean;
  thumbnail_url: string;
  preview_url: string;
  created_at: string;
}

export function GalleryPage() {
  const [search, setSearch] = useState('');
  const [angle, setAngle] = useState('');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [variant, setVariant] = useState('original');
  const [size, setSize] = useState('M');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['gallery', search, angle, page],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (angle) params.set('angle', angle);
      params.set('page', String(page));
      params.set('limit', '60');
      return api.get<{ data: Photo[]; total: number }>(`/api/gallery?${params}`);
    },
  });

  const { data: detail } = useQuery({
    queryKey: ['photo-detail', selectedId],
    queryFn: () => api.get<{
      id: number; barcode: string; angle: string; filename: string;
      width: number; height: number; status: string;
      urls: Record<string, Record<string, string>>;
    }>(`/api/photos/${selectedId}`),
    enabled: !!selectedId,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/photos/${id}`),
    onSuccess: () => {
      toast.success('ลบรูปแล้ว');
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ['gallery'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const photos = data?.data || [];
  const total = data?.total || 0;

  const angles = [
    { value: '', label: 'ทุกมุม', active: 'bg-zinc-800 text-white dark:bg-zinc-200 dark:text-zinc-900' },
    { value: 'front', label: 'ด้านหน้า', active: 'bg-blue-500 text-white' },
    { value: 'back', label: 'ด้านหลัง', active: 'bg-violet-500 text-white' },
    { value: 'left', label: 'ด้านซ้าย', active: 'bg-emerald-500 text-white' },
    { value: 'right', label: 'ด้านขวา', active: 'bg-orange-500 text-white' },
    { value: 'top', label: 'ด้านบน', active: 'bg-pink-500 text-white' },
    { value: 'bottom', label: 'ด้านล่าง', active: 'bg-sky-500 text-white' },
    { value: 'detail', label: 'รายละเอียด', active: 'bg-lime-500 text-white' },
    { value: 'package', label: 'แพ็คเกจ', active: 'bg-fuchsia-500 text-white' },
    { value: '360', label: '360°', active: 'bg-amber-500 text-white' },
  ];

  return (
    <div className="p-5 lg:p-7 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">แกลเลอรี่</h1>
          <p className="text-sm text-muted-foreground mt-1">{total} รูปทั้งหมด</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="ค้นหาบาร์โค้ด ชื่อ หมวดหมู่..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {angles.map((a) => (
            <button
              key={a.value}
              onClick={() => { setAngle(a.value); setPage(1); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                angle === a.value
                  ? `${a.active} shadow-sm`
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {a.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-card animate-pulse">
              <div className="aspect-square bg-muted rounded-t-xl" />
              <div className="p-3 space-y-2">
                <div className="h-3 bg-muted rounded w-3/4" />
                <div className="h-2 bg-muted rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : photos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="size-16 rounded-2xl bg-muted flex items-center justify-center mb-5">
            <ImageIcon className="size-7 text-muted-foreground/60" />
          </div>
          <h3 className="text-base font-semibold text-foreground mb-1">ยังไม่มีรูปภาพ</h3>
          <p className="text-sm text-muted-foreground max-w-md text-center">
            เริ่มถ่ายรูปสินค้าโดยไปที่หน้า "ถ่ายภาพ" แล้วสแกนบาร์โค้ด
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {photos.map((photo) => (
            <div
              key={photo.id}
              onClick={() => { setSelectedId(photo.id); setVariant('original'); setSize('M'); }}
              className="group rounded-xl border border-border bg-card overflow-hidden cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className="aspect-square bg-muted relative overflow-hidden">
                <img
                  src={photo.thumbnail_url}
                  alt={photo.filename}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  loading="lazy"
                />
                {/* Hover overlay */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <Eye className="size-6 text-white" />
                </div>
                {/* Status dot */}
                <div className={`absolute top-2 right-2 size-2.5 rounded-full ring-2 ring-card ${
                  photo.status === 'done' ? 'bg-emerald-500' :
                  photo.status === 'processing' ? 'bg-amber-500 animate-pulse' :
                  photo.status === 'error' ? 'bg-red-500' : 'bg-muted-foreground'
                }`} />
              </div>
              <div className="p-3">
                <p className="text-xs font-mono font-semibold text-foreground truncate">{photo.barcode}</p>
                <div className="flex items-center gap-1.5 mt-1.5">
                  <span className="text-2xs px-1.5 py-0.5 rounded-md bg-primary/10 text-primary font-medium">
                    {photo.angle}
                  </span>
                  {photo.has_cutout && (
                    <span className="text-2xs px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 font-medium">
                      cutout
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 60 && (
        <div className="flex justify-center gap-2 pt-2">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-xl border border-border text-sm font-medium hover:bg-muted disabled:opacity-30 transition-colors"
          >
            ก่อนหน้า
          </button>
          <span className="px-4 py-2 text-sm text-muted-foreground">
            {page} / {Math.ceil(total / 60)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page * 60 >= total}
            className="px-4 py-2 rounded-xl border border-border text-sm font-medium hover:bg-muted disabled:opacity-30 transition-colors"
          >
            ถัดไป
          </button>
        </div>
      )}

      {/* Lightbox */}
      {selectedId && detail && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
             onClick={() => setSelectedId(null)}>
          <div className="bg-card rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl border border-border"
               onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-border/50">
              <div>
                <h3 className="text-sm font-semibold text-foreground">{detail.filename}</h3>
                <p className="text-2xs text-muted-foreground mt-0.5">
                  {detail.barcode} · {detail.angle} · {detail.width}×{detail.height} · {detail.status}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                <button onClick={() => deleteMutation.mutate(detail.id)}
                  className="size-8 rounded-lg flex items-center justify-center hover:bg-destructive/10 text-destructive transition-colors">
                  <Trash2 className="size-4" />
                </button>
                <button onClick={() => setSelectedId(null)}
                  className="size-8 rounded-lg flex items-center justify-center hover:bg-muted transition-colors">
                  <X className="size-4" />
                </button>
              </div>
            </div>

            {/* Image */}
            <div className="flex items-center justify-center bg-black/90 min-h-[400px] max-h-[60vh]">
              {detail.urls[variant]?.[size] ? (
                <img src={detail.urls[variant][size]} alt={detail.filename}
                  className="max-w-full max-h-[60vh] object-contain" />
              ) : (
                <div className="flex flex-col items-center justify-center py-16">
                  <div className="size-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
                    <ImageIcon className="size-5 text-muted-foreground/60" />
                  </div>
                  <p className="text-sm text-muted-foreground">ไม่พบรูปสำหรับ {variant}/{size}</p>
                </div>
              )}
            </div>

            {/* Controls */}
            <div className="p-5 border-t border-border/50 flex flex-wrap gap-5">
              <div>
                <label className="text-2xs text-muted-foreground font-medium uppercase tracking-wider block mb-1.5">ประเภท</label>
                <div className="flex gap-1">
                  {[
                    { key: 'original', label: 'ต้นฉบับ', color: 'blue' },
                    { key: 'cutout', label: 'ลบพื้นหลัง', color: 'emerald' },
                    { key: 'watermarked', label: 'ลายน้ำ', color: 'violet' },
                    { key: 'watermarked_original', label: 'ลายน้ำ+ต้นฉบับ', color: 'amber' },
                  ].map((v) => (
                    <button key={v.key} onClick={() => setVariant(v.key)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        variant === v.key
                          ? `bg-${v.color}-500/10 text-${v.color}-500 ring-1 ring-${v.color}-500/20`
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      }`}>
                      {v.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-2xs text-muted-foreground font-medium uppercase tracking-wider block mb-1.5">ขนาด</label>
                <div className="flex gap-1">
                  {['S', 'M', 'L', 'OG'].map((s) => (
                    <button key={s} onClick={() => setSize(s)}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                        size === s
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      }`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              {detail.urls[variant]?.[size] && (
                <a href={detail.urls[variant][size]} download
                  className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm">
                  <Download className="size-4" /> ดาวน์โหลด
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
