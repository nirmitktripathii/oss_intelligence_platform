'use client';

import * as React from 'react';
import { ASTGraphData, GraphNode } from '@/types/graph';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  FileCode,
  Layers,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Copy,
  Check,
  Eye,
  Crosshair,
  Flame,
  Network,
  Compass,
  Cpu,
  Code2,
  Activity,
  GitFork,
  ExternalLink,
} from 'lucide-react';

interface GraphCanvasProps {
  data: ASTGraphData;
  initialTargetFile?: string;
  className?: string;
  onSelectRepo?: (repoId: string) => void;
  currentRepoId?: string;
}

type LayoutMode = 'organic' | 'layered' | 'concentric' | 'grid';

export function GraphCanvas({
  data,
  initialTargetFile,
  className,
}: GraphCanvasProps) {
  const [zoom, setZoom] = React.useState<number>(1);
  const [pan, setPan] = React.useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = React.useState(false);
  const [dragStart, setDragStart] = React.useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [searchQuery, setSearchQuery] = React.useState('');
  const [selectedCommunity, setSelectedCommunity] = React.useState<number | 'all'>('all');
  const [selectedType, setSelectedType] = React.useState<string | 'all'>('all');
  const [showGodNodesOnly, setShowGodNodesOnly] = React.useState(false);
  const [layoutMode, setLayoutMode] = React.useState<LayoutMode>('organic');
  const [selectedNode, setSelectedNode] = React.useState<GraphNode | null>(null);
  const [copiedPath, setCopiedPath] = React.useState(false);
  const [hoveredNode, setHoveredNode] = React.useState<GraphNode | null>(null);

  const containerRef = React.useRef<HTMLDivElement>(null);

  // Set initial selected node from target file or default
  React.useEffect(() => {
    if (initialTargetFile) {
      const match = data.nodes.find(
        (n) => n.id === initialTargetFile || n.file === initialTargetFile
      );
      if (match) setSelectedNode(match);
    } else if (data.nodes.length > 0 && !selectedNode) {
      const target = data.nodes.find((n) => n.isTarget) || data.nodes.find((n) => n.isGodNode) || data.nodes[0];
      setSelectedNode(target);
    }
  }, [initialTargetFile, data]);

  // Dynamic Multi-Layout Engine
  const nodePositions = React.useMemo(() => {
    const posMap = new Map<string, { x: number; y: number }>();
    const centerX = 600;
    const centerY = 450;

    if (layoutMode === 'concentric') {
      // Concentric Rings: Center = God Nodes, Ring 1 = Classes/Modules, Ring 2 = Functions/Files
      const godNodes = data.nodes.filter((n) => n.isGodNode);
      const midNodes = data.nodes.filter((n) => !n.isGodNode && (n.type === 'class' || n.type === 'module'));
      const outerNodes = data.nodes.filter((n) => !n.isGodNode && n.type !== 'class' && n.type !== 'module');

      godNodes.forEach((node, i) => {
        const angle = (i / Math.max(godNodes.length, 1)) * 2 * Math.PI;
        posMap.set(node.id, {
          x: centerX + Math.cos(angle) * 170,
          y: centerY + Math.sin(angle) * 170,
        });
      });

      midNodes.forEach((node, i) => {
        const angle = (i / Math.max(midNodes.length, 1)) * 2 * Math.PI;
        posMap.set(node.id, {
          x: centerX + Math.cos(angle) * 330,
          y: centerY + Math.sin(angle) * 330,
        });
      });

      outerNodes.forEach((node, i) => {
        const angle = (i / Math.max(outerNodes.length, 1)) * 2 * Math.PI;
        posMap.set(node.id, {
          x: centerX + Math.cos(angle) * 470,
          y: centerY + Math.sin(angle) * 470,
        });
      });
    } else if (layoutMode === 'layered') {
      // Layered Hierarchy by Community ID
      const communityGroups: Record<number, GraphNode[]> = {};
      data.nodes.forEach((n) => {
        if (!communityGroups[n.communityId]) communityGroups[n.communityId] = [];
        communityGroups[n.communityId].push(n);
      });

      const layerKeys = Object.keys(communityGroups).map(Number).sort((a, b) => a - b);
      const layerSpacing = 150;
      const startY = 160;

      layerKeys.forEach((commId, layerIdx) => {
        const nodesInLayer = communityGroups[commId];
        const nodeSpacing = 900 / Math.max(nodesInLayer.length + 1, 2);
        nodesInLayer.forEach((node, i) => {
          posMap.set(node.id, {
            x: 150 + (i + 1) * nodeSpacing,
            y: startY + layerIdx * layerSpacing,
          });
        });
      });
    } else if (layoutMode === 'grid') {
      // Community Quadrant Matrix
      const communityKeys = Object.keys(data.communities).map(Number);
      const cols = 3;
      communityKeys.forEach((commId, idx) => {
        const commCenterX = 260 + (idx % cols) * 360;
        const commCenterY = 220 + Math.floor(idx / cols) * 340;
        const nodesInComm = data.nodes.filter((n) => n.communityId === commId);

        nodesInComm.forEach((node, i) => {
          const angle = (i / Math.max(nodesInComm.length, 1)) * 2 * Math.PI;
          const r = node.isGodNode ? 0 : 90 + (i % 2 === 0 ? 30 : -20);
          posMap.set(node.id, {
            x: commCenterX + Math.cos(angle) * r,
            y: commCenterY + Math.sin(angle) * r,
          });
        });
      });
    } else {
      // Default: Organic Force-Clustered Layout
      const communityCenters = new Map<number, { x: number; y: number }>();
      const totalCommunities = Object.keys(data.communities).length;
      Object.keys(data.communities).forEach((cId, i) => {
        const angle = (i / Math.max(totalCommunities, 1)) * 2 * Math.PI;
        communityCenters.set(Number(cId), {
          x: centerX + Math.cos(angle) * 280,
          y: centerY + Math.sin(angle) * 240,
        });
      });

      data.nodes.forEach((node, i) => {
        const cCenter = communityCenters.get(node.communityId) || { x: centerX, y: centerY };
        const localAngle = (i * 1.618) * 2 * Math.PI; // Golden ratio dispersion
        const dist = node.isGodNode ? 25 : 70 + (node.degree > 6 ? 35 : 75);
        posMap.set(node.id, {
          x: cCenter.x + Math.cos(localAngle) * dist,
          y: cCenter.y + Math.sin(localAngle) * dist,
        });
      });
    }

    return posMap;
  }, [data, layoutMode]);

  // Zoom and Pan Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).tagName === 'circle' || (e.target as HTMLElement).tagName === 'text') {
      return;
    }
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom((z) => Math.min(Math.max(z * zoomFactor, 0.3), 3.0));
  };

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.3));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleFocusNode = (node: GraphNode) => {
    setSelectedNode(node);
    const pos = nodePositions.get(node.id);
    if (pos) {
      setPan({ x: 450 - pos.x, y: 350 - pos.y });
      setZoom(1.2);
    }
  };

  const handleCopyPath = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  // Filtered nodes
  const filteredNodes = React.useMemo(() => {
    return data.nodes.filter((node) => {
      const matchesSearch =
        searchQuery === '' ||
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (node.file && node.file.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesCommunity = selectedCommunity === 'all' || node.communityId === selectedCommunity;
      const matchesType = selectedType === 'all' || node.type === selectedType;
      const matchesGod = !showGodNodesOnly || node.isGodNode;
      return matchesSearch && matchesCommunity && matchesType && matchesGod;
    });
  }, [data.nodes, searchQuery, selectedCommunity, selectedType, showGodNodesOnly]);

  const filteredNodeIds = React.useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  // Edges linked to filtered nodes
  const visibleEdges = React.useMemo(() => {
    return data.edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target));
  }, [data.edges, filteredNodeIds]);

  // Active callers and callees for selected node
  const nodeConnections = React.useMemo(() => {
    if (!selectedNode) return { callers: [], callees: [] };
    const callers = data.edges
      .filter((e) => e.target === selectedNode.id)
      .map((e) => data.nodes.find((n) => n.id === e.source))
      .filter(Boolean) as GraphNode[];
    const callees = data.edges
      .filter((e) => e.source === selectedNode.id)
      .map((e) => data.nodes.find((n) => n.id === e.target))
      .filter(Boolean) as GraphNode[];
    return { callers, callees };
  }, [selectedNode, data]);

  return (
    <div
      ref={containerRef}
      className={`relative flex h-full w-full overflow-hidden bg-background font-mono text-foreground select-none ${className || ''}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* 1. TOP TOOLBAR: Layout Switcher, Stats HUD & Quick Search */}
      <div className="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Left Side: Search & Filters */}
        <div className="flex items-center gap-3 pointer-events-auto">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search AST symbols, files, classes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 w-72 pl-9 text-xs sm:text-sm bg-card/90 border-border focus:border-primary rounded-xl shadow-xl backdrop-blur-md text-foreground placeholder:text-muted-foreground"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-2.5 text-xs text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            )}
          </div>

          {/* Layout Mode Switcher */}
          <div className="hidden sm:flex items-center rounded-xl border border-border bg-card/90 p-1 shadow-xl backdrop-blur-md text-xs">
            <button
              onClick={() => setLayoutMode('organic')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                layoutMode === 'organic' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Organic Force Clusters"
            >
              <Compass className="h-3.5 w-3.5" />
              <span>Organic</span>
            </button>
            <button
              onClick={() => setLayoutMode('concentric')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                layoutMode === 'concentric' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Concentric Subsystem Rings"
            >
              <Activity className="h-3.5 w-3.5" />
              <span>Concentric</span>
            </button>
            <button
              onClick={() => setLayoutMode('layered')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                layoutMode === 'layered' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Architectural Layer Hierarchy"
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Layered</span>
            </button>
            <button
              onClick={() => setLayoutMode('grid')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                layoutMode === 'grid' ? 'bg-primary text-primary-foreground shadow-md' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Community Matrix Grid"
            >
              <Network className="h-3.5 w-3.5" />
              <span>Matrix</span>
            </button>
          </div>
        </div>

        {/* Right Side: Quick Stats Telemetry Badge */}
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="flex items-center gap-2.5 rounded-xl border border-border bg-card/90 px-3.5 py-1.5 text-xs sm:text-sm shadow-xl backdrop-blur-md">
            <span className="flex h-2.5 w-2.5 rounded-full bg-primary animate-ping" />
            <span className="text-muted-foreground">Showing:</span>
            <span className="font-extrabold text-primary">{filteredNodes.length} / {data.nodes.length} Nodes</span>
            <span className="text-muted-foreground">•</span>
            <span className="font-extrabold text-accent">{visibleEdges.length} Edges</span>
            <span className="text-muted-foreground hidden md:inline">•</span>
            <span className="font-extrabold text-bounty-gold hidden md:inline">{data.godNodes.length} Hubs</span>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center rounded-xl border border-border bg-card/90 p-1 shadow-xl backdrop-blur-md">
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={handleZoomIn} title="Zoom In">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={handleZoomOut} title="Zoom Out">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-foreground" onClick={handleResetView} title="Reset View">
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* 2. LEFT FLOATING CONTROL DECK: Community Filter & Node Filters (Enlarged & Easy to Read) */}
      <div className="absolute left-3 top-16 z-20 w-76 sm:w-80 rounded-2xl border border-border bg-background/90 p-4 font-mono shadow-2xl backdrop-blur-2xl space-y-3.5 pointer-events-auto">
        <div className="flex items-center justify-between border-b border-border/80 pb-2.5">
          <span className="font-extrabold text-foreground flex items-center gap-2 text-sm">
            <Layers className="h-4 w-4 text-accent" />
            <span>Architectural Clusters</span>
          </span>
          <button
            onClick={() => { setSelectedCommunity('all'); setSelectedType('all'); setShowGodNodesOnly(false); }}
            className="text-xs text-primary hover:underline font-semibold"
          >
            Reset
          </button>
        </div>

        {/* Communities List */}
        <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
          <button
            onClick={() => setSelectedCommunity('all')}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs sm:text-sm transition-all ${
              selectedCommunity === 'all'
                ? 'bg-secondary text-foreground font-extrabold border border-border shadow-sm'
                : 'text-muted-foreground hover:bg-card hover:text-foreground'
            }`}
          >
            <span>All Architectural Layers</span>
            <span className="text-xs bg-card font-bold px-2 py-0.5 rounded-md text-primary border border-border">
              {data.nodes.length}
            </span>
          </button>

          {Object.values(data.communities).map((comm) => (
            <button
              key={comm.id}
              onClick={() => setSelectedCommunity(comm.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs sm:text-sm transition-all ${
                selectedCommunity === comm.id
                  ? 'bg-secondary text-foreground font-extrabold border shadow-sm'
                  : 'text-muted-foreground hover:bg-card hover:text-foreground'
              }`}
              style={{
                borderColor: selectedCommunity === comm.id ? comm.color : 'transparent',
              }}
            >
              <div className="flex items-center gap-2 truncate">
                <span className="h-2.5 w-2.5 rounded-full shrink-0 shadow-sm" style={{ backgroundColor: comm.color }} />
                <span className="truncate">{comm.name}</span>
              </div>
              <span className="text-xs bg-card font-bold px-2 py-0.5 rounded-md text-foreground shrink-0 border border-border">
                {data.nodes.filter((n) => n.communityId === comm.id).length}
              </span>
            </button>
          ))}
        </div>

        {/* Toggles: Hubs Only */}
        <div className="pt-2.5 border-t border-border/80 space-y-2.5">
          <div className="flex items-center justify-between bg-card/60 p-2 rounded-xl border border-border">
            <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
              <Flame className="h-3.5 w-3.5 text-bounty-gold" />
              <span>Hubs & God Nodes Only</span>
            </span>
            <input
              type="checkbox"
              checked={showGodNodesOnly}
              onChange={(e) => setShowGodNodesOnly(e.target.checked)}
              className="accent-bounty-gold cursor-pointer h-4 w-4 rounded"
            />
          </div>

          {/* Node Type Selector */}
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {['all', 'class', 'function', 'module', 'file'].map((type) => (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className={`px-2.5 py-1 rounded-lg text-xs uppercase font-mono transition-all ${
                  selectedType === type
                    ? 'bg-primary text-primary-foreground font-extrabold shadow-sm'
                    : 'bg-card text-muted-foreground border border-border hover:text-foreground hover:bg-secondary'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 3. MAIN SVG GRAPH CANVAS */}
      <div className="flex-1 w-full h-full relative">
        <svg
          className="w-full h-full cursor-grab active:cursor-grabbing"
          viewBox="0 0 1200 900"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            {/* Edge Gradients */}
            <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.4" />
            </linearGradient>
            <linearGradient id="active-edge" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#ec4899" stopOpacity="0.8" />
            </linearGradient>

            {/* Glowing Arrow Markers */}
            <marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" opacity="0.8" />
            </marker>
            <marker id="arrow-selected" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#10b981" />
            </marker>
          </defs>

          {/* Dynamic Transform Layer for Zoom and Pan */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Subtle Cyberspace Grid Lines */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#27272a" strokeWidth="0.5" strokeOpacity="0.4" />
            </pattern>
            <rect x="-2000" y="-2000" width="4000" height="4000" fill="url(#grid)" />

            {/* Render Dependency Edges with Smooth Bezier Curves */}
            {visibleEdges.map((edge) => {
              const src = nodePositions.get(edge.source);
              const tgt = nodePositions.get(edge.target);
              if (!src || !tgt) return null;

              const isLinkedToSelected =
                selectedNode && (selectedNode.id === edge.source || selectedNode.id === edge.target);

              // Curved Bezier Path
              const dx = tgt.x - src.x;
              const dy = tgt.y - src.y;
              const cx = (src.x + tgt.x) / 2 - dy * 0.15;
              const cy = (src.y + tgt.y) / 2 + dx * 0.15;
              const pathData = `M ${src.x} ${src.y} Q ${cx} ${cy} ${tgt.x} ${tgt.y}`;

              return (
                <g key={edge.id}>
                  <path
                    d={pathData}
                    fill="none"
                    stroke={isLinkedToSelected ? '#10b981' : edge.isExtracted ? '#3f3f46' : '#27272a'}
                    strokeWidth={isLinkedToSelected ? 3 : edge.isExtracted ? 1.5 : 1}
                    strokeDasharray={edge.isExtracted ? undefined : '4 3'}
                    opacity={isLinkedToSelected ? 0.95 : 0.6}
                    markerEnd={isLinkedToSelected ? 'url(#arrow-selected)' : 'url(#arrow)'}
                    className="transition-colors duration-200"
                  />

                  {/* Flowing particle animation on selected edges */}
                  {isLinkedToSelected && (
                    <circle r="3.5" fill="#10b981">
                      <animateMotion dur="2.2s" repeatCount="indefinite" path={pathData} />
                    </circle>
                  )}
                </g>
              );
            })}

            {/* Render AST Nodes (Enlarged for Clear Readability) */}
            {filteredNodes.map((node) => {
              const pos = nodePositions.get(node.id);
              if (!pos) return null;

              const isSelected = selectedNode?.id === node.id;
              const isHovered = hoveredNode?.id === node.id;
              const community = data.communities[node.communityId];
              const nodeColor = node.isTarget
                ? '#10b981'
                : node.isGodNode
                ? '#f59e0b'
                : community?.color || '#a855f7';

              const radius = node.isGodNode ? 26 : node.isTarget ? 22 : 17;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFocusNode(node);
                  }}
                  onMouseEnter={() => setHoveredNode(node)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className="cursor-pointer transition-transform duration-200 hover:scale-125"
                >
                  {/* Glowing Outer Halo for God Nodes & Target Nodes */}
                  {(isSelected || node.isGodNode || node.isTarget) && (
                    <circle
                      r={radius + (isSelected ? 12 : 7)}
                      fill="none"
                      stroke={nodeColor}
                      strokeWidth={isSelected ? 3.5 : 2}
                      opacity={isSelected ? 0.8 : 0.4}
                      className={node.isGodNode || isSelected ? 'animate-pulse' : ''}
                    />
                  )}

                  {/* Main Node Body */}
                  <circle
                    r={radius}
                    fill="#09090b"
                    stroke={nodeColor}
                    strokeWidth={isSelected ? 4 : 2.5}
                    className="shadow-2xl"
                  />

                  {/* Inner Node Icon Glyphs (Larger Text) */}
                  {node.type === 'class' && (
                    <text textAnchor="middle" y="5" fill={nodeColor} fontSize="12" fontWeight="bold">C</text>
                  )}
                  {node.type === 'function' && (
                    <text textAnchor="middle" y="5" fill={nodeColor} fontSize="13" fontWeight="bold">ƒ</text>
                  )}
                  {node.type === 'module' && (
                    <text textAnchor="middle" y="5" fill={nodeColor} fontSize="12" fontWeight="bold">M</text>
                  )}
                  {node.type === 'file' && (
                    <text textAnchor="middle" y="5" fill={nodeColor} fontSize="11" fontWeight="bold">📄</text>
                  )}

                  {/* Node Label Text (High Readability) */}
                  <text
                    y={radius + 16}
                    textAnchor="middle"
                    fill={isSelected ? '#ffffff' : isHovered ? '#38bdf8' : '#f4f4f5'}
                    fontSize={isSelected ? '14' : '12'}
                    fontWeight={isSelected || node.isGodNode ? 'bold' : '600'}
                    className="font-mono select-none drop-shadow-[0_2px_6px_rgba(0,0,0,0.95)]"
                  >
                    {node.label}
                  </text>

                  {/* God Node Star Icon Badge */}
                  {node.isGodNode && (
                    <text x={radius - 2} y={-radius + 4} fontSize="13" fill="#f59e0b">★</text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* 4. RIGHT SLIDE-OUT AST NODE INSPECTOR & CODE SANDBOX (Larger Fonts & Clear Details) */}
      {selectedNode && (
        <div className="absolute top-16 right-3 z-20 w-96 sm:w-[420px] rounded-2xl border border-border bg-background/95 p-6 font-mono text-xs sm:text-sm text-foreground shadow-2xl backdrop-blur-2xl space-y-4 pointer-events-auto max-h-[82vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-border/80 pb-3.5 gap-2">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <FileCode className="h-5 w-5 text-primary shrink-0" />
                <h3 className="font-extrabold text-base sm:text-lg text-foreground truncate">{selectedNode.label}</h3>
              </div>
              <p className="text-xs sm:text-sm text-accent font-semibold">{selectedNode.communityName}</p>
            </div>

            <div className="flex items-center gap-1.5">
              <Badge
                variant={selectedNode.isTarget ? 'emerald' : selectedNode.isGodNode ? 'amber' : 'outline'}
                className="text-xs uppercase font-extrabold px-2.5 py-0.5"
              >
                {selectedNode.type}
              </Badge>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-muted-foreground hover:text-foreground px-2 py-1 rounded text-sm font-bold"
              >
                ✕
              </button>
            </div>
          </div>

          {/* File Path + Copy */}
          {selectedNode.file && (
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">Source File Location:</span>
              <div className="flex items-center justify-between bg-card/90 border border-border p-2.5 rounded-xl text-xs sm:text-sm">
                <code className="text-accent truncate mr-2 font-mono">{selectedNode.file}{selectedNode.line ? `:${selectedNode.line}` : ''}</code>
                <button
                  onClick={() => handleCopyPath(selectedNode.file || '')}
                  className="text-muted-foreground hover:text-foreground shrink-0 p-1 hover:bg-secondary rounded"
                  title="Copy File Path"
                >
                  {copiedPath ? <Check className="h-4 w-4 text-primary" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
            </div>
          )}

          {/* Centrality & Impact Metrics */}
          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="rounded-xl bg-card/70 border border-border p-3">
              <span className="text-xs text-muted-foreground block font-semibold">AST Centrality</span>
              <span className="text-base sm:text-lg font-extrabold text-foreground">{selectedNode.degree} Edges</span>
            </div>
            <div className="rounded-xl bg-card/70 border border-border p-3">
              <span className="text-xs text-muted-foreground block font-semibold">Blast Radius Impact</span>
              <span className="text-base sm:text-lg font-extrabold text-primary">
                {selectedNode.blastRadiusConfidence ? `${Math.round(selectedNode.blastRadiusConfidence * 100)}% Match` : 'Localized Hub'}
              </span>
            </div>
          </div>

          {/* Callers & Callees Dependency Graph Navigation */}
          <div className="space-y-2.5 pt-2 border-t border-border/80">
            <span className="text-xs sm:text-sm font-bold text-foreground flex items-center gap-2">
              <GitFork className="h-4 w-4 text-accent" />
              <span>Dependency Traces (Click to Jump)</span>
            </span>

            {/* Inbound Callers */}
            <div className="space-y-1.5">
              <span className="text-xs text-muted-foreground font-semibold">Upstream Callers ({nodeConnections.callers.length}):</span>
              <div className="flex flex-wrap gap-1.5">
                {nodeConnections.callers.length === 0 ? (
                  <span className="text-xs text-muted-foreground">No incoming caller edges</span>
                ) : (
                  nodeConnections.callers.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => handleFocusNode(c)}
                      className="px-2.5 py-1 rounded-lg bg-card hover:bg-primary border border-border hover:border-primary text-xs text-foreground transition-colors flex items-center gap-1.5 font-medium"
                    >
                      <span>{c.label}</span>
                      <ArrowRight className="h-3 w-3 text-primary" />
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Outbound Callees */}
            <div className="space-y-1.5 pt-1.5">
              <span className="text-xs text-muted-foreground font-semibold">Downstream Callees ({nodeConnections.callees.length}):</span>
              <div className="flex flex-wrap gap-1.5">
                {nodeConnections.callees.length === 0 ? (
                  <span className="text-xs text-muted-foreground">No outgoing dependency edges</span>
                ) : (
                  nodeConnections.callees.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => handleFocusNode(c)}
                      className="px-2.5 py-1 rounded-lg bg-card hover:bg-accent border border-border hover:border-accent text-xs text-foreground transition-colors flex items-center gap-1.5 font-medium"
                    >
                      <ArrowLeft className="h-3 w-3 text-accent" />
                      <span>{c.label}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Action Bar */}
          <div className="pt-2.5 border-t border-border/80 flex items-center gap-2">
            <Button
              variant="glow"
              size="default"
              className="w-full text-xs sm:text-sm font-bold gap-2 h-10 shadow-lg"
              onClick={() => handleFocusNode(selectedNode)}
            >
              <Crosshair className="h-4 w-4" />
              <span>Center in Viewport</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
