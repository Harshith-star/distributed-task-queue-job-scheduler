import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../api';
import toast from 'react-hot-toast';
import { X, Loader2 } from 'lucide-react';

const TASK_TYPES    = ['email', 'http', 'file_cleanup', 'db_backup', 'custom'];
const SCHEDULE_TYPES = ['daily', 'weekly', 'monthly', 'cron', 'one_time'];

const DEFAULT_CONFIGS = {
  email:        { to_email: '', subject: 'TaskQ Notification', body: 'Hello from TaskQ!' },
  http:         { url: 'https://httpbin.org/get', method: 'GET', headers: {}, payload: {} },
  file_cleanup: { directory: '/tmp', pattern: '*.tmp', older_than_days: 30 },
  db_backup:    { output_path: '/app/backups', compress: true },
  custom:       { code: 'print("Hello from TaskQ!")\nresult = 42\nprint(f"Result: {result}")' },
};

export default function CreateTaskModal({ onClose }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name:            '',
    description:     '',
    task_type:       'http',
    schedule_type:   'daily',
    cron_expression: '0 9 * * *',
    scheduled_at:    '',
    max_retries:     3,
    timeout_seconds: 300,
    tags:            '',
    task_config:     DEFAULT_CONFIGS.http,
  });
  const [configJson, setConfigJson] = useState(JSON.stringify(DEFAULT_CONFIGS.http, null, 2));
  const [jsonError, setJsonError]   = useState('');

  const mutation = useMutation({
    mutationFn: (data) => tasksApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      toast.success('Task created successfully!');
      onClose();
    },
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleTypeChange = (type) => {
    const cfg = DEFAULT_CONFIGS[type] || {};
    set('task_type', type);
    setConfigJson(JSON.stringify(cfg, null, 2));
    setJsonError('');
  };

  const handleConfigChange = (v) => {
    setConfigJson(v);
    try { setForm(f => ({ ...f, task_config: JSON.parse(v) })); setJsonError(''); }
    catch { setJsonError('Invalid JSON'); }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (jsonError) return;
    const payload = {
      ...form,
      tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      scheduled_at: form.schedule_type === 'one_time' ? form.scheduled_at : null,
      cron_expression: form.schedule_type === 'cron' ? form.cron_expression : null,
    };
    mutation.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative card w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white">Create New Task</h2>
          <button onClick={onClose} className="btn-ghost p-1.5"><X className="w-4 h-4" /></button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Name */}
          <div>
            <label className="label">Task Name *</label>
            <input className="input" value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Daily Email Report" required />
          </div>

          {/* Description */}
          <div>
            <label className="label">Description</label>
            <textarea className="input resize-none" rows={2} value={form.description} onChange={e => set('description', e.target.value)} placeholder="What does this task do?" />
          </div>

          {/* Type + Schedule */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Task Type *</label>
              <select className="input" value={form.task_type} onChange={e => handleTypeChange(e.target.value)}>
                {TASK_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Schedule *</label>
              <select className="input" value={form.schedule_type} onChange={e => set('schedule_type', e.target.value)}>
                {SCHEDULE_TYPES.map(t => <option key={t} value={t}>{t.replace('_', ' ').toUpperCase()}</option>)}
              </select>
            </div>
          </div>

          {/* Cron / one-time */}
          {form.schedule_type === 'cron' && (
            <div>
              <label className="label">Cron Expression</label>
              <input className="input font-mono" value={form.cron_expression} onChange={e => set('cron_expression', e.target.value)} placeholder="0 9 * * *" />
              <p className="text-xs text-gray-500 mt-1">Format: minute hour day month weekday — e.g. <code>0 9 * * 1-5</code> = weekdays at 9am</p>
            </div>
          )}
          {form.schedule_type === 'one_time' && (
            <div>
              <label className="label">Run At</label>
              <input className="input" type="datetime-local" value={form.scheduled_at} onChange={e => set('scheduled_at', e.target.value)} required />
            </div>
          )}

          {/* Config JSON */}
          <div>
            <label className="label">Task Configuration (JSON)</label>
            <textarea
              className={`input font-mono text-xs resize-none ${jsonError ? 'border-red-500' : ''}`}
              rows={8}
              value={configJson}
              onChange={e => handleConfigChange(e.target.value)}
            />
            {jsonError && <p className="text-xs text-red-400 mt-1">{jsonError}</p>}
          </div>

          {/* Retries + Timeout */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Max Retries</label>
              <input className="input" type="number" min={0} max={10} value={form.max_retries} onChange={e => set('max_retries', +e.target.value)} />
            </div>
            <div>
              <label className="label">Timeout (sec)</label>
              <input className="input" type="number" min={10} max={3600} value={form.timeout_seconds} onChange={e => set('timeout_seconds', +e.target.value)} />
            </div>
            <div>
              <label className="label">Tags (comma-separated)</label>
              <input className="input" value={form.tags} onChange={e => set('tags', e.target.value)} placeholder="prod, api, daily" />
            </div>
          </div>

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
            <button type="submit" className="btn-primary" disabled={mutation.isPending || !!jsonError}>
              {mutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating…</> : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
