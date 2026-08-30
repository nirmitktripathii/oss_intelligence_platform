export interface GraphNode {
  id: string;
  label: string;
  type: 'file' | 'function' | 'class' | 'module' | 'subsystem';
  file?: string;
  line?: number;
  communityId: number;
  communityName: string;
  confidence: number;
  degree: number;
  isGodNode?: boolean;
  isTarget?: boolean;
  blastRadiusConfidence?: number;
  x?: number;
  y?: number;
  size?: number;
  color?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: 'imports' | 'calls' | 'extends' | 'instantiates' | 'inferred';
  confidence: number;
  isExtracted: boolean; // True for strict AST, False for heuristic inference
}

export interface CommunityCluster {
  id: number;
  name: string;
  color: string;
  nodeCount: number;
  description: string;
}

export interface ASTGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  communities: Record<number, CommunityCluster>;
  godNodes: string[];
  metadata: {
    totalFiles: number;
    totalFunctions: number;
    totalClasses: number;
    generatedAt: string;
    repoName?: string;
  };
}

export interface GraphStats {
  totalNodes: number;
  totalEdges: number;
  clusterCount: number;
  godNodesCount: number;
  density: number;
}
