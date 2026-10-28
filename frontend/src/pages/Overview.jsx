import React, { useState, useEffect } from 'react';
import { useBackendStatus, fmtInt } from '../services/status';
import { useOutletContext, useNavigate } from 'react-router-dom';
import {
  BellRing,
  Flame,
  CheckCircle2,
  TrendingDown,
  Layers,
  Upload,
  ArrowRight,
  ShieldAlert,
  Sparkles,
  RefreshCw,
  GitFork
} from 'lucide-react';
import { MetricCard } from '../components/dashboard/MetricCard';
import { AlertVolumeChart } from '../components/charts/AlertVolumeChart';
import { SeverityDonutChart } from '../components/charts/SeverityDonutChart';
import { ServiceIncidentsChart } from '../components/charts/ServiceIncidentsChart';
import { RecentIncidentsTable } from '../components/dashboard/RecentIncidentsTable';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { analyticsService } from '../services/analyticsService';
import { incidentService } from '../services/incidentService';

export const Overview = () => {
  const { stats, live } = useBackendStatus();
  const { openUploadModal } = useOutletContext() || {};
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [incidents, setIncidents] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [analyticsRes, incidentsRes] = await Promise.all([
          analyticsService.getAnalyticsSummary('24h'),
          incidentService.getIncidents()
        ]);
        setAnalytics(analyticsRes.data);
        setIncidents(incidentsRes.data || []);
      } catch (err) {
        console.error('Failed to load overview data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Welcome & Hero Section */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-[#151D2E] via-[#162137] to-[#121A2B] border border-[#293449] relative overflow-hidden shadow-xl">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-radial from-indigo-500/10 via-transparent to-transparent pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold border border-indigo-500/30 mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>AO-01 Incident Intelligence Active</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Welcome to SignalIQ
            </h1>
            <p className="text-sm sm:text-base text-[#94A3B8] mt-2 leading-relaxed">
              Monitor alerts, discover incidents, and understand the root cause of system failures.
              Transforming <span className="text-white font-medium">{stats ? fmtInt(stats.rawAlerts) : "16,339"} noisy alerts</span> into <span className="text-indigo-400 font-medium">{stats ? fmtInt(stats.surfaced) : "correlated"} surfaced cards</span> without deleting original alert data.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={openUploadModal}
              className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold text-sm transition-all shadow-lg shadow-indigo-600/30 hover:scale-[1.02]"
            >
              <Upload className="w-4 h-4" />
              <span>Upload Alerts</span>
            </button>
            <button
              onClick={() => navigate('/root-cause')}
              className="flex items-center gap-2 px-4 py-2.5 bg-[#1E293B] hover:bg-slate-700 text-slate-200 hover:text-white rounded-xl font-semibold text-sm transition-all border border-[#293449]"
            >
              <GitFork className="w-4 h-4 text-indigo-400" />
              <span>Root Cause Graph</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Total Alerts"
          value={analytics?.summary?.totalAlerts != null ? fmtInt(analytics.summary.totalAlerts) : "—"}
          subtitle="Ingested from multi-service monitoring"
          icon={BellRing}
          color="indigo"
        />
        <MetricCard
          title="Alerts in real incidents (ground truth)"
          value={analytics?.summary?.correlatedAlerts != null ? fmtInt(analytics.summary.correlatedAlerts) : "—"}
          subtitle="Labelled by the simulator, not by the model"
          icon={CheckCircle2}
          color="sky"
        />
        <MetricCard
          title="Surfaced incident cards"
          value={stats ? fmtInt(stats.surfaced) : "—"}
          subtitle={stats ? `${fmtInt(stats.redOrange)} RED+ORANGE · ${fmtInt(stats.yellow)} YELLOW` : "Backend unreachable"}
          icon={Flame}
          color="red"
        />
        <MetricCard
          title="Alerts outside real incidents"
          value={analytics?.summary?.uncorrelatedAlerts != null ? fmtInt(analytics.summary.uncorrelatedAlerts) : "—"}
          subtitle="Ground truth: noise and singletons (all kept)"
          icon={Layers}
          color="amber"
        />
        <MetricCard
          title="Noise Reduction"
          value={stats ? `${stats.noiseCutPct}%` : "—"}
          subtitle="Alerts → surfaced cards (see Analytics for precision)"
          icon={TrendingDown}
          color="emerald"
        />
      </div>

      {/* Visual Analytics Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart 1: Volume Over Time */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[#151D2E] border border-[#293449] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">
                Alert Volume Over Time (Ingress vs Correlated)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Hourly telemetry stream showing incident burst compression at 15:00 UTC
              </p>
            </div>
            <span className="text-[11px] text-slate-400 font-mono px-2 py-0.5 rounded bg-[#111827] border border-[#293449]">
              Hourly Window
            </span>
          </div>
          {analytics?.hourlyData ? (
            <AlertVolumeChart data={analytics.hourlyData} />
          ) : (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">Loading telemetry chart...</div>
          )}
        </div>

        {/* Chart 2: Alerts by Severity */}
        <div className="p-5 rounded-xl bg-[#151D2E] border border-[#293449] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Alerts by Severity</h2>
              <p className="text-xs text-slate-400 mt-0.5">{live && stats ? `Breakdown of ${fmtInt(stats.rawAlerts)} ingested alerts` : "Breakdown of ingested alerts"}</p>
            </div>
            <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
              Donut
            </span>
          </div>
          {analytics?.alertsBySeverity ? (
            <SeverityDonutChart data={analytics.alertsBySeverity} />
          ) : (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">Loading severity chart...</div>
          )}
        </div>
      </div>

      {/* Second Row: Incidents by Service & Activity Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Incidents by Service Bar Chart */}
        <div className="p-5 rounded-xl bg-[#151D2E] border border-[#293449]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Alert Volume by Service</h2>
              <p className="text-xs text-slate-400 mt-0.5">Affected service distribution</p>
            </div>
            <button
              onClick={() => navigate('/service-map')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium hover:underline"
            >
              Service Map →
            </button>
          </div>
          {analytics?.alertsByService ? (
            <ServiceIncidentsChart data={analytics.alertsByService} />
          ) : (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">Loading services...</div>
          )}
        </div>

        {/* Recent Activity Feed */}
        <div className="lg:col-span-2 p-5 rounded-xl bg-[#151D2E] border border-[#293449] flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Recent Platform Activity</h2>
              <p className="text-xs text-slate-400 mt-0.5">Real-time deduplication and correlation events</p>
            </div>
            <span className="text-[11px] text-emerald-400 flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Stream Active
            </span>
          </div>
          <ActivityFeed />
        </div>
      </div>

      {/* Recent Incidents Table */}
      <div className="p-5 rounded-xl bg-[#151D2E] border border-[#293449]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide">Active Correlated Incidents</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Identified by SignalIQ multi-service topology correlation
            </p>
          </div>
          <button
            onClick={() => navigate('/incidents')}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium hover:underline"
          >
            <span>View All Incidents</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
        <RecentIncidentsTable incidents={incidents} />
      </div>
    </div>
  );
};
