import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PhotoTagState {
  tags: Record<number, string[]>; // photoId → tags[]
  addTag: (photoId: number, tag: string) => void;
  removeTag: (photoId: number, tag: string) => void;
  getTagsForPhoto: (photoId: number) => string[];
}

export const PRESET_TAGS = ['มีรอย', 'สวย', 'สีดำ', 'สีขาว', 'สีทอง', 'แตก', 'มือสอง', 'ใหม่'];

export const usePhotoTagStore = create<PhotoTagState>()(
  persist(
    (set, get) => ({
      tags: {},
      addTag: (photoId, tag) =>
        set((state) => {
          const current = state.tags[photoId] || [];
          if (current.includes(tag)) return state;
          return { tags: { ...state.tags, [photoId]: [...current, tag] } };
        }),
      removeTag: (photoId, tag) =>
        set((state) => {
          const current = state.tags[photoId] || [];
          return { tags: { ...state.tags, [photoId]: current.filter((t) => t !== tag) } };
        }),
      getTagsForPhoto: (photoId) => get().tags[photoId] || [],
    }),
    { name: 'photo-tags' }
  )
);
