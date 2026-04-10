import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Upload, Wifi, WifiOff, ScanBarcode, Loader2, Camera } from 'lucide-react';
import { api } from '@/lib/api';
import { useShootingStore } from '@/store/shootingStore';
import { useProcessingStatus } from '@/hooks/useProcessingStatus';

export function ShootingPage() {
  const {
    currentBarcode, currentAngle, angleCounters, angles,
    setBarcode, setAngle, incrementCounter, setLastPreview, lastPreviewUrl,
  } = useShootingStore();

  const { lastMessage, isConnected } = useProcessingStatus();
  const [barcodeInput, setBarcodeInput] = useState('');
  const [productInfo, setProductInfo] = useState<{ name: string; category: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activityLog, setActivityLog] = useState<{ time: string; msg: string; type: string }[]>([]);
  const barcodeRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);

  const log = useCallback((msg: string, type = 'info') => {
    const time = new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setActivityLog((prev) => [...prev.slice(-50), { time, msg, type }]);
    setTimeout(() => logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' }), 50);
  }, []);

  // WebSocket processing status
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'processing_done') {
      log(`✓ ประมวลผลเสร็จ: ${lastMessage.barcode}`, 'success');
    } else if (lastMessage.type === 'processing_error') {
      log(`✗ ประมวลผลผิดพลาด: ${lastMessage.barcode}`, 'error');
    } else if (lastMessage.type === 'processing_start') {
      log(`⏳ กำลังประมวลผล: ${lastMessage.filename || lastMessage.barcode}`, 'info');
    }
  }, [lastMessage, log]);

  // Barcode scan
  const handleBarcodeScan = async () => {
    const raw = barcodeInput.trim();
    if (!raw) return;
    try {
      let product;
      try {
        product = await api.get<{ barcode: string; name: string; category: string }>(`/api/products/${raw}`);
      } catch {
        product = await api.post<{ barcode: string; name: string; category: string }>('/api/products', { barcode: raw });
      }
      setBarcode(raw);
      setProductInfo({ name: product.name, category: product.category });
      log(`สแกน: ${raw}${product.name ? ` — ${product.name}` : ''}`, 'success');
      setBarcodeInput('');
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'เกิดข้อผิดพลาด');
    }
  };

  // File upload
  const handleFiles = async (files: FileList | File[]) => {
    if (!currentBarcode || !currentAngle) {
      toast.error('กรุณาสแกนบาร์โค้ดและเลือกมุมถ่ายก่อน');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('barcode', currentBarcode);
    formData.append('angle', currentAngle);
    for (const file of files) formData.append('files', file);
    try {
      const res = await api.upload<{ uploaded: { filename: string; preview_url: string }[]; total: number }>(
        '/api/photos/upload', formData
      );
      for (const photo of res.uploaded) {
        incrementCounter(currentAngle);
        setLastPreview(photo.preview_url);
        log(`✓ ${photo.filename}`, 'success');
      }
      toast.success(`อัปโหลดสำเร็จ ${res.total} รูป`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'อัปโหลดไม่สำเร็จ');
      log(`✗ อัปโหลดไม่สำเร็จ`, 'error');
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // F1-F8 should work even when typing in input
      const keyMap: Record<string, string> = {};
      angles.forEach((a) => { keyMap[a.key.toUpperCase()] = a.id; });
      if (keyMap[e.key.toUpperCase()] && currentBarcode) {
        e.preventDefault();
        setAngle(keyMap[e.key.toUpperCase()]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [angles, currentBarcode, setAngle]);

  const totalPhotos = Object.values(angleCounters).reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-var(--header-height,60px))] gap-4 p-4 overflow-auto">
      {/* ── LEFT PANEL ── */}
      <div className="w-full lg:w-80 lg:shrink-0 flex flex-col gap-3 lg:overflow-y-auto">

        {/* Barcode */}
        <div className="rounded-2xl border border-blue-500/20 bg-gradient-to-br from-card to-blue-950/20 p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <ScanBarcode className="w-4 h-4 text-white" />
            </div>
            <h3 className="text-sm font-semibold text-foreground">สแกนบาร์โค้ด</h3>
          </div>
          <div className="relative">
            <input
              ref={barcodeRef}
              type="text"
              value={barcodeInput}
              onChange={(e) => setBarcodeInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleBarcodeScan()}
              placeholder="สแกนหรือพิมพ์บาร์โค้ด..."
              className="w-full px-4 py-3.5 rounded-xl border border-border bg-background text-foreground text-lg font-mono font-bold focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent focus:shadow-lg focus:shadow-primary/10 transition-all placeholder:text-muted-foreground/40"
              autoFocus
            />
          </div>
          {currentBarcode && (
            <div className="mt-3 flex items-center gap-2">
              <span className="px-3 py-1 rounded-lg bg-gradient-to-r from-blue-500 to-violet-600 text-white text-sm font-bold shadow-sm">
                {currentBarcode}
              </span>
              {productInfo?.name && (
                <span className="text-sm text-muted-foreground">{productInfo.name}</span>
              )}
            </div>
          )}
        </div>

        {/* Angle Selection */}
        <div className="rounded-2xl border border-violet-500/20 bg-gradient-to-br from-card to-violet-950/20 p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-foreground">🎯 มุมถ่ายภาพ</h3>
            {!currentBarcode && (
              <span className="text-2xs text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded-md font-medium">
                สแกนบาร์โค้ดก่อน
              </span>
            )}
          </div>
          <div className="space-y-1.5">
            {angles.map((angle) => {
              const isActive = currentAngle === angle.id;
              const count = angleCounters[angle.id] || 0;
              return (
                <button
                  key={angle.id}
                  onClick={() => currentBarcode && setAngle(angle.id)}
                  disabled={!currentBarcode}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-500 to-violet-600 text-white shadow-lg shadow-blue-500/25 scale-[1.02]'
                      : 'hover:bg-accent/10 text-foreground disabled:opacity-40 disabled:cursor-not-allowed'
                  }`}
                >
                  <kbd className={`px-2 py-0.5 rounded-md text-xs font-mono font-bold ${
                    isActive ? 'bg-white/20' : 'bg-muted text-muted-foreground'
                  }`}>
                    {angle.key}
                  </kbd>
                  <span className="flex-1 text-left">{angle.label_th}</span>
                  {count > 0 && (
                    <span className={`min-w-[24px] h-6 flex items-center justify-center rounded-full text-xs font-bold ${
                      isActive ? 'bg-white/20' : 'bg-primary/10 text-primary'
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Session Info */}
        <div className="rounded-2xl border border-emerald-500/20 bg-gradient-to-br from-card to-emerald-950/20 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">เซสชัน</p>
              <p className="text-3xl font-bold text-foreground mt-1">{totalPhotos}</p>
              <p className="text-xs text-muted-foreground">รูปทั้งหมด</p>
            </div>
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/25">
              <Camera className="w-7 h-7 text-white" />
            </div>
          </div>
        </div>
      </div>

      {/* ── MAIN AREA ── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-[400px]">

        {/* Dropzone + Preview */}
        <div
          className={`flex-1 rounded-2xl border-2 border-dashed transition-all duration-300 flex items-center justify-center relative overflow-hidden ${
            isDragging ? 'border-primary bg-primary/5 shadow-inner scale-[0.99]' :
            uploading ? 'border-amber-400 bg-amber-400/5' :
            'border-border bg-gradient-to-br from-card to-blue-950/10 hover:border-blue-400/50 hover:shadow-lg hover:shadow-blue-500/5'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
        >
          {lastPreviewUrl ? (
            <img src={lastPreviewUrl} alt="preview" className="max-w-full max-h-full object-contain p-4" />
          ) : (
            <div className="text-center p-8">
              <div className={`mx-auto mb-6 w-20 h-20 rounded-3xl flex items-center justify-center ${
                isDragging ? 'bg-primary/20 scale-110' : 'bg-muted'
              } transition-all duration-300`}>
                <Upload className={`w-10 h-10 ${isDragging ? 'text-primary animate-bounce' : 'text-muted-foreground/40'}`} />
              </div>
              <p className="text-foreground font-medium text-lg">
                {!currentBarcode ? 'สแกนบาร์โค้ดก่อน' :
                 !currentAngle ? 'เลือกมุมถ่ายก่อน' :
                 'ลากรูปมาวางที่นี่'}
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                {currentBarcode && currentAngle ? 'หรือคลิกเพื่อเลือกไฟล์ · JPG, PNG, CR2, CR3, ARW, NEF, TIF' : ''}
              </p>
            </div>
          )}

          <input
            type="file" multiple accept="image/*,.cr2,.cr3,.arw,.nef,.tif,.tiff"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
            disabled={!currentBarcode || !currentAngle}
          />

          {uploading && (
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
                <span className="text-foreground font-medium">กำลังอัปโหลด...</span>
              </div>
            </div>
          )}
        </div>

        {/* Activity Log */}
        <div className="rounded-2xl border border-amber-500/20 bg-gradient-to-br from-card to-amber-950/10 overflow-hidden">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">บันทึกกิจกรรม</h3>
            <span className="flex items-center gap-1.5 text-xs">
              {isConnected
                ? <><Wifi className="w-3 h-3 text-emerald-500" /><span className="text-emerald-500">เชื่อมต่อ</span></>
                : <><WifiOff className="w-3 h-3 text-red-500" /><span className="text-red-500">ขาดการเชื่อมต่อ</span></>
              }
            </span>
          </div>
          <div ref={logRef} className="h-36 overflow-y-auto px-5 py-3 space-y-1.5">
            {activityLog.length === 0 ? (
              <p className="text-muted-foreground/40 py-6 text-center text-sm">ยังไม่มีกิจกรรม</p>
            ) : (
              activityLog.map((entry, i) => (
                <div key={i} className={`flex gap-3 items-start text-sm rounded-lg px-3 py-2 ${
                  entry.type === 'success' ? 'bg-emerald-500/5 text-emerald-500' :
                  entry.type === 'error' ? 'bg-red-500/5 text-red-500' :
                  entry.type === 'warning' ? 'bg-amber-500/5 text-amber-500' :
                  'bg-muted/30 text-muted-foreground'
                }`}>
                  <span className="text-[11px] text-muted-foreground shrink-0 font-mono mt-0.5">{entry.time}</span>
                  <span>{entry.msg}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
