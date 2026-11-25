import { describe, expect, it } from 'vitest';
import { canConnectNodes, isValidGraphConnection } from '../pipelineConnectionRules';
import type { CatalogNodeType, DataFlowGraph, DataFlowNode } from '@/services/dataFlowService';

const CATALOG: CatalogNodeType[] = [
  { type: 'source.google_drive', category: 'sources', label: 'GDrive', description: '', icon: 'folder' },
  { type: 'source.social_listening', category: 'sources', label: 'Social', description: '', icon: 'megaphone-or-rss' },
  { type: 'transform.map_fields', category: 'transform', label: 'Map', description: '', icon: 'shuffle' },
  { type: 'sink.verify', category: 'sinks', label: 'Verify', description: '', icon: 'check-circle' },
];

function node(id: string, type: string): DataFlowNode {
  return { id, type, params: {}, ui: { position: { x: 0, y: 0 } } };
}

describe('pipelineConnectionRules', () => {
  it('rejects source to source', () => {
    const a = node('a', 'source.google_drive');
    const b = node('b', 'source.social_listening');
    expect(canConnectNodes(a, b, CATALOG).allowed).toBe(false);
  });

  it('allows source to transform', () => {
    const a = node('a', 'source.google_drive');
    const b = node('b', 'transform.map_fields');
    expect(canConnectNodes(a, b, CATALOG).allowed).toBe(true);
  });

  it('rejects sink onward', () => {
    const a = node('a', 'sink.verify');
    const b = node('b', 'transform.map_fields');
    expect(canConnectNodes(a, b, CATALOG).allowed).toBe(false);
  });

  it('rejects duplicate edge', () => {
    const graph: DataFlowGraph = {
      nodes: [node('a', 'source.google_drive'), node('b', 'transform.map_fields')],
      edges: [{ id: 'e1', source: 'a', target: 'b' }],
    };
    expect(isValidGraphConnection('a', 'b', graph, CATALOG).allowed).toBe(false);
  });
});