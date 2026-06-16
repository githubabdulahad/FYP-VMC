import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Activity,
  ClipboardList,
  FileCheck2,
  LayoutDashboard,
  LogOut,
  PlusCircle,
  Stethoscope,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/Button';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/submit', label: 'New submission', icon: PlusCircle },
  { to: '/review', label: 'Review queue', icon: ClipboardList },
  { to: '/results', label: 'Coding results', icon: Activity },
  { to: '/reports', label: 'Reports', icon: FileCheck2 },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="flex min-h-screen">
      <aside className="glass-panel fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-slate-700/30">
        <div className="flex items-center gap-3 border-b border-slate-700/30 px-5 py-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-teal-500 to-purple-600">
            <Stethoscope className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-sm font-bold text-white">Virtual Medical</p>
            <p className="text-xs text-slate-400">Coder</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-teal-500/15 text-teal-300'
                    : 'text-slate-400 hover:bg-surface-800 hover:text-slate-100',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-700/30 p-4">
          <p className="truncate text-sm font-medium text-white">{user?.username}</p>
          <p className="truncate text-xs text-slate-500">{user?.role}</p>
          <Button variant="ghost" className="mt-3 w-full justify-start" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      <main className="ml-64 flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
