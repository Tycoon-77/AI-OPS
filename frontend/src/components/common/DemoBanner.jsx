import React from 'react';
import { WifiOff } from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import { useBackendStatus } from '../../services/status';

// Shown only while the backend is unreachable and pages are rendering MOCK data.
export const DemoBanner = () => {
  const { live } = useBackendStatus();
  if (live !== false) return null;
  return (
    <div role="alert" className="bg-amber-950/80 border-b border-amber-500/50 px-4 py-2 text-xs flex flex-wrap items-center gap-3 text-amber-100">
      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-semibold tracking-wide uppercase text-[10px]">
        <WifiOff className="w-3 h-3" />
        Demo data (backend unreachable)
      </span>
      <span>
        Cannot reach <code className="text-sky-300">{API_BASE_URL}</code>. Numbers on screen come from built-in mock data, not from the pipeline.
      </span>
    </div>
  );
};
