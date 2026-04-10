import { useState, useEffect } from 'react';
import { X, Keyboard } from 'lucide-react';

const SHORTCUTS = [
  { keys: 'F1-F8', desc: 'เลือกมุมถ่ายภาพ' },
  { keys: 'Enter', desc: 'สแกนบาร์โค้ด' },
  { keys: 'Ctrl+Z', desc: 'เลิกทำ (undo)' },
  { keys: '?', desc: 'แสดง/ซ่อนคู่มือนี้' },
];

export function ShortcutsModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === '?') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
         onClick={() => setOpen(false)}>
      <div className="bg-card rounded-xl border border-border w-full max-w-sm p-6"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Keyboard className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-bold text-foreground">คีย์ลัด</h2>
          </div>
          <button onClick={() => setOpen(false)} className="p-1 rounded hover:bg-muted">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-3">
          {SHORTCUTS.map((s) => (
            <div key={s.keys} className="flex items-center justify-between">
              <span className="text-sm text-foreground">{s.desc}</span>
              <kbd className="px-2 py-1 rounded bg-muted text-xs font-mono text-muted-foreground">
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground text-center">กด ? เพื่อเปิด/ปิด</p>
      </div>
    </div>
  );
}
