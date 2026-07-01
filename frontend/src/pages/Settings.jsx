import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api';
import { PageHeader } from '../components/ui.jsx';
import toast from 'react-hot-toast';
import { Loader2, Shield, User } from 'lucide-react';

export default function Settings() {
  const { user, setUser } = useAuth();
  const [name,     setName]     = useState(user?.full_name ?? '');
  const [cpForm,   setCpForm]   = useState({ current_password: '', new_password: '' });
  const [saving,   setSaving]   = useState(false);
  const [changing, setChanging] = useState(false);

  const saveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await authApi.updateProfile({ full_name: name });
      setUser(data);
      toast.success('Profile updated');
    } catch {
      // error already toasted by interceptor
    } finally { setSaving(false); }
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setChanging(true);
    try {
      await authApi.changePassword(cpForm);
      toast.success('Password changed successfully');
      setCpForm({ current_password: '', new_password: '' });
    } catch {} finally { setChanging(false); }
  };

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <PageHeader title="Settings" subtitle="Manage your account and security" />

      {/* Profile */}
      <div className="card p-6 space-y-5">
        <div className="flex items-center gap-3 pb-4 border-b border-gray-800">
          <div className="w-9 h-9 rounded-lg bg-blue-600/20 flex items-center justify-center">
            <User className="w-4 h-4 text-blue-400" />
          </div>
          <h3 className="text-sm font-semibold text-white">Profile</h3>
        </div>

        {/* Avatar */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center text-xl font-bold text-white shrink-0">
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{user?.full_name}</p>
            <p className="text-xs text-gray-500">{user?.email}</p>
            <span className={`badge mt-1 ${user?.role === 'admin' ? 'badge-purple' : 'badge-blue'}`}>
              {user?.role}
            </span>
          </div>
        </div>

        <form onSubmit={saveProfile} className="space-y-4">
          <div>
            <label className="label">Email address</label>
            <input className="input opacity-50 cursor-not-allowed" value={user?.email ?? ''} disabled />
            <p className="text-xs text-gray-600 mt-1">Email cannot be changed</p>
          </div>
          <div>
            <label className="label">Full name</label>
            <input
              className="input"
              value={name}
              onChange={e => setName(e.target.value)}
              minLength={2}
              required
            />
          </div>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</> : 'Save profile'}
          </button>
        </form>
      </div>

      {/* Change password */}
      <div className="card p-6 space-y-5">
        <div className="flex items-center gap-3 pb-4 border-b border-gray-800">
          <div className="w-9 h-9 rounded-lg bg-amber-500/20 flex items-center justify-center">
            <Shield className="w-4 h-4 text-amber-400" />
          </div>
          <h3 className="text-sm font-semibold text-white">Change Password</h3>
        </div>

        <form onSubmit={changePassword} className="space-y-4">
          <div>
            <label className="label">Current password</label>
            <input
              className="input"
              type="password"
              value={cpForm.current_password}
              onChange={e => setCpForm(f => ({ ...f, current_password: e.target.value }))}
              required
              autoComplete="current-password"
            />
          </div>
          <div>
            <label className="label">New password</label>
            <input
              className="input"
              type="password"
              value={cpForm.new_password}
              onChange={e => setCpForm(f => ({ ...f, new_password: e.target.value }))}
              required
              minLength={8}
              autoComplete="new-password"
            />
            <p className="text-xs text-gray-600 mt-1">Min 8 characters, at least 1 uppercase and 1 digit</p>
          </div>
          <button type="submit" className="btn-primary" disabled={changing}>
            {changing ? <><Loader2 className="w-4 h-4 animate-spin" /> Changing…</> : 'Change password'}
          </button>
        </form>
      </div>
    </div>
  );
}
