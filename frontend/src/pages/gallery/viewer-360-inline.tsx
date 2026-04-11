import { Eye, X } from 'lucide-react';

interface Viewer360InlineProps {
  barcode: string;
  onClose: () => void;
}

export function Viewer360Inline({ barcode, onClose }: Viewer360InlineProps) {
  return (
    <div className="rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-50/30 to-card dark:from-card dark:to-amber-950/10 overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="size-7 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <Eye className="size-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold text-foreground">360° — {barcode}</span>
        </div>
        <button onClick={onClose}
          className="size-7 rounded-lg flex items-center justify-center hover:bg-muted transition-colors">
          <X className="size-4" />
        </button>
      </div>
      <iframe
        src={`/api/spin360/${barcode}/viewer`}
        className="w-full bg-black"
        style={{ height: '450px' }}
        title="360 Viewer"
      />
    </div>
  );
}
