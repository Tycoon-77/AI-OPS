import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  BellRing,
  Flame,
  GitFork,
  Network,
  BarChart3,
  Settings as SettingsIcon,
  LogOut,
  Radio,
  ShieldCheck,
  ChevronRight
} from 'lucide-react';

const navItems = [
  { name: 'Overview', path: '/', icon: LayoutDashboard },
  { name: 'Alert Explorer', path: '/alerts', icon: BellRing, badge: '400' },
  { name: 'Incidents', path: '/incidents', icon: Flame, badge: '3', badgeColor: 'bg-red-500/20 text-red-400 border border-red-500/30' },
  { name: 'Root Cause Analysis', path: '/root-cause', icon: GitFork },
  { name: 'Service Map', path: '/service-map', icon: Network },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Settings', path: '/settings', icon: SettingsIcon },
];

export const Sidebar = ({ isOpen, onClose }) => {
  const navigate = useNavigate();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#111827] border-r border-[#293449] flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-5 border-b border-[#293449] flex items-center justify-between">
          <div
            onClick={() => navigate('/')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-sky-500 flex items-center justify-center shadow-lg shadow-indigo-600/30 group-hover:scale-105 transition-transform">
              <Radio className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-lg tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                  Signal<span className="text-indigo-400">IQ</span>
                </span>
                <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  v1.0
                </span>
              </div>
              <p className="text-[10px] text-[#94A3B8] font-medium tracking-tight">
                Incident Intelligence
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Platform Navigation
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => {
                  if (window.innerWidth < 1024 && onClose) onClose();
                }}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group ${
                    isActive
                      ? 'bg-indigo-600/20 text-white border border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                      : 'text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1E293B]/70'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`w-4 h-4 transition-colors ${
                          isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-indigo-300'
                        }`}
                      />
                      <span>{item.name}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                          item.badgeColor || 'bg-slate-800 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Live System Status Widget */}
        <div className="px-4 py-3 mx-3 mb-3 rounded-lg bg-[#151D2E] border border-[#293449]">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-[#94A3B8] flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Correlation Engine
            </span>
            <span className="text-emerald-400 font-semibold">Active</span>
          </div>
          <div className="text-[11px] text-slate-400">
            Deduplication & Graph ML: <span className="text-slate-200 font-medium">93.75% Noise Cut</span>
          </div>
        </div>

        {/* User Profile Footer */}
        <div className="p-3 border-t border-[#293449] bg-[#0E1524]">
          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-[#151D2E] transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm shadow">
                AD
              </div>
              <div>
                <div className="flex items-center gap-1">
                  <span className="text-sm font-semibold text-white">Admin</span>
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                </div>
                <p className="text-[11px] text-[#94A3B8]">System Administrator</p>
              </div>
            </div>
            <button
              onClick={() => alert('Logged out demo session')}
              className="p-1.5 text-slate-400 hover:text-red-400 rounded-md hover:bg-red-500/10 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
