import React from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import PermissionDebugPanel from './PermissionDebugPanel'
import type { Role } from '../auth/permissions'

const navItems: {
  label: string
  to: string
  icon: string
  roles?: Role[]
}[] = [
  { label: 'Inbox', to: '/inbox', icon: '🤖', roles: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC', 'Viewer'] },
  { label: 'Dashboard', to: '/dashboard', icon: '📊', roles: ['Admin', 'Manager', 'PM', 'Sales'] },
  { label: 'Projects', to: '/projects', icon: '🧭', roles: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC'] },
  { label: 'Work', to: '/work', icon: '🛠️', roles: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC'] },
  { label: 'Quality', to: '/quality', icon: '✅', roles: ['Admin', 'Manager', 'QC', 'Engineer', 'Technician'] },
  { label: 'CRM', to: '/customers', icon: '🏢', roles: ['Admin', 'Manager', 'Sales', 'PM'] },
  { label: 'Messages', to: '/messages', icon: '💬', roles: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC', 'Viewer'] },
  { label: 'Documents', to: '/documents', icon: '📄', roles: ['Admin', 'Manager', 'PM', 'Sales', 'Engineer', 'Technician', 'QC', 'Viewer'] },
  { label: 'Admin', to: '/status', icon: '🧰', roles: ['Admin', 'Manager'] },
]

// Small, dependency-free class join helper
function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

function MenuIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function CloseIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" {...props}>
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function BrandMark() {
  return (
    <div className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 shadow-sm ring-1 ring-slate-900/10">
      <span className="text-base text-white">🧩</span>
      <span className="pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-white" />
    </div>
  )
}

/**
 * Cyberpunk active nav item:
 * - gradient neon plate
 * - outer bloom glow
 * - shimmer sweep on hover
 * - left neon bar
 * No CSS file needed.
 */
function NavItem({
  to,
  icon,
  label,
  onClick,
}: {
  to: string
  icon: string
  label: string
  onClick?: () => void
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        cx(
          'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm',
          'transition duration-200 active:scale-[0.98]',
          isActive ? 'text-white' : 'text-slate-700 hover:text-slate-900'
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* Active cyber glow background */}
          {isActive ? (
            <>
              {/* Gradient plate */}
              <span
                className={cx(
                  'absolute inset-0 rounded-xl',
                  'bg-gradient-to-r from-emerald-500/25 via-cyan-400/30 to-fuchsia-500/25',
                  'shadow-[0_0_18px_rgba(16,185,129,0.45)]',
                  'ring-1 ring-emerald-400/30'
                )}
                aria-hidden="true"
              />

              {/* Outer bloom */}
              <span
                className={cx(
                  'absolute -inset-1 rounded-2xl blur-lg',
                  'bg-gradient-to-r from-emerald-400/25 via-cyan-400/25 to-fuchsia-400/25',
                  'animate-pulse'
                )}
                aria-hidden="true"
              />

              {/* Shimmer sweep (on hover) */}
              <span className="absolute inset-0 overflow-hidden rounded-xl" aria-hidden="true">
                <span
                  className={cx(
                    'absolute inset-0',
                    'bg-[linear-gradient(120deg,transparent_0%,rgba(255,255,255,0.18)_45%,transparent_60%)]',
                    'translate-x-[-120%] group-hover:translate-x-[120%]',
                    'transition-transform duration-700 ease-out'
                  )}
                />
              </span>

              {/* Left neon bar */}
              <span
                className={cx(
                  'absolute left-1 top-1/2 h-7 w-1 -translate-y-1/2 rounded-full',
                  'bg-gradient-to-b from-emerald-300 via-cyan-300 to-fuchsia-300',
                  'shadow-[0_0_12px_rgba(34,211,238,0.75)]'
                )}
                aria-hidden="true"
              />
            </>
          ) : (
            // Non-active indicator on hover
            <span
              className="absolute left-1 top-1/2 h-6 w-1 -translate-y-1/2 rounded-full bg-transparent transition group-hover:bg-slate-300"
              aria-hidden="true"
            />
          )}

          {/* Icon chip */}
          <span
            className={cx(
              'relative grid h-8 w-8 place-items-center rounded-lg transition',
              isActive ? 'bg-white/10 ring-1 ring-white/10' : 'bg-slate-100 group-hover:bg-white'
            )}
            aria-hidden="true"
          >
            <span className="text-base">{icon}</span>
          </span>

          {/* Label */}
          <span className="relative font-medium">{label}</span>
        </>
      )}
    </NavLink>
  )
}

/**
 * Bottom nav item (mobile): smaller cyber glow
 */
function BottomNavItem({ to, icon, label }: { to: string; icon: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cx(
          'relative flex flex-col items-center justify-center gap-1 rounded-xl px-2 py-2 text-[11px] font-medium transition active:scale-[0.98]',
          isActive ? 'text-white' : 'text-slate-700 hover:bg-slate-100'
        )
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <>
              <span
                className={cx(
                  'absolute inset-0 rounded-xl',
                  'bg-gradient-to-r from-emerald-500/25 via-cyan-400/30 to-fuchsia-500/25',
                  'shadow-[0_0_16px_rgba(16,185,129,0.35)]',
                  'ring-1 ring-emerald-400/25'
                )}
                aria-hidden="true"
              />
              <span
                className={cx(
                  'absolute -inset-1 rounded-2xl blur-lg',
                  'bg-gradient-to-r from-emerald-400/20 via-cyan-400/20 to-fuchsia-400/20',
                  'animate-pulse'
                )}
                aria-hidden="true"
              />
            </>
          )}
          <span className="relative text-base">{icon}</span>
          <span className="relative truncate">{label}</span>
        </>
      )}
    </NavLink>
  )
}

