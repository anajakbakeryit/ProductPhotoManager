import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';
import {
  Upload, ScanBarcode, Loader2, Camera, Check, RotateCw,
  ArrowRight, AlertTriangle, Wifi, WifiOff, ChevronLeft,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useShootingStore } from '@/store/shootingStore';
import { useProcessingStatus } from '@/hooks/useProcessingStatus';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const GUIDED_ANGLES = [
  { id: 'front', label: 'ด้านหน้า', color: 'blue' },
  { id: 'back', label: 'ด้านหลัง', color: 'violet' },
  { id: 'left', label: 'ด้านซ้าย', color: 'emerald' },
  { id: 'right', label: 'ด้านขวา', color: 'orange' },
  { id: 'top', label: 'ด้านบน', color: 'pink' },
  { id: 'bottom', label: 'ด้านล่าง', color: 'sky' },
  { id: 'detail', label: 'รายละเอียด', color: 'lime' },
  { id: 'package', label: 'แพ็คเกจ', color: 'fuchsia' },
];

interface ExistingPhoto {
  id: number;
  angle: string;
  thumbnail_url: string;
  quality_score: number | null;
  quality_issues: string[] | null;
}

export function ShootingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentBarcode, setBarcode } = useShootingStore();
  const { lastMessage, isConnected } = useProcessingStatus();

  const [barcodeInput, setBarcodeInput] = useState('');
  const [activeAngle, setActiveAngle] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const barcodeRef = useRef<HTMLInputElement>(null);

  // Fetch existing photos for current barcode
  const { data: existingPhotos, refetch: refetchPhotos } = useQuery({
    queryKey: ['shooting-photos', currentBarcode],
    queryFn: () => api.get<{ data: ExistingPhoto[] }>(`/api/photos?barcode=${currentBarcode}&limit=100`),
    enabled: !!currentBarcode,
  });

  const photosByAngle = new Map<string, ExistingPhoto>();
  for (const p of existingPhotos?.data || []) {
    if (!photosByAngle.has(p.angle)) photosByAngle.set(p.angle, p);
  }

  const doneCount = GUIDED_ANGLES.filter((a) => photosByAngle.has(a.id)).length;
  const allDone = doneCount === GUIDED_ANGLES.length;

  // Auto-select first empty angle
  useEffect(() => {
    if (!currentBarcode) return;
    const firstEmpty = GUIDED_ANGLES.find((a) => !photosByAngle.has(a.id));
    if (firstEmpty && !activeAngle) {
      setActiveAngle(firstEmpty.id);
    }
  }, [currentBarcode, photosByAngle, activeAngle]);

  // WebSocket processing status
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'processing_done') {
      toast.success('ประมวลผลเสร็จ!', {
        description: lastMessage.barcode,
        action: { label: 'ดูผล', onClick: () => navigate(`/gallery?search=${lastMessage.barcode}`) },
      });
    }
  }, [lastMessage, navigate]);

  // Barcode scan
  const handleBarcodeScan = async () => {
    const raw = barcodeInput.trim();
    if (!raw) return;
    try {
      try { await api.get(`/api/products/${raw}`); }
      catch { await api.post('/api/products', { barcode: raw }); }
      setBarcode(raw);
      setActiveAngle(null); // Reset to auto-select first empty
      setBarcodeInput('');
      refetchPhotos();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'เกิดข้อผิดพลาด');
    }
  };

  // Upload photo for active angle
  const handleUpload = async (files: FileList | File[]) => {
    if (!currentBarcode || !activeAngle) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('barcode', currentBarcode);
    fd.append('angle', activeAngle);
    for (const f of files) fd.append('files', f);
    try {
      const res = await api.upload<{ uploaded: { filename: string; quality: { score: number; issues: string[]; passed: boolean } }[]; total: number }>(
        '/api/photos/upload', fd
      );
      const qc = res.uploaded[0]?.quality;
      if (qc && !qc.passed) {
        toast.warning('คุณภาพรูปต่ำ', {
          description: qc.issues.map((i: string) =>
            i === 'blurry' ? 'ภาพเบลอ' : i === 'too_dark' ? 'มืดเกินไป' : i === 'too_bright' ? 'สว่างเกินไป' : i === 'no_product' ? 'ไม่เห็นสินค้า' : i
          ).join(', '),
        });
      } else {
        toast.success(`✓ ${activeAngle} — อัปโหลดสำเร็จ`);
      }

      await refetchPhotos();
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });

      // Auto-advance to next empty angle
      const nextEmpty = GUIDED_ANGLES.find((a) => a.id !== activeAngle && !photosByAngle.has(a.id));
      if (nextEmpty) {
        setActiveAngle(nextEmpty.id);
      } else {
        // All done!
        setActiveAngle(null);
        confetti({ particleCount: 150, spread: 80, origin: { y: 0.7 } });
        toast.success('🎉 ครบ 8 มุมแล้ว!');
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ');
    } finally {
      setUploading(false);
    }
  };

  // No barcode selected — show scan screen
  if (!currentBarcode) {
    return (
      <>
        <Toolbar>
          <ToolbarHeading title="ถ่ายภาพ" description="สแกนบาร์โค้ดเพื่อเริ่มถ่าย" />
        </Toolbar>
        <div className="container pb-7 flex items-center justify-center min-h-[60vh]">
          <div className="max-w-md w-full space-y-6 text-center">
            <div className="size-20 rounded-3xl bg-primary/10 flex items-center justify-center mx-auto">
              <ScanBarcode className="size-10 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">สแกนบาร์โค้ด</h2>
              <p className="text-sm text-muted-foreground mt-1">สแกนหรือพิมพ์บาร์โค้ดเพื่อเริ่มถ่ายรูป</p>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleBarcodeScan(); }} className="flex gap-2">
              <Input ref={barcodeRef} value={barcodeInput} onChange={(e) => setBarcodeInput(e.target.value)}
                placeholder="บาร์โค้ด..." className="font-mono text-lg text-center" autoFocus />
              <Button type="submit" disabled={!barcodeInput.trim()}>เริ่ม</Button>
            </form>
            <Button variant="outline" onClick={() => navigate('/')}>
              <ChevronLeft className="size-4" /> กลับ Pipeline
            </Button>
          </div>
        </div>
      </>
    );
  }

  // Active barcode — show guided 8-angle grid
  const activeAngleConfig = GUIDED_ANGLES.find((a) => a.id === activeAngle);

  return (
    <>
      <Toolbar>
        <ToolbarHeading
          title={currentBarcode}
          description={`${doneCount}/8 มุม${allDone ? ' — ครบแล้ว!' : ''}`}
        />
        <ToolbarActions>
          <span className="flex items-center gap-1.5 text-xs mr-2">
            {isConnected
              ? <><Wifi className="size-3 text-emerald-500" /><span className="text-emerald-500">เชื่อมต่อ</span></>
              : <><WifiOff className="size-3 text-red-500" /><span className="text-red-500">ขาดการเชื่อมต่อ</span></>
            }
          </span>
          {allDone && (
            <Button variant="outline" onClick={() => navigate('/360')}>
              <RotateCw className="size-4" /> ทำ 360°
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => { setBarcode(''); setActiveAngle(null); }}>
            เปลี่ยน barcode
          </Button>
        </ToolbarActions>
      </Toolbar>

      <div className="container pb-7 space-y-5">
        {/* 8-Angle Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {GUIDED_ANGLES.map((angle) => {
            const existing = photosByAngle.get(angle.id);
            const isActive = activeAngle === angle.id;
            const isDone = !!existing;

            return (
              <button
                key={angle.id}
                onClick={() => !isDone && setActiveAngle(angle.id)}
                className={`relative rounded-xl border-2 overflow-hidden transition-all ${
                  isActive
                    ? `border-${angle.color}-500 ring-4 ring-${angle.color}-500/20 shadow-lg`
                    : isDone
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-border hover:border-muted-foreground/30'
                }`}
              >
                <div className="aspect-square bg-muted relative flex items-center justify-center">
                  {existing ? (
                    <>
                      <img src={existing.thumbnail_url} alt={angle.label}
                        className="w-full h-full object-cover" />
                      <div className="absolute top-2 right-2 size-6 rounded-full bg-emerald-500 flex items-center justify-center shadow">
                        <Check className="size-3.5 text-white" />
                      </div>
                      {existing.quality_issues && existing.quality_issues.length > 0 && (
                        <div className="absolute top-2 left-2 size-6 rounded-full bg-amber-500 flex items-center justify-center shadow">
                          <AlertTriangle className="size-3.5 text-white" />
                        </div>
                      )}
                    </>
                  ) : isActive ? (
                    <div className="text-center p-4">
                      <Camera className={`size-8 text-${angle.color}-500 mx-auto mb-2`} />
                      <p className="text-xs text-muted-foreground">ลากรูปมาวาง</p>
                    </div>
                  ) : (
                    <div className="size-10 rounded-xl bg-muted flex items-center justify-center">
                      <Camera className="size-5 text-muted-foreground/30" />
                    </div>
                  )}
                </div>
                <div className={`px-3 py-2 text-center ${
                  isDone ? 'bg-emerald-500/10' : isActive ? `bg-${angle.color}-500/10` : 'bg-card'
                }`}>
                  <p className={`text-xs font-medium ${
                    isDone ? 'text-emerald-600 dark:text-emerald-400' : isActive ? `text-${angle.color}-500` : 'text-muted-foreground'
                  }`}>
                    {isDone ? '✓ ' : ''}{angle.label}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Active Angle Dropzone */}
        {activeAngle && !allDone && (
          <div
            className={`rounded-2xl border-2 border-dashed p-12 text-center transition-all ${
              isDragging ? 'border-primary bg-primary/5 scale-[0.99]'
              : uploading ? 'border-amber-400 bg-amber-400/5'
              : 'border-border hover:border-primary/40'
            }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); handleUpload(e.dataTransfer.files); }}
          >
            {uploading ? (
              <div className="flex items-center justify-center gap-3">
                <Loader2 className="size-6 animate-spin text-primary" />
                <span className="text-foreground font-medium">กำลังอัปโหลด...</span>
              </div>
            ) : (
              <>
                <div className={`size-16 rounded-2xl bg-${activeAngleConfig?.color}-500/10 flex items-center justify-center mx-auto mb-4`}>
                  <Upload className={`size-7 ${isDragging ? 'text-primary animate-bounce' : `text-${activeAngleConfig?.color}-500`}`} />
                </div>
                <p className="text-lg font-semibold text-foreground">
                  ถ่าย{activeAngleConfig?.label}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  ลากรูปมาวางที่นี่ หรือคลิกเลือกไฟล์
                </p>
                <label className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium cursor-pointer hover:bg-primary/90 transition-colors shadow-sm">
                  เลือกไฟล์
                  <input type="file" multiple accept="image/*,.cr2,.cr3,.arw,.nef,.tif,.tiff"
                    className="hidden" onChange={(e) => e.target.files && handleUpload(e.target.files)} />
                </label>
              </>
            )}
          </div>
        )}

        {/* All Done — Next Actions */}
        {allDone && (
          <div className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-emerald-50/50 to-card dark:from-card dark:to-emerald-950/10 p-8 text-center">
            <div className="size-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
              <Check className="size-8 text-emerald-500" />
            </div>
            <h2 className="text-xl font-bold text-foreground">ครบ 8 มุมแล้ว!</h2>
            <p className="text-sm text-muted-foreground mt-1">{currentBarcode} — ถ่ายรูปครบทุกมุมแล้ว</p>
            <div className="flex items-center justify-center gap-3 mt-6">
              <Button onClick={() => navigate('/360')}>
                <RotateCw className="size-4" /> ทำ 360° ต่อ
              </Button>
              <Button variant="outline" onClick={() => {
                setBarcode('');
                setActiveAngle(null);
                navigate('/');
              }}>
                สินค้าถัดไป <ArrowRight className="size-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
