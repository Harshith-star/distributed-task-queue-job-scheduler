import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useQuery } from '@tanstack/react-query';
import { notifApi } from '../api';
import { useTaskWebSocket } from '../hooks/useWebSocket';
import {
  LayoutDashboard, ListTodo, History, BarChart3,
  Bell, Settings, LogOut, Zap, Shield, Users
} from 'lucide-react';

const NAV = [
  { to: '/',             icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/tasks',        icon: ListTodo,        label: 'Tasks'      },
  { to: '/history',      icon: History,         label: 'History'    },
  { to: '/analytics',    icon: BarChart3,       label: 'Analytics'  },
  { to: '/notifications',icon: Bell,            label: 'Notifications'},
  { to: '/settings',     icon: Settings,        label: 'Settings'   },
];

const ADMIN_NAV = [
  { to: '/admin/users',   icon: Users,  label: 'Users'   },
  { to: '/admin/workers', icon: Shield, label: 'Workers' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();
  useTaskWebSocket(user?.id);

  const { data: notifData } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn:  () => notifApi.list({ unread_only: true, page_size: 1 }).then(r => r.data),
    refetchInterval: 30_000,
  });
  const unread = notifData?.unread_count ?? 0;

  const handleLogout = async () => { await logout(); navigate('/login'); };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 flex items-center gap-3 border-b border-gray-800">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-bold text-white text-sm">TaskQ</p>
            <p className="text-xs text-gray-500">Job Scheduler</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`}>
              <Icon className="w-4 h-4" />
              {label}
              {label === 'Notifications' && unread > 0 && (
                <span className="ml-auto bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </NavLink>
          ))}

          {user?.role === 'admin' && (
            <>
              <p className="px-3 pt-4 pb-1 text-xs font-semibold text-gray-600 uppercase tracking-wider">Admin</p>
              {ADMIN_NAV.map(({ to, icon: Icon, label }) => (
                <NavLink key={to} to={to} className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
                  <Icon className="w-4 h-4" /> {label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        {/* User footer */}
        <div className="px-3 py-3 border-t border-gray-800">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-sm font-bold text-white">
              {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.role}</p>
            </div>
            <button onClick={handleLogout} className="text-gray-500 hover:text-red-400 transition-colors" title="Sign out">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-gray-950">
        <Outlet />
      </main>
    </div>
  );
}
