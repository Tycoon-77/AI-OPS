import React, { useState, useRef } from 'react';
import { useBackendStatus, fmtInt } from '../../services/status';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X, ArrowRight, Sparkles } from 'lucide-react';
import { alertService } from '../../services/alertService';

export const AlertUploadModal = ({ isOpen, onClose, onUploadSuccess }) => {
  const { stats, live } = useBackendStatus();
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [resultSummary, setResultSummary] = useState(null);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSelectFile = (file) => {
    setErrorMsg(null);
    setResultSummary(null);
    if (!file) return;

    const validExtensions = ['.csv', '.json'];
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!hasValidExt) {
      setErrorMsg('Invalid format. Please upload an alert dataset in .CSV or .JSON format.');
      setSelectedFile(null);
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMsg('File exceeds 25MB limit. Please upload a smaller dataset.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleStartUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadProgress(10);
    setErrorMsg(null);

    try {
      const response = await alertService.uploadAlertsFile(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setResultSummary(response.data);
      if (onUploadSuccess) onUploadSuccess(response.data);
    } catch (err) {
      setErrorMsg(err.message || 'Error occurred while processing alert dataset.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setUploadProgress(0);
    setErrorMsg(null);
    setResultSummary(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-[#151D2E] border border-[#293449] rounded-2xl max-w-xl w-full p-6 shadow-2xl relative my-8 animate-in fade-in duration-200">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#293449]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">Ingest Alert Dataset</h2>
              <p className="text-xs text-[#94A3B8]">
                Upload Prometheus, Datadog, or CloudWatch dumps in CSV or JSON
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-[#1E293B] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="mt-5 space-y-4">
          {!resultSummary ? (
            <>
              {/* Drag & Drop Box */}
              <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                  dragActive
                    ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
                    : selectedFile
                    ? 'border-emerald-500/60 bg-emerald-500/5'
                    : 'border-[#293449] hover:border-slate-500 bg-[#0B1020]/60'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.json"
                  onChange={handleChange}
                  className="hidden"
                />

                <div className="flex flex-col items-center">
                  <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mb-3 text-slate-300">
                    <FileText className="w-6 h-6 text-indigo-400" />
                  </div>
                  <p className="text-sm font-medium text-slate-200">
                    Click to browse or drag & drop alert dataset
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Supported formats: <span className="text-indigo-300 font-mono">.CSV, .JSON</span> (up to 25MB)
                  </p>
                </div>
              </div>

              {/* Selected File Card */}
              {selectedFile && (
                <div className="p-3 bg-[#111827] border border-[#293449] rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-indigo-400 shrink-0" />
                    <div>
                      <div className="text-xs font-semibold text-white truncate max-w-xs">
                        {selectedFile.name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {formatFileSize(selectedFile.size)} • {selectedFile.type || 'text/plain'}
                      </div>
                    </div>
                  </div>
                  {!isUploading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReset();
                      }}
                      className="text-xs text-red-400 hover:text-red-300 px-2 py-1"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}

              {/* Progress Bar */}
              {isUploading && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                      Parsing telemetry and running deduplication graph...
                    </span>
                    <span className="font-mono text-indigo-400 font-semibold">{uploadProgress}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-sky-400 transition-all duration-300 rounded-full"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error Alert */}
              {errorMsg && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-2.5 text-xs text-red-300">
                  <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Validation Error:</span> {errorMsg}
                  </div>
                </div>
              )}
            </>
          ) : (
            /* Upload Success Result Card */
            <div className="space-y-4 py-2">
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto mb-2" />
                <h3 className="text-base font-bold text-white">Alert Telemetry Ingested</h3>
                <p className="text-xs text-slate-300 mt-1">
                  File <span className="font-mono text-emerald-300">{resultSummary.filename}</span> parsed and processed by the SignalIQ correlation pipeline.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-[#111827] border border-[#293449] rounded-lg">
                  <span className="text-slate-400 block mb-0.5">Alerts Parsed</span>
                  <span className="text-base font-bold text-white font-mono">{resultSummary.alertsParsed || (stats ? fmtInt(stats.rawAlerts) : '—')}</span>
                </div>
                <div className="p-3 bg-[#111827] border border-[#293449] rounded-lg">
                  <span className="text-slate-400 block mb-0.5">Duplicate Alerts Identified</span>
                  <span className="text-base font-bold text-amber-400 font-mono">{resultSummary.duplicatesIdentified || (stats ? fmtInt(stats.rawAlerts - stats.alertGroups) : '—')}</span>
                </div>
                <div className="p-3 bg-[#111827] border border-[#293449] rounded-lg">
                  <span className="text-slate-400 block mb-0.5">Correlated Incidents</span>
                  <span className="text-base font-bold text-indigo-400 font-mono">{resultSummary.incidentsCount ? `${resultSummary.incidentsCount} Incidents` : (stats ? `${fmtInt(stats.surfaced)} Incidents` : '—')}</span>
                </div>
                <div className="p-3 bg-[#111827] border border-[#293449] rounded-lg">
                  <span className="text-slate-400 block mb-0.5">Noise Reduction</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">{resultSummary.noiseReducedPercentage || (stats ? `${stats.noiseCutPct}%` : '—')}</span>
                </div>
              </div>

              <div className="p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-xs text-indigo-300 flex items-center gap-2">
                <Sparkles className="w-4 h-4 shrink-0 text-indigo-400" />
                <span>Original alerts remain untouched and fully accessible in Alert Explorer.</span>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="mt-6 pt-4 border-t border-[#293449] flex items-center justify-between">
          <div className="text-[11px] text-slate-400">
            SignalIQ Ingestion API: <code className="text-slate-300 font-mono">/api/alerts/upload</code>
          </div>
          <div className="flex items-center gap-2">
            {!resultSummary ? (
              <>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isUploading}
                  className="px-4 py-2 text-xs font-medium text-slate-300 hover:text-white bg-[#1E293B] hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStartUpload}
                  disabled={!selectedFile || isUploading}
                  className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg text-white transition-all shadow-md ${
                    !selectedFile || isUploading
                      ? 'bg-indigo-600/50 cursor-not-allowed opacity-60'
                      : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/30'
                  }`}
                >
                  {isUploading ? (
                    <>Processing...</>
                  ) : (
                    <>
                      <span>Upload & Correlate</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => {
                  handleReset();
                  onClose();
                }}
                className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
              >
                Done & View Results
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
