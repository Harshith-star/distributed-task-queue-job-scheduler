import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notifApi } from '../api';
import { PageHeader } from '../components/ui.jsx';
import { fmtRelative } from '../utils/helpers';
import { Bell } from 'lucide-react';

const TYPE_ICON  = { success: '✅', failure: '❌', retry: '🔄', info: 'ℹ️' };
const TYPE_CLASS = {
  success: 'text-emerald-400', failure: 'text-red-400',
  retry:   'text-amber-400',   info:    'text-blue-400',
};

export default function Notifications() {
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn:  () => notifApi.list({ page_size: 50 }).then(r => r.data),
    refetchInterval: 15_000,
  });

  const markMut = useMutation({
    mutationFn: (ids) => notifApi.markRead(ids),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const notifs    = data?.items ?? [];
  const unreadIds = notifs.filter(n => !n.is_read).map(n => n.id);

  return (
    <div className="p-6 space-y-5">
      <PageHeader
        title="Notifications"
        subtitle={`${data?.unread_count ?? 0} unread`}
        actions={
          unreadIds.length > 0 && (
            <button onClick={() => markMut.mutate(unreadIds)} className="btn-ghost text-sm">
              Mark all read
            </button>
          )
        }
      />

      <div className="card divide-y divide-gray-800">
        {notifs.length === 0 ? (
          <div className="py-20 text-center">
            <Bell className="w-10 h-10 mx-auto mb-3 text-gray-700" />
            <p className="text-gray-500 text-sm">No notifications yet</p>
            <p className="text-gray-600 text-xs mt-1">Alerts appear here when tasks complete or fail</p>
          </div>
        ) : (
          notifs.map(n => (
            <div
              key={n.id}
              className={`flex gap-4 px-5 py-4 transition-colors ${!n.is_read ? 'bg-gray-800/25' : ''}`}
            >
              <span className="text-xl mt-0.5 shrink-0">{TYPE_ICON[n.type] ?? 'ℹ️'}</span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold ${TYPE_CLASS[n.type] ?? 'text-gray-300'}`}>
                  {n.title}
                </p>
                <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{n.message}</p>
                <p className="text-xs text-gray-600 mt-1">{fmtRelative(n.created_at)}</p>
              </div>
              {!n.is_read && (
                <div className="flex items-start shrink-0 pt-1">
                  <button
                    onClick={() => markMut.mutate([n.id])}
                    className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
                  >
                    Mark read
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
