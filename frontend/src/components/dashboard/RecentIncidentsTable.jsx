import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, Flame, Database, ShieldAlert, AlertCircle } from 'lucide-react';
import { SeverityBadge, StatusBadge } from '../common/Badge';

export const RecentIncidentsTable = ({ incidents }) => {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead className="bg-[#111827] text-slate-400 uppercase text-[11px] font-semibold border-b border-[#293449]">
          <tr>
            <th className="py-3 px-4">Incident ID</th>
            <th className="py-3 px-4">Incident Title</th>
            <th className="py-3 px-4">Root Cause Service</th>
            <th className="py-3 px-4">Severity</th>
            <th className="py-3 px-4">Related Alerts</th>
            <th className="py-3 px-4">Status</th>
            <th className="py-3 px-4 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#293449]/60">
          {incidents.map((inc) => (
            <tr
              key={inc.id}
              onClick={() => navigate(`/incidents/${inc.id}`)}
              className="hover:bg-[#1E293B]/60 transition-colors cursor-pointer group"
            >
              <td className="py-3.5 px-4 font-mono font-semibold text-indigo-400 group-hover:text-indigo-300">
                {inc.id}
              </td>
              <td className="py-3.5 px-4 font-semibold text-white">
                <div className="flex items-center gap-2">
                  <Flame className="w-3.5 h-3.5 text-red-400 shrink-0" />
                  <span>{inc.title}</span>
                </div>
              </td>
              <td className="py-3.5 px-4">
                <span className="font-mono text-slate-300 bg-[#111827] px-2 py-0.5 rounded border border-[#293449]">
                  {inc.probableRootCauseService}
                </span>
              </td>
              <td className="py-3.5 px-4">
                <SeverityBadge severity={inc.severity} size="sm" />
              </td>
              <td className="py-3.5 px-4 font-mono font-semibold text-slate-200">
                <span className="text-indigo-400">{inc.relatedAlertsCount}</span>
                <span className="text-slate-400 text-[11px] font-normal"> alerts</span>
              </td>
              <td className="py-3.5 px-4">
                <StatusBadge status={inc.status} size="sm" />
              </td>
              <td className="py-3.5 px-4 text-right">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/incidents/${inc.id}`);
                  }}
                  className="inline-flex items-center gap-1 text-xs text-indigo-400 group-hover:text-indigo-300 hover:underline font-medium"
                >
                  <span>Investigate</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
