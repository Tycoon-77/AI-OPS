import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#151D2E] border border-[#293449] p-3 rounded-lg shadow-xl text-xs">
        <div className="font-semibold text-white mb-1.5 flex items-center gap-2">
          <span>Window: {label}</span>
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4 text-indigo-400">
            <span>Raw Ingress Alerts:</span>
            <span className="font-mono font-bold text-white">{payload[0]?.value}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-emerald-400">
            <span>Correlated to Incidents:</span>
            <span className="font-mono font-bold text-white">{payload[1]?.value}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-amber-400">
            <span>Duplicate Suppressed:</span>
            <span className="font-mono font-bold text-white">{payload[2]?.value}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export const AlertVolumeChart = ({ data }) => {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366F1" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#6366F1" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="colorCorr" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.0} />
            </linearGradient>
            <linearGradient id="colorDup" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
          <XAxis dataKey="hour" stroke="#64748B" fontSize={11} tickLine={false} />
          <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="totalAlerts"
            stroke="#6366F1"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorTotal)"
            name="Raw Alerts"
          />
          <Area
            type="monotone"
            dataKey="correlated"
            stroke="#38BDF8"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorCorr)"
            name="Correlated"
          />
          <Area
            type="monotone"
            dataKey="duplicates"
            stroke="#F59E0B"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            fillOpacity={1}
            fill="url(#colorDup)"
            name="Duplicates"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
