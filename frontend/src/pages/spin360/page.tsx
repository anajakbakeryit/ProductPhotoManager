import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Upload, RotateCw, ExternalLink } from 'lucide-react';

export function Spin360Page() {
  const [barcode, setBarcode] = useState('');
  const [viewBarcode, setViewBarcode] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const queryClient = useQueryClient();

  // Fetch 360 data for viewer
  const { data: spinData } = useQuery({
    queryKey: ['spin360', viewBarcode],
    queryFn: () => api.get<{ barcode: string; total_frames: number; size_map: Record<string, string[]> }>(
      `/api/spin360/${viewBarcode}`
    ),
    enabled: !!viewBarcode,
    retry: false,
  });

  // Upload frames mutation
  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => api.upload<{ total: number; barcode: string }>(
      '/api/spin360/frames', formData
    ),
    onSuccess: (data) => {
      toast.success(`อัปโหลด 360° สำเร็จ ${data.total} เฟรม`);
      setViewBarcode(data.barcode);
      queryClient.invalidateQueries({ queryKey: ['spin360'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleFiles = useCallback((files: FileList | File[]) => {
    if (!barcode.trim()) {
      toast.error('กรุณาระบุบาร์โค้ดก่อน');
      return;
    }
    const sorted = Array.from(files).sort((a, b) => a.name.localeCompare(b.name));
    const fd = new FormData();
    fd.append('barcode', barcode.trim());
    for (const f of sorted) fd.append('files', f);
    uploadMutation.mutate(fd);
  }, [barcode, uploadMutation]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold text-foreground">360 องศา</h1>

      {/* Upload Section */}
      <div className="rounded-xl border border-border bg-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-muted-foreground">อัปโหลดเฟรม 360°</h2>

        <div className="flex gap-3">
          <input
            type="text"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            placeholder="บาร์โค้ด"
            className="px-4 py-2 rounded-lg border border-border bg-background text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={() => barcode.trim() && setViewBarcode(barcode.trim())}
            className="px-4 py-2 rounded-lg border border-border text-sm text-foreground hover:bg-accent/10"
          >
            ดู Viewer
          </button>
        </div>

        {/* Drop zone */}
        <div
          className={`rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
            isDragging ? 'border-primary bg-primary/5' :
            uploadMutation.isPending ? 'border-yellow-500 bg-yellow-500/5' :
            'border-border'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
          }}
        >
          {uploadMutation.isPending ? (
            <div className="flex items-center justify-center gap-3">
              <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
              <span className="text-foreground">กำลังอัปโหลดและประมวลผล...</span>
            </div>
          ) : (
            <>
              <Upload className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-muted-foreground">ลากไฟล์รูปเฟรม 360° มาวางที่นี่</p>
              <p className="text-xs text-muted-foreground/60 mt-1">เรียงตามลำดับชื่อไฟล์อัตโนมัติ (01, 02, 03...)</p>
              <label className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm cursor-pointer hover:bg-primary/90">
                เลือกไฟล์
                <input
                  type="file" multiple accept="image/*"
                  className="hidden"
                  onChange={(e) => e.target.files && handleFiles(e.target.files)}
                />
              </label>
            </>
          )}
        </div>
      </div>

      {/* Viewer Section */}
      {spinData && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-muted-foreground">
              <RotateCw className="w-4 h-4 inline mr-1" />
              360° Viewer — {spinData.barcode} ({spinData.total_frames} เฟรม)
            </h2>
            <a
              href={`/api/spin360/${spinData.barcode}/viewer`}
              target="_blank"
              className="flex items-center gap-1.5 text-xs text-primary hover:underline"
            >
              <ExternalLink className="w-3.5 h-3.5" /> เปิด Viewer เต็มจอ
            </a>
          </div>

          <iframe
            src={`/api/spin360/${spinData.barcode}/viewer`}
            className="w-full rounded-lg border border-border bg-black"
            style={{ height: '500px' }}
            title="360 Viewer"
          />
        </div>
      )}
    </div>
  );
}
