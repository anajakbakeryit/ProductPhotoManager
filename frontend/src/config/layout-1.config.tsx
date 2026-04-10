import {
  LayoutDashboard,
  Camera,
  Image,
  RotateCw,
  Clock,
  BarChart3,
  Settings,
} from 'lucide-react';
import { MenuConfig } from '@/config/types';

// Mega menus (required by layout component — minimal items to prevent crash)
export const MENU_MEGA: MenuConfig = [
  { title: 'แดชบอร์ด', icon: LayoutDashboard, path: '/' },
];
export const MENU_MEGA_MOBILE: MenuConfig = [
  { title: 'แดชบอร์ด', icon: LayoutDashboard, path: '/' },
];

export const MENU_SIDEBAR: MenuConfig = [
  {
    heading: 'เมนูหลัก',
  },
  {
    title: 'แดชบอร์ด',
    icon: LayoutDashboard,
    path: '/',
    badge: '🏠',
  },
  {
    title: 'ถ่ายภาพ',
    icon: Camera,
    path: '/shooting',
    badge: '📸',
  },
  {
    title: 'แกลเลอรี่',
    icon: Image,
    path: '/gallery',
    badge: '🖼️',
  },
  {
    title: '360 องศา',
    icon: RotateCw,
    path: '/360',
    badge: '🔄',
  },
  {
    heading: 'ข้อมูล',
  },
  {
    title: 'เซสชัน',
    icon: Clock,
    path: '/sessions',
    badge: '⏱️',
  },
  {
    title: 'รายงาน',
    icon: BarChart3,
    path: '/reports',
    badge: '📊',
  },
  {
    heading: 'ระบบ',
  },
  {
    title: 'ตั้งค่า',
    icon: Settings,
    path: '/settings',
    badge: '⚙️',
  },
];
