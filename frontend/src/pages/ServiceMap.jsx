import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType
} from '@xyflow/react';
import {
  Network,
  Info,
  Flame,
  RotateCcw,
  Maximize2,
  ZoomIn,
  ZoomOut,
  Move,
  MapPin,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Server,
  Layers,
  ArrowRight,
  Database,
  Radio,
  X,
  Eye,
  EyeOff
} from 'lucide-react';
import { serviceGraphService } from '../services/serviceGraphService';
import { incidentService } from '../services/incidentService';
import { CustomServiceNode } from '../components/service-map/CustomServiceNode';
import { ServiceDetailsDrawer } from '../components/service-map/ServiceDetailsDrawer';
import { mockServices } from '../data/mockServices';

const nodeTypes = {
  serviceNode: CustomServiceNode,
  customServiceNode: CustomServiceNode,
};

export const ServiceMap = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedService, setSelectedService] = useState(null);
  const [selectedIncidentFilter, setSelectedIncidentFilter] = useState('ALL');
  const [selectedTierFilter, setSelectedTierFilter] = useState('ALL');
  const [servicesList, setServicesList] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rfInstance, setRfInstance] = useState(null);
  const [showMiniMap, setShowMiniMap] = useState(true);
  const [panMode, setPanMode] = useState(false);

  // Initialize service graph and incidents
  useEffect(() => {
    const initGraph = async () => {
      setLoading(true);
      try {
        const [graphRes, incRes] = await Promise.all([
          serviceGraphService.getServiceGraph(),
          incidentService.getIncidents()
        ]);

        const rawNodes = graphRes.data.nodes || [];
        const rawEdges = (graphRes.data.edges || []).map((edge) => ({
          ...edge,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 14,
            height: 14,
            color: edge.style?.stroke || '#6366F1'
          }
        }));

        setServicesList(graphRes.data.services || []);
        setNodes(rawNodes);
        setEdges(rawEdges);
        setIncidents(incRes.data || []);
      } catch (err) {
        console.error('Failed to load service graph', err);
      } finally {
        setLoading(false);
      }
    };

    initGraph();
  }, []);

  // Filter and highlight graph when an incident or tier is selected
  useEffect(() => {
    if (nodes.length === 0) return;

    if (selectedIncidentFilter === 'ALL') {
      const tierNum = selectedTierFilter !== 'ALL' ? parseInt(selectedTierFilter) : null;
      // Reset all highlights, apply tier dimming if tier filter is active
      setNodes((nds) =>
        nds.map((node) => {
          const isTierMatch = tierNum === null || node.data?.tier === tierNum;
          return {
            ...node,
            style: {
              ...node.style,
              opacity: isTierMatch ? 1 : 0.2,
              transition: 'opacity 0.3s ease',
            },
            data: {
              ...node.data,
              isHighlighted: false,
              isRootCause: false
            }
          };
        })
      );
      setEdges((eds) =>
        eds.map((edge) => ({
          ...edge,
          animated: edge.id.includes('db') || edge.id.includes('payment') || edge.id.includes('gw')
        }))
      );
      return;
    }

    const inc = incidents.find((i) => i.id === selectedIncidentFilter);
    if (!inc) return;

    const affected = inc.affectedServices || [];
    const rootCause = inc.probableRootCauseService;

    // Highlight affected nodes and dim unrelated
    setNodes((nds) =>
      nds.map((node) => {
        const isAff = affected.includes(node.id);
        const isRoot = node.id === rootCause;
        const isInChain = isAff || isRoot;
        return {
          ...node,
          style: {
            ...node.style,
            opacity: isInChain ? 1 : 0.15,
            transition: 'opacity 0.3s ease',
          },
          data: {
            ...node.data,
            isHighlighted: isAff,
            isRootCause: isRoot
          }
        };
      })
    );

    // Highlight edges belonging to the chain
    setEdges((eds) =>
      eds.map((edge) => {
        const involvesAffected = affected.includes(edge.source) && affected.includes(edge.target);
        return {
          ...edge,
          animated: involvesAffected,
          style: {
            ...edge.style,
            stroke: involvesAffected ? '#EF4444' : '#334155',
            strokeWidth: involvesAffected ? 3 : 1
          }
        };
      })
    );
  }, [selectedIncidentFilter, selectedTierFilter, incidents]);

  const onNodeClick = useCallback((event, node) => {
    const s = servicesList.find((item) => item.id === node.id) ||
              mockServices.find((item) => item.id === node.id) ||
              node.data?.service ||
              node.data;
    if (s) {
      setSelectedService({
        id: node.id,
        name: s.name || node.id,
        type: s.type || 'Microservice',
        tier: s.tier ?? (node.data?.tier ?? 2),
        status: s.status || 'HEALTHY',
        uptime: s.uptime || '99.9%',
        latency: s.latency || '24ms',
        rps: s.rps || '2,400 req/s',
        errorRate: s.errorRate || '0.0%',
        activeAlerts: s.activeAlerts ?? 0,
        associatedIncidents: s.associatedIncidents || [],
        dependencies: s.dependencies || [],
        dependents: s.dependents || [],
        description: s.description || `Tier ${s.tier ?? 2} service in distributed architecture.`,
        maintainer: s.maintainer || 'Platform Core',
        healthReason: s.healthReason || (s.status === 'CRITICAL' ? 'Active incident impact' : 'Healthy'),
      });
    }
  }, [servicesList]);

  // Viewport action helpers
  const handleZoomIn = () => rfInstance && rfInstance.zoomIn({ duration: 300 });
  const handleZoomOut = () => rfInstance && rfInstance.zoomOut({ duration: 300 });
  const handleFitView = () => rfInstance && rfInstance.fitView({ padding: 0.12, duration: 600 });

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <Network className="w-6 h-6 text-indigo-400" />
            Service Dependency Map
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Directional topology showing 70 microservices across 4 tiers with 184 RPC dependencies.
          </p>
        </div>

        {/* Incident Filter & Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-2 bg-[#151D2E] border border-[#293449] px-3 py-1.5 rounded-xl text-xs">
            <Flame className="w-4 h-4 text-red-400" />
            <span className="text-slate-300 font-medium hidden sm:inline">Highlight Incident Chain:</span>
            <select
              value={selectedIncidentFilter}
              onChange={(e) => {
                setSelectedIncidentFilter(e.target.value);
                if (e.target.value !== 'ALL') setSelectedTierFilter('ALL');
              }}
              className="bg-[#111827] text-white border border-[#293449] rounded-lg px-2 py-1 focus:outline-none focus:border-indigo-500 font-mono text-xs"
            >
              <option value="ALL">All Services (Full Map)</option>
              {incidents.slice(0, 30).map((inc) => (
                <option key={inc.id} value={inc.id}>
                  {inc.id}: {inc.title.slice(0, 26)}…
                </option>
              ))}
            </select>
          </div>

          {(selectedIncidentFilter !== 'ALL' || selectedTierFilter !== 'ALL') && (
            <button
              onClick={() => {
                setSelectedIncidentFilter('ALL');
                setSelectedTierFilter('ALL');
                handleFitView();
              }}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-[#151D2E] hover:bg-[#1E293B] text-slate-300 rounded-lg border border-[#293449] transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset View</span>
            </button>
          )}
        </div>
      </div>

      {/* Tier Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#151D2E]/70 border border-[#293449] p-2.5 rounded-xl">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1.5 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            Tier Focus:
          </span>
          {[
            { id: 'ALL', label: 'All 70 Services', count: 70 },
            { id: '3', label: 'Tier 3: Gateways', count: 18, color: 'text-sky-400' },
            { id: '2', label: 'Tier 2: Business Core', count: 30, color: 'text-indigo-400' },
            { id: '1', label: 'Tier 1: Platform Infra', count: 14, color: 'text-purple-400' },
            { id: '0', label: 'Tier 0: Datastores & Storage', count: 8, color: 'text-emerald-400' },
          ].map((tier) => (
            <button
              key={tier.id}
              onClick={() => {
                setSelectedTierFilter(tier.id);
                if (tier.id !== 'ALL') setSelectedIncidentFilter('ALL');
              }}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                selectedTierFilter === tier.id
                  ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30'
                  : 'bg-[#111827] text-slate-300 border-[#293449] hover:bg-[#1E293B] hover:text-white'
              }`}
            >
              <span>{tier.label}</span>
              <span className="text-[10px] px-1.5 rounded-full bg-black/40 text-slate-400 font-mono">
                {tier.count}
              </span>
            </button>
          ))}
        </div>

        {/* Viewport Action Controls */}
        <div className="flex items-center gap-1.5 ml-auto">
          <button
            onClick={() => setPanMode(!panMode)}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all ${
              panMode
                ? 'bg-amber-600/80 text-white border-amber-500 shadow-md'
                : 'bg-[#111827] text-slate-300 border-[#293449] hover:bg-[#1E293B]'
            }`}
            title="Pan Mode: Click and drag anywhere to move map"
          >
            <Move className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{panMode ? 'Pan Mode: ON' : 'Pan Mode'}</span>
          </button>
          <button
            onClick={handleZoomIn}
            className="p-1.5 bg-[#111827] hover:bg-[#1E293B] text-slate-300 hover:text-white rounded-lg border border-[#293449] transition-colors"
            title="Zoom In (+)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-1.5 bg-[#111827] hover:bg-[#1E293B] text-slate-300 hover:text-white rounded-lg border border-[#293449] transition-colors"
            title="Zoom Out (-)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleFitView}
            className="flex items-center gap-1 px-2.5 py-1 bg-[#111827] hover:bg-[#1E293B] text-slate-300 hover:text-white rounded-lg border border-[#293449] transition-colors text-xs font-semibold"
            title="Fit Entire Map to View"
          >
            <Maximize2 className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Fit View</span>
          </button>
          <button
            onClick={() => setShowMiniMap(!showMiniMap)}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all ${
              showMiniMap
                ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/50'
                : 'bg-[#111827] text-slate-400 border-[#293449] hover:bg-[#1E293B]'
            }`}
            title="Toggle Minimap on/off"
          >
            {showMiniMap ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">Minimap</span>
          </button>
        </div>
      </div>

      {/* Visual Line & Node Meaning Legend */}
      <div className="p-3.5 bg-[#151D2E] border border-[#293449] rounded-xl space-y-2.5 text-xs">
        {/* Row 1: Node Sizes & Tiers */}
        <div className="flex items-center justify-between gap-4 flex-wrap border-b border-[#293449]/70 pb-2">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold uppercase text-[11px]">
            <span>Node Hierarchy:</span>
          </div>
          <div className="flex items-center gap-4 flex-wrap text-slate-300 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-emerald-500/30 border border-emerald-500 text-emerald-400 flex items-center justify-center font-bold text-[8px]">0</span>
              <span className="font-semibold text-emerald-300">Tier 0 (Main Datastores)</span>
              <span className="text-slate-400">— Largest (Backbone)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-sky-500/30 border border-sky-500 text-sky-400 flex items-center justify-center font-bold text-[8px]">3</span>
              <span className="font-semibold text-sky-300">Tier 3 (Entry Gateways)</span>
              <span className="text-slate-400">— Ingress entry</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-purple-500/30 border border-purple-500 text-purple-400 flex items-center justify-center font-bold text-[8px]">1</span>
              <span className="font-semibold text-purple-300">Tier 1 (Platform Core)</span>
              <span className="text-slate-400">— Shared capabilities</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-indigo-500/30 border border-indigo-500 text-indigo-400 flex items-center justify-center font-bold text-[8px]">2</span>
              <span className="font-semibold text-indigo-300">Tier 2 (Business Microservices)</span>
              <span className="text-slate-400">— Dependent domain logic</span>
            </div>
          </div>
        </div>

        {/* Row 2: Connection Lines and Arrow Meanings */}
        <div className="flex items-center justify-between gap-4 flex-wrap text-[11px]">
          <div className="flex items-center gap-1.5 text-slate-400 font-semibold uppercase text-[11px]">
            <span>Line Meanings:</span>
          </div>
          <div className="flex items-center gap-4 flex-wrap text-slate-300">
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] animate-pulse" />
              <span className="text-red-400 font-semibold">Critical Incident Cascade</span>
              <span className="text-slate-400">(Failure path)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-amber-400" />
              <span className="text-amber-300 font-semibold">Warning Latency</span>
              <span className="text-slate-400">(Elevated response time)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 h-0.5 bg-slate-500" />
              <span className="text-slate-300">Healthy RPC Call</span>
              <span className="text-slate-400">(Nominal telemetry)</span>
            </div>
            <div className="flex items-center gap-1.5 border-l border-slate-700 pl-3 text-slate-400">
              <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
              <span>Arrow points from <strong>Dependent Caller</strong> → <strong>Target Provider</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* React Flow Interactive Graph Canvas */}
      <div className="h-[700px] rounded-2xl bg-[#0B1020] border border-[#293449] relative overflow-hidden shadow-2xl">
        {loading ? (
          <div className="h-full flex items-center justify-center text-xs text-slate-400">
            Loading service topology graph...
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onInit={setRfInstance}
            fitView
            minZoom={0.12}
            maxZoom={1.8}
            panOnDrag={panMode ? true : [1, 2]}
            panOnScroll={true}
            zoomOnScroll={true}
            zoomOnPinch={true}
            preventScrolling={true}
            nodesDraggable={!panMode}
            selectionOnDrag={false}
            attributionPosition="bottom-left"
          >
            <Background color="#1E293B" gap={28} size={1} />
            <Controls
              position="top-right"
              showInteractive={true}
              className="!bg-[#151D2E] !border !border-[#3b4d6e] !rounded-xl !shadow-2xl overflow-hidden !m-3"
            />
          </ReactFlow>
        )}

        {/* Floating MiniMap Radar Dock with Close Button */}
        {showMiniMap && !loading && (
          <div className="absolute bottom-4 right-4 z-20 bg-[#111827]/95 backdrop-blur-md border border-[#293449] rounded-xl p-2.5 shadow-2xl flex flex-col gap-1.5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between px-1 text-[11px] text-slate-300 font-semibold border-b border-[#293449]/80 pb-1.5">
              <span className="flex items-center gap-1.5 text-indigo-400 font-mono">
                <Network className="w-3.5 h-3.5" />
                Radar Minimap
              </span>
              <button
                onClick={() => setShowMiniMap(false)}
                className="text-slate-400 hover:text-white p-0.5 rounded hover:bg-[#1E293B] transition-colors"
                title="Minimize radar"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="w-[210px] h-[135px] overflow-hidden rounded-lg border border-[#293449] bg-[#0d1424]">
              <MiniMap
                style={{ width: '100%', height: '100%', position: 'relative', margin: 0 }}
                nodeColor={(n) => {
                  const s = servicesList.find((item) => item.id === n.id) || n.data;
                  if (s?.status === 'CRITICAL' || n.data?.status === 'CRITICAL') return '#EF4444';
                  if (s?.status === 'WARNING' || n.data?.status === 'WARNING') return '#F59E0B';
                  return '#22C55E';
                }}
                maskColor="rgba(11, 16, 32, 0.75)"
              />
            </div>
            <span className="text-[9px] text-slate-400 text-center font-mono">
              🔴 Critical • 🟡 Warning • 🟢 Healthy
            </span>
          </div>
        )}

        {/* Quick Instructions / Navigation Overlay */}
        <div className="absolute top-4 left-4 z-10 bg-[#111827]/85 backdrop-blur-xs border border-[#293449] px-3 py-2 rounded-lg text-[11px] text-slate-300 pointer-events-none flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Click any node for details. Drag or two-finger scroll to pan. Scroll/pinch to zoom.</span>
        </div>
      </div>

      {/* Service Details Drawer */}
      {selectedService && (
        <ServiceDetailsDrawer
          service={selectedService}
          onClose={() => setSelectedService(null)}
        />
      )}
    </div>
  );
};