import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { statusBadgeClass } from '../utils/helpers';
import { Loader2 } from 'lucide-react';

// ── ProtectedRoute ─────────────────────────────────────────────────────────
export function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && user.role !== 'admin') return <Navigate to="/" replace />;
  return children;
}

// ── PageLoader ─────────────────────────────────────────────────────────────
export function PageLoader() {
  return (
    <div className="h-screen flex items-center justify-center">
      <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
    </div>
  );
}

// ── StatusBadge ────────────────────────────────────────────────────────────
export function StatusBadge({ status }) {
  const cls = statusBadgeClass(status);
  const dot = { completed:'bg-emerald-400', running:'bg-blue-400', queued:'bg-amber-400',
                failed:'bg-red-400', retrying:'bg-amber-400', cancelled:'bg-gray-500',
                active:'bg-emerald-400', paused:'bg-amber-400', deleted:'bg-gray-500' }[status];
  return (
    <span className={cls}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot ?? 'bg-gray-500'}`} />
      {status}
    </span>
  );
}

// ── LoadingSkeleton ────────────────────────────────────────────────────────
export function TableSkeleton({ rows = 5, cols = 5 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 items-center px-4 py-3">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className={`skeleton h-4 rounded ${j === 0 ? 'w-8' : j === 1 ? 'flex-1' : 'w-24'}`} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton() {
  return <div className="card p-5 space-y-3"><div className="skeleton h-4 w-24 rounded" /><div className="skeleton h-8 w-16 rounded" /></div>;
}

// ── EmptyState ─────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center px-4">
      <div className="w-16 h-16 rounded-2xl bg-gray-800 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-gray-600" />
      </div>
      <h3 className="text-lg font-semibold text-gray-300 mb-1">{title}</h3>
      <p className="text-sm text-gray-500 max-w-xs mb-6">{description}</p>
      {action}
    </div>
  );
}

// ── PageHeader ─────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between px-6 pt-6 pb-4">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

// ── StatCard ───────────────────────────────────────────────────────────────
export function StatCard({ icon: Icon, label, value, sub, color = 'blue' }) {
  const colors = {
    blue:   'bg-blue-500/15 text-blue-400',
    green:  'bg-emerald-500/15 text-emerald-400',
    red:    'bg-red-500/15 text-red-400',
    amber:  'bg-amber-500/15 text-amber-400',
    purple: 'bg-purple-500/15 text-purple-400',
  };
  return (
    <div className="stat-card">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${colors[color]}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-gray-400 mt-1">{label}</p>
        {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}
