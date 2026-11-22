import { describe, expect, it } from 'vitest';
import { addPaletteNode } from '../PipelineGraphCanvas';
import { defaultGraphForSource, emptyGraph } from '../pipelineStudioState';

describe('defaultGraphForSource', () => {
  it('builds linear chain for generic source', () => {
    const g = defaultGraphForSource('generic', 'rule-1');
    expect(g.nodes[0].type).toBe('source.external_feed');
    expect(g.edges.length).toBe(g.nodes.length - 1);
    expect(g.nodes.some(n => n.type === 'sink.register_vdl')).toBe(false);
  });

  it('includes VDL sinks for external_full', () => {
    const g = defaultGraphForSource('external_full');
    expect(g.nodes[0].type).toBe('source.external_full');
    expect(g.nodes.some(n => n.type === 'sink.register_vdl')).toBe(true);
    expect(g.nodes.some(n => n.type === 'sink.materialize_warehouse')).toBe(true);
  });
});

describe('empty canvas', () => {
  it('starts with no nodes', () => {
    expect(emptyGraph().nodes).toEqual([]);
  });

  it('appends a source from the palette', () => {
    const next = addPaletteNode(emptyGraph(), 'source.kafka', [
      { type: 'source.kafka', category: 'sources', label: 'Kafka topic', description: '', icon: 'refresh' },
    ]);
    expect(next.nodes).toHaveLength(1);
    expect(next.nodes[0].type).toBe('source.kafka');
  });
});