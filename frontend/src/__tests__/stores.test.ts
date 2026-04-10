import { describe, it, expect } from 'vitest';
import { useShootingStore } from '../store/shootingStore';

describe('shootingStore', () => {
  it('should set barcode and reset counters', () => {
    const store = useShootingStore.getState();
    store.setBarcode('SKU001');
    const state = useShootingStore.getState();
    expect(state.currentBarcode).toBe('SKU001');
    expect(state.currentAngle).toBe('');
    expect(state.angleCounters).toEqual({});
  });

  it('should set angle', () => {
    const store = useShootingStore.getState();
    store.setBarcode('SKU002');
    store.setAngle('front');
    expect(useShootingStore.getState().currentAngle).toBe('front');
  });

  it('should increment counter', () => {
    const store = useShootingStore.getState();
    store.setBarcode('SKU003');
    store.incrementCounter('front');
    store.incrementCounter('front');
    store.incrementCounter('back');
    const state = useShootingStore.getState();
    expect(state.angleCounters['front']).toBe(2);
    expect(state.angleCounters['back']).toBe(1);
  });

  it('should toggle 360 mode', () => {
    const store = useShootingStore.getState();
    expect(store.is360Mode).toBe(false);
    store.toggle360Mode();
    expect(useShootingStore.getState().is360Mode).toBe(true);
    expect(useShootingStore.getState().currentAngle).toBe('360');
    store.toggle360Mode();
    expect(useShootingStore.getState().is360Mode).toBe(false);
  });

  it('should have 8 default angles', () => {
    expect(useShootingStore.getState().angles).toHaveLength(8);
  });

  it('should set last preview', () => {
    const store = useShootingStore.getState();
    store.setLastPreview('/api/storage/test.jpg');
    expect(useShootingStore.getState().lastPreviewUrl).toBe('/api/storage/test.jpg');
  });
});
