import { useState, useRef, useCallback, useEffect } from 'react';
import { Image as ImageIcon, X, Download, Trash2, SplitSquareHorizontal, Tag } from 'lucide-react';
import { usePhotoTagStore, PRESET_TAGS } from '@/store/photoTagStore';
import type { PhotoDetail } from './types';

interface PhotoLightboxProps {
  detail: PhotoDetail;
  onClose: () => void;
  onDelete: (id: number) => void;
}

function PhotoTagBar({ photoId }: { photoId: number }) {
  const { getTagsForPhoto, addTag, removeTag, loadTags } = usePhotoTagStore();
  const tags = getTagsForPhoto(photoId);
  useEffect(() => { loadTags(photoId); }, [photoId, loadTags]);

  return (
    <div className="px-5 py-3 border-t border-border/50 flex items-center gap-2 flex-wrap">
      <Tag className="size-3.5 text-muted-foreground shrink-0" />
      {tags.map((t) => (
        <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-primary/10 text-primary text-2xs font-medium">
          {t}
          <button onClick={() => removeTag(photoId, t)} className="hover:text-destructive"><X className="size-3" /></button>
        </span>
      ))}
      {PRESET_TAGS.filter((t) => !tags.includes(t)).map((t) => (
        <button key={t} onClick={() => addTag(photoId, t)}
          className="px-2 py-0.5 rounded-md bg-muted text-2xs text-muted-foreground font-medium hover:bg-muted/80 transition-colors">
          + {t}
        </button>
      ))}
    </div>
  );
}

export function PhotoLightbox({ detail, onClose, onDelete }: PhotoLightboxProps) {
  const [variant, setVariant] = useState('original');
  const [size, setSize] = useState('M');
  const [compareMode, setCompareMode] = useState(false);
  const [sliderPos, setSliderPos] = useState(50);
  const compareRef = useRef<HTMLDivElement>(null);

  const handleSliderDrag = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!compareRef.current) return;
    const rect = compareRef.current.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    setSliderPos((x / rect.width) * 100);
  }, []);

  const hasComparison = detail.urls['original']?.[size] && detail.urls['cutout']?.[size];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
         onClick={() => { onClose(); setCompareMode(false); }}>
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
            {hasComparison && (
              <button onClick={() => { setCompareMode(!compareMode); setSliderPos(50); }}
                className={`size-8 rounded-lg flex items-center justify-center transition-colors ${
                  compareMode ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
                }`} title="เปรียบเทียบ">
                <SplitSquareHorizontal className="size-4" />
              </button>
            )}
            <button onClick={() => onDelete(detail.id)}
              className="size-8 rounded-lg flex items-center justify-center hover:bg-destructive/10 text-destructive transition-colors">
              <Trash2 className="size-4" />
            </button>
            <button onClick={() => { onClose(); setCompareMode(false); }}
              className="size-8 rounded-lg flex items-center justify-center hover:bg-muted transition-colors">
              <X className="size-4" />
            </button>
          </div>
        </div>

        {/* Image / Comparison */}
        {compareMode && hasComparison ? (
          <div ref={compareRef}
            className="relative bg-black/90 min-h-[400px] max-h-[60vh] overflow-hidden cursor-col-resize select-none"
            onMouseMove={(e) => e.buttons === 1 && handleSliderDrag(e)}
            onTouchMove={handleSliderDrag} onClick={handleSliderDrag}>
            <img src={detail.urls['cutout'][size]} alt="cutout"
              className="w-full h-full object-contain absolute inset-0" style={{ maxHeight: '60vh' }} />
            <div className="absolute inset-0 overflow-hidden" style={{ width: `${sliderPos}%` }}>
              <img src={detail.urls['original'][size]} alt="original"
                className="absolute inset-0 w-full h-full object-contain" style={{ maxHeight: '60vh' }} />
            </div>
            <div className="absolute top-0 bottom-0 w-0.5 bg-white/80 shadow-lg" style={{ left: `${sliderPos}%` }}>
              <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 size-8 rounded-full bg-white shadow-lg flex items-center justify-center">
                <SplitSquareHorizontal className="size-4 text-zinc-700" />
              </div>
            </div>
            <span className="absolute top-3 left-3 px-2 py-0.5 rounded bg-blue-500/80 text-white text-xs font-medium">ต้นฉบับ</span>
            <span className="absolute top-3 right-3 px-2 py-0.5 rounded bg-emerald-500/80 text-white text-xs font-medium">ลบพื้นหลัง</span>
          </div>
        ) : (
          <div className="flex items-center justify-center bg-black/90 min-h-[400px] max-h-[60vh]">
            {detail.urls[variant]?.[size] ? (
              <img src={detail.urls[variant][size]} alt={detail.filename} className="max-w-full max-h-[60vh] object-contain" />
            ) : (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="size-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
                  <ImageIcon className="size-5 text-muted-foreground/60" />
                </div>
                <p className="text-sm text-muted-foreground">ไม่พบรูปสำหรับ {variant}/{size}</p>
              </div>
            )}
          </div>
        )}

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
                    size === s ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}>
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 ml-auto">
            {detail.urls[variant]?.[size] && (
              <a href={detail.urls[variant][size]} download
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm">
                <Download className="size-4" /> ดาวน์โหลด
              </a>
            )}
          </div>
        </div>

        <PhotoTagBar photoId={detail.id} />
      </div>
    </div>
  );
}
