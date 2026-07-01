import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { executionsApi } from '../api';
import { StatusBadge, PageHeader, TableSkeleton, EmptyState } from '../components/ui.jsx';
import { fmtDate, fmtDuration } from '../utils/helpers';
import { History, RotateCcw, XCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TaskHistory() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const { data, isLoading } = useQuery({
    queryKey: ['executions', page, status],
    queryFn: () => executionsApi.list({ page, page_size: 20, status: status || undefined }).then(r => r.data),
    keepPreviousData: true,
    refetchInterval: 10_000,
  });
  const retryMut  = useMutation({ mutationFn: (id) => executionsApi.retry(id),  onSuccess: () => { qc.invalidateQueries({ queryKey: ['executions'] }); toast.success('Retried'); } });
  const cancelMut = useMutation({ mutationFn: (id) => executionsApi.cancel(id), onSuccess: () => { qc.invalidateQueries({ queryKey: ['executions'] }); toast.success('Cancelled'); } });
  const execs = data?.items ?? [];
  const totalPages = data?.total_pages ?? 1;
  return (
    <div className="p-6 space-y-5">
      <PageHeader title="Execution History" subtitle="Every job run, with logs and timing" />
      <select className="input w-40" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
        <option value="">All statuses</option>
        {['queued','running','completed','failed','retrying','cancelled'].map(s => <option key={s} value={s}>{s}</option>)}
      </select>
      <div className="card overflow-hidden">
        {isLoading ? <TableSkeleton rows={10} cols={7} /> : execs.length === 0 ? (
          <EmptyState icon={History} title="No executions yet" description="Executions appear here when tasks run." />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-800"><tr className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              {['ID','Task','Status','Started','Duration','Worker','Actions'].map(h => <th key={h} className="px-4 py-3 text-left">{h}</th>)}
            </tr></thead>
            <tbody className="divide-y divide-gray-800/50">
              {execs.map(ex => (
                <tr key={ex.id} className="hover:bg-gray-800/30 transition-colors group">
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">#{ex.id}</td>
                  <td className="px-4 py-3 text-gray-300">Task #{ex.task_id}</td>
                  <td className="px-4 py-3"><StatusBadge status={ex.status} /></td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{fmtDate(ex.started_at)}</td>
                  <td className="px-4 py-3 text-gray-300">{fmtDuration(ex.duration_ms)}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-32">{ex.worker_name || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {['failed','cancelled'].includes(ex.status) && <button onClick={() => retryMut.mutate(ex.id)} className="btn-ghost p-1.5" title="Retry"><RotateCcw className="w-3.5 h-3.5 text-amber-400" /></button>}
                      {['queued','running'].includes(ex.status) && <button onClick={() => cancelMut.mutate(ex.id)} className="btn-ghost p-1.5" title="Cancel"><XCircle className="w-3.5 h-3.5 text-red-400" /></button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <button className="btn-ghost text-xs" disabled={page<=1} onClick={()=>setPage(p=>p-1)}><ChevronLeft className="w-4 h-4" /> Prev</button>
            <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
            <button className="btn-ghost text-xs" disabled={page>=totalPages} onClick={()=>setPage(p=>p+1)}>Next <ChevronRight className="w-4 h-4" /></button>
          </div>
        )}
      </div>
    </div>
  );
}
