import React from 'react';
import { Layers, GitMerge, AlertCircle, UploadCloud, Clock, CheckCircle } from 'lucide-react';

const activities = [
  {
    id: 1,
    title: '25 duplicate alerts detected & clustered',
    detail: 'High frequency query timeouts suppressed into deduplicated signatures.',
    time: '2 mins ago',
    icon: Layers,
    color: 'text-amber-400 bg-amber-500/10 border-amber-500/30'
  },
  {
    id: 2,
    title: '12 alerts correlated across payment-api & postgres',
    detail: 'Synchronous timeout cascade clustered into INC-001 by graph topology engine.',
    time: '8 mins ago',
    icon: GitMerge,
    color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30'
  },
  {
    id: 3,
    title: 'New Critical Incident Identified: INC-001',
    detail: 'Postgres primary database connection pool reached 98% saturation ceiling.',
    time: '18 mins ago',
    icon: AlertCircle,
    color: 'text-red-400 bg-red-500/10 border-red-500/30'
  },
  {
    id: 4,
    title: 'Dataset uploaded successfully: alert_dump_prod_oct.csv',
    detail: '400 alerts ingested from Prometheus & Datadog APM streams.',
    time: '25 mins ago',
    icon: UploadCloud,
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
  },
  {
    id: 5,
    title: 'Probable Root Cause Isolated on postgres-primary-db',
    detail: 'Confidence score calculated at 96% based on temporal burst and topology.',
    time: '32 mins ago',
    icon: CheckCircle,
    color: 'text-sky-400 bg-sky-500/10 border-sky-500/30'
  }
];

export const ActivityFeed = () => {
  return (
    <div className="space-y-3">
      {activities.map((act) => {
        const Icon = act.icon;
        return (
          <div
            key={act.id}
            className="p-3 rounded-lg bg-[#111827] border border-[#293449]/70 hover:border-slate-600 transition-colors flex items-start gap-3"
          >
            <div className={`w-8 h-8 rounded-lg ${act.color} border flex items-center justify-center shrink-0 mt-0.5`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-white truncate">
                  {act.title}
                </span>
                <span className="text-[10px] text-slate-400 shrink-0 font-mono flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" />
                  {act.time}
                </span>
              </div>
              <p className="text-[11px] text-[#94A3B8] mt-0.5 line-clamp-1">
                {act.detail}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
