import { formatDistanceToNow, format } from 'date-fns';

export const fmtDate = (d) => {
  if (!d) return '—';
  return format(new Date(d), 'MMM d, yyyy HH:mm');
};

export const fmtRelative = (d) => {
  if (!d) return '—';
  return formatDistanceToNow(new Date(d), { addSuffix: true });
};

export const fmtDuration = (ms) => {
  if (!ms) return '—';
  if (ms < 1000)      return `${Math.round(ms)}ms`;
  if (ms < 60_000)    return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`;
};

export const statusBadgeClass = (status) => ({
  completed: 'badge-green',
  running:   'badge-blue',
  queued:    'badge-yellow',
  failed:    'badge-red',
  retrying:  'badge-yellow',
  cancelled: 'badge-gray',
  active:    'badge-green',
  paused:    'badge-yellow',
  deleted:   'badge-gray',
}[status] ?? 'badge-gray');

export const taskTypeIcon = (type) => ({
  email:        '📧',
  http:         '🌐',
  file_cleanup: '🗑️',
  db_backup:    '💾',
  custom:       '⚙️',
}[type] ?? '📋');

export const scheduleLabel = (type, cron) => ({
  one_time: 'One Time',
  daily:    'Daily',
  weekly:   'Weekly',
  monthly:  'Monthly',
  cron:     `Cron: ${cron || ''}`,
}[type] ?? type);
