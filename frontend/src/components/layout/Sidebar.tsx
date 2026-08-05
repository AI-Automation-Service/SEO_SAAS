import { NavLink, useNavigate, useMatch, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, FolderOpen, LogOut, ChevronLeft, ChevronRight,
  Settings, ShieldCheck, BarChart3, Plug,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/context/AuthContext'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/projects', label: 'Projects', icon: FolderOpen, end: false },
]

const PROJECT_NAV = [
  { tab: 'overview',      label: 'Overview',      icon: BarChart3 },
  { tab: 'integrations',  label: 'Integrations',  icon: Plug },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Detect if we're inside a project page and extract the name
  const projectMatch = useMatch('/projects/:name')
  const projectName = projectMatch?.params?.name

  const currentTab = new URLSearchParams(location.search).get('tab')

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-50 bg-slate-900 flex flex-col transition-all duration-200',
        collapsed ? 'w-14' : 'w-60',
      )}
    >
      {/* Logo + collapse toggle */}
      <div className="h-16 flex items-center justify-between px-3 border-b border-slate-800 shrink-0">
        {!collapsed && (
          <span className="font-display text-white font-semibold text-lg tracking-tight pl-2">
            SEO <span className="text-emerald-400">OS</span>
          </span>
        )}
        <button
          type="button"
          onClick={onToggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={cn(
            'p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer transition-colors shrink-0',
            collapsed && 'mx-auto',
          )}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 py-2 rounded-lg text-sm font-medium transition-colors',
                collapsed ? 'justify-center px-2' : 'px-3',
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800',
              )
            }
          >
            <Icon size={16} className="shrink-0" />
            {!collapsed && label}
          </NavLink>
        ))}

        {user?.is_admin && (
          <NavLink
            to="/admin"
            title={collapsed ? 'Admin' : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 py-2 rounded-lg text-sm font-medium transition-colors',
                collapsed ? 'justify-center px-2' : 'px-3',
                isActive
                  ? 'bg-purple-500/10 text-purple-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800',
              )
            }
          >
            <ShieldCheck size={16} className="shrink-0" />
            {!collapsed && 'Admin'}
          </NavLink>
        )}

        {/* Project-level links — visible only when inside a project page */}
        {projectName && (
          <div className={cn('pt-3', !collapsed && 'border-t border-slate-800 mt-2')}>
            {!collapsed && (
              <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                Project
              </p>
            )}
            {collapsed && <div className="border-t border-slate-800 mb-2 mx-1" />}
            {PROJECT_NAV.map(({ tab, label, icon: Icon }) => {
              const isActive = currentTab === tab || (!currentTab && false)
              return (
                <button
                  key={tab}
                  type="button"
                  onClick={() => navigate(`/projects/${projectName}?tab=${tab}`)}
                  title={collapsed ? label : undefined}
                  className={cn(
                    'w-full flex items-center gap-3 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer',
                    collapsed ? 'justify-center px-2' : 'px-3',
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800',
                  )}
                >
                  <Icon size={16} className="shrink-0" />
                  {!collapsed && label}
                </button>
              )
            })}
          </div>
        )}
      </nav>

      {/* User info + logout */}
      <div className="p-2 border-t border-slate-800 space-y-1">
        {!collapsed && user && (
          <div className="px-3 py-1.5">
            <p className="text-xs text-slate-400 truncate">{user.full_name}</p>
            <p className="text-xs text-slate-600 truncate">{user.email}</p>
          </div>
        )}
        <NavLink
          to="/account"
          title={collapsed ? 'Account' : undefined}
          className={({ isActive }) =>
            cn(
              'w-full flex items-center gap-3 py-2 rounded-lg text-sm transition-colors cursor-pointer',
              collapsed ? 'justify-center px-2' : 'px-3',
              isActive
                ? 'bg-emerald-500/10 text-emerald-400'
                : 'text-slate-400 hover:text-white hover:bg-slate-800',
            )
          }
        >
          <Settings size={15} className="shrink-0" />
          {!collapsed && 'Account'}
        </NavLink>
        <button
          type="button"
          onClick={handleLogout}
          title={collapsed ? 'Sign out' : undefined}
          className={cn(
            'w-full flex items-center gap-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 text-sm transition-colors cursor-pointer',
            collapsed ? 'justify-center px-2' : 'px-3',
          )}
        >
          <LogOut size={15} className="shrink-0" />
          {!collapsed && 'Sign out'}
        </button>
      </div>
    </aside>
  )
}
