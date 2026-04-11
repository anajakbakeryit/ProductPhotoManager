export interface Photo {
  id: number;
  barcode: string;
  angle: string;
  filename: string;
  status: string;
  has_cutout: boolean;
  has_watermark: boolean;
  thumbnail_url: string;
  preview_url: string;
  created_at: string;
}

export interface PhotoDetail {
  id: number;
  barcode: string;
  angle: string;
  filename: string;
  width: number;
  height: number;
  status: string;
  urls: Record<string, Record<string, string>>;
}

export interface AngleFilter {
  value: string;
  label: string;
  active: string;
}

export const ANGLE_FILTERS: AngleFilter[] = [
  { value: '', label: 'ทุกมุม', active: 'bg-primary text-primary-foreground' },
  { value: 'front', label: 'ด้านหน้า', active: 'bg-blue-500 text-white' },
  { value: 'back', label: 'ด้านหลัง', active: 'bg-violet-500 text-white' },
  { value: 'left', label: 'ด้านซ้าย', active: 'bg-emerald-500 text-white' },
  { value: 'right', label: 'ด้านขวา', active: 'bg-orange-500 text-white' },
  { value: 'top', label: 'ด้านบน', active: 'bg-pink-500 text-white' },
  { value: 'bottom', label: 'ด้านล่าง', active: 'bg-sky-500 text-white' },
  { value: 'detail', label: 'รายละเอียด', active: 'bg-lime-500 text-white' },
  { value: 'package', label: 'แพ็คเกจ', active: 'bg-fuchsia-500 text-white' },
  { value: '360', label: '360°', active: 'bg-amber-500 text-white' },
];
