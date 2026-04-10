import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Search, Image as ImageIcon, X, Download, Trash2, RotateCw } from 'lucide-react';

interface Photo {
  id: number;
  barcode: string;
  angle: string;
  filename: string;
  status: string;
  has_cutout: boolean;
  thumbnail_url: string;
  preview_url: string;
  created_at: string;
}

export function GalleryPage() {
  const [search, setSearch] = useState('');
  const [angle, setAngle] = useState('');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [variant, setVariant] = useState<string>('original');
  const [size, setSize] = useState<string>('M');
  const queryClient = useQueryClient();

  // Photo detail query
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

  const photos = data?.data || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">แกลเลอรี่</h1>
        <span className="text-sm text-muted-foreground">{total} รูป</span>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="ค้นหาบาร์โค้ด..."
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={angle}
          onChange={(e) => { setAngle(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm"
        >
          <option value="">ทุกมุม</option>
          <option value="front">ด้านหน้า</option>
          <option value="back">ด้านหลัง</option>
          <option value="left">ด้านซ้าย</option>
          <option value="right">ด้านขวา</option>
          <option value="top">ด้านบน</option>
          <option value="bottom">ด้านล่าง</option>
          <option value="detail">รายละเอียด</option>
          <option value="package">แพ็คเกจ</option>
          <option value="360">360°</option>
        </select>
      </div>

      {/* Photo Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
        </div>
      ) : photos.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
          <ImageIcon className="w-12 h-12 mb-3 opacity-30" />
          <p>ยังไม่มีรูปภาพ</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {photos.map((photo) => (
            <div
              key={photo.id}
              onClick={() => { setSelectedId(photo.id); setVariant('original'); setSize('M'); }}
              className="group relative rounded-lg overflow-hidden border border-border bg-card hover:border-primary transition-colors cursor-pointer"
            >
              <div className="aspect-square bg-muted">
                <img
                  src={photo.thumbnail_url}
                  alt={photo.filename}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
              <div className="p-2">
                <p className="text-xs font-mono text-foreground truncate">{photo.barcode}</p>
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                    {photo.angle}
                  </span>
                  {photo.has_cutout && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-500">
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
        <div className="flex justify-center gap-2 pt-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 rounded border border-border text-sm disabled:opacity-30"
          >
            ก่อนหน้า
          </button>
          <span className="px-3 py-1.5 text-sm text-muted-foreground">
            หน้า {page} / {Math.ceil(total / 60)}
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page * 60 >= total}
            className="px-3 py-1.5 rounded border border-border text-sm disabled:opacity-30"
          >
            ถัดไป
          </button>
        </div>
      )}
      {/* Lightbox Modal */}
      {selectedId && detail && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
             onClick={() => setSelectedId(null)}>
          <div className="bg-card rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
               onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border">
              <div>
                <h3 className="text-foreground font-semibold">{detail.filename}</h3>
                <p className="text-xs text-muted-foreground">
                  {detail.barcode} / {detail.angle} — {detail.width}x{detail.height} — {detail.status}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => deleteMutation.mutate(detail.id)}
                  className="p-2 rounded-lg hover:bg-destructive/10 text-destructive">
                  <Trash2 className="w-4 h-4" />
                </button>
                <button onClick={() => setSelectedId(null)}
                  className="p-2 rounded-lg hover:bg-muted">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Image */}
            <div className="flex items-center justify-center bg-black min-h-[400px] max-h-[60vh]">
              {detail.urls[variant]?.[size] ? (
                <img src={detail.urls[variant][size]} alt={detail.filename}
                  className="max-w-full max-h-[60vh] object-contain" />
              ) : (
                <p className="text-muted-foreground">ไม่พบรูปสำหรับ {variant}/{size}</p>
              )}
            </div>

            {/* Controls */}
            <div className="p-4 border-t border-border flex flex-wrap gap-4">
              {/* Variant selector */}
              <div>
                <label className="text-xs text-muted-foreground block mb-1">ประเภท</label>
                <div className="flex gap-1">
                  {['original', 'cutout', 'watermarked', 'watermarked_original'].map((v) => (
                    <button key={v} onClick={() => setVariant(v)}
                      className={`px-2 py-1 rounded text-xs ${variant === v ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent/10'}`}>
                      {v === 'original' ? 'ต้นฉบับ' : v === 'cutout' ? 'ลบพื้นหลัง' : v === 'watermarked' ? 'ลายน้ำ' : 'ลายน้ำ+ต้นฉบับ'}
                    </button>
                  ))}
                </div>
              </div>
              {/* Size selector */}
              <div>
                <label className="text-xs text-muted-foreground block mb-1">ขนาด</label>
                <div className="flex gap-1">
                  {['S', 'M', 'L', 'OG'].map((s) => (
                    <button key={s} onClick={() => setSize(s)}
                      className={`px-2 py-1 rounded text-xs font-mono ${size === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent/10'}`}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              {/* Download */}
              {detail.urls[variant]?.[size] && (
                <a href={detail.urls[variant][size]} download
                  className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm">
                  <Download className="w-3.5 h-3.5" /> ดาวน์โหลด
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
