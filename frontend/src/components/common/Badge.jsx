import React from 'react';
import { getSeverityBadgeStyle, getStatusBadgeStyle } from '../../utils/formatters';

export const SeverityBadge = ({ severity, size = 'md' }) => {
  const style = getSeverityBadgeStyle(severity);
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${style.bg} ${style.text} ${style.border} ${sizeClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
      {severity}
    </span>
  );
};

export const StatusBadge = ({ status, size = 'md' }) => {
  const style = getStatusBadgeStyle(status);
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-md border ${style.bg} ${style.text} ${style.border} ${sizeClasses}`}
    >
      {style.label || status}
    </span>
  );
};

export const CorrelationTypeBadge = ({ isConfirmed = false }) => {
  if (isConfirmed) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        Confirmed Evidence
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping"></span>
      Probable Root Cause
    </span>
  );
};
