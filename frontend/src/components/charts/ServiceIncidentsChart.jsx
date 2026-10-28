import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#151D2E] border border-[#293449] p-3 rounded-lg shadow-xl text-xs">
        <div className="font-semibold text-white mb-1.5">{label}</div>
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4 text-red-400">
            <span>Critical Alerts:</span>
            <span className="font-mono font-bold text-white">{payload[0]?.value}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-amber-400">
            <span>Warning Alerts:</span>
            <span className="font-mono font-bold text-white">{payload[1]?.value}</span>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export const ServiceIncidentsChart = ({ data }) => {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" horizontal={false} />
          <XAxis type="number" stroke="#64748B" fontSize={11} tickLine={false} />
          <YAxis
            type="category"
            dataKey="service"
            stroke="#94A3B8"
            fontSize={11}
            tickLine={false}
            width={110}
            tickFormatter={(val) => (val.length > 13 ? `${val.slice(0, 12)}…` : val)}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="critical" name="Critical" fill="#EF4444" radius={[0, 4, 4, 0]} stackId="a" />
          <Bar dataKey="warning" name="Warning" fill="#F59E0B" radius={[0, 4, 4, 0]} stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
