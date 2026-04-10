import { create } from 'zustand';

const DEFAULT_ANGLES = [
  { id: 'front', label: 'Front', label_th: 'ด้านหน้า', key: 'F1' },
  { id: 'back', label: 'Back', label_th: 'ด้านหลัง', key: 'F2' },
  { id: 'left', label: 'Left', label_th: 'ด้านซ้าย', key: 'F3' },
  { id: 'right', label: 'Right', label_th: 'ด้านขวา', key: 'F4' },
  { id: 'top', label: 'Top', label_th: 'ด้านบน', key: 'F5' },
  { id: 'bottom', label: 'Bottom', label_th: 'ด้านล่าง', key: 'F6' },
  { id: 'detail', label: 'Detail', label_th: 'รายละเอียด', key: 'F7' },
  { id: 'package', label: 'Package', label_th: 'แพ็คเกจ', key: 'F8' },
];

export interface Angle {
  id: string;
  label: string;
  label_th: string;
  key: string;
}

interface ShootingState {
  currentBarcode: string;
  currentAngle: string;
  angleCounters: Record<string, number>;
  angles: Angle[];
  is360Mode: boolean;
  spin360Counter: number;
  lastPreviewUrl: string;

  setBarcode: (barcode: string) => void;
  setAngle: (angleId: string) => void;
  incrementCounter: (angleId: string) => void;
  resetCounters: () => void;
  toggle360Mode: () => void;
  setLastPreview: (url: string) => void;
  reorderAngles: (fromIndex: number, toIndex: number) => void;
}

export const useShootingStore = create<ShootingState>((set) => ({
  currentBarcode: '',
  currentAngle: '',
  angleCounters: {},
  angles: DEFAULT_ANGLES,
  is360Mode: false,
  spin360Counter: 0,
  lastPreviewUrl: '',

  setBarcode: (barcode) =>
    set({ currentBarcode: barcode, currentAngle: '', angleCounters: {} }),

  setAngle: (angleId) => set({ currentAngle: angleId }),

  incrementCounter: (angleId) =>
    set((state) => ({
      angleCounters: {
        ...state.angleCounters,
        [angleId]: (state.angleCounters[angleId] || 0) + 1,
      },
    })),

  resetCounters: () => set({ angleCounters: {}, currentAngle: '' }),

  toggle360Mode: () =>
    set((state) => ({
      is360Mode: !state.is360Mode,
      spin360Counter: state.is360Mode ? state.spin360Counter : 0,
      currentAngle: state.is360Mode ? '' : '360',
    })),

  setLastPreview: (url) => set({ lastPreviewUrl: url }),

  reorderAngles: (fromIndex, toIndex) =>
    set((state) => {
      const newAngles = [...state.angles];
      const [moved] = newAngles.splice(fromIndex, 1);
      newAngles.splice(toIndex, 0, moved);
      // Reassign F-keys by position
      return {
        angles: newAngles.map((a, i) => ({ ...a, key: `F${i + 1}` })),
      };
    }),
}));
