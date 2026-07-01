import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api';
import { PageHeader } from '../components/ui.jsx';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const TOOLTIP_STYLE = {
  contentStyle: { background: '#111827', border: '1px solid #374151', borderRadius: '8px', color: '#f3f4f6' },
};

export default function Analytics() {
  const { data: analytics } = useQuery({
    queryKey: ['analytics'],
    queryFn:  () => dashboardApi.analytics(14).then(r => r.data),
    refetchInterval: 60_000,
  });

  const daily    = analytics?.daily_executions ?? [];
  const typeData = Object.entries(analytics?.task_type_breakdown  ?? {}).map(([k, v]) => ({ name: k, value: v }));
  const statData = Object.entries(analytics?.status_breakdown     ?? {}).map(([k, v]) => ({ name: k, value: v }));

  return (
    <div className="p-6 space-y-6">
      <PageHeader title="Analytics" subtitle="Execution trends over the last 14 days" />

      {/* Daily trend */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Daily Executions</h3>
        {daily.length === 0 ? (
          <div className="h-56 flex items-center justify-center text-gray-600 text-sm">No execution data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={daily}>
              <defs>
                <linearGradient id="gC" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gF" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} /><stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date"  tick={{ fill: '#6b7280', fontSize: 11 }} />
              <YAxis               tick={{ fill: '#6b7280', fontSize: 11 }} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend />
              <Area type="monotone" dataKey="completed" stroke="#10b981" fill="url(#gC)" strokeWidth={2} name="Completed" />
              <Area type="monotone" dataKey="failed"    stroke="#ef4444" fill="url(#gF)" strokeWidth={2} name="Failed"    />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Task type distribution */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Task Types</h3>
          {typeData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-gray-600 text-sm">No tasks created yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={typeData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                  paddingAngle={3} dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}>
                  {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip {...TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Status breakdown */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Status Breakdown</h3>
          {statData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-gray-600 text-sm">No executions yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={statData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis type="number"   tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} width={72} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {statData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top failing tasks */}
      {(analytics?.top_failing_tasks ?? []).length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Top Failing Tasks</h3>
          <div className="space-y-2">
            {analytics.top_failing_tasks.map(t => (
              <div key={t.task_id} className="flex items-center justify-between py-2.5 border-b border-gray-800 last:border-0">
                <div>
                  <p className="text-sm text-gray-200">{t.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Task #{t.task_id}</p>
                </div>
                <span className="badge-red badge">{t.fail_count} failures</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
