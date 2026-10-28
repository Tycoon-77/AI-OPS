import React, { useState } from 'react';
import { Database, Activity, Sparkles, X, Wifi } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';

export const DemoBanner = () => {
  const [dismissed, setDismissed] = useState(true);

  if (dismissed) return null;

  return (
    <div className="bg-gradient-to-r from-indigo-950/80 via-slate-900/90 to-sky-950/80 border-b border-indigo-500/30 px-4 py-2 text-xs flex flex-wrap items-center justify-between gap-3 text-slate-300">
      <div className="flex items-center gap-2.5 flex-wrap">
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 font-semibold tracking-wide uppercase text-[10px]">
          <Sparkles className="w-3 h-3 text-indigo-400" />
          AO-01 Benchmark Active
        </span>
        <span className="text-slate-200 font-medium">
          Demonstration Dataset: <strong className="text-white">400 alerts</strong> correlated into <strong className="text-indigo-300">3 incidents</strong> (93.75% noise reduction).
        </span>
        <span className="hidden md:inline-flex items-center gap-1 text-slate-400 border-l border-slate-700/60 pl-2.5">
          <Wifi className="w-3 h-3 text-emerald-400" />
          Backend Gateway: <code className="text-sky-300 ml-1">{API_BASE_URL}</code> (FastAPI Autodetect / Mock Fallback)
        </span>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        <span className="text-[11px] text-slate-400 hidden sm:inline">
          Original alert data is strictly preserved.
        </span>
        <button
          onClick={() => setDismissed(true)}
          className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800/60 transition-colors"
          title="Dismiss notification"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
