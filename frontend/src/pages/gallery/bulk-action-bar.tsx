import { X, FileArchive, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface BulkActionBarProps {
  count: number;
  onSelectAll: () => void;
  onDownload: () => void;
  onDelete: () => void;
  onCancel: () => void;
}

export function BulkActionBar({ count, onSelectAll, onDownload, onDelete, onCancel }: BulkActionBarProps) {
  if (count === 0) return null;

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 px-5 py-3 rounded-2xl bg-card border border-border shadow-2xl">
      <span className="text-sm font-medium text-foreground">เลือก {count} รูป</span>
      <div className="w-px h-5 bg-border" />
      <Button size="sm" variant="outline" onClick={onSelectAll}>เลือกทั้งหมด</Button>
      <Button size="sm" variant="outline" onClick={onDownload}>
        <FileArchive className="size-4" /> ZIP
      </Button>
      <Button size="sm" variant="destructive" onClick={onDelete}>
        <Trash2 className="size-4" /> ลบ
      </Button>
      <Button size="sm" variant="ghost" onClick={onCancel}>
        <X className="size-4" />
      </Button>
    </div>
  );
}
