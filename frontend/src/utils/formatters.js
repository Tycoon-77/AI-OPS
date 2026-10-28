// Utility formatting functions for SignalIQ

export const formatDateTime = (isoString) => {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return isoString;
  }
};

export const formatTimeOnly = (isoString) => {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString('en-US', { hour12: false });
  } catch (e) {
    return isoString;
  }
};

export const getSeverityBadgeStyle = (severity) => {
  const sev = (severity || '').toUpperCase();
  switch (sev) {
    case 'CRITICAL':
      return {
        bg: 'bg-red-500/15',
        text: 'text-red-400',
        border: 'border-red-500/30',
        dot: 'bg-red-500'
      };
    case 'WARNING':
      return {
        bg: 'bg-amber-500/15',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        dot: 'bg-amber-500'
      };
    case 'INFO':
    case 'LOW':
      return {
        bg: 'bg-sky-500/15',
        text: 'text-sky-400',
        border: 'border-sky-500/30',
        dot: 'bg-sky-400'
      };
    case 'HEALTHY':
    case 'SUCCESS':
      return {
        bg: 'bg-emerald-500/15',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        dot: 'bg-emerald-400'
      };
    default:
      return {
        bg: 'bg-slate-500/15',
        text: 'text-slate-400',
        border: 'border-slate-500/30',
        dot: 'bg-slate-400'
      };
  }
};

export const getStatusBadgeStyle = (status) => {
  const stat = (status || '').toUpperCase();
  switch (stat) {
    case 'ACTIVE':
      return {
        bg: 'bg-red-500/20',
        text: 'text-red-400',
        border: 'border-red-500/40',
        label: 'Active Incident'
      };
    case 'INVESTIGATING':
      return {
        bg: 'bg-amber-500/20',
        text: 'text-amber-400',
        border: 'border-amber-500/40',
        label: 'Investigating'
      };
    case 'MONITORING':
      return {
        bg: 'bg-sky-500/20',
        text: 'text-sky-400',
        border: 'border-sky-500/40',
        label: 'Monitoring'
      };
    case 'RESOLVED':
      return {
        bg: 'bg-emerald-500/20',
        text: 'text-emerald-400',
        border: 'border-emerald-500/40',
        label: 'Resolved'
      };
    default:
      return {
        bg: 'bg-slate-500/20',
        text: 'text-slate-400',
        border: 'border-slate-500/40',
        label: status
      };
  }
};
