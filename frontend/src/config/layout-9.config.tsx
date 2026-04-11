import {
  ClipboardList,
  Camera,
  Image,
  Settings,
} from 'lucide-react';
import { type MenuConfig } from './types';

export const MENU_MEGA: MenuConfig = [
  { title: 'Pipeline', icon: ClipboardList, path: '/' },
  { title: 'ถ่ายภาพ', icon: Camera, path: '/shooting' },
  { title: 'แกลเลอรี่', icon: Image, path: '/gallery' },
  { title: 'ตั้งค่า', icon: Settings, path: '/settings' },
];

export const MENU_MEGA_MOBILE: MenuConfig = [
  { title: 'Pipeline', icon: ClipboardList, path: '/' },
  { title: 'ถ่ายภาพ', icon: Camera, path: '/shooting' },
  { title: 'แกลเลอรี่', icon: Image, path: '/gallery' },
  { title: 'ตั้งค่า', icon: Settings, path: '/settings' },
];
