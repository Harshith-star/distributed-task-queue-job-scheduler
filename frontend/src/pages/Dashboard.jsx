import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api';
import { useAuth } from '../context/AuthContext';
import { StatCard, PageHeader, CardSkeleton } from '../components/ui.jsx';
import { fmtDuration, fmtRelative } from '../utils/helpers';
import {
  ListTodo, Play, CheckCircle2, XCircle, Clock, TrendingUp,
  Zap, Calendar, AlertTriangle
} from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn:  () => dashboardApi.stats().then(r => r.data),
    refetchInterval: 15_000,
  });

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title={`Good day, ${user?.full_name?.split(' ')[0] ?? 'there'} 👋`}
        subtitle="Here's what's happening with your scheduled jobs"
      />

      {/* Stats grid */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={ListTodo}   label="Total Tasks"       value={stats?.total_tasks}           color="blue"   />
            <StatCard icon={Play}       label="Active Tasks"      value={stats?.active_tasks}          color="green"  />
            <StatCard icon={Calendar}   label="Paused Tasks"      value={stats?.paused_tasks}          color="amber"  />
            <StatCard icon={TrendingUp} label="Today's Runs"      value={stats?.executions_today}      color="purple" />
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard icon={Zap}          label="Running Now"      value={stats?.running_executions}   color="blue"   />
            <StatCard icon={CheckCircle2} label="Completed"        value={stats?.completed_executions} color="green"  />
            <StatCard icon={XCircle}      label="Failed"           value={stats?.failed_executions}    color="red"    />
            <StatCard icon={Clock}        label="Avg Duration"     value={fmtDuration(stats?.avg_duration_ms)} color="purple" />
          </div>

          {/* Success rate bar */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-sm font-semibold text-white">Overall Success Rate</p>
                <p className="text-xs text-gray-500 mt-0.5">{stats?.completed_executions} completed of {stats?.total_executions} total runs</p>
              </div>
              <span className={`text-2xl font-bold ${stats?.success_rate >= 90 ? 'text-emerald-400' : stats?.success_rate >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                {stats?.success_rate ?? 0}%
              </span>
            </div>
            <div className="h-2.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${stats?.success_rate >= 90 ? 'bg-emerald-500' : stats?.success_rate >= 70 ? 'bg-amber-500' : 'bg-red-500'}`}
                style={{ width: `${stats?.success_rate ?? 0}%` }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
