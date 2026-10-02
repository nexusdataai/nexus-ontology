import { describe, expect, it } from 'vitest';
import {
  topoOrderClient, makeEdgeId, encodeInputHandle, encodeOutputHandle,
  type BuilderGraphEdge, type BuilderNode,
} from '../builderState';

function _node(id: string): BuilderNode {
  return {
    id,
    type: 'tool',
    position: { x: 0, y: 0 },
    data: { tool: id, name: id, params: {} },
  };
}

function _edge(source: string, target: string, fromKey = 'out', toParam = 'in'): BuilderGraphEdge {
  return {
    id: makeEdgeId({
      source, target,
      sourceHandle: encodeOutputHandle(fromKey),
      targetHandle: encodeInputHandle(toParam),
    }),
    source, target,
    sourceHandle: encodeOutputHandle(fromKey),
    targetHandle: encodeInputHandle(toParam),
  };
}

describe('topoOrderClient', () => {
  it('linear chain returns 1/2/3 in edge order', () => {
    const nodes = [_node('s1'), _node('s2'), _node('s3')];
    const edges = [_edge('s1', 's2'), _edge('s2', 's3')];
    const order = topoOrderClient(nodes, edges);
    expect(order.get('s1')).toBe(1);
    expect(order.get('s2')).toBe(2);
    expect(order.get('s3')).toBe(3);
  });

  it('mid-cycle bump: out-of-insertion-order edges still produce correct topo', () => {
    // s2 -> s1 -> s3 means s2 must come first, despite s1 being
    // inserted first.
    const nodes = [_node('s1'), _node('s2'), _node('s3')];
    const edges = [_edge('s2', 's1'), _edge('s1', 's3')];
    const order = topoOrderClient(nodes, edges);
    expect(order.get('s2')).toBe(1);
    expect(order.get('s1')).toBe(2);
    expect(order.get('s3')).toBe(3);
  });

  it('cycle: every member of the cycle is marked -1', () => {
    const nodes = [_node('s1'), _node('s2'), _node('s3')];
    // s1 -> s2 -> s1 is a 2-cycle; s3 sits outside.
    const edges = [_edge('s1', 's2'), _edge('s2', 's1')];
    const order = topoOrderClient(nodes, edges);
    expect(order.get('s1')).toBe(-1);
    expect(order.get('s2')).toBe(-1);
    expect(order.get('s3')).toBe(1);
  });

  it('isolated nodes fall back to insertion order positions', () => {
    const nodes = [_node('s1'), _node('s2'), _node('s3')];
    const order = topoOrderClient(nodes, []);
    expect(order.get('s1')).toBe(1);
    expect(order.get('s2')).toBe(2);
    expect(order.get('s3')).toBe(3);
  });

  it('empty input returns empty map', () => {
    const order = topoOrderClient([], []);
    expect(order.size).toBe(0);
  });

  it('ignores self-edges for ordering and does not flag the node as a cycle', () => {
    const nodes = [_node('s1'), _node('s2')];
    const edges = [_edge('s1', 's1'), _edge('s1', 's2')];
    const order = topoOrderClient(nodes, edges);
    expect(order.get('s1')).toBe(1);
    expect(order.get('s2')).toBe(2);
  });
});
