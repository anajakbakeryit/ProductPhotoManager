# Frontend Rules (React + Vite + Tailwind + Metronic)

## Data Fetching
- ใช้ `useQuery` / `useMutation` จาก `@tanstack/react-query` เท่านั้น
- **ห้ามใช้** raw `useEffect` + `fetch` สำหรับ data fetching
- Cache invalidation: `queryClient.invalidateQueries()` หลัง mutation เสมอ

## State Management
- **Server state**: TanStack React Query
- **Client state**: Zustand stores (`store/authStore.ts`, `store/shootingStore.ts`)
- **ห้ามใช้** Redux, MobX, Context API สำหรับ server state

## API Calls
- ใช้ `api.get()` / `api.post()` จาก `@/lib/api` เท่านั้น
- **ห้ามใช้** raw `fetch()` หรือ raw `axios`
- ข้อยกเว้น: `/api/health` ใช้ raw fetch ได้ (dev mode check)

## UI Components
- ใช้ **Metronic v9.4.8** components + **Radix UI** primitives + **Tailwind CSS** + **lucide-react** icons
- **ห้ามใช้** Material UI, Ant Design, Bootstrap
- Components เป็น functional components + hooks เท่านั้น

## Notifications
- ใช้ `toast.success()` / `toast.error()` จาก `sonner`

## Routing
- ใช้ `react-router-dom` v7
- Protected pages อยู่ภายใต้ `<ProtectedRoute>`
- Metronic Layout1 เป็น layout หลัก

## Language
- **UI text ทั้งหมดเป็นภาษาไทย**
- Variable/function names เป็นภาษาอังกฤษ

## Reference Files
- Page reference: `frontend/src/pages/shooting/page.tsx`
- API client: `frontend/src/lib/api.ts`
- Store reference: `frontend/src/store/shootingStore.ts`
- Sidebar config: `frontend/src/config/layout-1.config.tsx`
