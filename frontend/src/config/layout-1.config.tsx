import {
  Camera,
  Image,
  RotateCw,
  Clock,
  BarChart3,
  Settings,
} from 'lucide-react';
import { MenuConfig } from '@/config/types';

// Mega menus (not used — required by layout component)
export const MENU_MEGA: MenuConfig = [];
export const MENU_MEGA_MOBILE: MenuConfig = [];

export const MENU_SIDEBAR: MenuConfig = [
  {
    heading: 'เมนูหลัก',
  },
  {
    title: 'ถ่ายภาพ',
    icon: Camera,
    path: '/',
  },
  {
    title: 'แกลเลอรี่',
    icon: Image,
    path: '/gallery',
  },
  {
    title: '360 องศา',
    icon: RotateCw,
    path: '/360',
  },
  {
    heading: 'ข้อมูล',
  },
  {
    title: 'เซสชัน',
    icon: Clock,
    path: '/sessions',
  },
  {
    title: 'รายงาน',
    icon: BarChart3,
    path: '/reports',
  },
  {
    heading: 'ระบบ',
  },
  {
    title: 'ตั้งค่า',
    icon: Settings,
    path: '/settings',
  },
];
