import {
  LayoutDashboard,
  Camera,
  Image,
  RotateCw,
  Clock,
  BarChart3,
  Settings,
} from 'lucide-react';
import { type MenuConfig } from './types';

export const MENU_MEGA: MenuConfig = [
  { title: 'แดชบอร์ด', icon: LayoutDashboard, path: '/' },
  { title: 'ถ่ายภาพ', icon: Camera, path: '/shooting' },
  { title: 'แกลเลอรี่', icon: Image, path: '/gallery' },
  { title: '360 องศา', icon: RotateCw, path: '/360' },
  { title: 'เซสชัน', icon: Clock, path: '/sessions' },
  { title: 'รายงาน', icon: BarChart3, path: '/reports' },
  { title: 'ตั้งค่า', icon: Settings, path: '/settings' },
];

export const MENU_MEGA_MOBILE: MenuConfig = [
  { title: 'แดชบอร์ด', icon: LayoutDashboard, path: '/' },
  { title: 'ถ่ายภาพ', icon: Camera, path: '/shooting' },
  { title: 'แกลเลอรี่', icon: Image, path: '/gallery' },
  { title: '360 องศา', icon: RotateCw, path: '/360' },
  { title: 'เซสชัน', icon: Clock, path: '/sessions' },
  { title: 'รายงาน', icon: BarChart3, path: '/reports' },
  { title: 'ตั้งค่า', icon: Settings, path: '/settings' },
];
