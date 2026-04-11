import { useState } from 'react';
import { toast } from 'sonner';
import { Image as ImageIcon, Eye, CheckSquare, Square, Copy, FolderOpen, ChevronDown, ChevronRight, Camera } from 'lucide-react';
import type { Photo } from './types';

interface PhotoGridProps {
  photos: Photo[];
  isLoading: boolean;
  gridSize: 'sm' | 'md' | 'lg';
  viewMode: 'grid' | 'product';
  selectMode: boolean;
  selectedIds: Set<number>;
  onPhotoClick: (photo: Photo) => void;
  onToggleSelect: (id: number) => void;
  onView360: (barcode: string) => void;
}

const GRID_CLASSES = {
  sm: 'grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10',
  md: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6',
  lg: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
};

function StatusDot({ status }: { status: string }) {
  const color = status === 'done' ? 'bg-emerald-500'
    : status === 'processing' ? 'bg-amber-500 animate-pulse'
    : status === 'error' ? 'bg-red-500' : 'bg-muted-foreground';
  return <div className={`absolute top-2 right-2 size-2.5 rounded-full ring-2 ring-card ${color}`} />;
}

function PhotoCard({ photo, selectMode, isSelected, onClick, onView360 }: {
  photo: Photo; selectMode: boolean; isSelected: boolean;
  onClick: () => void; onView360: (barcode: string) => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`group rounded-xl border overflow-hidden cursor-pointer hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 ${
        selectMode && isSelected
          ? 'border-primary ring-2 ring-primary/20 bg-primary/5'
          : 'border-border bg-card'
      }`}
    >
      <div className="aspect-square bg-muted relative overflow-hidden">
        <img src={photo.thumbnail_url} alt={photo.filename}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy" />
        {selectMode ? (
          <div className="absolute top-2 left-2 z-10">
            {isSelected ? <CheckSquare className="size-5 text-primary drop-shadow" /> : <Square className="size-5 text-white/70 drop-shadow" />}
          </div>
        ) : (
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <Eye className="size-6 text-white" />
          </div>
        )}
        <StatusDot status={photo.status} />
      </div>
      <div className="p-3">
        <div className="flex items-center gap-1">
          <p className="text-xs font-mono font-semibold text-foreground truncate flex-1">{photo.barcode}</p>
          <button
            onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(photo.barcode); toast.success('คัดลอกบาร์โค้ดแล้ว'); }}
            className="size-5 rounded flex items-center justify-center text-muted-foreground hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
          >
            <Copy className="size-3" />
          </button>
        </div>
        <div className="flex items-center gap-1.5 mt-1.5">
          <span className="text-2xs px-1.5 py-0.5 rounded-md bg-primary/10 text-primary font-medium">{photo.angle}</span>
          {photo.has_cutout && (
            <span className="text-2xs px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 font-medium">cutout</span>
          )}
          {photo.angle === '360' && (
            <button onClick={(e) => { e.stopPropagation(); onView360(photo.barcode); }}
              className="text-2xs px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-500 font-medium hover:bg-amber-500/20 transition-colors">
              360°
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const ANGLE_LABELS: Record<string, string> = {
  front: 'ด้านหน้า', back: 'ด้านหลัง', left: 'ด้านซ้าย', right: 'ด้านขวา',
  top: 'ด้านบน', bottom: 'ด้านล่าง', detail: 'รายละเอียด', package: 'แพ็คเกจ', '360': '360°',
};

const ANGLE_COLORS: Record<string, string> = {
  front: 'text-blue-500', back: 'text-violet-500', left: 'text-emerald-500', right: 'text-orange-500',
  top: 'text-pink-500', bottom: 'text-sky-500', detail: 'text-lime-600', package: 'text-fuchsia-500', '360': 'text-amber-500',
};

function ProductView({ photos, onPhotoClick }: { photos: Photo[]; onPhotoClick: (photo: Photo) => void }) {
  const [expandedBarcodes, setExpandedBarcodes] = useState<Set<string>>(new Set());
  const barcodes = Array.from(new Set(photos.map((p) => p.barcode)));

  const toggleBarcode = (bc: string) => {
    setExpandedBarcodes((prev) => {
      const next = new Set(prev);
      next.has(bc) ? next.delete(bc) : next.add(bc);
      return next;
    });
  };

  // Auto-expand first barcode
  if (expandedBarcodes.size === 0 && barcodes.length > 0) {
    expandedBarcodes.add(barcodes[0]);
  }

  return (
    <div className="space-y-3">
      {barcodes.map((barcode) => {
        const barcodePhotos = photos.filter((p) => p.barcode === barcode);
        const isExpanded = expandedBarcodes.has(barcode);

        // Group by angle
        const angleGroups = new Map<string, Photo[]>();
        for (const p of barcodePhotos) {
          if (!angleGroups.has(p.angle)) angleGroups.set(p.angle, []);
          angleGroups.get(p.angle)!.push(p);
        }
        const angles = Array.from(angleGroups.keys());

        return (
          <div key={barcode} className="rounded-xl border border-border bg-card overflow-hidden">
            {/* Barcode folder header */}
            <button onClick={() => toggleBarcode(barcode)}
              className="w-full flex items-center gap-3 p-4 border-b border-border/50 bg-muted/30 hover:bg-muted/50 transition-colors text-left">
              {isExpanded ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
              <FolderOpen className="size-4.5 text-primary" />
              <span className="font-mono font-bold text-foreground">{barcode}</span>
              <span className="text-2xs text-muted-foreground bg-muted px-2 py-0.5 rounded-md">
                {barcodePhotos.length} รูป · {angles.length} มุม
              </span>
              <button onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(barcode); toast.success('คัดลอกแล้ว'); }}
                className="ml-auto text-muted-foreground hover:text-primary">
                <Copy className="size-3.5" />
              </button>
            </button>

            {/* Angle sub-folders */}
            {isExpanded && (
              <div className="divide-y divide-border/30">
                {angles.map((angle) => {
                  const anglePhotos = angleGroups.get(angle) || [];
                  return (
                    <div key={angle} className="p-4">
                      {/* Angle label */}
                      <div className="flex items-center gap-2 mb-3">
                        <Camera className={`size-3.5 ${ANGLE_COLORS[angle] || 'text-muted-foreground'}`} />
                        <span className={`text-xs font-semibold ${ANGLE_COLORS[angle] || 'text-muted-foreground'}`}>
                          {ANGLE_LABELS[angle] || angle}
                        </span>
                        <span className="text-2xs text-muted-foreground">{anglePhotos.length} รูป</span>
                      </div>

                      {/* Photos in this angle */}
                      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
                        {anglePhotos.map((photo) => (
                          <div key={photo.id} onClick={() => onPhotoClick(photo)}
                            className="group cursor-pointer rounded-lg border border-border overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all">
                            <div className="aspect-square bg-muted relative">
                              <img src={photo.thumbnail_url} alt={photo.filename}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform" loading="lazy" />
                              <div className={`absolute top-1 right-1 size-2 rounded-full ring-1 ring-card ${
                                photo.status === 'done' ? 'bg-emerald-500' : photo.status === 'processing' ? 'bg-amber-500 animate-pulse' : 'bg-muted-foreground'
                              }`} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
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
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="size-16 rounded-2xl bg-muted flex items-center justify-center mb-5">
        <ImageIcon className="size-7 text-muted-foreground/60" />
      </div>
      <h3 className="text-base font-semibold text-foreground mb-1">ยังไม่มีรูปภาพ</h3>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        เริ่มถ่ายรูปสินค้าโดยไปที่หน้า "ถ่ายภาพ" แล้วสแกนบาร์โค้ด
      </p>
    </div>
  );
}

export function PhotoGrid(props: PhotoGridProps) {
  const { photos, isLoading, gridSize, viewMode, selectMode, selectedIds, onPhotoClick, onToggleSelect, onView360 } = props;

  if (isLoading) return <LoadingSkeleton />;
  if (photos.length === 0) return <EmptyState />;

  if (viewMode === 'product') {
    return <ProductView photos={photos} onPhotoClick={onPhotoClick} />;
  }

  return (
    <div className={`grid gap-4 ${GRID_CLASSES[gridSize]}`}>
      {photos.map((photo) => (
        <PhotoCard
          key={photo.id}
          photo={photo}
          selectMode={selectMode}
          isSelected={selectedIds.has(photo.id)}
          onClick={() => selectMode ? onToggleSelect(photo.id) : onPhotoClick(photo)}
          onView360={onView360}
        />
      ))}
    </div>
  );
}
