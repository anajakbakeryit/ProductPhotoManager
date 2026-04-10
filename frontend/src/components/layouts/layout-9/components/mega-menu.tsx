import { Link, useLocation } from 'react-router-dom';
import { MENU_MEGA } from '@/config/layout-9.config';
import { cn } from '@/lib/utils';
import { useMenu } from '@/hooks/use-menu';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';

export function MegaMenu() {
  const { pathname } = useLocation();
  const { isActive } = useMenu(pathname);

  const linkClass = `
    inline-flex flex-row items-center gap-1.5 h-12 py-0 border-b-2 border-transparent rounded-none bg-transparent -mb-[1px]
    text-sm text-secondary-foreground font-medium
    hover:text-primary hover:bg-transparent
    focus:text-primary focus:bg-transparent
    data-[active=true]:text-primary data-[active=true]:bg-transparent data-[active=true]:border-primary
  `;

  return (
    <NavigationMenu>
      <NavigationMenuList className="gap-1">
        {MENU_MEGA.map((item) => (
          <NavigationMenuItem key={item.path}>
            <NavigationMenuLink asChild>
              <Link
                to={item.path || '/'}
                className={cn(linkClass)}
                data-active={isActive(item.path) || undefined}
              >
                {item.icon && <item.icon className="size-4" />}
                {item.title}
              </Link>
            </NavigationMenuLink>
          </NavigationMenuItem>
        ))}
      </NavigationMenuList>
    </NavigationMenu>
  );
}
