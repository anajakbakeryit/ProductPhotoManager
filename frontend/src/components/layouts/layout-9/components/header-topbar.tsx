import { Sun, Moon, LogOut } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuthStore } from '@/store/authStore';
import { setToken } from '@/lib/api';
import { useNavigate } from 'react-router';

export function HeaderTopbar() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const handleLogout = () => {
    setToken(null);
    useAuthStore.setState({ user: null });
    navigate('/login');
  };

  return (
    <div className="flex items-center gap-2 lg:gap-3.5 lg:w-[400px] justify-end">
      <Button
        variant="ghost"
        mode="icon"
        shape="circle"
        className="hover:bg-transparent hover:[&_svg]:text-primary"
        onClick={() => setTheme(isDark ? 'light' : 'dark')}
        title={isDark ? 'Light Mode' : 'Dark Mode'}
      >
        {isDark ? (
          <Sun className="size-4.5! text-amber-400" />
        ) : (
          <Moon className="size-4.5! text-violet-500" />
        )}
      </Button>

      <div className="border-e border-border h-5" />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Avatar className="size-9 cursor-pointer border-2 border-primary/30 hover:border-primary transition-colors">
            <AvatarFallback className="bg-primary/10 text-primary text-sm font-semibold">
              {user?.display_name?.charAt(0) || 'A'}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <div className="px-3 py-2 border-b border-border">
            <p className="text-sm font-medium text-foreground">{user?.display_name || 'Admin'}</p>
            <p className="text-xs text-muted-foreground">{user?.role || 'admin'}</p>
          </div>
          <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
            <LogOut className="size-4 mr-2" />
            ออกจากระบบ
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
