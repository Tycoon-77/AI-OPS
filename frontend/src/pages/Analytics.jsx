import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { analyticsService } from '../services/analyticsService';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#151D2E] border border-[#293449] p-3 rounded-lg shadow-xl text-xs">
        <div className="font-semibold text-white mb-1.5">{label}</div>
        <div className="space-y-1">
          {payload.map((entry, idx) => (
            <div key={idx} className="flex items-center justify-between gap-4" style={{ color: entry.color }}>
              <span>{entry.name}:</span>
              <span className="font-mono font-bold text-white">{entry.value}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export const Analytics = () => {
  const [timeRange, setTimeRange] = useState('24h');
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isCancelled = false;
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        const res = await analyticsService.getAnalyticsSummary(timeRange);
        if (!isCancelled) {
          setAnalyticsData(res.data);
        }
      } catch (err) {
        console.error('Failed to load analytics', err);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };
    fetchAnalytics();
    return () => {
      isCancelled = true;
    };
  }, [timeRange]);

  if (loading || !analyticsData) {
    return (
      <div className="p-16 text-center text-xs text-slate-400">
        Loading analytics visualizations...
      </div>
    );
  }

  const { summary, hourlyData, alertsByService, alertsBySeverity, duplicateTrends, evaluationMetrics } = analyticsData;

  return (
    <div className="space-y-6">
      {/* Page Header with Time Range Filter */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-indigo-400" />
            Alert Analytics & Performance
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Analyze alert influx velocity, deduplication efficiency, and incident clustering benchmarks.
          </p>
        </div>

        {/* Date Range Selector */}
        <div className="flex items-center bg-[#151D2E] border border-[#293449] rounded-xl p-1 text-xs">
          {['24h', '7d', '30d'].map((range) => {
            const labelMap = { '24h': 'Last 24 Hours', '7d': 'Last 7 Days', '30d': 'Last 30 Days' };
            const isActive = timeRange === range;
            return (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                  isActive ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-white'
                }`}
              >
                {labelMap[range]}
              </button>
            );
          })}
        </div>
      </div>

      {/* High-Level Benchmark Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449]">
          <span className="text-slate-400 text-xs font-semibold block uppercase">Total Ingested</span>
          <div className="text-2xl font-bold font-mono text-white mt-1">{summary.totalAlerts}</div>
          <span className="text-[11px] text-slate-400">Full telemetry fidelity</span>
        </div>
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449]">
          <span className="text-slate-400 text-xs font-semibold block uppercase">Correlated Signals</span>
          <div className="text-2xl font-bold font-mono text-indigo-400 mt-1">{summary.correlatedAlerts}</div>
          <span className="text-[11px] text-indigo-300">Clustered into incidents</span>
        </div>
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449]">
          <span className="text-slate-400 text-xs font-semibold block uppercase">Noise Reduction Rate</span>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">{summary.alertNoiseReduction || summary.noiseReduction}</div>
          <span className="text-[11px] text-emerald-300">Mitigates on-call fatigue</span>
        </div>
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449]">
          <span className="text-slate-400 text-xs font-semibold block uppercase">Active Incident Groups</span>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">{summary.activeIncidents}</div>
          <span className="text-[11px] text-slate-400">Mean time: {summary.meanTimeToCorrelateSec}</span>
        </div>
      </div>

      {/* Row 1: Charts (Total vs Correlated & Alert Volume by Hour) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Total Alerts vs Correlated Alerts */}
        <div className="p-5 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">
                Total Ingress Alerts vs Correlated
              </h2>
              <p className="text-xs text-slate-400">Raw volume versus intelligence compression</p>
            </div>
            <span className="text-[10px] text-indigo-400 font-mono bg-[#111827] px-2 py-0.5 rounded border border-[#293449]">
              Recharts Area
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={hourlyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="anTot" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="anCorr" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="hour" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Area type="monotone" dataKey="totalAlerts" name="Total Ingress" stroke="#6366F1" fill="url(#anTot)" strokeWidth={2} />
                <Area type="monotone" dataKey="correlated" name="Correlated Signals" stroke="#38BDF8" fill="url(#anCorr)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Duplicate Alert Trends */}
        <div className="p-5 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">
                Deduplication Suppression Trends
              </h2>
              <p className="text-xs text-slate-400">Raw alert spike rate vs unique deduplicated alerts</p>
            </div>
            <span className="text-[10px] text-amber-400 font-mono bg-[#111827] px-2 py-0.5 rounded border border-[#293449]">
              Rate / min
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={duplicateTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Line type="monotone" dataKey="rawRate" name="Raw Ingress Rate" stroke="#EF4444" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="deduplicatedRate" name="Deduplicated Unique Rate" stroke="#22C55E" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 2: Alerts by Service & Severity Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 3. Alerts by Service */}
        <div className="p-5 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Alerts by Service Target</h2>
              <p className="text-xs text-slate-400">Total alert volume mapped to microservices</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={alertsByService} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="service" stroke="#64748B" fontSize={10} tickLine={false} tickFormatter={(v) => v.slice(0, 10)} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Total Alerts" fill="#6366F1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Incidents & Severity Distribution */}
        <div className="p-5 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Incidents & Alerts by Severity</h2>
              <p className="text-xs text-slate-400">Distribution across Critical, Warning, and Info</p>
            </div>
          </div>
          <div className="h-64 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Tooltip content={<CustomTooltip />} />
                <Pie
                  data={alertsBySeverity}
                  innerRadius={60}
                  outerRadius={85}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="#151D2E"
                  strokeWidth={2}
                >
                  {alertsBySeverity.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Model Evaluation Metrics Section (Clearly labeled demonstration values) */}
      <div className="p-6 rounded-2xl bg-[#151D2E] border border-indigo-500/30 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white tracking-wide">
                Correlation Model Evaluation Benchmarks
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {evaluationMetrics.note}
            </p>
          </div>
          <span className="px-2.5 py-1 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold">
            {evaluationMetrics.label}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2">
          {evaluationMetrics.metrics.map((metric, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-xl border space-y-1.5 ${
                metric.status === 'pending'
                  ? 'bg-[#111827] border-amber-500/30 text-amber-200'
                  : 'bg-[#111827] border-[#293449] text-slate-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                  {metric.name}
                </span>
                {metric.status === 'pending' ? (
                  <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-mono">
                    PENDING
                  </span>
                ) : (
                  <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-mono">
                    DEMO
                  </span>
                )}
              </div>
              <div
                className={`text-xl font-bold font-mono ${
                  metric.status === 'pending' ? 'text-amber-400 text-sm py-1' : 'text-white'
                }`}
              >
                {metric.value}
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">
                {metric.description}
              </p>
            </div>
          ))}
        </div>

        <div className="p-3 rounded-lg bg-[#0B1020] border border-[#293449] text-[11px] text-slate-400 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>
            <strong>Evaluation Transparency Notice:</strong> Metrics above are calculated based on benchmark test datasets for AO-01. Production environments require a real-time post-mortem feedback loop to verify incident boundary precision.
          </span>
        </div>
      </div>
    </div>
  );
};
