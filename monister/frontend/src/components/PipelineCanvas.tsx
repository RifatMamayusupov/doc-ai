/**
 * Pipeline Canvas Component - Center zone
 * Visual node-based representation of agent workflow with real-time data preview
 */

import { useMemo, useEffect } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    MarkerType,
    Handle,
    Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useMonisterStore } from '../stores/monisterStore';

// Custom node component with data preview
function ToolNode({ data }: { data: { label: string; status: string; dataPreview?: string; summary?: string } }) {
    const statusColors: Record<string, string> = {
        idle: '#6b7280',
        running: '#fbbf24',
        complete: '#10b981',
        error: '#ef4444',
    };

    const statusIcons: Record<string, string> = {
        idle: '⏸️',
        running: '⚡',
        complete: '✅',
        error: '❌',
    };

    return (
        <div
            className="tool-node"
            style={{
                borderColor: statusColors[data.status] || '#6b7280',
                minWidth: '180px',
            }}
        >
            <Handle type="target" position={Position.Top} />

            {/* Header */}
            <div className="tool-node-header" style={{ backgroundColor: statusColors[data.status] + '20' }}>
                <span className="tool-node-icon">{statusIcons[data.status]}</span>
                <span className="tool-node-label">{data.label}</span>
            </div>

            {/* Data Preview */}
            {data.dataPreview && (
                <div className="tool-node-preview">
                    <pre>{data.dataPreview}</pre>
                </div>
            )}

            {/* Summary */}
            {data.summary && (
                <div className="tool-node-summary">
                    📊 {data.summary}
                </div>
            )}

            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

// Input node
function InputNode({ data }: { data: { label: string } }) {
    return (
        <div className="input-node">
            <span>📥 {data.label}</span>
            <Handle type="source" position={Position.Bottom} />
        </div>
    );
}

// Output node
function OutputNode({ data }: { data: { label: string } }) {
    return (
        <div className="output-node">
            <Handle type="target" position={Position.Top} />
            <span>📤 {data.label}</span>
        </div>
    );
}

const nodeTypes = {
    tool: ToolNode,
    input: InputNode,
    output: OutputNode,
};

export function PipelineCanvas() {
    const { pipelineNodes, clearPipeline } = useMonisterStore();

    // Convert pipeline nodes to React Flow nodes
    const flowNodes = useMemo<Node[]>(() => {
        if (pipelineNodes.length === 0) {
            return [
                {
                    id: 'start',
                    type: 'input',
                    position: { x: 250, y: 25 },
                    data: { label: 'Input' },
                },
                {
                    id: 'end',
                    type: 'output',
                    position: { x: 250, y: 250 },
                    data: { label: 'Output' },
                },
            ];
        }

        const nodes: Node[] = [
            {
                id: 'start',
                type: 'input',
                position: { x: 250, y: 25 },
                data: { label: 'Input' },
            },
        ];

        pipelineNodes.forEach((node, index) => {
            nodes.push({
                id: node.id,
                type: 'tool',
                position: { x: 200, y: 120 + index * 120 },
                data: {
                    label: node.label,
                    status: node.status,
                    dataPreview: node.dataPreview,
                    summary: node.summary,
                },
            });
        });

        nodes.push({
            id: 'end',
            type: 'output',
            position: { x: 250, y: 120 + pipelineNodes.length * 120 + 50 },
            data: { label: 'Output' },
        });

        return nodes;
    }, [pipelineNodes]);

    // Create edges
    const flowEdges = useMemo<Edge[]>(() => {
        const edges: Edge[] = [];
        const nodeIds = ['start', ...pipelineNodes.map((n) => n.id), 'end'];

        for (let i = 0; i < nodeIds.length - 1; i++) {
            const sourceStatus = pipelineNodes.find((n) => n.id === nodeIds[i])?.status;

            edges.push({
                id: `e-${nodeIds[i]}-${nodeIds[i + 1]}`,
                source: nodeIds[i],
                target: nodeIds[i + 1],
                animated: sourceStatus === 'running',
                style: {
                    stroke: sourceStatus === 'complete' ? '#10b981' : '#6b7280',
                    strokeWidth: 2,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: sourceStatus === 'complete' ? '#10b981' : '#6b7280',
                },
            });
        }

        return edges;
    }, [pipelineNodes]);

    const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

    // Update nodes when pipeline changes
    useEffect(() => {
        setNodes(flowNodes);
        setEdges(flowEdges);
    }, [flowNodes, flowEdges, setNodes, setEdges]);

    return (
        <div className="pipeline-canvas">
            {/* Header */}
            <div className="canvas-header">
                <h2>🔄 Pipeline</h2>
                {pipelineNodes.length > 0 && (
                    <button className="clear-button" onClick={clearPipeline}>
                        Clear
                    </button>
                )}
            </div>

            {/* React Flow */}
            <div className="canvas-container">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    attributionPosition="bottom-left"
                >
                    <Background color="#1f2937" gap={16} />
                    <Controls />
                    <MiniMap
                        nodeColor={(node) => {
                            if (node.type === 'input') return '#3b82f6';
                            if (node.type === 'output') return '#10b981';
                            const status = (node.data as any)?.status;
                            if (status === 'running') return '#fbbf24';
                            if (status === 'complete') return '#10b981';
                            if (status === 'error') return '#ef4444';
                            return '#6b7280';
                        }}
                    />
                </ReactFlow>
            </div>

            {/* Legend */}
            <div className="canvas-legend">
                <span><span className="dot idle"></span> Idle</span>
                <span><span className="dot running"></span> Running</span>
                <span><span className="dot complete"></span> Complete</span>
                <span><span className="dot error"></span> Error</span>
            </div>
        </div>
    );
}
