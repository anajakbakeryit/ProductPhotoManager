import { create } from 'zustand';
import { api, setToken } from '@/lib/api';

interface User {
  id: number;
  username: string;
  display_name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  login: async (username, password) => {
    const res = await api.post<{ access_token: string; user: User }>(
      '/api/auth/login',
      { username, password }
    );
    setToken(res.access_token);
    set({ user: res.user });
  },

  logout: () => {
    setToken(null);
    set({ user: null });
  },

  checkAuth: async () => {
    try {
      const user = await api.get<User>('/api/auth/me');
      set({ user, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },
}));
