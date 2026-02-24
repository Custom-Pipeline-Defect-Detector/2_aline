import React from 'react'
import { NavLink, type NavLinkProps } from 'react-router-dom'

function cx(...classes: Array<string | false | undefined | null>) {
  return classes.filter(Boolean).join(' ')
}

type Props = NavLinkProps & {
  icon: string
  label: string
  onClick?: () => void
}

export default function GlowNavLink({ icon, label, onClick, ...props }: Props) {
  return (
    <NavLink
      {...props}
      onClick={onClick}
      className={({ isActive }) =>
        cx(
          'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm',
          'transition duration-50 active:scale-[0.98]',
          isActive ? 'text-white' : 'text-slate-700 hover:text-slate-900'
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* CYBER ACTIVE GLOW */}
          {isActive && (
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

              {/* Shimmer sweep (hover) */}
              <span className="absolute inset-0 rounded-xl overflow-hidden" aria-hidden="true">
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
          )}

          {/* Left bar when NOT active */}
          {!isActive && (
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
