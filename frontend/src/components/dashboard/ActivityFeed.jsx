import React, { useEffect, useState } from 'react';
import { AlertCircle, Clock } from 'lucide-react';
import apiClient from '../../services/api';
import { useBackendStatus } from '../../services/status';

// Built from real surfaced incidents (/api/incidents); no invented events.
export const ActivityFeed = () => {
  const { live, stats } = useBackendStatus();
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!live) { setItems([]); return; }
    apiClient.get('/api/incidents', { params: { limit: 6 } })
      .then((r) => setItems(r.data || []))
      .catch(() => setItems([]));
  }, [live, stats?.runId]);

  if (!live) {
    return <p className="text-xs text-amber-300">Backend unreachable: no live activity to show.</p>;
  }
  if (items.length === 0) {
    return <p className="text-xs text-slate-400">No surfaced incidents yet.</p>;
  }
  return (
    <div className="space-y-3">
      {items.map((inc) => (
        <div key={inc.id} className="p-3 rounded-lg bg-[#111827] border border-[#293449]/70 flex items-start gap-3">
          <div className={`w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 mt-0.5 ${inc.band === 'RED' ? 'text-red-400 bg-red-500/10 border-red-500/30' : 'text-amber-400 bg-amber-500/10 border-amber-500/30'}`}>
            <AlertCircle className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-white truncate">{inc.band}: {inc.title}</span>
              <span className="text-[10px] text-slate-400 shrink-0 font-mono flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />{String(inc.firstDetected).replace('T', ' ').replace('Z', '')}
              </span>
            </div>
            <p className="text-[11px] text-[#94A3B8] mt-0.5 line-clamp-1">
              {inc.relatedAlertsCount} alerts · {inc.affectedServices?.length} services · likely origin {inc.probableRootCauseService} (origin score {inc.originScore})
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};
