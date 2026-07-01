import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../api';
import { StatusBadge, PageHeader, TableSkeleton, EmptyState } from '../components/ui.jsx';
import CreateTaskModal from '../components/CreateTaskModal.jsx';
import { fmtDate, taskTypeIcon, scheduleLabel } from '../utils/helpers';
import toast from 'react-hot-toast';
import {
  Plus, Play, Pause, Trash2, Zap, Search, Filter,
  ListTodo, RefreshCw, ChevronLeft, ChevronRight
} from 'lucide-react';

export default function Tasks() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [search,   setSearch]       = useState('');
  const [status,   setStatus]       = useState('');
  const [type,     setType]         = useState('');
  const [page,     setPage]         = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tasks', page, search, status, type],
    queryFn: () => tasksApi.list({ page, page_size: 15, search: search || undefined, status: status || undefined, task_type: type || undefined }).then(r => r.data),
    keepPreviousData: true,
  });

  const invalidate = () => { qc.invalidateQueries({ queryKey: ['tasks'] }); qc.invalidateQueries({ queryKey: ['dashboard'] }); };

  const pauseMut   = useMutation({ mutationFn: (id) => tasksApi.pause(id),   onSuccess: () => { invalidate(); toast.success('Task paused');   } });
  const resumeMut  = useMutation({ mutationFn: (id) => tasksApi.resume(id),  onSuccess: () => { invalidate(); toast.success('Task resumed');  } });
  const deleteMut  = useMutation({ mutationFn: (id) => tasksApi.delete(id),  onSuccess: () => { invalidate(); toast.success('Task deleted');  } });
  const triggerMut = useMutation({ mutationFn: (id) => tasksApi.trigger(id), onSuccess: () => { toast.success('Task triggered!'); } });

  const tasks       = data?.items ?? [];
  const totalPages  = data?.total_pages ?? 1;

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Tasks"
        subtitle={`${data?.total ?? 0} scheduled jobs`}
        actions={<>
          <button onClick={() => refetch()} className="btn-ghost"><RefreshCw className="w-4 h-4" /> Refresh</button>
          <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4" /> New Task</button>
        </>}
      />

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input className="input pl-9" placeholder="Search tasks…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
        </div>
        <select className="input w-36" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All status</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
        </select>
        <select className="input w-40" value={type} onChange={e => { setType(e.target.value); setPage(1); }}>
          <option value="">All types</option>
          {['email','http','file_cleanup','db_backup','custom'].map(t =>
            <option key={t} value={t}>{t.replace('_',' ')}</option>
          )}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {isLoading ? <TableSkeleton rows={8} cols={6} /> : tasks.length === 0 ? (
          <EmptyState icon={ListTodo} title="No tasks yet" description="Create your first scheduled task to get started." action={<button onClick={() => setShowCreate(true)} className="btn-primary"><Plus className="w-4 h-4" /> New Task</button>} />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-800">
              <tr className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                {['Task', 'Type', 'Schedule', 'Status', 'Runs', 'Actions'].map(h =>
                  <th key={h} className={`px-4 py-3 text-left`}>{h}</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {tasks.map(task => (
                <tr key={task.id} className="hover:bg-gray-800/30 transition-colors group">
                  <td className="px-4 py-3">
                    <p className="font-medium text-white">{task.name}</p>
                    <p className="text-xs text-gray-500 mt-0.5 truncate max-w-48">{task.description || '—'}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    <span className="flex items-center gap-1.5">
                      <span className="text-lg leading-none">{taskTypeIcon(task.task_type)}</span>
                      {task.task_type.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{scheduleLabel(task.schedule_type, task.cron_expression)}</td>
                  <td className="px-4 py-3"><StatusBadge status={task.status} /></td>
                  <td className="px-4 py-3">
                    <span className="text-gray-300">{task.total_executions}</span>
                    <span className="text-gray-600 mx-1">/</span>
                    <span className="text-emerald-400">{task.successful_executions}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button title="Trigger now" onClick={() => triggerMut.mutate(task.id)} className="btn-ghost p-1.5"><Zap className="w-3.5 h-3.5 text-amber-400" /></button>
                      {task.status === 'active'
                        ? <button title="Pause" onClick={() => pauseMut.mutate(task.id)}  className="btn-ghost p-1.5"><Pause className="w-3.5 h-3.5" /></button>
                        : <button title="Resume" onClick={() => resumeMut.mutate(task.id)} className="btn-ghost p-1.5"><Play className="w-3.5 h-3.5 text-emerald-400" /></button>
                      }
                      <button title="Delete" onClick={() => { if (confirm('Delete this task?')) deleteMut.mutate(task.id); }} className="btn-ghost p-1.5"><Trash2 className="w-3.5 h-3.5 text-red-400" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <button className="btn-ghost text-xs" disabled={page <= 1} onClick={() => setPage(p => p-1)}><ChevronLeft className="w-4 h-4" /> Prev</button>
            <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
            <button className="btn-ghost text-xs" disabled={page >= totalPages} onClick={() => setPage(p => p+1)}>Next <ChevronRight className="w-4 h-4" /></button>
          </div>
        )}
      </div>

      {showCreate && <CreateTaskModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
