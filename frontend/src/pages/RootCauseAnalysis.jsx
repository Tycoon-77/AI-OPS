import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  GitFork,
  Server,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Sparkles,
  Layers,
  ChevronRight,
  ExternalLink,
  Flame,
  CheckCircle2,
  Database
} from 'lucide-react';
import { incidentService } from '../services/incidentService';
import { SeverityBadge, CorrelationTypeBadge } from '../components/common/Badge';

export const RootCauseAnalysis = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const incidentQuery = searchParams.get('incident') || 'INC-001';

  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchIncidents = async () => {
      setLoading(true);
      try {
        const res = await incidentService.getIncidents();
        const list = res.data || [];
        setIncidents(list);
        const match = list.find((i) => i.id.toLowerCase() === incidentQuery.toLowerCase()) || list[0];
        setSelectedIncident(match);
      } catch (err) {
        console.error('Failed to load RCA data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchIncidents();
  }, [incidentQuery]);

  const handleSelectIncident = (incId) => {
    setSearchParams({ incident: incId });
  };

  if (loading || !selectedIncident) {
    return (
      <div className="p-16 text-center text-xs text-slate-400">
        Loading Root Cause Analysis workspace...
      </div>
    );
  }

  const { probableRootCause, dependencyChain, timeline, correlationExplanation } = selectedIncident;

  return (
    <div className="space-y-6">
      {/* Page Title & Incident Selector */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <GitFork className="w-6 h-6 text-indigo-400" />
            Root Cause Analysis (RCA)
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Understand the likely origin and cascading propagation of system incidents across service boundaries.
          </p>
        </div>

        {/* Incident Selector Tabs */}
        <div className="flex items-center gap-2 bg-[#151D2E] border border-[#293449] p-1.5 rounded-xl text-xs overflow-x-auto">
          {incidents.map((inc) => (
            <button
              key={inc.id}
              onClick={() => handleSelectIncident(inc.id)}
              className={`px-3 py-1.5 rounded-lg font-mono font-semibold transition-all flex items-center gap-2 whitespace-nowrap ${
                selectedIncident.id === inc.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-white hover:bg-[#1E293B]'
              }`}
            >
              <span>{inc.id}</span>
              <span className={`w-1.5 h-1.5 rounded-full ${inc.severity === 'CRITICAL' ? 'bg-red-400' : 'bg-amber-400'}`} />
            </button>
          ))}
        </div>
      </div>

      {/* Hero: Active RCA Hypothesis Card */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-[#181D33] via-[#151D2E] to-[#111827] border border-indigo-500/40 relative shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="font-mono text-sm font-bold text-indigo-400">{selectedIncident.id}</span>
              <span className="text-white font-bold text-base">• {selectedIncident.title}</span>
              <SeverityBadge severity={selectedIncident.severity} size="sm" />
              <CorrelationTypeBadge isConfirmed={false} />
            </div>

            <p className="text-sm text-slate-200 leading-relaxed">
              {probableRootCause?.explanation}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
              <span>
                Suspected Origin:{' '}
                <strong className="text-white font-mono">{probableRootCause?.suspectedOrigin}</strong>
              </span>
              <span>•</span>
              <span>
                Failure Vector: <strong className="text-slate-200">{selectedIncident.suspectedCauseType}</strong>
              </span>
              <span>•</span>
              <span>
                Correlated: <strong className="text-indigo-400 font-mono">{selectedIncident.relatedAlertsCount} alerts</strong>
              </span>
            </div>
          </div>

          {/* Confidence Meter Box */}
          <div className="p-4 rounded-xl bg-[#0B1020] border border-[#293449] min-w-[200px] text-center space-y-1">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold block">
              Origin score (heuristic, not a probability)
            </span>
            <div className="text-3xl font-extrabold font-mono text-indigo-400">
              {selectedIncident.confidenceScore}%
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1">
              <div
                className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${selectedIncident.confidenceScore}%` }}
              />
            </div>
            <span className="text-[10px] text-emerald-400 block pt-1">
              Topology & Signal Validated
            </span>
          </div>
        </div>
      </div>

      {/* 1. Visual Dependency Propagation Chain */}
      <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
              <Server className="w-4 h-4 text-indigo-400" />
              Visual Root Cause Dependency Chain
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Directional propagation flow from suspected root cause service to impacted downstream dependencies.
            </p>
          </div>
          <button
            onClick={() => navigate('/service-map')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
          >
            <span>Full Service Map</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Chain Visual Flow */}
        <div className="p-5 bg-[#0B1020] rounded-xl border border-[#293449] overflow-x-auto">
          <div className="flex items-center gap-3 min-w-[700px]">
            {dependencyChain?.map((item, idx) => {
              const isRoot = item.role === 'ROOT_CAUSE';
              return (
                <React.Fragment key={item.id}>
                  <div
                    className={`flex-1 p-4 rounded-xl border relative transition-all ${
                      isRoot
                        ? 'bg-gradient-to-b from-red-950/40 to-[#151D2E] border-red-500/60 ring-2 ring-red-500/20'
                        : 'bg-[#151D2E] border-[#293449]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${
                          isRoot
                            ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {isRoot ? 'Probable Source' : `Downstream Hop #${idx}`}
                      </span>
                      <span
                        className={`w-2 h-2 rounded-full ${
                          item.status === 'CRITICAL' ? 'bg-red-500 animate-pulse' : 'bg-amber-400'
                        }`}
                      />
                    </div>

                    <div className="font-mono text-sm font-bold text-white mb-1">
                      {item.name}
                    </div>
                    <div className="text-[11px] font-mono text-indigo-300">
                      {item.id}
                    </div>

                    <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">
                      {isRoot
                        ? 'Resource contention / pool saturation origin.'
                        : 'Cascaded timeouts caused by upstream unavailability.'}
                    </p>
                  </div>

                  {idx < dependencyChain.length - 1 && (
                    <div className="flex flex-col items-center justify-center px-1 text-slate-500">
                      <ArrowRight className="w-5 h-5 text-indigo-400 shrink-0" />
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 mt-1 font-mono">
                        Cascade
                      </span>
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-400 pt-1">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-red-500/30 border border-red-500" />
            <span>Suspected Root Cause (Probable Conclusion)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#151D2E] border border-[#293449]" />
            <span>Downstream Affected Service</span>
          </div>
        </div>
      </div>

      {/* 2-Column Section: Evidence & Temporal Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evidence Supporting Root Cause */}
        <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Evidence Supporting Suspected Cause
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Verified metric anomalies vs inferred correlation linkages
            </p>
          </div>

          <div className="space-y-3">
            {probableRootCause?.evidence?.map((item) => (
              <div
                key={item.id}
                className="p-3.5 rounded-xl bg-[#111827] border border-[#293449] space-y-1.5"
              >
                <div className="flex items-center justify-between text-xs">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                      item.isFact
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    }`}
                  >
                    {item.isFact ? 'Confirmed Metric Telemetry' : 'Probable Inferred Link'}
                  </span>
                  <span className="text-slate-400 font-mono text-[11px]">
                    Confidence: <strong className="text-white">{item.confidence}%</strong>
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-white">{item.title}</h4>
                <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Timeline of Events */}
        <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
              <Clock className="w-4 h-4 text-sky-400" />
              Chronological Propagation Timeline
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Sequence of events leading up to alert saturation
            </p>
          </div>

          <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#293449]">
            {timeline?.map((step, idx) => (
              <div key={idx} className="relative">
                <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-indigo-400 ring-4 ring-[#151D2E]" />
                <div className="p-3 bg-[#111827] rounded-lg border border-[#293449] text-xs">
                  <div className="flex items-center justify-between text-[11px] font-mono text-indigo-300 mb-0.5">
                    <span>{step.time}</span>
                    <span className="text-slate-400 font-sans">{step.type}</span>
                  </div>
                  <p className="text-slate-200">{step.event}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Explanation of the Correlation Process */}
      <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
        <div>
          <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            Correlation Process Architecture
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            How SignalIQ distilled alerts down to this incident without loss of information
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="p-3.5 rounded-xl bg-[#111827] border border-[#293449] space-y-1">
            <span className="text-indigo-400 font-semibold block">Step 1: Ingestion & Fingerprint</span>
            <p className="text-slate-300">
              Raw telemetry ingested via CSV/JSON API and normalized into standardized event tokens.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-[#111827] border border-[#293449] space-y-1">
            <span className="text-indigo-400 font-semibold block">Step 2: Deduplication Engine</span>
            <p className="text-slate-300">
              Identical alert hashes suppressed with occurrence counters while keeping telemetry intact.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-[#111827] border border-[#293449] space-y-1">
            <span className="text-indigo-400 font-semibold block">Step 3: Graph Topology Clustering</span>
            <p className="text-slate-300">
              Alerts mapped onto upstream/downstream dependency graph edges using time proximity.
            </p>
          </div>
          <div className="p-3.5 rounded-xl bg-[#111827] border border-[#293449] space-y-1">
            <span className="text-indigo-400 font-semibold block">Step 4: Probable RCA Hypothesis</span>
            <p className="text-slate-300">
              Topological source nodes evaluated against metric anomalies to calculate root cause confidence.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
