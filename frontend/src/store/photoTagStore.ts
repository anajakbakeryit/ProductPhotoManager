import { create } from 'zustand';
import { api } from '@/lib/api';

interface PhotoTagState {
  tagsCache: Record<number, string[]>;
  loadTags: (photoId: number) => Promise<string[]>;
  addTag: (photoId: number, tag: string) => Promise<void>;
  removeTag: (photoId: number, tag: string) => Promise<void>;
  getTagsForPhoto: (photoId: number) => string[];
}

export const PRESET_TAGS = ['มีรอย', 'สวย', 'สีดำ', 'สีขาว', 'สีทอง', 'แตก', 'มือสอง', 'ใหม่'];

export const usePhotoTagStore = create<PhotoTagState>((set, get) => ({
  tagsCache: {},

  getTagsForPhoto: (photoId) => get().tagsCache[photoId] || [],

  loadTags: async (photoId) => {
    try {
      const res = await api.get<{ tags: string[] }>(`/api/photos/${photoId}/tags`);
      const tags = res.tags || [];
      set((state) => ({ tagsCache: { ...state.tagsCache, [photoId]: tags } }));
      return tags;
    } catch {
      return [];
    }
  },

  addTag: async (photoId, tag) => {
    // Optimistic update
    set((state) => {
      const current = state.tagsCache[photoId] || [];
      if (current.includes(tag)) return state;
      return { tagsCache: { ...state.tagsCache, [photoId]: [...current, tag] } };
    });
    try {
      const res = await api.post<{ tags: string[] }>(`/api/photos/${photoId}/tags`, { tag });
      set((state) => ({ tagsCache: { ...state.tagsCache, [photoId]: res.tags } }));
    } catch { /* optimistic stays */ }
  },

  removeTag: async (photoId, tag) => {
    // Optimistic update
    set((state) => {
      const current = state.tagsCache[photoId] || [];
      return { tagsCache: { ...state.tagsCache, [photoId]: current.filter((t) => t !== tag) } };
    });
    try {
      const res = await api.delete<{ tags: string[] }>(`/api/photos/${photoId}/tags/${encodeURIComponent(tag)}`);
      set((state) => ({ tagsCache: { ...state.tagsCache, [photoId]: res.tags } }));
    } catch { /* optimistic stays */ }
  },
}));
