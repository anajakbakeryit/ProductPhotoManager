import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { Upload, RotateCw, ExternalLink, Loader2, Video } from 'lucide-react';

export function Spin360Page() {
  const [barcode, setBarcode] = useState('');
  const [viewBarcode, setViewBarcode] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const queryClient = useQueryClient();

  const { data: spinData } = useQuery({
    queryKey: ['spin360', viewBarcode],
    queryFn: () => api.get<{ barcode: string; total_frames: number }>(`/api/spin360/${viewBarcode}`),
    enabled: !!viewBarcode,
    retry: false,
  });

  const uploadMutation = useMutation({
    mutationFn: (formData: FormData) => api.upload<{ total: number; barcode: string }>('/api/spin360/frames', formData),
    onSuccess: (data) => {
      toast.success(`อัปโหลด 360° สำเร็จ ${data.total} เฟรม`);
      setViewBarcode(data.barcode);
      queryClient.invalidateQueries({ queryKey: ['spin360'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const handleFiles = useCallback((files: FileList | File[]) => {
    if (!barcode.trim()) { toast.error('กรุณาระบุบาร์โค้ดก่อน'); return; }
    const sorted = Array.from(files).sort((a, b) => a.name.localeCompare(b.name));
    const fd = new FormData();
    fd.append('barcode', barcode.trim());
    for (const f of sorted) fd.append('files', f);
    uploadMutation.mutate(fd);
  }, [barcode, uploadMutation]);

  return (
    <div className="p-5 lg:p-7 space-y-5">
      <div>
        <h1 className="text-xl font-bold text-foreground">360 องศา</h1>
        <p className="text-sm text-muted-foreground mt-1">อัปโหลดเฟรม 360° หรือวิดีโอ</p>
      </div>

      {/* Upload */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-5 border-b border-border/50">
          <div className="flex items-center gap-2 mb-4">
            <div className="size-8 rounded-lg bg-violet-500/10 flex items-center justify-center">
              <RotateCw className="size-4 text-violet-500" />
            </div>
            <h2 className="text-sm font-semibold text-foreground">อัปโหลดเฟรม 360°</h2>
          </div>

          <div className="flex gap-3">
            <input
              type="text" value={barcode} onChange={(e) => setBarcode(e.target.value)}
              placeholder="บาร์โค้ด"
              className="px-4 py-2.5 rounded-xl border border-border bg-background text-foreground font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
            />
            <button onClick={() => barcode.trim() && setViewBarcode(barcode.trim())}
              className="px-4 py-2.5 rounded-xl border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
              ดู Viewer
            </button>
          </div>
        </div>

        {/* Dropzone */}
        <div className="p-5">
          <div
            className={`rounded-xl border-2 border-dashed p-12 text-center transition-all duration-200 ${
              isDragging ? 'border-primary bg-primary/5' :
              uploadMutation.isPending ? 'border-amber-400 bg-amber-400/5' :
              'border-border hover:border-primary/40'
            }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files); }}
          >
            {uploadMutation.isPending ? (
              <div className="flex items-center justify-center gap-3">
                <Loader2 className="size-6 animate-spin text-primary" />
                <span className="text-foreground font-medium">กำลังอัปโหลดและประมวลผล...</span>
              </div>
            ) : (
              <>
                <div className="size-14 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
                  <Upload className={`size-6 ${isDragging ? 'text-primary animate-bounce' : 'text-muted-foreground/60'}`} />
                </div>
                <p className="text-sm font-medium text-foreground">ลากไฟล์รูปเฟรม 360° มาวางที่นี่</p>
                <p className="text-2xs text-muted-foreground mt-1">เรียงตามลำดับชื่อไฟล์อัตโนมัติ (01, 02, 03...)</p>
                <label className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium cursor-pointer hover:bg-primary/90 transition-colors shadow-sm">
                  เลือกไฟล์
                  <input type="file" multiple accept="image/*" className="hidden"
                    onChange={(e) => e.target.files && handleFiles(e.target.files)} />
                </label>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Viewer */}
      {spinData && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-border/50">
            <div className="flex items-center gap-2">
              <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <RotateCw className="size-4 text-primary" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-foreground">360° Viewer — {spinData.barcode}</h2>
                <p className="text-2xs text-muted-foreground">{spinData.total_frames} เฟรม</p>
              </div>
            </div>
            <a href={`/api/spin360/${spinData.barcode}/viewer`} target="_blank"
              className="flex items-center gap-1.5 text-xs text-primary hover:underline font-medium">
              <ExternalLink className="size-3.5" /> เปิดเต็มจอ
            </a>
          </div>
          <iframe
            src={`/api/spin360/${spinData.barcode}/viewer`}
            className="w-full bg-black"
            style={{ height: '500px' }}
            title="360 Viewer"
          />
        </div>
      )}
    </div>
  );
}
