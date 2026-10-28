import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Server,
  Activity,
  AlertTriangle,
  Flame,
  ArrowRight,
  Shield,
  Layers,
  ExternalLink,
  Users
} from 'lucide-react';
import { SeverityBadge, StatusBadge } from '../common/Badge';

export const ServiceDetailsDrawer = ({ service, onClose }) => {
  const navigate = useNavigate();

  if (!service) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#111827] border-l border-[#293449] shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-5 border-b border-[#293449] flex items-center justify-between bg-[#151D2E]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-mono font-bold">
            <Server className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white font-mono">{service.name}</h2>
            <span className="text-[11px] text-slate-400">{service.type}</span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B]"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 p-5 overflow-y-auto space-y-5 text-xs text-slate-300">
        {/* Health Status Banner */}
        <div
          className={`p-4 rounded-xl border ${
            service.status === 'CRITICAL'
              ? 'bg-red-500/10 border-red-500/30 text-red-200'
              : service.status === 'WARNING'
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-200'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-bold text-xs uppercase tracking-wider">
              Health Status: {service.status}
            </span>
            <span className="font-mono text-xs">Uptime: {service.uptime}</span>
          </div>
          <p className="text-xs text-slate-300">
            {service.healthReason || 'All health checks passing.'}
          </p>
        </div>

        {/* Live Metrics Grid */}
        <div>
          <span className="text-[11px] text-slate-400 uppercase font-semibold block mb-2">
            Service Telemetry & Performance
          </span>
          <div className="grid grid-cols-3 gap-2 text-center font-mono">
            <div className="p-3 bg-[#151D2E] rounded-lg border border-[#293449]">
              <span className="text-slate-400 text-[10px] block uppercase">p99 Latency</span>
              <span className="text-white font-bold text-sm">{service.latency}</span>
            </div>
            <div className="p-3 bg-[#151D2E] rounded-lg border border-[#293449]">
              <span className="text-slate-400 text-[10px] block uppercase">Throughput</span>
              <span className="text-white font-bold text-sm">{service.rps}</span>
            </div>
            <div className="p-3 bg-[#151D2E] rounded-lg border border-[#293449]">
              <span className="text-slate-400 text-[10px] block uppercase">Error Rate</span>
              <span
                className={`font-bold text-sm ${
                  parseFloat(service.errorRate) > 1 ? 'text-red-400' : 'text-emerald-400'
                }`}
              >
                {service.errorRate}
              </span>
            </div>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Active System Alerts ({service.activeAlerts})
            </span>
            <button
              onClick={() => {
                onClose();
                navigate(`/alerts?search=${service.id}`);
              }}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 underline font-medium"
            >
              Filter in Explorer →
            </button>
          </div>
          <p className="text-[11px] text-slate-400">
            Raw alarms originating from this service instance.
          </p>
        </div>

        {/* Associated Correlated Incidents */}
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449] space-y-2.5">
          <span className="text-xs font-semibold text-white flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-red-400" />
            Correlated Incidents ({service.associatedIncidents?.length || 0})
          </span>
          {service.associatedIncidents?.length > 0 ? (
            <div className="space-y-1.5">
              {service.associatedIncidents.map((incId) => (
                <div
                  key={incId}
                  onClick={() => {
                    onClose();
                    navigate(`/incidents/${incId}`);
                  }}
                  className="p-2.5 rounded-lg bg-[#111827] border border-[#293449] hover:border-indigo-500/60 cursor-pointer flex items-center justify-between text-xs transition-colors"
                >
                  <span className="font-mono font-bold text-indigo-400">{incId}</span>
                  <span className="text-slate-400 text-[11px] flex items-center gap-1">
                    <span>Investigate</span>
                    <ArrowRight className="w-3 h-3 text-indigo-400" />
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No active incidents associated.</p>
          )}
        </div>

        {/* Configured Topology Dependencies */}
        <div className="space-y-2">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">
            Direct Downstream Dependencies
          </span>
          {service.dependencies?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {service.dependencies.map((dep) => (
                <span
                  key={dep}
                  className="px-2.5 py-1 rounded bg-[#151D2E] border border-[#293449] font-mono text-[11px] text-slate-200"
                >
                  {dep}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-slate-400 italic">None (Leaf / Terminal Data Node)</span>
          )}
        </div>

        {/* Service Metadata & Maintainer */}
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449] text-[11px] space-y-2 text-slate-400">
          <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
            <Users className="w-3.5 h-3.5 text-indigo-400" />
            <span>Ownership: {service.maintainer}</span>
          </div>
          <p>{service.description}</p>
        </div>
      </div>
    </div>
  );
};
