import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Sliders,
  Bell,
  Network,
  User,
  Shield,
  Save,
  CheckCircle2,
  RotateCcw,
  Sparkles,
  Lock,
  Globe
} from 'lucide-react';

export const Settings = () => {
  // General Settings
  const [appName, setAppName] = useState('SignalIQ');
  const [theme, setTheme] = useState('dark');
  const [timezone, setTimezone] = useState('UTC');

  // Alert Settings
  const [autoHighlightCritical, setAutoHighlightCritical] = useState(true);
  const [audioNotifications, setAudioNotifications] = useState(false);
  const [defaultRowsPerPage, setDefaultRowsPerPage] = useState('15');
  const [displayDensity, setDisplayDensity] = useState('comfortable');

  // Correlation Settings
  const [timeWindowMin, setTimeWindowMin] = useState(5);
  const [similarityThreshold, setSimilarityThreshold] = useState(90);
  const [topologyAware, setTopologyAware] = useState(true);
  const [maxHopDistance, setMaxHopDistance] = useState(2);

  // Account Settings
  const [name, setName] = useState('Admin');
  const [email, setEmail] = useState('admin@signaliq.internal');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Save feedback state
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState('general'); // 'general' | 'alerts' | 'correlation' | 'account'

  const handleSave = (e) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const handleReset = () => {
    setAppName('SignalIQ');
    setTheme('dark');
    setTimezone('UTC');
    setTimeWindowMin(5);
    setSimilarityThreshold(90);
    setTopologyAware(true);
    setMaxHopDistance(2);
    setSaveSuccess(false);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <SettingsIcon className="w-6 h-6 text-indigo-400" />
            Platform Settings
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Configure correlation thresholds, visualization preferences, and system administration profiles.
          </p>
        </div>

        {saveSuccess && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Preferences saved successfully (Client Cache)</span>
          </div>
        )}
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[#293449] text-xs font-semibold pb-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('general')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'general'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Globe className="w-3.5 h-3.5 text-indigo-400" />
          <span>General Settings</span>
        </button>

        <button
          onClick={() => setActiveTab('alerts')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'alerts'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bell className="w-3.5 h-3.5 text-sky-400" />
          <span>Alert Ingestion</span>
        </button>

        <button
          onClick={() => setActiveTab('correlation')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'correlation'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-3.5 h-3.5 text-amber-400" />
          <span>Correlation Engine (AO-01)</span>
        </button>

        <button
          onClick={() => setActiveTab('account')}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-t-lg transition-colors border-b-2 ${
            activeTab === 'account'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <User className="w-3.5 h-3.5 text-emerald-400" />
          <span>Account & Security</span>
        </button>
      </div>

      {/* Main Settings Form Container */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* 1. General Settings */}
        {activeTab === 'general' && (
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-5 text-xs">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">General Platform Preferences</h2>
              <p className="text-slate-400 text-xs mt-0.5">Control the system appearance and timezone alignment</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">Application Name</label>
                <input
                  type="text"
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">Active UI Theme</label>
                <select
                  value={theme}
                  onChange={(e) => setTheme(e.target.value)}
                  className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                >
                  <option value="dark">Dark Theme (Default Obsidian / Navy #0B1020)</option>
                  <option value="system">System Synchronized</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">Display Timezone</label>
                <select
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                >
                  <option value="UTC">UTC (Universal Coordinated Time)</option>
                  <option value="EST">EST (US Eastern Time)</option>
                  <option value="PST">PST (US Pacific Time)</option>
                  <option value="IST">IST (Indian Standard Time)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* 2. Alert Settings */}
        {activeTab === 'alerts' && (
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-5 text-xs">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">Alert Preferences & Filtering</h2>
              <p className="text-slate-400 text-xs mt-0.5">Customize table layout and critical alarm highlighting</p>
            </div>

            <div className="space-y-4">
              <label className="flex items-center gap-3 p-3 rounded-lg bg-[#111827] border border-[#293449] cursor-pointer hover:border-slate-600 transition-colors">
                <input
                  type="checkbox"
                  checked={autoHighlightCritical}
                  onChange={(e) => setAutoHighlightCritical(e.target.checked)}
                  className="w-4 h-4 accent-indigo-600 rounded"
                />
                <div>
                  <span className="text-white font-semibold block">Auto-Highlight Critical Severity Alarms</span>
                  <span className="text-slate-400 text-[11px]">
                    Visually pulse high-priority alerts with red glow in Explorer tables.
                  </span>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 rounded-lg bg-[#111827] border border-[#293449] cursor-pointer hover:border-slate-600 transition-colors">
                <input
                  type="checkbox"
                  checked={audioNotifications}
                  onChange={(e) => setAudioNotifications(e.target.checked)}
                  className="w-4 h-4 accent-indigo-600 rounded"
                />
                <div>
                  <span className="text-white font-semibold block">Audible Incident Bell</span>
                  <span className="text-slate-400 text-[11px]">
                    Play sound chime when new incident cross-correlation occurs.
                  </span>
                </div>
              </label>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold block">Default Rows per Table Page</label>
                  <select
                    value={defaultRowsPerPage}
                    onChange={(e) => setDefaultRowsPerPage(e.target.value)}
                    className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                  >
                    <option value="15">15 alerts per page</option>
                    <option value="25">25 alerts per page</option>
                    <option value="50">50 alerts per page</option>
                    <option value="100">100 alerts per page</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-slate-300 font-semibold block">Table Density</label>
                  <select
                    value={displayDensity}
                    onChange={(e) => setDisplayDensity(e.target.value)}
                    className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                  >
                    <option value="comfortable">Comfortable (Enterprise standard)</option>
                    <option value="compact">Compact (High Information Density)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 3. Correlation Settings */}
        {activeTab === 'correlation' && (
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-5 text-xs">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">Correlation Engine Algorithms</h2>
              <p className="text-slate-400 text-xs mt-0.5">Tune temporal envelope, semantic cosine threshold, and graph topology hops</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-white font-semibold">Correlation Sliding Time Window</label>
                  <span className="font-mono text-indigo-400 font-bold">{timeWindowMin} minutes</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={timeWindowMin}
                  onChange={(e) => setTimeWindowMin(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <span className="text-[11px] text-slate-400 block">
                  Alerts firing within this burst window are analyzed for cascading dependencies.
                </span>
              </div>

              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-white font-semibold">Semantic Message Similarity Threshold</label>
                  <span className="font-mono text-indigo-400 font-bold">{similarityThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="98"
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <span className="text-[11px] text-slate-400 block">
                  Cosine distance required between alert text embeddings to merge clusters.
                </span>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <label className="flex items-center gap-3 p-3 rounded-lg bg-[#111827] border border-[#293449] cursor-pointer">
                <input
                  type="checkbox"
                  checked={topologyAware}
                  onChange={(e) => setTopologyAware(e.target.checked)}
                  className="w-4 h-4 accent-indigo-600 rounded"
                />
                <div>
                  <span className="text-white font-semibold block">Enable Topology-Aware Graph Traversal</span>
                  <span className="text-slate-400 text-[11px]">
                    Trace upstream datastores and ingress routers using service dependency graph.
                  </span>
                </div>
              </label>

              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2 max-w-sm">
                <label className="text-white font-semibold block">Maximum Dependency Hop Distance</label>
                <select
                  value={maxHopDistance}
                  onChange={(e) => setMaxHopDistance(Number(e.target.value))}
                  className="w-full bg-[#0B1020] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500 font-mono"
                >
                  <option value={1}>1 Hop (Immediate upstream/downstream only)</option>
                  <option value={2}>2 Hops (Default - captures edge to database cascades)</option>
                  <option value={3}>3 Hops (Deep multi-tier architecture)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* 4. Account Settings */}
        {activeTab === 'account' && (
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-5 text-xs">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">Administrator Profile & Security</h2>
              <p className="text-slate-400 text-xs mt-0.5">Frontend mock authentication profile management</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">User Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-slate-300 font-semibold block">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="pt-4 border-t border-[#293449] space-y-3">
              <span className="text-white font-semibold block flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-indigo-400" />
                Change Password UI
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  type="password"
                  placeholder="Current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="password"
                  placeholder="New password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="bg-[#111827] border border-[#293449] text-white px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white bg-[#151D2E] hover:bg-[#1E293B] border border-[#293449] rounded-lg transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-all shadow-md shadow-indigo-600/30"
          >
            <Save className="w-4 h-4" />
            <span>Save Preferences</span>
          </button>
        </div>
      </form>
    </div>
  );
};
