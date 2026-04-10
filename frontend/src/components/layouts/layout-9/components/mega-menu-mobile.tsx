import { useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MENU_MEGA_MOBILE } from '@/config/layout-9.config';
import {
  AccordionMenu,
  AccordionMenuClassNames,
  AccordionMenuGroup,
  AccordionMenuItem,
} from '@/components/ui/accordion-menu';

export function MegaMenuMobile() {
  const { pathname } = useLocation();

  const matchPath = useCallback(
    (path: string): boolean =>
      path === pathname || (path.length > 1 && pathname.startsWith(path)),
    [pathname],
  );

  const classNames: AccordionMenuClassNames = {
    root: 'space-y-1',
    group: 'gap-px',
    item: 'h-10 hover:bg-transparent text-accent-foreground hover:text-primary data-[selected=true]:text-primary data-[selected=true]:bg-primary/5 data-[selected=true]:font-medium',
  };

  return (
    <div className="flex grow shrink-0 py-5 px-5">
      <AccordionMenu
        selectedValue={pathname}
        matchPath={matchPath}
        type="single"
        collapsible
        classNames={classNames}
      >
        <AccordionMenuGroup>
          {MENU_MEGA_MOBILE.map((item) => (
            <AccordionMenuItem
              key={item.path}
              value={item.path || ''}
              className="text-sm font-medium"
            >
              <Link to={item.path || '/'} className="flex items-center gap-2.5">
                {item.icon && <item.icon className="size-4.5" data-slot="accordion-menu-icon" />}
                <span data-slot="accordion-menu-title">{item.title}</span>
              </Link>
            </AccordionMenuItem>
          ))}
        </AccordionMenuGroup>
      </AccordionMenu>
    </div>
  );
}
