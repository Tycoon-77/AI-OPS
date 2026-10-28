import React, { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { DemoBanner } from '../common/DemoBanner';
import { AlertUploadModal } from '../alerts/AlertUploadModal';

export const Layout = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const navigate = useNavigate();

  const handleUploadSuccess = (result) => {
    // Optionally trigger route refresh or navigate to Alerts explorer
  };

  return (
    <div className="min-h-screen bg-[#0B1020] text-[#F8FAFC] flex flex-col">
      {/* Top System Demo Banner */}
      <DemoBanner />

      <div className="flex flex-1">
        {/* Left Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
          <TopNavbar
            onOpenSidebar={() => setSidebarOpen(true)}
            onOpenUploadModal={() => setUploadModalOpen(true)}
          />

          <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
            <Outlet context={{ openUploadModal: () => setUploadModalOpen(true) }} />
          </main>

          {/* Clean Enterprise Footer */}
          <footer className="px-6 py-4 border-t border-[#293449]/80 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-2 bg-[#0B1020]">
            <div>
              <span className="font-semibold text-slate-300">SignalIQ</span> – Less Alert Noise. More Incident Intelligence. (AO-01)
            </div>
            <div className="flex items-center gap-4">
              <span>Telemetry Preserved: 100%</span>
              <span className="h-3 w-px bg-slate-800" />
              <span>Noise Reduction: 93.75%</span>
              <span className="h-3 w-px bg-slate-800" />
              <span>FastAPI Architecture Ready</span>
            </div>
          </footer>
        </div>
      </div>

      {/* Global Ingestion Modal */}
      <AlertUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
};
