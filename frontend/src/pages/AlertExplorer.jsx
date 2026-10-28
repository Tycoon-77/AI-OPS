import React, { useState, useEffect } from 'react';
import { useSearchParams, useOutletContext } from 'react-router-dom';
import {
  Search,
  UploadCloud,
  ChevronLeft,
  ChevronRight,
  Eye,
  BellRing,
  AlertTriangle,
  AlertOctagon,
  Layers,
  Download,
  RotateCcw
} from 'lucide-react';
import { alertService } from '../services/alertService';
import { SeverityBadge } from '../components/common/Badge';
import { AlertDetailDrawer } from '../components/alerts/AlertDetailDrawer';
import { formatDateTime } from '../utils/formatters';

export const AlertExplorer = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { openUploadModal } = useOutletContext() || {};

  // Search and filter states
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [serviceFilter, setServiceFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [page, setPage] = useState(1);
  const limit = 15;

  const [alertsData, setAlertsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAlert, setSelectedAlert] = useState(null);

  // Sync search param from URL if present
  useEffect(() => {
    const q = searchParams.get('search');
    if (q !== null && q !== search) {
      setSearch(q);
      setPage(1);
    }
  }, [searchParams, search]);

  useEffect(() => {
    let isCancelled = false;
    const loadAlerts = async () => {
      setLoading(true);
      try {
        const res = await alertService.getAlerts({
          search,
          severity: severityFilter,
          service: serviceFilter,
          status: statusFilter,
          page,
          limit
        });
        if (!isCancelled) {
          setAlertsData(res.data);
        }
      } catch (err) {
        console.error('Failed to query alerts', err);
      } finally {
        if (!isCancelled) setLoading(false);
      }
    };

    loadAlerts();
    return () => {
      isCancelled = true;
    };
  }, [search, severityFilter, serviceFilter, statusFilter, page]);

  const handleResetFilters = () => {
    setSearch('');
    setSeverityFilter('ALL');
    setServiceFilter('ALL');
    setStatusFilter('ALL');
    setPage(1);
    setSearchParams({});
  };

  const handleExportCSV = () => {
    if (!alertsData?.alerts) return;
    const headers = ['Alert ID', 'Timestamp', 'Service', 'Severity', 'Source', 'Message', 'Status', 'Incident'];
    const rows = alertsData.alerts.map((a) => [
      a.id,
      a.timestamp,
      a.service,
      a.severity,
      a.source,
      `"${a.message.replace(/"/g, '""')}"`,
      a.correlationStatus,
      a.incidentId || 'None'
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'signaliq_alerts_export.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <BellRing className="w-6 h-6 text-indigo-400" />
            Alert Explorer
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Explore, filter, and investigate incoming system alerts. Full telemetry is preserved with zero destructive edits.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white bg-[#151D2E] hover:bg-[#1E293B] border border-[#293449] rounded-lg transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={openUploadModal}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-all shadow-md shadow-indigo-600/30 cursor-pointer"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Dataset</span>
          </button>
        </div>
      </div>

      {/* Alert Statistics Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-[#151D2E] border border-indigo-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 block font-medium">Total Ingested</span>
            <span className="text-2xl font-bold font-mono text-white mt-0.5 block">
              {alertsData?.stats?.total || 400}
            </span>
          </div>
          <div className="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
            <BellRing className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#151D2E] border border-red-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 block font-medium">Critical Alerts</span>
            <span className="text-2xl font-bold font-mono text-red-400 mt-0.5 block">
              {alertsData?.stats?.critical || 262}
            </span>
          </div>
          <div className="w-9 h-9 rounded-lg bg-red-500/10 text-red-400 flex items-center justify-center">
            <AlertOctagon className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#151D2E] border border-amber-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 block font-medium">Warning Alerts</span>
            <span className="text-2xl font-bold font-mono text-amber-400 mt-0.5 block">
              {alertsData?.stats?.warning || 118}
            </span>
          </div>
          <div className="w-9 h-9 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[#151D2E] border border-sky-500/30 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 block font-medium">Duplicates Identified</span>
            <span className="text-2xl font-bold font-mono text-sky-400 mt-0.5 block">
              {alertsData?.stats?.duplicates || 94}
            </span>
          </div>
          <div className="w-9 h-9 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
            <Layers className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-xl bg-[#151D2E] border border-[#293449] space-y-3">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Filter by Alert ID (e.g. ALT-0001), message keywords, host..."
              className="w-full bg-[#111827] border border-[#293449] text-xs text-white pl-9 pr-4 py-2 rounded-lg focus:outline-none focus:border-indigo-500 placeholder:text-slate-400"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white text-xs cursor-pointer"
              >
                Clear
              </button>
            )}
          </div>

          {/* Filter Selectors */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="bg-[#111827] border border-[#293449] text-slate-300 px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
            </select>

            {/* Service Filter */}
            <select
              value={serviceFilter}
              onChange={(e) => {
                setServiceFilter(e.target.value);
                setPage(1);
              }}
              className="bg-[#111827] border border-[#293449] text-slate-300 px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500 max-w-[170px]"
            >
              <option value="ALL">All Services</option>
              <option value="postgres-primary-db">postgres-primary-db</option>
              <option value="payment-api">payment-api</option>
              <option value="api-gateway">api-gateway</option>
              <option value="order-service">order-service</option>
              <option value="auth-service">auth-service</option>
              <option value="notification-service">notification-service</option>
              <option value="redis-cluster">redis-cluster</option>
              <option value="search-indexer">search-indexer</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-[#111827] border border-[#293449] text-slate-300 px-3 py-2 rounded-lg focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Correlation Status</option>
              <option value="CORRELATED">Correlated</option>
              <option value="DUPLICATE">Duplicate</option>
              <option value="UNCORRELATED">Uncorrelated</option>
            </select>

            {(search || severityFilter !== 'ALL' || serviceFilter !== 'ALL' || statusFilter !== 'ALL') && (
              <button
                onClick={handleResetFilters}
                className="flex items-center gap-1 px-2.5 py-2 text-slate-400 hover:text-white bg-[#1E293B] rounded-lg transition-colors cursor-pointer"
                title="Reset filters"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Results summary counter */}
        <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-[#293449]/40">
          <span>
            Showing <strong className="text-white font-mono">{alertsData?.alerts?.length || 0}</strong> of{' '}
            <strong className="text-white font-mono">{alertsData?.total || 0}</strong> matching alerts
          </span>
          <span className="text-[11px] text-slate-400">
            Source: <strong className="text-indigo-400 font-mono">AO-01 Primary Alert Repository</strong>
          </span>
        </div>
      </div>

      {/* Alert Table */}
      <div className="rounded-xl bg-[#151D2E] border border-[#293449] overflow-hidden shadow-lg">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping inline-block mr-2" />
            Loading alert repository...
          </div>
        ) : alertsData?.alerts?.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400 space-y-2">
            <p className="text-slate-300 text-sm font-semibold">No alerts found matching your criteria</p>
            <p>Try clearing search keywords or resetting filters.</p>
            <button
              onClick={handleResetFilters}
              className="mt-3 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-medium cursor-pointer"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#111827] text-slate-400 uppercase text-[11px] font-semibold border-b border-[#293449]">
                <tr>
                  <th className="py-3 px-4">Alert ID</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Service</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Collector Source</th>
                  <th className="py-3 px-4 min-w-[280px]">Alert Message</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#293449]/60">
                {alertsData.alerts.map((alert) => (
                  <tr
                    key={alert.id}
                    onClick={() => setSelectedAlert(alert)}
                    className="hover:bg-[#1E293B]/70 transition-colors cursor-pointer group"
                  >
                    <td className="py-3 px-4 font-mono font-semibold text-indigo-400 group-hover:text-indigo-300">
                      {alert.id}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-mono text-[11px] whitespace-nowrap">
                      {formatDateTime(alert.timestamp)}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-slate-300 bg-[#111827] px-2 py-0.5 rounded border border-[#293449] whitespace-nowrap">
                        {alert.service}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <SeverityBadge severity={alert.severity} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px] whitespace-nowrap">
                      {alert.source}
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-mono text-[11px]">
                      <div className="line-clamp-1 group-hover:text-white transition-colors">
                        {alert.message}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                          alert.correlationStatus === 'CORRELATED'
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                            : alert.correlationStatus === 'DUPLICATE'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-slate-700/60 text-slate-300 border border-slate-600'
                        }`}
                      >
                        {alert.correlationStatus}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedAlert(alert);
                        }}
                        className="inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white px-2.5 py-1 rounded bg-[#111827] hover:bg-[#1E293B] border border-[#293449] transition-colors cursor-pointer"
                      >
                        <Eye className="w-3 h-3 text-indigo-400" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {alertsData?.totalPages > 1 && (
          <div className="p-4 border-t border-[#293449] flex items-center justify-between text-xs text-slate-400 bg-[#111827]">
            <div>
              Page <strong className="text-white font-mono">{page}</strong> of{' '}
              <strong className="text-white font-mono">{alertsData.totalPages}</strong>
            </div>

            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                className="p-1.5 rounded-lg bg-[#151D2E] border border-[#293449] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#1E293B] text-white transition-colors cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <div className="flex items-center gap-1">
                {[...Array(Math.min(alertsData.totalPages, 7))].map((_, idx) => {
                  const pNum = idx + 1;
                  return (
                    <button
                      key={pNum}
                      onClick={() => setPage(pNum)}
                      className={`w-7 h-7 rounded text-xs font-mono font-medium transition-colors cursor-pointer ${
                        page === pNum
                          ? 'bg-indigo-600 text-white font-bold'
                          : 'bg-[#151D2E] text-slate-300 hover:bg-[#1E293B]'
                      }`}
                    >
                      {pNum}
                    </button>
                  );
                })}
              </div>
              <button
                disabled={page >= alertsData.totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, alertsData.totalPages))}
                className="p-1.5 rounded-lg bg-[#151D2E] border border-[#293449] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#1E293B] text-white transition-colors cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Slide-over Alert Detail Drawer */}
      {selectedAlert && (
        <AlertDetailDrawer
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}
    </div>
  );
};
