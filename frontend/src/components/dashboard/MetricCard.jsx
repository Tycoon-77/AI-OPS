import React from 'react';
import { Sparkles } from 'lucide-react';

export const MetricCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'indigo',
  isDemo = false
}) => {
  const colorMap = {
    indigo: {
      border: 'border-indigo-500/30 hover:border-indigo-500/60',
      bg: 'bg-indigo-500/10 text-indigo-400',
      glow: 'hover:shadow-indigo-500/10'
    },
    emerald: {
      border: 'border-emerald-500/30 hover:border-emerald-500/60',
      bg: 'bg-emerald-500/10 text-emerald-400',
      glow: 'hover:shadow-emerald-500/10'
    },
    red: {
      border: 'border-red-500/30 hover:border-red-500/60',
      bg: 'bg-red-500/10 text-red-400',
      glow: 'hover:shadow-red-500/10'
    },
    amber: {
      border: 'border-amber-500/30 hover:border-amber-500/60',
      bg: 'bg-amber-500/10 text-amber-400',
      glow: 'hover:shadow-amber-500/10'
    },
    sky: {
      border: 'border-sky-500/30 hover:border-sky-500/60',
      bg: 'bg-sky-500/10 text-sky-400',
      glow: 'hover:shadow-sky-500/10'
    }
  };

  const scheme = colorMap[color] || colorMap.indigo;

  return (
    <div
      className={`p-5 rounded-xl bg-[#151D2E] border ${scheme.border} transition-all duration-300 hover:shadow-lg ${scheme.glow} relative flex flex-col justify-between`}
    >
      <div>
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-10 h-10 rounded-lg ${scheme.bg} flex items-center justify-center`}>
            {Icon && <Icon className="w-5 h-5" />}
          </div>
          <span className="text-xs font-semibold text-slate-300 tracking-wide uppercase">
            {title}
          </span>
        </div>

        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono tracking-tight">
            {value}
          </span>
          {trend && (
            <span className="text-xs font-semibold text-emerald-400 font-mono">
              {trend}
            </span>
          )}
        </div>
      </div>

      {subtitle && (
        <p className="text-xs text-slate-400 mt-3 pt-2.5 border-t border-[#293449]/60">
          {subtitle}
        </p>
      )}
    </div>
  );
};
