import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const item = payload[0];
    return (
      <div className="bg-[#151D2E] border border-[#293449] p-2.5 rounded-lg shadow-xl text-xs">
        <div className="font-semibold text-white flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.payload.color }} />
          <span>{item.name} Severity</span>
        </div>
        <div className="text-slate-300 mt-1 font-mono">
          {item.value} alerts ({((item.value / 400) * 100).toFixed(1)}%)
        </div>
      </div>
    );
  }
  return null;
};

export const SeverityDonutChart = ({ data }) => {
  const total = data.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div className="h-64 w-full flex flex-col items-center justify-center relative">
      <ResponsiveContainer width="100%" height="80%">
        <PieChart>
          <Tooltip content={<CustomTooltip />} />
          <Pie
            data={data}
            innerRadius={55}
            outerRadius={80}
            paddingAngle={4}
            dataKey="value"
            stroke="#151D2E"
            strokeWidth={3}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      {/* Central Metric overlay */}
      <div className="absolute top-[40%] -translate-y-1/2 flex flex-col items-center pointer-events-none">
        <span className="text-2xl font-bold font-mono text-white">{total}</span>
        <span className="text-[10px] text-slate-400 uppercase tracking-wider">Total Alerts</span>
      </div>

      {/* Sleek Legend */}
      <div className="flex items-center justify-center gap-4 text-xs mt-1">
        {data.map((item) => (
          <div key={item.name} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="text-slate-300 font-medium">{item.name}</span>
            <span className="text-slate-400 font-mono text-[11px]">({item.value})</span>
          </div>
        ))}
      </div>
    </div>
  );
};