export default function AppShell() {
  const navigate = useNavigate()
  const location = useLocation()
  const { hasRole, logout } = useAuth()

  const [mobileOpen, setMobileOpen] = React.useState(false)

  const visibleNavItems = React.useMemo(
    () =>
      navItems.filter((item) => {
        if (!item.roles) return true
        return item.roles.some((role) => hasRole(role))
      }),
    [hasRole]
  )

  const currentTitle =
    visibleNavItems.find((item) => location.pathname.startsWith(item.to))?.label ?? 'Aline Ops'

  // Close drawer when route changes (feels polished)
  React.useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  // ESC closes mobile drawer
  React.useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Decorative background */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-emerald-200/30 blur-3xl" />
        <div className="absolute -bottom-40 right-0 h-96 w-96 rounded-full bg-sky-200/30 blur-3xl" />
      </div>

      {/* Mobile drawer backdrop */}
      <div
        className={cx(
          'fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm transition-opacity md:hidden',
          mobileOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        )}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      {/* Mobile drawer */}
      <aside
        className={cx(
          'fixed left-0 top-0 z-50 h-full w-[84%] max-w-[320px] md:hidden',
          'bg-white shadow-2xl ring-1 ring-slate-900/10',
          'transition-transform duration-300 ease-out',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Mobile navigation"
      >
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <div className="text-sm font-semibold text-slate-900">Aline Ops</div>
              <div className="text-xs text-slate-500">Industrial AI Workspace</div>
            </div>
          </div>

          <button
            className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-700 active:scale-[0.98]"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="px-4 pb-4">
          <div className="rounded-2xl bg-gradient-to-r from-slate-900 to-slate-700 px-4 py-3 text-white shadow-sm">
            <div className="text-xs opacity-80">Workspace</div>
            <div className="text-base font-semibold">{currentTitle}</div>
          </div>

          <nav className="mt-4 space-y-1">
            {visibleNavItems.map((item) => (
              <NavItem key={item.to} to={item.to} icon={item.icon} label={item.label} />
            ))}
          </nav>

          <div className="mt-5 grid gap-2">
            <button
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 active:scale-[0.98]"
              onClick={() => {
                logout()
                window.location.href = '/login'
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        {/* Desktop sidebar */}
        <aside className="hidden w-72 flex-col px-4 py-6 md:flex">
          <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-900/10">
            <div className="flex items-center gap-3">
              <BrandMark />
              <div>
                <div className="text-sm font-semibold text-slate-900">Aline Ops</div>
                <div className="text-xs text-slate-500">Industrial AI Workspace</div>
              </div>
            </div>

            <nav className="mt-4 space-y-1">
              {visibleNavItems.map((item) => (
                <NavItem key={item.to} to={item.to} icon={item.icon} label={item.label} />
              ))}
            </nav>
          </div>

          <div className="mt-4 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-900/10">
            <div className="text-xs font-medium text-slate-500">Quick actions</div>
            <div className="mt-2 flex gap-2">
              <button
                className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 active:scale-[0.98]"
                onClick={() => navigate('/documents')}
              >
                Upload docs
              </button>
              <button
                className="flex-1 rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 active:scale-[0.98]"
                onClick={() => navigate('/inbox')}
              >
                Review AI
              </button>
            </div>
          </div>
        </aside>

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Header */}
          <header className="sticky top-0 z-30">
            <div className="mx-3 mt-3 rounded-2xl bg-white/80 px-4 py-3 shadow-sm ring-1 ring-slate-900/10 backdrop-blur supports-[backdrop-filter]:bg-white/70 md:mx-4 md:mt-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {/* Mobile hamburger */}
                  <button
                    className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-700 transition hover:bg-slate-50 active:scale-[0.98] md:hidden"
                    onClick={() => setMobileOpen(true)}
                    aria-label="Open menu"
                  >
                    <MenuIcon className="h-5 w-5" />
                  </button>

                  <div className="min-w-0">
                    <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      Workspace
                    </div>
                    <div className="truncate text-lg font-semibold text-slate-900">{currentTitle}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="hidden rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 md:block">
                    User
                  </div>

                  <button
                    className="rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 active:scale-[0.98]"
                    onClick={() => {
                      logout()
                      window.location.href = '/login'
                    }}
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <main className="flex-1 px-3 pb-24 pt-4 md:px-4 md:pb-6">
            <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-900/10 md:p-6">
              <Outlet />
            </div>

            <div className="mt-4">
              <PermissionDebugPanel />
            </div>
          </main>

          {/* Mobile bottom nav */}
          <nav className="fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200 bg-white/90 backdrop-blur md:hidden">
            <div className="mx-auto grid max-w-[680px] grid-cols-4 gap-1 px-2 py-2">
              {visibleNavItems.slice(0, 4).map((item) => (
                <BottomNavItem key={item.to} to={item.to} icon={item.icon} label={item.label} />
              ))}
            </div>
          </nav>
        </div>
      </div>
    </div>
  )
}
