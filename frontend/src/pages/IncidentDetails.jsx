import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  GitFork,
  Clock,
  Server,
  Layers,
  ChevronRight,
  ShieldCheck,
  ArrowRight
} from 'lucide-react';
import { incidentService } from '../services/incidentService';
import { alertService } from '../services/alertService';
import { SeverityBadge, StatusBadge, CorrelationTypeBadge } from '../components/common/Badge';
import { AlertDetailDrawer } from '../components/alerts/AlertDetailDrawer';
import { formatDateTime } from '../utils/formatters';

export const IncidentDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [incident, setIncident] = useState(null);
  const [relatedAlerts, setRelatedAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'alerts' | 'correlation' | 'timeline'

  useEffect(() => {
    let isCancelled = false;
    const fetchIncident = async () => {
      setLoading(true);
      try {
        const incRes = await incidentService.getIncidentById(id || 'INC-001');
        if (!isCancelled) {
          setIncident(incRes.data);
        }

        // Fetch related alerts for this incident
        const alertsRes = await alertService.getAlerts({ limit: 100 });
        if (!isCancelled && alertsRes.data?.alerts) {
          const matched = alertsRes.data.alerts.filter(
            (a) => a.incidentId?.toLowerCase() === (id || 'INC-001').toLowerCase()
          );
          setRelatedAlerts(matched);
        }
      } catch (err) {
        console.error('Failed to load incident detail', err);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };
    fetchIncident();
    return () => {
      isCancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center text-xs text-slate-400">
        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping inline-block mr-2" />
        Loading incident intelligence...
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-12 text-center text-slate-300">
        <h2 className="text-lg font-bold mb-2">Incident not found</h2>
        <button
          onClick={() => navigate('/incidents')}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs cursor-pointer"
        >
          Return to Incidents
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/incidents')}
            className="p-2 rounded-lg bg-[#151D2E] hover:bg-[#1E293B] text-slate-300 hover:text-white border border-[#293449] transition-colors cursor-pointer"
            title="Back to Incidents"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-indigo-400 text-lg">
                {incident.id}
              </span>
              <SeverityBadge severity={incident.severity} size="sm" />
              <StatusBadge status={incident.status} size="sm" />
            </div>
            <h1 className="text-xl font-extrabold text-white mt-0.5">
              {incident.title}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/root-cause?incident=${incident.id}`)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-indigo-600/30 cursor-pointer"
          >
            <GitFork className="w-4 h-4" />
            <span>Root Cause Topology</span>
          </button>
          <button
            onClick={() => navigate('/service-map')}
            className="flex items-center gap-2 px-3 py-2 bg-[#151D2E] hover:bg-[#1E293B] text-slate-300 hover:text-white rounded-lg text-xs font-medium border border-[#293449] transition-colors cursor-pointer"
          >
            <Server className="w-4 h-4 text-sky-400" />
            <span>Service Map</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-[#293449] text-xs font-semibold pb-1 overflow-x-auto">
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-4 py-2 rounded-t-lg transition-colors border-b-2 cursor-pointer ${
            activeTab === 'summary'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Incident Summary & RCA
        </button>
        <button
          onClick={() => setActiveTab('correlation')}
          className={`px-4 py-2 rounded-t-lg transition-colors border-b-2 cursor-pointer ${
            activeTab === 'correlation'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Correlation Rationale
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 rounded-t-lg transition-colors border-b-2 flex items-center gap-1.5 cursor-pointer ${
            activeTab === 'alerts'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>Correlated Alerts</span>
          <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">
            {incident.relatedAlertsCount}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2 rounded-t-lg transition-colors border-b-2 cursor-pointer ${
            activeTab === 'timeline'
              ? 'border-indigo-500 text-white bg-[#151D2E]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Propagation Timeline
        </button>
      </div>

      {/* Tab 1: Incident Summary & Probable Root Cause */}
      {activeTab === 'summary' && (
        <div className="space-y-6">
          {/* Probable Root Cause Hero Banner */}
          <div className="p-6 rounded-2xl bg-gradient-to-r from-[#181C30] via-[#151D2E] to-[#121A2B] border border-indigo-500/40 relative overflow-hidden shadow-xl">
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
              <div className="space-y-3 max-w-3xl">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <CorrelationTypeBadge isConfirmed={false} />
                  <span className="text-xs text-slate-400">
                    Confidence Score:{' '}
                    <strong className="text-indigo-400 font-mono text-sm">{incident.confidenceScore}%</strong>
                  </span>
                  <span className="text-[11px] text-amber-400/90 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    Important: Probable conclusion, not guaranteed certainty
                  </span>
                </div>

                <div>
                  <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold block">
                    Suspected Root Cause Service
                  </span>
                  <div className="text-xl sm:text-2xl font-mono font-bold text-white mt-1 flex items-center gap-2">
                    <Server className="w-5 h-5 text-indigo-400" />
                    <span>{incident.probableRootCauseService}</span>
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed">
                  {incident.probableRootCause?.explanation}
                </p>

                <div className="text-xs text-slate-400 flex items-center gap-4 pt-1">
                  <span>
                    Suspected Origin: <strong className="text-slate-200">{incident.probableRootCause?.suspectedOrigin || 'Primary Node'}</strong>
                  </span>
                  <span>•</span>
                  <span>
                    Failure Vector: <strong className="text-slate-200">{incident.suspectedCauseType}</strong>
                  </span>
                </div>
              </div>

              {/* Quick KPI stats */}
              <div className="grid grid-cols-2 lg:grid-cols-1 gap-3 shrink-0 min-w-[200px]">
                <div className="p-3 rounded-xl bg-[#0B1020] border border-[#293449]">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Correlated Alerts</span>
                  <span className="text-xl font-bold font-mono text-white">{incident.relatedAlertsCount}</span>
                  <span className="text-[10px] text-emerald-400 block mt-0.5">Noise Cut: {incident.noiseReduction}</span>
                </div>
                <div className="p-3 rounded-xl bg-[#0B1020] border border-[#293449]">
                  <span className="text-[10px] text-slate-400 uppercase font-semibold block">Affected Services</span>
                  <span className="text-xl font-bold font-mono text-sky-400">{incident.affectedServices.length}</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">Cascaded downstream</span>
                </div>
              </div>
            </div>
          </div>

          {/* Evidence Supporting Conclusion (Confirmed vs Probable) */}
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Evidence Supporting Root Cause Hypothesis
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Mathematical proof and metric breaches analyzed by the SignalIQ correlation graph.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {incident.probableRootCause?.evidence?.map((item) => (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border ${
                    item.isFact
                      ? 'bg-emerald-950/20 border-emerald-500/30'
                      : 'bg-indigo-950/20 border-indigo-500/30'
                  } space-y-2`}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        item.isFact
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                      }`}
                    >
                      {item.isFact ? 'CONFIRMED EVIDENCE' : 'PROBABLE CORRELATION'}
                    </span>
                    <span className="text-xs font-mono font-semibold text-slate-300">
                      Confidence: {item.confidence}%
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                  <p className="text-xs text-slate-300 leading-relaxed">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Visual Dependency Chain */}
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-white tracking-wide">
                  Service Failure Propagation Chain
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Trace from suspected root cause service to affected downstream consumers
                </p>
              </div>
              <button
                onClick={() => navigate(`/root-cause?incident=${incident.id}`)}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <span>Interactive View</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3 p-4 bg-[#0B1020] rounded-xl border border-[#293449]">
              {incident.dependencyChain?.map((node, idx) => (
                <React.Fragment key={node.id}>
                  <div
                    className={`p-3 rounded-xl border text-xs min-w-[170px] ${
                      node.role === 'ROOT_CAUSE'
                        ? 'bg-red-500/15 border-red-500/40 text-white'
                        : 'bg-[#151D2E] border-[#293449] text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                        {node.role === 'ROOT_CAUSE' ? 'Root Cause (Probable)' : 'Downstream'}
                      </span>
                      <span
                        className={`w-2 h-2 rounded-full ${
                          node.status === 'CRITICAL' ? 'bg-red-500' : 'bg-amber-500'
                        }`}
                      />
                    </div>
                    <div className="font-mono font-bold text-sm text-white">{node.name}</div>
                    <div className="text-[11px] text-slate-400 mt-1 font-mono">{node.id}</div>
                  </div>

                  {idx < incident.dependencyChain.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-slate-500 shrink-0" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Correlation Explanation */}
      {activeTab === 'correlation' && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Why Were These Alerts Correlated?
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                SignalIQ evaluated four distinct intelligence axes to group this incident with {incident.confidenceScore}% confidence.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {/* 1. Time Proximity */}
              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center gap-2 text-indigo-400 font-semibold text-sm">
                  <Clock className="w-4 h-4" />
                  <span>1. Time Proximity Envelope</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  {incident.correlationExplanation.timeProximity}
                </p>
                <div className="text-[11px] text-slate-400 pt-1 font-mono">
                  Calculated Window: 4 minutes • Burst Kurtosis: 8.42
                </div>
              </div>

              {/* 2. Service Dependency */}
              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center gap-2 text-sky-400 font-semibold text-sm">
                  <Server className="w-4 h-4" />
                  <span>2. Service Dependency Topology</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  {incident.correlationExplanation.serviceDependency}
                </p>
                <div className="text-[11px] text-slate-400 pt-1 font-mono">
                  Hop Distance: 1-2 hops • Edge Weight: Synchronous RPC
                </div>
              </div>

              {/* 3. Similar Alert Messages */}
              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
                  <Layers className="w-4 h-4" />
                  <span>3. Semantic Alert Message Clustering</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  {incident.correlationExplanation.similarMessages}
                </p>
                <div className="text-[11px] text-slate-400 pt-1 font-mono">
                  Embedding Cosine Distance: 0.94 • Top Keywords: connection, timeout, pool
                </div>
              </div>

              {/* 4. Historical Association */}
              <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                  <ShieldCheck className="w-4 h-4" />
                  <span>4. Historical Incident Fingerprint</span>
                </div>
                <p className="text-slate-300 leading-relaxed">
                  {incident.correlationExplanation.historicalAssociation}
                </p>
                <div className="text-[11px] text-slate-400 pt-1 font-mono">
                  Fingerprint Match: FP-DB-CONN-04 (Confidence 91%)
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Correlated Alerts Chronological Table */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Related Alerts ({incident.relatedAlertsCount} alerts)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Sorted in chronological order showing the sequence of alerts that formed this incident.
              </p>
            </div>
            <button
              onClick={() => navigate(`/alerts?search=${incident.id}`)}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium underline cursor-pointer"
            >
              Filter in Alert Explorer →
            </button>
          </div>

          <div className="rounded-xl bg-[#151D2E] border border-[#293449] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#111827] text-slate-400 uppercase text-[11px] font-semibold border-b border-[#293449]">
                  <tr>
                    <th className="py-3 px-4">Alert ID</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Service</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Collector Source</th>
                    <th className="py-3 px-4 min-w-[280px]">Alert Message</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#293449]/60">
                  {relatedAlerts.map((alert) => (
                    <tr
                      key={alert.id}
                      onClick={() => setSelectedAlert(alert)}
                      className="hover:bg-[#1E293B]/70 transition-colors cursor-pointer group"
                    >
                      <td className="py-3 px-4 font-mono font-semibold text-indigo-400">
                        {alert.id}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-mono text-[11px] whitespace-nowrap">
                        {formatDateTime(alert.timestamp)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono text-slate-300 bg-[#111827] px-2 py-0.5 rounded border border-[#293449]">
                          {alert.service}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <SeverityBadge severity={alert.severity} size="sm" />
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {alert.source}
                      </td>
                      <td className="py-3 px-4 text-slate-200 font-mono text-[11px]">
                        <div className="line-clamp-1">{alert.message}</div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAlert(alert);
                          }}
                          className="text-xs text-indigo-400 hover:text-indigo-300 underline font-medium cursor-pointer"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Propagation Timeline */}
      {activeTab === 'timeline' && (
        <div className="p-6 rounded-2xl bg-[#151D2E] border border-[#293449] space-y-4">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">
              Failure Cascade Timeline
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Exact temporal progression from initial symptom to multi-service failure
            </p>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#293449]">
            {incident.timeline?.map((step, idx) => (
              <div key={idx} className="relative group">
                <span
                  className={`absolute -left-6 top-1 w-3 h-3 rounded-full border-2 border-[#151D2E] ${
                    step.type === 'ROOT_CAUSE_EVENT'
                      ? 'bg-red-500'
                      : step.type === 'INTELLIGENCE'
                      ? 'bg-indigo-400 animate-ping'
                      : 'bg-amber-400'
                  }`}
                />
                <div className="p-4 rounded-xl bg-[#111827] border border-[#293449] space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-indigo-400 font-semibold">{step.time}</span>
                    <span className="text-[10px] uppercase font-bold text-slate-400 bg-[#0B1020] px-2 py-0.5 rounded">
                      {step.type}
                    </span>
                  </div>
                  <p className="text-xs text-white font-medium">{step.event}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected Alert Drawer */}
      {selectedAlert && (
        <AlertDetailDrawer
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}
    </div>
  );
};
