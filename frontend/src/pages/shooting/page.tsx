import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';
import {
  Upload, ScanBarcode, Loader2, Camera, Check, RotateCw,
  ArrowRight, AlertTriangle, Wifi, WifiOff, ChevronLeft, Video,
  Image, MonitorPlay,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useShootingStore } from '@/store/shootingStore';
import { useProcessingStatus } from '@/hooks/useProcessingStatus';
import { Toolbar, ToolbarActions, ToolbarHeading } from '@/components/layouts/layout-9/components/toolbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

// ── Constants ──────────────────────────────────

const GUIDED_ANGLES = [
  { id: 'front', label: 'ด้านหน้า', border: 'border-blue-500', ring: 'ring-blue-500/20', text: 'text-blue-500', bg: 'bg-blue-500/10' },
  { id: 'back', label: 'ด้านหลัง', border: 'border-violet-500', ring: 'ring-violet-500/20', text: 'text-violet-500', bg: 'bg-violet-500/10' },
  { id: 'left', label: 'ด้านซ้าย', border: 'border-emerald-500', ring: 'ring-emerald-500/20', text: 'text-emerald-500', bg: 'bg-emerald-500/10' },
  { id: 'right', label: 'ด้านขวา', border: 'border-orange-500', ring: 'ring-orange-500/20', text: 'text-orange-500', bg: 'bg-orange-500/10' },
  { id: 'top', label: 'ด้านบน', border: 'border-pink-500', ring: 'ring-pink-500/20', text: 'text-pink-500', bg: 'bg-pink-500/10' },
  { id: 'bottom', label: 'ด้านล่าง', border: 'border-sky-500', ring: 'ring-sky-500/20', text: 'text-sky-500', bg: 'bg-sky-500/10' },
  { id: 'detail', label: 'รายละเอียด', border: 'border-lime-500', ring: 'ring-lime-500/20', text: 'text-lime-600', bg: 'bg-lime-500/10' },
  { id: 'package', label: 'แพ็คเกจ', border: 'border-fuchsia-500', ring: 'ring-fuchsia-500/20', text: 'text-fuchsia-500', bg: 'bg-fuchsia-500/10' },
];

type ShootingStep = 'scan' | 'method' | 'shooting' | 'spin360' | 'done';

const STEPS: { key: ShootingStep; label: string; num: number }[] = [
  { key: 'scan', label: 'สแกน', num: 1 },
  { key: 'method', label: 'เลือกวิธี', num: 2 },
  { key: 'shooting', label: 'ถ่าย 8 มุม', num: 3 },
  { key: 'spin360', label: '360°', num: 4 },
  { key: 'done', label: 'เสร็จ', num: 5 },
];

interface ExistingPhoto {
  id: number;
  angle: string;
  thumbnail_url: string;
  quality_score: number | null;
  quality_issues: string[] | null;
}

// ── Stepper Bar ──────────────────────────────

