import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { UserPlus, Shield, User as UserIcon } from 'lucide-react';

interface UserItem {
  id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

export function UsersSection() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', display_name: '', role: 'user' });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<UserItem[]>('/api/users'),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof newUser) => api.post('/api/users', data),
    onSuccess: () => {
      toast.success('สร้างผู้ใช้แล้ว');
      setShowCreate(false);
      setNewUser({ username: '', password: '', display_name: '', role: 'user' });
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      api.put(`/api/users/${id}`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <section className="rounded-xl border border-border bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-muted-foreground">จัดการผู้ใช้</h2>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs">
          <UserPlus className="w-3.5 h-3.5" /> เพิ่มผู้ใช้
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="p-4 rounded-lg border border-border space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input placeholder="ชื่อผู้ใช้" value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm" />
            <input placeholder="รหัสผ่าน" type="password" value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm" />
            <input placeholder="ชื่อที่แสดง" value={newUser.display_name}
              onChange={(e) => setNewUser({ ...newUser, display_name: e.target.value })}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm" />
            <select value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              className="px-3 py-2 rounded-lg border border-border bg-background text-foreground text-sm">
              <option value="user">ผู้ใช้</option>
              <option value="admin">ผู้ดูแลระบบ</option>
            </select>
          </div>
          <button onClick={() => createMutation.mutate(newUser)}
            disabled={createMutation.isPending}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm">
            {createMutation.isPending ? 'กำลังสร้าง...' : 'สร้างผู้ใช้'}
          </button>
        </div>
      )}

      {/* User list */}
      <div className="space-y-2">
        {(users || []).map((u) => (
          <div key={u.id} className="flex items-center gap-3 p-3 rounded-lg border border-border">
            <div className="flex items-center gap-2 flex-1">
              {u.role === 'admin' ? <Shield className="w-4 h-4 text-yellow-500" /> : <UserIcon className="w-4 h-4 text-muted-foreground" />}
              <span className="text-sm font-medium text-foreground">{u.display_name || u.username}</span>
              <span className="text-xs text-muted-foreground">@{u.username}</span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${u.role === 'admin' ? 'bg-yellow-500/10 text-yellow-500' : 'bg-muted text-muted-foreground'}`}>
                {u.role === 'admin' ? 'ผู้ดูแล' : 'ผู้ใช้'}
              </span>
            </div>
            <button
              onClick={() => toggleMutation.mutate({ id: u.id, is_active: !u.is_active })}
              className={`px-2 py-1 rounded text-xs ${u.is_active ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
              {u.is_active ? 'เปิดใช้งาน' : 'ปิดใช้งาน'}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
