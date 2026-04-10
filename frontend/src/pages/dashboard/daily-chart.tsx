import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';

interface DailyItem {
  date: string;
  count: number;
}

export function DailyChart({ data }: { data: DailyItem[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-[200px] flex flex-col items-center justify-center">
        <div className="size-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
          <TrendingUp className="size-5 text-muted-foreground/60" />
        </div>
        <p className="text-sm text-muted-foreground">ยังไม่มีข้อมูล</p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    date: new Date(d.date).toLocaleDateString('th-TH', { day: '2-digit', month: 'short' }),
    count: d.count,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--muted-foreground)' }} axisLine={false} tickLine={false} allowDecimals={false} width={30} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--card)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            fontSize: '13px',
          }}
          labelStyle={{ color: 'var(--foreground)', fontWeight: 600 }}
          itemStyle={{ color: 'var(--primary)' }}
          formatter={(value: number) => [`${value} รูป`, 'อัปโหลด']}
        />
        <Bar dataKey="count" fill="var(--primary)" radius={[6, 6, 0, 0]} barSize={32} />
      </BarChart>
    </ResponsiveContainer>
  );
}
