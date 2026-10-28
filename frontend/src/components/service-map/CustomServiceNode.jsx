import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Server, Database, Shield, Radio, Cpu, HardDrive, Flame, AlertTriangle, Layers } from 'lucide-react';
import { mockServices } from '../../data/mockServices';

const getIcon = (type, tier) => {
  if (tier === 0 || type.includes('Database') || type.includes('Datastore') || type.includes('Storage')) return Database;
  if (type.includes('Cache')) return Cpu;
  if (type.includes('Queue') || type.includes('Broker')) return HardDrive;
  if (tier === 3 || type.includes('Gateway') || type.includes('Ingress') || type.includes('Frontend')) return Radio;
  if (tier === 1 || type.includes('Security') || type.includes('Auth') || type.includes('Identity')) return Shield;
  return Server;
};

export const CustomServiceNode = memo(({ data, selected }) => {
  const service = data.service ||
    (data.name && data.status ? data : null) ||
    mockServices.find((s) => s.id === (data.serviceId || data.id)) || {
      name: data.serviceId || data.name || data.id || 'service',
      type: data.type || 'Microservice',
      status: data.status || 'HEALTHY',
      tier: data.tier ?? 2,
      activeAlerts: data.activeAlerts || 0,
      latency: data.latency || '24ms',
      errorRate: data.errorRate || '0.0%'
    };

  const tier = service.tier ?? (data.tier ?? 2);
  const Icon = getIcon(service.type || '', tier);

  // Visual size & tier badge configuration
  const tierConfig = {
    0: {
      width: 'w-[280px]',
      tierBadge: 'bg-emerald-500/25 text-emerald-300 border-emerald-500/40',
      label: 'MAIN DATASTORE • TIER 0',
      bgGradient: 'bg-gradient-to-br from-[#0c2420] via-[#111c24] to-[#151D2E]',
      borderBase: 'border-emerald-500/60',
      accentText: 'text-emerald-400',
      roleDescription: 'Core Foundation Backbone',
    },
    3: {
      width: 'w-[250px]',
      tierBadge: 'bg-sky-500/25 text-sky-300 border-sky-500/40',
      label: 'ENTRY GATEWAY • TIER 3',
      bgGradient: 'bg-gradient-to-br from-[#0e1d38] via-[#121a2c] to-[#151D2E]',
      borderBase: 'border-sky-500/50',
      accentText: 'text-sky-400',
      roleDescription: 'User Traffic Entry Point',
    },
    1: {
      width: 'w-[235px]',
      tierBadge: 'bg-purple-500/25 text-purple-300 border-purple-500/40',
      label: 'PLATFORM CORE • TIER 1',
      bgGradient: 'bg-gradient-to-br from-[#1d1436] via-[#16182c] to-[#151D2E]',
      borderBase: 'border-purple-500/50',
      accentText: 'text-purple-400',
      roleDescription: 'Shared Platform Service',
    },
    2: {
      width: 'w-[220px]',
      tierBadge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      label: 'BUSINESS SERVICE • TIER 2',
      bgGradient: 'bg-[#151D2E]',
      borderBase: 'border-indigo-500/40',
      accentText: 'text-indigo-400',
      roleDescription: 'Dependent Business Microservice',
    }
  };

  const cfg = tierConfig[tier] || tierConfig[2];

  // Status badges & color schemes
  const statusColors = {
    CRITICAL: {
      border: 'border-red-500/90 shadow-red-500/25',
      badge: 'bg-red-500/25 text-red-300 border-red-500/50',
      dot: 'bg-red-500 animate-pulse',
      glow: 'shadow-[0_0_25px_rgba(239,68,68,0.3)]'
    },
    WARNING: {
      border: 'border-amber-500/80 shadow-amber-500/20',
      badge: 'bg-amber-500/25 text-amber-300 border-amber-500/50',
      dot: 'bg-amber-500',
      glow: 'shadow-[0_0_20px_rgba(245,158,11,0.25)]'
    },
    HEALTHY: {
      border: cfg.borderBase,
      badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      dot: 'bg-emerald-500',
      glow: 'shadow-[0_0_12px_rgba(34,197,94,0.12)]'
    }
  };

  const scheme = statusColors[service.status] || statusColors.HEALTHY;
  const isHighlighted = data.isHighlighted;
  const isRootCause = data.isRootCause;

  return (
    <div
      className={`relative ${cfg.width} rounded-xl ${cfg.bgGradient} border-2 transition-all duration-300 text-xs p-3.5 shadow-2xl select-none ${
        selected ? 'border-indigo-400 ring-2 ring-indigo-500/60 scale-105 z-30' : scheme.border
      } ${
        isRootCause
          ? 'ring-4 ring-red-500 shadow-[0_0_35px_rgba(239,68,68,0.5)] border-red-500 scale-105 z-30 animate-pulse-subtle'
          : isHighlighted
          ? `${scheme.glow} ring-2 ring-red-400/70 border-red-400`
          : ''
      }`}
    >
      {/* Handles on 4 sides for smooth clean connections */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-[#0B1020] hover:!bg-white"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-[#0B1020]"
      />

      {/* Top Banner: Tier & Architectural Role */}
      <div className="flex items-center justify-between gap-1.5 mb-2 pb-1.5 border-b border-[#293449]/60">
        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${cfg.tierBadge}`}>
          {cfg.label}
        </span>
        <div className={`px-1.5 py-0.5 rounded-full text-[9px] font-bold border flex items-center gap-1 shrink-0 ${scheme.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${scheme.dot}`} />
          {service.status}
        </div>
      </div>

      {/* Node Header: Service Icon, Name and Type */}
      <div className="flex items-center gap-2.5 mb-2.5">
        <div className={`w-8 h-8 rounded-lg bg-[#111827] border border-[#293449] flex items-center justify-center shrink-0 ${cfg.accentText}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="min-w-0 flex-1">
          <span className="font-bold text-white text-xs block leading-tight font-mono truncate" title={service.name}>
            {service.name}
          </span>
          <span className="text-[10px] text-slate-400 truncate block">
            {service.type || cfg.roleDescription}
          </span>
        </div>
      </div>

      {/* Live Performance & Telemetry Grid */}
      <div className="pt-2 border-t border-[#293449]/70 grid grid-cols-3 gap-1 text-[10px] font-mono text-center">
        <div className="bg-[#111827]/90 p-1.5 rounded border border-[#293449]/40">
          <span className="text-slate-400 block text-[9px] uppercase">Alerts</span>
          <span className={`font-bold ${service.activeAlerts > 0 ? 'text-red-400' : 'text-slate-300'}`}>
            {service.activeAlerts}
          </span>
        </div>
        <div className="bg-[#111827]/90 p-1.5 rounded border border-[#293449]/40">
          <span className="text-slate-400 block text-[9px] uppercase">p99 Lat</span>
          <span className="font-semibold text-slate-200 truncate">{service.latency}</span>
        </div>
        <div className="bg-[#111827]/90 p-1.5 rounded border border-[#293449]/40">
          <span className="text-slate-400 block text-[9px] uppercase">Errors</span>
          <span className={`font-semibold ${parseFloat(service.errorRate) > 1 ? 'text-red-400' : 'text-emerald-400'}`}>
            {service.errorRate}
          </span>
        </div>
      </div>

      {/* Root Cause or Affected Incident Banner */}
      {isRootCause && (
        <div className="mt-2 text-center py-1 px-1.5 bg-red-600/30 text-red-200 rounded-lg border border-red-500/70 font-bold text-[10px] flex items-center justify-center gap-1.5 animate-pulse shadow-md shadow-red-500/20">
          <Flame className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <span>🚨 ROOT CAUSE ORIGIN</span>
        </div>
      )}
      {!isRootCause && isHighlighted && (
        <div className="mt-2 text-center py-0.5 px-1 bg-amber-500/20 text-amber-200 rounded border border-amber-500/50 font-medium text-[9px] flex items-center justify-center gap-1">
          <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
          <span>Cascading Impact</span>
        </div>
      )}

      {/* Source Handles */}
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-[#0B1020] hover:!bg-white"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="!w-2.5 !h-2.5 !bg-indigo-400 !border-2 !border-[#0B1020]"
      />
    </div>
  );
});