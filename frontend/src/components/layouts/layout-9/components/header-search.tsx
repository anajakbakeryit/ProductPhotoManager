import { useState, useRef, useEffect } from 'react';
import { Search } from 'lucide-react';
import { useNavigate } from 'react-router';
import { Input } from '@/components/ui/input';

export function HeaderSearch() {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Cmd+/ or Ctrl+/ to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/gallery?search=${encodeURIComponent(query.trim())}`);
      inputRef.current?.blur();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="hidden md:flex items-center">
      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 start-3.5 -translate-y-1/2 size-4" />
        <Input
          ref={inputRef}
          placeholder="ค้นหาบาร์โค้ด, สินค้า..."
          className="px-9 min-w-0 w-64"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <span className="text-xs text-muted-foreground absolute end-3.5 top-1/2 -translate-y-1/2">
          ⌘ /
        </span>
      </div>
    </form>
  );
}
