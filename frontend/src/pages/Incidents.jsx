import React, { useState, useEffect } from 'react';
import { useBackendStatus, fmtInt } from '../services/status';
import { useNavigate } from 'react-router-dom';
import {
  Flame,
  ShieldAlert,
  GitFork,
  ArrowRight,
  Clock,
  Layers,
  Sparkles,
  Server,
  Zap,
  TrendingUp,
  LayoutGrid,
  List
} from 'lucide-react';
import { incidentService } from '../services/incidentService';
import { SeverityBadge, StatusBadge, CorrelationTypeBadge } from '../components/common/Badge';
import { formatDateTime } from '../utils/formatters';

export const Incidents = () => {
  const { stats } = useBackendStatus();
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isCorrelating, setIsCorrelating] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'

  const loadIncidents = async () => {
    setLoading(true);
    try {
      const res = await incidentService.getIncidents({ severity: filterSeverity });
      setIncidents(res.data || []);
    } catch (err) {
      console.error('Failed to load incidents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, [filterSeverity]);

  const handleRunCorrelationEngine = async () => {
    setIsCorrelating(true);
    try {
      await incidentService.triggerDetection();
      await loadIncidents();
    } catch (err) {
      console.error('Correlation error', err);
    } finally {
      setIsCorrelating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <Flame className="w-6 h-6 text-red-500" />
            Incident Intelligence
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Correlated alert clusters grouped by service topology, temporal windows, and semantic signatures.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex items-center bg-[#151D2E] border border-[#293449] rounded-lg p-1 text-xs">
            <button
              onClick={() => setViewMode('cards')}
              className={`p-1.5 rounded flex items-center gap-1 transition-colors ${
                viewMode === 'cards' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
              title="Card Grid View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded flex items-center gap-1 transition-colors ${
                viewMode === 'table' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
              title="Table List View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Trigger Detection Button */}
          <button
            onClick={handleRunCorrelationEngine}
            disabled={isCorrelating}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-all shadow-md shadow-indigo-600/30 disabled:opacity-60"
          >
            <Zap className={`w-3.5 h-3.5 ${isCorrelating ? 'animate-spin' : 'text-yellow-300'}`} />
            <span>{isCorrelating ? 'Correlating Ingress...' : 'Run Correlation Engine'}</span>
          </button>
        </div>
      </div>

      {/* Intelligence Engine Status Pill Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-r from-[#151D2E] to-[#121A2B] border border-indigo-500/30 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <span className="font-semibold text-white block">
              Multi-Service Alert Compression Active
            </span>
            <span className="text-slate-400 text-[11px]">
              {stats ? `${fmtInt(stats.rawAlerts)} alerts → ${fmtInt(stats.surfaced)} surfaced cards (${fmtInt(stats.redOrange)} RED+ORANGE). Showing the top ${incidents?.length ?? 0} by priority.` : 'Backend unreachable: counts unavailable.'}
            </span>
          </div>
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-xs">Severity Filter:</span>
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-[#111827] border border-[#293449] text-xs text-white px-3 py-1.5 rounded-lg focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
          </select>
        </div>
      </div>

      {/* Main Content: Card View vs Table View */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-400">Loading correlated incidents...</div>
      ) : viewMode === 'cards' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {incidents.map((inc) => (
            <div
              key={inc.id}
              onClick={() => navigate(`/incidents/${inc.id}`)}
              className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] hover:border-indigo-500/60 transition-all duration-300 hover:shadow-2xl hover:shadow-indigo-500/10 cursor-pointer flex flex-col justify-between group relative overflow-hidden"
            >
              <div className="space-y-4">
                {/* Card Top: ID + Severity + Status */}
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                    {inc.id}
                  </span>
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={inc.severity} size="sm" />
                    <StatusBadge status={inc.status} size="sm" />
                  </div>
                </div>

                {/* Title */}
                <div>
                  <h3 className="text-base font-bold text-white group-hover:text-indigo-200 transition-colors">
                    {inc.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {inc.probableRootCause?.explanation || 'Multi-service cascade detected across upstream datastores and APIs.'}
                  </p>
                </div>

                {/* Probable Root Cause Pill */}
                <div className="p-3 rounded-xl bg-[#111827] border border-[#293449]">
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <span className="text-slate-400 font-semibold uppercase tracking-wider">
                      Probable Root Cause
                    </span>
                    <span className="font-mono text-indigo-400 font-bold">
                      origin score {inc.originScore ?? inc.confidenceScore}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
                    <Server className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    <span className="truncate">{inc.probableRootCauseService}</span>
                  </div>
                  <div className="mt-2">
                    <CorrelationTypeBadge isConfirmed={false} />
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-[#0B1020] border border-[#293449]">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Related Alerts</span>
                    <span className="text-sm font-mono font-bold text-white">{inc.relatedAlertsCount} alerts</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-[#0B1020] border border-[#293449]">
                    <span className="text-slate-400 block text-[10px] uppercase font-semibold">Noise Cut</span>
                    <span className="text-sm font-mono font-bold text-emerald-400">{inc.noiseReduction}</span>
                  </div>
                </div>

                {/* Affected Services Tags */}
                <div>
                  <span className="text-[11px] text-slate-400 block mb-1.5 font-medium">
                    Affected Services ({inc.affectedServices.length}):
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {inc.affectedServices.map((svc) => (
                      <span
                        key={svc}
                        className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                          svc === inc.probableRootCauseService
                            ? 'bg-red-500/15 text-red-300 border-red-500/30 font-bold'
                            : 'bg-[#111827] text-slate-300 border-[#293449]'
                        }`}
                      >
                        {svc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="mt-5 pt-4 border-t border-[#293449] flex items-center justify-between text-xs">
                <span className="text-slate-400 text-[11px] flex items-center gap-1 font-mono">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {formatDateTime(inc.firstDetected)}
                </span>
                <span className="inline-flex items-center gap-1 text-indigo-400 group-hover:text-indigo-300 font-semibold">
                  <span>Deep Dive</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table View */
        <div className="rounded-xl bg-[#151D2E] border border-[#293449] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#111827] text-slate-400 uppercase text-[11px] font-semibold border-b border-[#293449]">
                <tr>
                  <th className="py-3 px-4">Incident ID</th>
                  <th className="py-3 px-4">Incident Title</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Probable Root Cause</th>
                  <th className="py-3 px-4" title="Heuristic ranking score, not a probability">Origin score</th>
                  <th className="py-3 px-4">Related Alerts</th>
                  <th className="py-3 px-4">Affected Services</th>
                  <th className="py-3 px-4">Detected</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#293449]/60">
                {incidents.map((inc) => (
                  <tr
                    key={inc.id}
                    onClick={() => navigate(`/incidents/${inc.id}`)}
                    className="hover:bg-[#1E293B]/70 transition-colors cursor-pointer group"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-indigo-400 group-hover:text-indigo-300">
                      {inc.id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-white">
                      {inc.title}
                    </td>
                    <td className="py-3.5 px-4">
                      <SeverityBadge severity={inc.severity} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      <span className="bg-[#111827] px-2 py-0.5 rounded border border-[#293449]">
                        {inc.probableRootCauseService}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono font-bold text-indigo-400">
                      {inc.originScore ?? inc.confidenceScore}
                    </td>
                    <td className="py-3.5 px-4 font-mono font-semibold text-white">
                      {inc.relatedAlertsCount}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="text-slate-400">{inc.affectedServices.join(', ')}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                      {formatDateTime(inc.firstDetected)}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/incidents/${inc.id}`);
                        }}
                        className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline"
                      >
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
