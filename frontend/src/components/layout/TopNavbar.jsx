import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  Search,
  Bell,
  HelpCircle,
  Upload,
  Calendar,
  Clock,
  ExternalLink,
  ChevronRight,
  Sparkles,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export const TopNavbar = ({ onOpenSidebar, onOpenUploadModal }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [currentDateTime, setCurrentDateTime] = useState(new Date());
  const [showNotifications, setShowNotifications] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Clock tick every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentDateTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Compute page title and breadcrumb based on route
  const getRouteInfo = (pathname) => {
    if (pathname === '/') return { title: 'Overview', breadcrumb: ['Home', 'Overview'] };
    if (pathname.startsWith('/alerts')) return { title: 'Alert Explorer', breadcrumb: ['Home', 'Alerts'] };
    if (pathname.startsWith('/incidents/')) return { title: 'Incident Investigation', breadcrumb: ['Home', 'Incidents', 'Detail'] };
    if (pathname.startsWith('/incidents')) return { title: 'Incident Intelligence', breadcrumb: ['Home', 'Incidents'] };
    if (pathname.startsWith('/root-cause')) return { title: 'Root Cause Analysis', breadcrumb: ['Home', 'Investigation', 'Root Cause'] };
    if (pathname.startsWith('/service-map')) return { title: 'Service Dependency Map', breadcrumb: ['Home', 'Topology', 'Service Map'] };
    if (pathname.startsWith('/analytics')) return { title: 'Alert & Incident Analytics', breadcrumb: ['Home', 'Analytics'] };
    if (pathname.startsWith('/settings')) return { title: 'Platform Settings', breadcrumb: ['Home', 'Configuration', 'Settings'] };
    return { title: 'SignalIQ', breadcrumb: ['Home'] };
  };

  const routeInfo = getRouteInfo(location.pathname);

  const handleGlobalSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/alerts?search=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
    }
  };

  return (
    <>
      <header className="sticky top-0 z-30 h-16 bg-[#111827]/90 backdrop-blur-md border-b border-[#293449] px-4 lg:px-6 flex items-center justify-between gap-4">
        {/* Left Side: Mobile Menu Button + Breadcrumb */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenSidebar}
            className="p-2 -ml-1 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B] lg:hidden focus:outline-hidden"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              {routeInfo.breadcrumb.map((crumb, idx) => (
                <React.Fragment key={crumb}>
                  {idx > 0 && <ChevronRight className="w-3 h-3 text-slate-400" />}
                  <span className={idx === routeInfo.breadcrumb.length - 1 ? 'text-indigo-400 font-medium' : ''}>
                    {crumb}
                  </span>
                </React.Fragment>
              ))}
            </div>
            <h1 className="text-base lg:text-lg font-bold text-white tracking-tight flex items-center gap-2">
              {routeInfo.title}
            </h1>
          </div>
        </div>

        {/* Center: Global Search Bar */}
        <form onSubmit={handleGlobalSearch} className="hidden md:flex flex-1 max-w-md mx-4">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search 400 alerts, services, or INC-001..."
              className="w-full bg-[#151D2E] border border-[#293449] text-sm text-slate-200 pl-9 pr-12 py-1.5 rounded-lg focus:outline-none focus:border-indigo-500 transition-colors placeholder:text-slate-400"
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-[#1E293B] rounded border border-slate-700/60">
              Enter
            </kbd>
          </div>
        </form>

        {/* Right Side: Quick Action + Clock + Notifications + Help */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick Upload Button */}
          <button
            onClick={onOpenUploadModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-all shadow-sm shadow-indigo-600/30 hover:scale-[1.02]"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload Alerts</span>
          </button>

          {/* Date & Time Display */}
          <div className="hidden xl:flex items-center gap-3 px-3 py-1 rounded-lg bg-[#151D2E] border border-[#293449] text-xs text-slate-300">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                {currentDateTime.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric'
                })}
              </span>
            </div>
            <div className="h-3 w-px bg-slate-700" />
            <div className="flex items-center gap-1.5 font-mono">
              <Clock className="w-3.5 h-3.5 text-sky-400" />
              <span>{currentDateTime.toLocaleTimeString('en-US', { hour12: false })} UTC</span>
            </div>
          </div>

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B] relative transition-colors"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            </button>

            {/* Notification Dropdown */}
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-[#151D2E] border border-[#293449] rounded-xl shadow-2xl py-2 z-50">
                <div className="px-3 py-2 border-b border-[#293449] flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">Live Intelligence Stream</span>
                  <span className="text-[10px] bg-red-500/20 text-red-300 px-1.5 py-0.5 rounded border border-red-500/30">
                    3 Active Incidents
                  </span>
                </div>
                <div className="divide-y divide-[#293449]/60 max-h-64 overflow-y-auto">
                  <div className="p-3 hover:bg-[#1E293B]/60 transition-colors cursor-pointer" onClick={() => navigate('/incidents/INC-001')}>
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-xs font-medium text-white">INC-001: Database Degraded</div>
                        <div className="text-[11px] text-slate-400">182 alerts correlated • Postgres connection pool 98%</div>
                        <div className="text-[10px] text-indigo-400 mt-1">2 mins ago</div>
                      </div>
                    </div>
                  </div>
                  <div className="p-3 hover:bg-[#1E293B]/60 transition-colors cursor-pointer" onClick={() => navigate('/incidents/INC-002')}>
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-xs font-medium text-white">INC-002: Ingress Latency Spike</div>
                        <div className="text-[11px] text-slate-400">114 alerts correlated • API Gateway 504 timeouts</div>
                        <div className="text-[10px] text-indigo-400 mt-1">14 mins ago</div>
                      </div>
                    </div>
                  </div>
                  <div className="p-3 hover:bg-[#1E293B]/60 transition-colors cursor-pointer" onClick={() => navigate('/incidents/INC-003')}>
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-xs font-medium text-white">INC-003: Payment Webhook Delay</div>
                        <div className="text-[11px] text-slate-400">79 alerts correlated • Retry queue depth surge</div>
                        <div className="text-[10px] text-indigo-400 mt-1">28 mins ago</div>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="px-3 pt-2 border-t border-[#293449] text-center">
                  <button
                    onClick={() => {
                      setShowNotifications(false);
                      navigate('/incidents');
                    }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                  >
                    View all incident groupings →
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Help Icon */}
          <button
            onClick={() => setShowHelpModal(true)}
            className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B] transition-colors"
            title="Platform Documentation & Rules"
          >
            <HelpCircle className="w-4 h-4" />
          </button>

          {/* User Avatar */}
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-sky-400 flex items-center justify-center text-white font-bold text-xs ring-2 ring-indigo-500/30">
            A
          </div>
        </div>
      </header>

      {/* Help Modal */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#151D2E] border border-[#293449] rounded-2xl max-w-lg w-full p-6 shadow-2xl relative">
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              About SignalIQ Incident Intelligence
            </h3>
            <p className="text-sm text-slate-300 mb-4">
              <strong>AO-01 Problem Statement:</strong> 400 alerts, three real incidents.
            </p>
            <div className="space-y-3 text-xs text-slate-300">
              <div className="p-3 rounded-lg bg-[#111827] border border-[#293449]">
                <strong className="text-white block mb-1">Zero Destructive Actions Principle:</strong>
                SignalIQ is an intelligence platform. It <em>never deletes, mutes, or closes</em> original alerts. Every incoming alert retains complete raw telemetry fidelity.
              </div>
              <div className="p-3 rounded-lg bg-[#111827] border border-[#293449]">
                <strong className="text-white block mb-1">Probable vs Confirmed Cause:</strong>
                Root cause recommendations are mathematically graded as <em>Probable Conclusions</em> with explicit evidence chains, rather than assuming unverified certainty.
              </div>
              <div className="p-3 rounded-lg bg-[#111827] border border-[#293449]">
                <strong className="text-white block mb-1">Correlation Engine:</strong>
                Alerts are clustered across four dimensions: Time Proximity, Service Dependency Topology, Semantic Similarity, and Historical Incident Signatures.
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowHelpModal(false)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition-colors"
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
