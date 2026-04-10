import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { Upload, Wifi, WifiOff } from 'lucide-react';
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

  // Log helper
  const log = useCallback((msg: string, type = 'info') => {
    const time = new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setActivityLog((prev) => [...prev.slice(-50), { time, msg, type }]);
    setTimeout(() => logRef.current?.scrollTo({ top: logRef.current.scrollHeight }), 50);
  }, []);

  // WebSocket processing status
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === 'processing_done') {
      log(`✓ ประมวลผลเสร็จ: ${lastMessage.barcode}`, 'success');
      toast.success('ประมวลผลเสร็จ');
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
      // Try lookup first
      let product;
      try {
        product = await api.get<{ barcode: string; name: string; category: string }>(`/api/products/${raw}`);
      } catch {
        // Auto-create if not found
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

  // File upload handler
  const handleFiles = async (files: FileList | File[]) => {
    if (!currentBarcode || !currentAngle) {
      toast.error('กรุณาสแกนบาร์โค้ดและเลือกมุมถ่ายก่อน');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('barcode', currentBarcode);
    formData.append('angle', currentAngle);
    for (const file of files) {
      formData.append('files', file);
    }
    try {
      const res = await api.upload<{ uploaded: { filename: string; preview_url: string; count: number }[]; total: number }>(
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

  // Drag & drop handlers
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  };

  // Keyboard shortcuts: F1-F8 for angle, Ctrl+Z for undo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const keyMap: Record<string, string> = {};
      angles.forEach((a) => { keyMap[a.key.toUpperCase()] = a.id; });
      if (keyMap[e.key.toUpperCase()]) {
        e.preventDefault();
        if (currentBarcode) setAngle(keyMap[e.key.toUpperCase()]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [angles, currentBarcode, setAngle]);

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-var(--header-height,60px))] gap-4 p-4 overflow-auto">
      {/* ── LEFT PANEL (320px on desktop, full width on mobile) ── */}
      <div className="w-full lg:w-80 lg:shrink-0 flex flex-col gap-3 lg:overflow-y-auto">

        {/* Barcode Input */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">สแกนบาร์โค้ด</h3>
          <input
            ref={barcodeRef}
            type="text"
            value={barcodeInput}
            onChange={(e) => setBarcodeInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleBarcodeScan()}
            placeholder="สแกนหรือพิมพ์บาร์โค้ด..."
            className="w-full px-4 py-3 rounded-lg border border-border bg-background text-foreground text-xl font-mono font-bold focus:outline-none focus:ring-2 focus:ring-primary placeholder:text-muted-foreground/50"
            autoFocus
          />
          {currentBarcode && (
            <div className="mt-2 flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-primary/10 text-primary text-sm font-semibold">
                {currentBarcode}
              </span>
              {productInfo?.name && (
                <span className="text-sm text-muted-foreground">{productInfo.name}</span>
              )}
            </div>
          )}
        </div>

        {/* Angle Selection */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-muted-foreground mb-3">มุมถ่ายภาพ</h3>
          <div className="space-y-1">
            {angles.map((angle) => {
              const isActive = currentAngle === angle.id;
              const count = angleCounters[angle.id] || 0;
              return (
                <button
                  key={angle.id}
                  onClick={() => currentBarcode && setAngle(angle.id)}
                  disabled={!currentBarcode}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent/10 text-foreground disabled:opacity-40'
                  }`}
                >
                  <kbd className={`px-1.5 py-0.5 rounded text-xs font-mono font-bold ${
                    isActive ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted text-muted-foreground'
                  }`}>
                    {angle.key}
                  </kbd>
                  <span className="flex-1 text-left">{angle.label_th} ({angle.label})</span>
                  {count > 0 && (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                      isActive ? 'bg-primary-foreground/20' : 'bg-muted text-muted-foreground'
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
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="text-sm font-semibold text-muted-foreground mb-2">เซสชัน</h3>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {Object.values(angleCounters).reduce((a, b) => a + b, 0)}
            </span>
            <span className="text-sm text-muted-foreground">รูป</span>
          </div>
        </div>
      </div>

      {/* ── MAIN AREA ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0 min-h-[400px]">

        {/* Photo Dropzone + Preview */}
        <div
          className={`flex-1 rounded-xl border-2 border-dashed transition-colors flex items-center justify-center relative overflow-hidden ${
            isDragging ? 'border-primary bg-primary/5' :
            uploading ? 'border-yellow-500 bg-yellow-500/5' :
            'border-border bg-card'
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
        >
          {lastPreviewUrl ? (
            <img
              src={lastPreviewUrl}
              alt="preview"
              className="max-w-full max-h-full object-contain"
            />
          ) : (
            <div className="text-center p-8">
              <Upload className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-muted-foreground">
                {!currentBarcode ? 'สแกนบาร์โค้ดก่อน' :
                 !currentAngle ? 'เลือกมุมถ่ายก่อน' :
                 'ลากรูปมาวางที่นี่ หรือคลิกเพื่อเลือก'}
              </p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                JPG, PNG, CR2, CR3, ARW, NEF, TIF
              </p>
            </div>
          )}

          {/* Hidden file input */}
          <input
            type="file"
            multiple
            accept="image/*,.cr2,.cr3,.arw,.nef,.tif,.tiff"
            className="absolute inset-0 opacity-0 cursor-pointer"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
            disabled={!currentBarcode || !currentAngle}
          />

          {uploading && (
            <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
              <div className="flex items-center gap-3">
                <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
                <span className="text-foreground font-medium">กำลังอัปโหลด...</span>
              </div>
            </div>
          )}
        </div>

        {/* Activity Log */}
        <div className="rounded-xl border border-border bg-card">
          <div className="px-4 py-2 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-muted-foreground">บันทึกกิจกรรม</h3>
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              {isConnected ? <Wifi className="w-3 h-3 text-green-500" /> : <WifiOff className="w-3 h-3 text-red-500" />}
              {isConnected ? 'เชื่อมต่อ' : 'ขาดการเชื่อมต่อ'}
            </span>
          </div>
          <div ref={logRef} className="h-36 overflow-y-auto px-4 py-2 font-mono text-xs space-y-0.5">
            {activityLog.length === 0 ? (
              <p className="text-muted-foreground/50 py-4 text-center">ยังไม่มีกิจกรรม</p>
            ) : (
              activityLog.map((entry, i) => (
                <div key={i} className={`flex gap-3 ${
                  entry.type === 'success' ? 'text-green-500' :
                  entry.type === 'error' ? 'text-red-500' :
                  entry.type === 'warning' ? 'text-yellow-500' :
                  'text-muted-foreground'
                }`}>
                  <span className="text-muted-foreground/60 shrink-0">{entry.time}</span>
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