function StepperBar({ currentStep }: { currentStep: ShootingStep }) {
  const currentIdx = STEPS.findIndex((s) => s.key === currentStep);
  return (
    <div className="flex items-center justify-center gap-2 py-4">
      {STEPS.map((step, idx) => {
        const isDone = idx < currentIdx;
        const isActive = idx === currentIdx;
        return (
          <div key={step.key} className="flex items-center gap-2">
            <div className={`size-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
              isDone ? 'bg-emerald-500 text-white'
              : isActive ? 'bg-primary text-primary-foreground ring-4 ring-primary/20'
              : 'bg-muted text-muted-foreground'
            }`}>
              {isDone ? <Check className="size-4" /> : step.num}
            </div>
            <span className={`text-xs font-medium hidden sm:inline ${
              isActive ? 'text-foreground' : isDone ? 'text-emerald-500' : 'text-muted-foreground'
            }`}>
              {step.label}
            </span>
            {idx < STEPS.length - 1 && (
              <div className={`w-8 lg:w-16 h-0.5 ${idx < currentIdx ? 'bg-emerald-500' : 'bg-muted'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main Component ────────────────────────────

export function ShootingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentBarcode, setBarcode } = useShootingStore();
  const { lastMessage, isConnected } = useProcessingStatus();

  const [step, setStep] = useState<ShootingStep>(currentBarcode ? 'shooting' : 'scan');
  const [barcodeInput, setBarcodeInput] = useState('');
  const [activeAngle, setActiveAngle] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const barcodeRef = useRef<HTMLInputElement>(null);

  // Fetch existing photos
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

  // Auto-select first empty angle when entering shooting step
  useEffect(() => {
    if (step !== 'shooting' || !currentBarcode) return;
    if (allDone) { setStep('spin360'); return; }
    const firstEmpty = GUIDED_ANGLES.find((a) => !photosByAngle.has(a.id));
    if (firstEmpty && !activeAngle) setActiveAngle(firstEmpty.id);
  }, [step, currentBarcode, allDone]);

  // WebSocket
  useEffect(() => {
    if (!lastMessage || lastMessage.type !== 'processing_done') return;
    toast.success('ประมวลผลเสร็จ!', {
      description: lastMessage.barcode,
      action: { label: 'ดูผล', onClick: () => navigate(`/gallery?search=${lastMessage.barcode}`) },
    });
  }, [lastMessage, navigate]);

  // ── Handlers ──

  const handleBarcodeScan = async () => {
    const raw = barcodeInput.trim();
    if (!raw) return;
    try {
      try { await api.get(`/api/products/${raw}`); }
      catch { await api.post('/api/products', { barcode: raw }); }
      setBarcode(raw);
      setBarcodeInput('');
      setActiveAngle(null);
      setStep('method');
      refetchPhotos();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'เกิดข้อผิดพลาด');
    }
  };

  const handleUpload = async (files: FileList | File[]) => {
    if (!currentBarcode || !activeAngle) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('barcode', currentBarcode);
    fd.append('angle', activeAngle);
    for (const f of files) fd.append('files', f);
    try {
      const res = await api.upload<{ uploaded: { quality: { score: number; issues: string[]; passed: boolean } }[]; total: number }>(
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
        toast.success(`✓ ${activeAngle}`);
      }
      await refetchPhotos();
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });

      // Auto-advance
      const nextEmpty = GUIDED_ANGLES.find((a) => a.id !== activeAngle && !photosByAngle.has(a.id));
      if (nextEmpty) {
        setActiveAngle(nextEmpty.id);
      } else {
        setStep('spin360');
        confetti({ particleCount: 100, spread: 60, origin: { y: 0.7 } });
        toast.success('ครบ 8 มุมแล้ว — ต่อไปทำ 360°');
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ');
    } finally {
      setUploading(false);
    }
  };

  const handleVideoUpload = async (file: File) => {
    if (!currentBarcode) return;
    setUploading(true);
    toast.info('กำลังตัดเฟรมจากวิดีโอ 360°...');
    const fd = new FormData();
    fd.append('barcode', currentBarcode);
    fd.append('file', file);
    try {
      const res = await api.upload<{ extracted: number; angles: string[]; message: string }>(
        '/api/spin360/video-to-angles', fd
      );
      toast.success(`ตัดได้ ${res.extracted} มุม: ${res.angles.join(', ')}`);
      await refetchPhotos();
      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
      setStep('shooting');
      // Find remaining
      const remaining = GUIDED_ANGLES.filter((a) => !photosByAngle.has(a.id) && !res.angles.includes(a.id));
      if (remaining.length > 0) {
        setActiveAngle(remaining[0].id);
        toast.info(`เหลือถ่ายเพิ่ม ${remaining.length} มุม`);
      } else {
        setStep('spin360');
        confetti({ particleCount: 100, spread: 60, origin: { y: 0.7 } });
        toast.success('ครบ 8 มุมแล้ว — ต่อไปทำ 360°');
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'ตัดเฟรมไม่สำเร็จ');
    } finally {
      setUploading(false);
    }
  };

  const activeAngleConfig = GUIDED_ANGLES.find((a) => a.id === activeAngle);

  // ── Render ──

  return (
    <>
      <Toolbar>
        <ToolbarHeading
          title={currentBarcode || 'ถ่ายภาพ'}
          description={currentBarcode ? `${doneCount}/8 มุม` : 'สแกนบาร์โค้ดเพื่อเริ่มถ่าย'}
        />
        <ToolbarActions>
          <span className="flex items-center gap-1.5 text-xs mr-2">
            {isConnected
              ? <><Wifi className="size-3 text-emerald-500" /><span className="text-emerald-500">เชื่อมต่อ</span></>
              : <><WifiOff className="size-3 text-red-500" /><span className="text-red-500">ขาดการเชื่อมต่อ</span></>
            }
          </span>
          {currentBarcode && (
            <Button variant="outline" size="sm" onClick={() => { setBarcode(''); setStep('scan'); setActiveAngle(null); }}>
              เปลี่ยน barcode
            </Button>
          )}
        </ToolbarActions>
      </Toolbar>

      <div className="container pb-7">
        {/* Stepper */}
        <StepperBar currentStep={step} />

        {/* ── Step 1: Scan ── */}
        {step === 'scan' && (
          <div className="flex items-center justify-center min-h-[50vh]">
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
        )}

        {/* ── Step 2: Choose Method ── */}
        {step === 'method' && (
          <div className="flex items-center justify-center min-h-[50vh]">
            <div className="max-w-lg w-full space-y-6 text-center">
              <div>
                <h2 className="text-xl font-bold text-foreground">เลือกวิธีถ่ายรูป</h2>
                <p className="text-sm text-muted-foreground mt-1">{currentBarcode}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {/* Option 1: Manual */}
                <button onClick={() => setStep('shooting')}
                  className="group rounded-2xl border-2 border-border hover:border-primary p-6 text-left transition-all hover:shadow-lg">
                  <div className="size-14 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Camera className="size-7 text-blue-500" />
                  </div>
                  <h3 className="text-base font-bold text-foreground">ถ่ายทีละมุม</h3>
                  <p className="text-sm text-muted-foreground mt-1">ระบบบอกว่าต้องถ่ายมุมไหน ทีละมุม</p>
                  <div className="flex items-center gap-1.5 mt-3 text-2xs text-muted-foreground">
                    <Image className="size-3.5" /> 8 มุม
                  </div>
                </button>

                {/* Option 2: Video */}
                <label className="group rounded-2xl border-2 border-border hover:border-amber-500 p-6 text-left transition-all hover:shadow-lg cursor-pointer">
                  <div className="size-14 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                    <Video className="size-7 text-amber-500" />
                  </div>
                  <h3 className="text-base font-bold text-foreground">วิดีโอ 360°</h3>
                  <p className="text-sm text-muted-foreground mt-1">ได้ 4 มุมอัตโนมัติ เหลือถ่ายเพิ่ม 4 มุม</p>
                  <div className="flex items-center gap-1.5 mt-3 text-2xs text-amber-500 font-medium">
                    <MonitorPlay className="size-3.5" /> ลดเวลา 50%
                  </div>
                  <input type="file" accept="video/*" className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleVideoUpload(e.target.files[0])} />
                </label>
              </div>

              {/* Show existing photos count */}
              {doneCount > 0 && (
                <p className="text-sm text-muted-foreground">
                  มีรูปแล้ว {doneCount} มุม — <button onClick={() => setStep('shooting')} className="text-primary hover:underline">ถ่ายต่อ</button>
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Step 3: Shooting (8-angle grid) ── */}
        {step === 'shooting' && (
          <div className="space-y-5">
            {/* 8-Angle Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {GUIDED_ANGLES.map((angle) => {
                const existing = photosByAngle.get(angle.id);
                const isActive = activeAngle === angle.id;
                const isDone = !!existing;

                return (
                  <button key={angle.id} onClick={() => !isDone && setActiveAngle(angle.id)}
                    className={`relative rounded-xl border-2 overflow-hidden transition-all ${
                      isActive ? `${angle.border} ring-4 ${angle.ring} shadow-lg`
                      : isDone ? 'border-emerald-500/30 bg-emerald-500/5'
                      : 'border-border hover:border-muted-foreground/30'
                    }`}>
                    <div className="aspect-square bg-muted relative flex items-center justify-center">
                      {existing ? (
                        <>
                          <img src={existing.thumbnail_url} alt={angle.label} className="w-full h-full object-cover" />
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
                          <Camera className={`size-8 ${angle.text} mx-auto mb-2`} />
                          <p className="text-xs text-muted-foreground">ลากรูปมาวาง</p>
                        </div>
                      ) : (
                        <Camera className="size-5 text-muted-foreground/30" />
                      )}
                    </div>
                    <div className={`px-3 py-2 text-center ${
                      isDone ? 'bg-emerald-500/10' : isActive ? angle.bg : 'bg-card'
                    }`}>
                      <p className={`text-xs font-medium ${
                        isDone ? 'text-emerald-600 dark:text-emerald-400' : isActive ? angle.text : 'text-muted-foreground'
                      }`}>
                        {isDone ? '✓ ' : ''}{angle.label}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Dropzone */}
            {activeAngle && (
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
                    <div className={`size-16 rounded-2xl ${activeAngleConfig?.bg || 'bg-primary/10'} flex items-center justify-center mx-auto mb-4`}>
                      <Upload className={`size-7 ${isDragging ? 'text-primary animate-bounce' : activeAngleConfig?.text || 'text-primary'}`} />
                    </div>
                    <p className="text-lg font-semibold text-foreground">ถ่าย{activeAngleConfig?.label}</p>
                    <p className="text-sm text-muted-foreground mt-1">ลากรูปมาวางที่นี่ หรือคลิกเลือกไฟล์</p>
                    <label className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-medium cursor-pointer hover:bg-primary/90 shadow-sm">
                      เลือกไฟล์
                      <input type="file" multiple accept="image/*,.cr2,.cr3,.arw,.nef,.tif,.tiff"
                        className="hidden" onChange={(e) => e.target.files && handleUpload(e.target.files)} />
                    </label>
                  </>
                )}
              </div>
            )}

            {/* Video shortcut */}
            {doneCount < 4 && (
              <label className="flex items-center justify-center gap-2 p-3 rounded-xl border border-dashed border-amber-500/30 text-sm text-amber-600 dark:text-amber-400 cursor-pointer hover:bg-amber-500/5 transition-colors">
                <Video className="size-4" />
                หรืออัปโหลดวิดีโอ 360° เพื่อได้ 4 มุมอัตโนมัติ
                <input type="file" accept="video/*" className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleVideoUpload(e.target.files[0])} />
              </label>
            )}
          </div>
        )}

        {/* ── Step 4: 360° ── */}
        {step === 'spin360' && (
          <div className="space-y-5">
            {/* 8-angle preview */}
            <div className="grid grid-cols-4 gap-2 max-w-md mx-auto">
              {GUIDED_ANGLES.map((a) => {
                const photo = photosByAngle.get(a.id);
                return (
                  <div key={a.id} className="rounded-lg border border-emerald-500/20 overflow-hidden">
                    {photo ? (
                      <img src={photo.thumbnail_url} alt={a.label} className="w-full aspect-square object-cover" />
                    ) : (
                      <div className="w-full aspect-square bg-muted" />
                    )}
                  </div>
                );
              })}
            </div>

            {/* 360 Upload */}
            <div className="rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-50/30 to-card dark:from-card dark:to-amber-950/10 p-8">
              <div className="text-center mb-6">
                <div className="size-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mx-auto mb-4">
                  <RotateCw className="size-8 text-amber-500" />
                </div>
                <h2 className="text-xl font-bold text-foreground">ถ่ายวิดีโอ 360°</h2>
                <p className="text-sm text-muted-foreground mt-1">หมุนสินค้ารอบตัว 1 รอบ แล้วอัปโหลดวิดีโอ</p>
              </div>

              <div
                className={`rounded-xl border-2 border-dashed p-10 text-center transition-all ${
                  uploading ? 'border-amber-400 bg-amber-400/5' : 'border-border hover:border-amber-500/40'
                }`}
              >
                {uploading ? (
                  <div className="flex items-center justify-center gap-3">
                    <Loader2 className="size-6 animate-spin text-amber-500" />
                    <span className="text-foreground font-medium">กำลังอัปโหลดและประมวลผล...</span>
                  </div>
                ) : (
                  <>
                    <Upload className="size-10 text-amber-500/50 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">ลากวิดีโอมาวาง หรือคลิกเลือกไฟล์</p>
                    <label className="mt-4 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 text-white text-sm font-medium cursor-pointer hover:bg-amber-600 shadow-sm">
                      <Video className="size-4" /> เลือกวิดีโอ
                      <input type="file" accept="video/*" className="hidden"
                        onChange={async (e) => {
                          const file = e.target.files?.[0];
                          if (!file || !currentBarcode) return;
                          setUploading(true);
                          toast.info('กำลังอัปโหลด 360°...');
                          const fd = new FormData();
                          fd.append('barcode', currentBarcode);
                          fd.append('file', file);
                          try {
                            await api.upload('/api/spin360/video', fd);
                            toast.success('360° สำเร็จ!');
                            confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
                            setStep('done');
                            queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
                          } catch (err: unknown) {
                            toast.error(err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ');
                          } finally {
                            setUploading(false);
                          }
                        }}
                      />
                    </label>
                  </>
                )}
              </div>

              <p className="text-center text-2xs text-muted-foreground mt-4">
                รองรับ MP4, MOV, AVI — สูงสุด 500 MB
              </p>
            </div>

            {/* Also allow frame upload */}
            <div className="rounded-xl border border-border p-5">
              <div className="flex items-center gap-3 mb-3">
                <Upload className="size-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">หรืออัปโหลดเฟรม 360°</span>
              </div>
              <label className="flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed border-border text-sm text-muted-foreground cursor-pointer hover:border-primary hover:text-primary transition-colors">
                เลือกรูปเฟรม 360° (เรียงตามชื่อไฟล์)
                <input type="file" multiple accept="image/*" className="hidden"
                  onChange={async (e) => {
                    const files = e.target.files;
                    if (!files || !currentBarcode) return;
                    setUploading(true);
                    const fd = new FormData();
                    fd.append('barcode', currentBarcode);
                    for (const f of Array.from(files).sort((a, b) => a.name.localeCompare(b.name))) {
                      fd.append('files', f);
                    }
                    try {
                      await api.upload('/api/spin360/frames', fd);
                      toast.success('360° สำเร็จ!');
                      confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
                      setStep('done');
                      queryClient.invalidateQueries({ queryKey: ['pipeline-stats'] });
                    } catch (err: unknown) {
                      toast.error(err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ');
                    } finally {
                      setUploading(false);
                    }
                  }}
                />
              </label>
            </div>
          </div>
        )}

        {/* ── Step 5: Done ── */}
        {step === 'done' && (
          <div className="flex items-center justify-center min-h-[50vh]">
            <div className="max-w-md w-full text-center space-y-6">
              <div className="size-20 rounded-3xl bg-emerald-500/10 flex items-center justify-center mx-auto">
                <Check className="size-10 text-emerald-500" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">เสร็จสมบูรณ์!</h2>
                <p className="text-sm text-muted-foreground mt-1">{currentBarcode} — ถ่ายรูป 8 มุม + 360° เรียบร้อย</p>
              </div>

              <div className="grid grid-cols-4 gap-2 max-w-xs mx-auto">
                {GUIDED_ANGLES.map((a) => {
                  const photo = photosByAngle.get(a.id);
                  return (
                    <div key={a.id} className="rounded-lg border border-emerald-500/20 overflow-hidden">
                      {photo ? (
                        <img src={photo.thumbnail_url} alt={a.label} className="w-full aspect-square object-cover" />
                      ) : (
                        <div className="w-full aspect-square bg-muted" />
                      )}
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-center gap-3">
                <Button variant="outline" onClick={() => navigate(`/gallery?search=${currentBarcode}`)}>
                  ดูรูปทั้งหมด
                </Button>
                <Button onClick={() => {
                  setBarcode('');
                  setStep('scan');
                  setActiveAngle(null);
                  navigate('/');
                }}>
                  สินค้าถัดไป <ArrowRight className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
