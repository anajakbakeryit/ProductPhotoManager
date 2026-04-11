import { Search } from 'lucide-react';
import { ANGLE_FILTERS } from './types';

interface PhotoFiltersProps {
  search: string;
  angle: string;
  onSearchChange: (value: string) => void;
  onAngleChange: (value: string) => void;
}

export function PhotoFilters({ search, angle, onSearchChange, onAngleChange }: PhotoFiltersProps) {
  return (
    <div className="flex gap-3 flex-wrap">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="ค้นหาบาร์โค้ด ชื่อ หมวดหมู่..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
        />
      </div>
      <div className="flex gap-1.5 flex-wrap">
        {ANGLE_FILTERS.map((a) => (
          <button
            key={a.value}
            onClick={() => onAngleChange(a.value)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              angle === a.value
                ? `${a.active} shadow-sm`
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}
