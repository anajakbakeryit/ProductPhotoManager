import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { FileArchive, CheckSquare, Grid2x2, Grid3x3, LayoutGrid, Layers } from 'lucide-react';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';
import type { Photo, PhotoDetail } from './types';
import { PhotoFilters } from './photo-filters';
import { PhotoGrid } from './photo-grid';
import { PhotoLightbox } from './photo-lightbox';
import { Viewer360Inline } from './viewer-360-inline';
import { BulkActionBar } from './bulk-action-bar';

export function GalleryPage() {
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [angle, setAngle] = useState('');
  const [page, setPage] = useState(1);

  // View
  const [gridSize, setGridSize] = useState<'sm' | 'md' | 'lg'>('md');
  const [viewMode, setViewMode] = useState<'grid' | 'product'>('grid');

  // Selection
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Lightbox
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // 360 viewer
  const [viewer360Barcode, setViewer360Barcode] = useState<string | null>(null);

  // Data
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
    queryFn: () => api.get<PhotoDetail>(`/api/photos/${selectedId}`),
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

  // Bulk actions
  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const bulkDelete = async () => {
    const count = selectedIds.size;
    for (const id of selectedIds) {
      try { await api.delete(`/api/photos/${id}`); } catch { /* skip */ }
    }
    toast.success(`ลบ ${count} รูปแล้ว`);
    setSelectedIds(new Set());
    setSelectMode(false);
    queryClient.invalidateQueries({ queryKey: ['gallery'] });
  };

  const downloadZip = async (ids: number[]) => {
    toast.info(`กำลังสร้าง ZIP (${ids.length} รูป)...`);
    try {
      const blob = await api.postBlob('/api/photos/download-zip', {
        photo_ids: ids, variant: 'original', size: 'OG',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'photos.zip'; a.click();
      URL.revokeObjectURL(url);
      toast.success('ดาวน์โหลด ZIP สำเร็จ');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'ดาวน์โหลดไม่สำเร็จ');
    }
  };

  return (
    <>
      {/* Toolbar */}
      <Toolbar>
        <ToolbarHeading title="แกลเลอรี่" description={`${total} รูปทั้งหมด`} />
        <ToolbarActions>
          {photos.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => downloadZip(photos.map((p) => p.id))}>
              <FileArchive className="size-4" /> ZIP
            </Button>
          )}
          <div className="flex items-center border border-border rounded-lg overflow-hidden">
            <button onClick={() => setViewMode('grid')}
              className={`p-1.5 transition-colors ${viewMode === 'grid' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}>
              <Grid2x2 className="size-4" />
            </button>
            <button onClick={() => setViewMode('product')}
              className={`p-1.5 transition-colors ${viewMode === 'product' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}>
              <Layers className="size-4" />
            </button>
            {viewMode === 'grid' && [
              { key: 'sm' as const, icon: Grid3x3 },
              { key: 'lg' as const, icon: LayoutGrid },
            ].map((g) => (
              <button key={g.key} onClick={() => setGridSize(g.key)}
                className={`p-1.5 transition-colors ${gridSize === g.key ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}>
                <g.icon className="size-4" />
              </button>
            ))}
          </div>
          {photos.length > 0 && (
            <Button variant={selectMode ? 'default' : 'outline'} size="sm"
              onClick={() => { setSelectMode(!selectMode); setSelectedIds(new Set()); }}>
              <CheckSquare className="size-4" />
              {selectMode ? `เลือกอยู่ (${selectedIds.size})` : 'เลือก'}
            </Button>
          )}
        </ToolbarActions>
      </Toolbar>

      <div className="container pb-7 space-y-5">
        {/* Filters */}
        <PhotoFilters
          search={search}
          angle={angle}
          onSearchChange={(v) => { setSearch(v); setPage(1); }}
          onAngleChange={(v) => { setAngle(v); setPage(1); }}
        />

        {/* Photo Grid / Product View */}
        <PhotoGrid
          photos={photos}
          isLoading={isLoading}
          gridSize={gridSize}
          viewMode={viewMode}
          selectMode={selectMode}
          selectedIds={selectedIds}
          onPhotoClick={(photo) => setSelectedId(photo.id)}
          onToggleSelect={toggleSelect}
          onView360={setViewer360Barcode}
        />

        {/* Pagination */}
        {total > 60 && (
          <div className="flex justify-center gap-2 pt-2">
            <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}
              className="px-4 py-2 rounded-xl border border-border text-sm font-medium hover:bg-muted disabled:opacity-30 transition-colors">
              ก่อนหน้า
            </button>
            <span className="px-4 py-2 text-sm text-muted-foreground">{page} / {Math.ceil(total / 60)}</span>
            <button onClick={() => setPage(page + 1)} disabled={page * 60 >= total}
              className="px-4 py-2 rounded-xl border border-border text-sm font-medium hover:bg-muted disabled:opacity-30 transition-colors">
              ถัดไป
            </button>
          </div>
        )}

        {/* 360 Viewer */}
        {viewer360Barcode && (
          <Viewer360Inline barcode={viewer360Barcode} onClose={() => setViewer360Barcode(null)} />
        )}

        {/* Lightbox */}
        {selectedId && detail && (
          <PhotoLightbox detail={detail} onClose={() => setSelectedId(null)} onDelete={(id) => deleteMutation.mutate(id)} />
        )}
      </div>

      {/* Bulk Actions */}
      {selectMode && (
        <BulkActionBar
          count={selectedIds.size}
          onSelectAll={() => setSelectedIds(new Set(photos.map((p) => p.id)))}
          onDownload={() => downloadZip(Array.from(selectedIds))}
          onDelete={bulkDelete}
          onCancel={() => { setSelectMode(false); setSelectedIds(new Set()); }}
        />
      )}
    </>
  );
}
