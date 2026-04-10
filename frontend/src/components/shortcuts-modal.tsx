import { useState, useEffect } from 'react';
import { X, Keyboard, Command } from 'lucide-react';

const SHORTCUTS = [
  { keys: 'F1 — F8', desc: 'เลือกมุมถ่ายภาพ', color: 'text-blue-500' },
  { keys: 'Enter', desc: 'สแกนบาร์โค้ด', color: 'text-emerald-500' },
  { keys: 'Ctrl + Z', desc: 'เลิกทำ (undo)', color: 'text-amber-500' },
  { keys: '?', desc: 'แสดง/ซ่อนคู่มือนี้', color: 'text-violet-500' },
];

export function ShortcutsModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === '?') { e.preventDefault(); setOpen((p) => !p); }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
         onClick={() => setOpen(false)}>
      <div className="bg-card rounded-2xl border border-border w-full max-w-sm shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
           onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-violet-600 p-5 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                <Keyboard className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold">คีย์ลัด</h2>
                <p className="text-sm text-white/70">ใช้งานเร็วขึ้น</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Shortcuts */}
        <div className="p-5 space-y-3">
          {SHORTCUTS.map((s) => (
            <div key={s.keys} className="flex items-center justify-between p-3 rounded-xl bg-muted/50 hover:bg-muted transition-colors">
              <span className="text-sm text-foreground font-medium">{s.desc}</span>
              <kbd className={`px-3 py-1.5 rounded-lg bg-background border border-border text-xs font-mono font-bold ${s.color}`}>
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>

        <div className="px-5 pb-5">
          <p className="text-xs text-muted-foreground text-center flex items-center justify-center gap-1">
            กด <Command className="w-3 h-3" /> <kbd className="px-1 rounded bg-muted text-[10px]">?</kbd> เพื่อเปิด/ปิด
          </p>
        </div>
      </div>
    </div>
  );
}
