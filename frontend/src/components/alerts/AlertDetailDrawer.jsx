import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Clock,
  Server,
  Layers,
  Flame,
  ShieldAlert,
  Terminal,
  ExternalLink,
  Copy,
  Check
} from 'lucide-react';
import { SeverityBadge, CorrelationTypeBadge } from '../common/Badge';
import { formatDateTime } from '../../utils/formatters';

export const AlertDetailDrawer = ({ alert, onClose, onSelectAlert }) => {
  const navigate = useNavigate();
  const [copied, setCopied] = React.useState(false);

  if (!alert) return null;

  const handleCopyRaw = () => {
    navigator.clipboard.writeText(JSON.stringify(alert, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[#111827] border-l border-[#293449] shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="p-5 border-b border-[#293449] flex items-center justify-between bg-[#151D2E]">
        <div className="flex items-center gap-3">
          <div className="font-mono text-base font-bold text-indigo-400">
            {alert.id}
          </div>
          <SeverityBadge severity={alert.severity} size="sm" />
          {alert.isDuplicate && (
            <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
              Duplicate ({alert.duplicateCount}x)
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-[#1E293B] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 p-5 overflow-y-auto space-y-5 text-xs text-slate-300">
        {/* Preserved Telemetry Notice */}
        <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-indigo-200">
          <span className="font-semibold block mb-0.5">Original Alert Telemetry Preserved:</span>
          SignalIQ does not alter or suppress raw telemetry. Downstream services and historical records retain unmodified source attributes.
        </div>

        {/* Message Banner */}
        <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449]">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold block mb-1">
            Full Alert Message
          </span>
          <p className="text-sm font-medium text-white font-mono break-words leading-relaxed">
            {alert.message}
          </p>
        </div>

        {/* Core Attributes Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449]">
            <span className="text-slate-400 block mb-1 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-indigo-400" />
              Service Name
            </span>
            <span className="text-white font-mono font-semibold">{alert.service}</span>
          </div>

          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449]">
            <span className="text-slate-400 block mb-1 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-sky-400" />
              Timestamp
            </span>
            <span className="text-white font-mono">{formatDateTime(alert.timestamp)}</span>
          </div>

          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449]">
            <span className="text-slate-400 block mb-1">Alert Source / Collector</span>
            <span className="text-white font-semibold">{alert.source}</span>
          </div>

          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449]">
            <span className="text-slate-400 block mb-1">Correlation Status</span>
            <span
              className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                alert.correlationStatus === 'CORRELATED'
                  ? 'bg-indigo-500/20 text-indigo-300'
                  : alert.correlationStatus === 'DUPLICATE'
                  ? 'bg-amber-500/20 text-amber-300'
                  : 'bg-slate-700 text-slate-300'
              }`}
            >
              {alert.correlationStatus}
            </span>
          </div>
        </div>

        {/* Incident Relationship Card */}
        {alert.incidentId ? (
          <div className="p-4 rounded-xl bg-gradient-to-r from-red-950/20 to-indigo-950/30 border border-indigo-500/40">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-red-400" />
                Associated Incident: <span className="font-mono text-indigo-400">{alert.incidentId}</span>
              </span>
              <button
                onClick={() => {
                  onClose();
                  navigate(`/incidents/${alert.incidentId}`);
                }}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 underline"
              >
                <span>Open Incident</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
            <p className="text-xs text-slate-300 font-medium">
              {alert.incidentTitle || 'Correlated Multi-Service Incident'}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              This alert is one of the correlated signals grouped by the SignalIQ temporal and topology engine.
            </p>
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449] text-slate-400">
            <span className="font-semibold block text-slate-300">Uncorrelated Alert:</span>
            No incident pattern crossed the correlation threshold for this alert. Retained as standalone signal.
          </div>
        )}

        {/* Environmental Metadata */}
        <div className="space-y-2">
          <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold block">
            Target Host & Cluster Environment
          </span>
          <div className="p-3 rounded-lg bg-[#151D2E] border border-[#293449] font-mono text-[11px] space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">Host Pod:</span>
              <span className="text-white">{alert.host || 'worker-pod-01'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Environment:</span>
              <span className="text-emerald-400">{alert.environment || 'production'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Region:</span>
              <span className="text-white">{alert.region || 'us-east-1'}</span>
            </div>
          </div>
        </div>

        {/* Raw Payload Inspector */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-indigo-400" />
              Raw Telemetry JSON
            </span>
            <button
              onClick={handleCopyRaw}
              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-[#151D2E] border border-[#293449]"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy JSON</span>
                </>
              )}
            </button>
          </div>
          <pre className="p-3 bg-[#0B1020] border border-[#293449] rounded-lg text-[11px] font-mono text-slate-300 overflow-x-auto max-h-48 leading-relaxed">
            {JSON.stringify(alert.rawPayload || alert, null, 2)}
          </pre>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-[#293449] bg-[#151D2E] flex justify-between items-center text-xs">
        <span className="text-slate-400">
          Source Engine: <span className="text-slate-300">{alert.source}</span>
        </span>
        <button
          onClick={onClose}
          className="px-4 py-1.5 bg-[#1E293B] hover:bg-slate-700 text-white rounded-lg transition-colors font-medium"
        >
          Close Drawer
        </button>
      </div>
    </div>
  );
};
