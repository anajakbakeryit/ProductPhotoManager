import { useEffect, useState } from 'react';
import { useTheme } from 'next-themes';
import {
  Camera,
  Menu,
  Sun,
  Moon,
} from 'lucide-react';
import { useLocation } from 'react-router';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { useScrollPosition } from '@/hooks/use-scroll-position';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetHeader,
  SheetTrigger,
} from '@/components/ui/sheet';
import { SidebarMenu } from './sidebar-menu';

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';
  return (
    <Button
      variant="ghost"
      mode="icon"
      shape="circle"
      className="size-9 hover:bg-primary/10"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      title={isDark ? 'เปลี่ยนเป็น Light Mode' : 'เปลี่ยนเป็น Dark Mode'}
    >
      {isDark ? <Sun className="size-4.5 text-amber-400" /> : <Moon className="size-4.5 text-violet-500" />}
    </Button>
  );
}

export function Header() {
  const [isSidebarSheetOpen, setIsSidebarSheetOpen] = useState(false);

  const { pathname } = useLocation();
  const mobileMode = useIsMobile();

  const scrollPosition = useScrollPosition();
  const headerSticky: boolean = scrollPosition > 0;

  // Close sheet when route changes
  useEffect(() => {
    setIsSidebarSheetOpen(false);
  }, [pathname]);

  return (
    <header
      className={cn(
        'header fixed top-0 z-10 start-0 flex items-stretch shrink-0 border-b border-transparent bg-background end-0 pe-[var(--removed-body-scroll-bar-size,0px)]',
        headerSticky && 'border-b border-border',
      )}
    >
      <div className="container-fluid flex justify-between items-stretch lg:gap-4">
        {/* HeaderLogo */}
        <div className="flex lg:hidden items-center gap-2.5">
          <Link to="/" className="shrink-0 flex items-center gap-1.5">
            <Camera className="size-5 text-primary" />
            <span className="text-sm font-bold text-foreground">Photo Manager</span>
          </Link>
          <div className="flex items-center">
            {mobileMode && (
              <Sheet
                open={isSidebarSheetOpen}
                onOpenChange={setIsSidebarSheetOpen}
              >
                <SheetTrigger asChild>
                  <Button variant="ghost" mode="icon">
                    <Menu className="text-muted-foreground/70" />
                  </Button>
                </SheetTrigger>
                <SheetContent
                  className="p-0 gap-0 w-[275px]"
                  side="left"
                  close={false}
                >
                  <SheetHeader className="p-0 space-y-0" />
                  <SheetBody className="p-0 overflow-y-auto">
                    <SidebarMenu />
                  </SheetBody>
                </SheetContent>
              </Sheet>
            )}
          </div>
        </div>

        {/* Spacer (mega menu removed) */}
        {!mobileMode && <div className="flex-1" />}

        {/* HeaderTopbar */}
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <span className="text-xs text-muted-foreground hidden sm:inline">
            Photo Manager
          </span>
        </div>
      </div>
    </header>
  );
}
