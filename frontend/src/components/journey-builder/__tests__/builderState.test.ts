import { describe, expect, it } from 'vitest';
import {
  toBuilderRequest, toBuilderRequestMultiStage, applyValidationToNodes,
  consumedParamsOf, makeEdgeId,
  encodeOutputHandle, encodeInputHandle, decodeOutputHandle, decodeInputHandle,
  verticalChainLayout, defaultStage, newStage,
  type BuilderNode, type BuilderGraphEdge, type BuilderValidationReport,
  type BuilderStageState,
} from '../builderState';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function _node(id: string, tool: string, params: Record<string, unknown> = {}): BuilderNode {
  return {
    id,
    type: 'tool',
    position: { x: 0, y: 0 },
    data: { tool, name: tool, params },
  };
}

function _edge(args: { source: string; from_key: string; target: string; to_param: string }): BuilderGraphEdge {
  return {
    id: makeEdgeId({
      source: args.source,
      target: args.target,
      sourceHandle: encodeOutputHandle(args.from_key),
      targetHandle: encodeInputHandle(args.to_param),
    }),
    source: args.source,
    target: args.target,
    sourceHandle: encodeOutputHandle(args.from_key),
    targetHandle: encodeInputHandle(args.to_param),
  };
}

// ---------------------------------------------------------------------------
// Handle encoding round-trip
// ---------------------------------------------------------------------------

describe('handle encoding', () => {
  it('output handle: encode + decode round trips the key', () => {
    const enc = encodeOutputHandle('results.0.customer_id');
    expect(enc).toBe('out:results.0.customer_id');
    expect(decodeOutputHandle(enc)).toBe('results.0.customer_id');
  });

  it('input handle: encode + decode round trips the param name', () => {
    const enc = encodeInputHandle('customer_id');
    expect(enc).toBe('in:customer_id');
    expect(decodeInputHandle(enc)).toBe('customer_id');
  });

  it('returns null when the prefix does not match', () => {
    expect(decodeOutputHandle('in:foo')).toBe(null);
    expect(decodeInputHandle('out:foo')).toBe(null);
    expect(decodeOutputHandle(null)).toBe(null);
    expect(decodeInputHandle(undefined)).toBe(null);
  });
});

// ---------------------------------------------------------------------------
// toBuilderRequest
// ---------------------------------------------------------------------------

describe('toBuilderRequest', () => {
  it('emits steps and edges in the wire shape, stripping graph positions', () => {
    const nodes = [
      _node('s1', 'find_churning_customers'),
      _node('s2', 'apply_promo_discount', { discount_pct: 12.5 }),
    ];
    const edges = [_edge({ source: 's1', from_key: 'results.0.customer_id', target: 's2', to_param: 'customer_id' })];
    const req = toBuilderRequest({
      nodes, edges,
      name: 'Retain risky customers',
      displayName: 'Retain risky customers',
      description: 'save play',
      trigger: 'manual',
    });
    expect(req.steps).toHaveLength(2);
    expect(req.steps[0]).toMatchObject({ id: 's1', tool: 'find_churning_customers' });
    expect(req.steps[1].params).toEqual({ discount_pct: 12.5 });
    expect(req.edges).toEqual([{
      from_node: 's1', from_key: 'results.0.customer_id',
      to_node: 's2', to_param: 'customer_id',
    }]);
  });

  it('drops nodes without a tool and edges that reference them', () => {
    const nodes = [
      _node('s1', 'find_churning_customers'),
      { id: 's2', type: 'tool', position: { x: 0, y: 0 }, data: { tool: '', name: 'empty', params: {} } } as BuilderNode,
    ];
    const edges = [_edge({ source: 's1', from_key: 'results', target: 's2', to_param: 'customer_id' })];
    const req = toBuilderRequest({ nodes, edges, name: 'x' });
    expect(req.steps.map((s) => s.id)).toEqual(['s1']);
    expect(req.edges).toEqual([]);
  });

  it('defaults solution_id to builder when not supplied', () => {
    const req = toBuilderRequest({ nodes: [_node('s1', 'x')], edges: [], name: 'y' });
    expect(req.solution_id).toBe('builder');
  });

  it('defaults bucket to "default" and round-trips a supplied bucket', () => {
    const reqDefault = toBuilderRequest({ nodes: [_node('s1', 'x')], edges: [], name: 'y' });
    expect(reqDefault.bucket).toBe('default');

    const reqCustom = toBuilderRequest({
      nodes: [_node('s1', 'x')], edges: [], name: 'y', bucket: 'customer-360',
    });
    expect(reqCustom.bucket).toBe('customer-360');
  });

  it('always emits a connections array (empty by default for legacy graphs)', () => {
    const req = toBuilderRequest({ nodes: [_node('s1', 'x')], edges: [], name: 'y' });
    expect(req.connections).toEqual([]);
  });

  it('emits one connection per edge with the decoded handle as from_relationship', () => {
    const nodes = [_node('s1', 'find_churning_customers'), _node('s2', 'apply_promo_discount')];
    const edges = [_edge({ source: 's1', from_key: 'matched', target: 's2', to_param: 'customer_id' })];
    const req = toBuilderRequest({
      nodes, edges, name: 'demo',
      toolRelationships: {
        find_churning_customers: [{ name: 'matched' }, { name: 'no_match', auto_terminate_default: true }],
      },
    });
    expect(req.connections).toEqual([{
      from_step: 's1', from_relationship: 'matched', from_path: undefined,
      to_step: 's2', to_param: 'customer_id',
    }]);
  });

  it('defaults execution_mode to dataflow', () => {
    const req = toBuilderRequest({ nodes: [_node('s1', 'x')], edges: [], name: 'y' });
    expect(req.execution_mode).toBe('dataflow');
  });

  it('forces empty edges + connections when executionMode is sequential', () => {
    const nodes = [_node('s1', 'a'), _node('s2', 'b')];
    const edges = [_edge({ source: 's1', from_key: 'results', target: 's2', to_param: 'x' })];
    const req = toBuilderRequest({ nodes, edges, name: 'y', executionMode: 'sequential' });
    expect(req.execution_mode).toBe('sequential');
    expect(req.edges).toEqual([]);
    expect(req.connections).toEqual([]);
  });

  it('coerces hint-keyed source handles to from_relationship=success + from_path=<key>', () => {
    // Background: ConnectionDoc.from_relationship is a slug-validated
    // Pydantic field (a-z0-9_- only). Hint-keyed handles like
    // "results.0.customer_id" carry dots / digits-first segments and
    // would 422 the wire out. The serialiser coerces them into the
    // default ``success`` channel and parks the dotted path in
    // ``from_path`` so the runner can still resolve via substitution.
    const nodes = [_node('s1', 'unmigrated'), _node('s2', 'consumer')];
    const edges = [_edge({ source: 's1', from_key: 'results.0.customer_id', target: 's2', to_param: 'customer_id' })];
    const req = toBuilderRequest({
      nodes, edges, name: 'demo',
      toolRelationships: { unmigrated: [{ name: 'success' }] },
    });
    expect(req.connections).toEqual([{
      from_step: 's1', from_relationship: 'success',
      from_path: 'results.0.customer_id',
      to_step: 's2', to_param: 'customer_id',
    }]);
    // Legacy ``edges`` field is still emitted unchanged.
    expect(req.edges).toEqual([{
      from_node: 's1', from_key: 'results.0.customer_id',
      to_node: 's2', to_param: 'customer_id',
    }]);
  });
});

// ---------------------------------------------------------------------------
// applyValidationToNodes
// ---------------------------------------------------------------------------

describe('applyValidationToNodes', () => {
  it('returns an empty map when no report or report.report is set', () => {
    expect(applyValidationToNodes(null, []).size).toBe(0);
    const report: BuilderValidationReport = { valid: true, errors: [], warnings: [] };
    expect(applyValidationToNodes(report, []).size).toBe(0);
  });

  it('buckets issues by step index in the validation path', () => {
    const nodes = [_node('s1', 'a'), _node('s2', 'b'), _node('s3', 'c')];
    const report: BuilderValidationReport = {
      valid: false,
      errors: ['x'],
      warnings: ['y'],
      report: {
        errors: [
          { severity: 'error', path: 'stages[0].steps[1].bindings[0]', code: 'unknown_tool', message: 'no such tool' },
        ],
        warnings: [
          { severity: 'warning', path: 'stages[0].steps[2]', code: 'no_tool', message: 'LLM-only step' },
        ],
      },
    };
    const m = applyValidationToNodes(report, nodes);
    expect(m.get('s1')).toBeUndefined();
    expect(m.get('s2')?.[0].code).toBe('unknown_tool');
    expect(m.get('s3')?.[0].code).toBe('no_tool');
  });

  it('ignores issues whose step index is out of range', () => {
    const nodes = [_node('s1', 'a')];
    const report: BuilderValidationReport = {
      valid: false, errors: [], warnings: [],
      report: {
        errors: [{ severity: 'error', path: 'stages[0].steps[42]', code: 'x', message: 'far' }],
        warnings: [],
      },
    };
    expect(applyValidationToNodes(report, nodes).size).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// consumedParamsOf
// ---------------------------------------------------------------------------

describe('consumedParamsOf', () => {
  it('returns the set of param names already wired into a node', () => {
    const edges = [
      _edge({ source: 's1', from_key: 'a', target: 's2', to_param: 'x' }),
      _edge({ source: 's1', from_key: 'b', target: 's2', to_param: 'y' }),
      _edge({ source: 's3', from_key: 'c', target: 's4', to_param: 'z' }),
    ];
    const consumed = consumedParamsOf('s2', edges);
    expect(Array.from(consumed).sort()).toEqual(['x', 'y']);
  });

  it('returns an empty set when no edges target the node', () => {
    expect(consumedParamsOf('s1', []).size).toBe(0);
  });
});


// ---------------------------------------------------------------------------
// verticalChainLayout (sequential mode positioning)
// ---------------------------------------------------------------------------

describe('verticalChainLayout', () => {
  it('places nodes in a single column ordered by topo position', () => {
    const nodes = [_node('s1', 'a'), _node('s2', 'b'), _node('s3', 'c')];
    const order = new Map([['s1', 1], ['s2', 2], ['s3', 3]]);
    const pos = verticalChainLayout(nodes, order);
    const xs = ['s1', 's2', 's3'].map((id) => pos.get(id)!.x);
    expect(new Set(xs).size).toBe(1); // all on the same column
    // y strictly increasing.
    const ys = ['s1', 's2', 's3'].map((id) => pos.get(id)!.y);
    expect(ys[0]).toBeLessThan(ys[1]);
    expect(ys[1]).toBeLessThan(ys[2]);
  });

  it('falls back to insertion order when topo position is missing', () => {
    const nodes = [_node('a', 'x'), _node('b', 'y')];
    const pos = verticalChainLayout(nodes, new Map()); // no order info
    expect(pos.get('a')!.y).toBeLessThan(pos.get('b')!.y);
  });
});


// ---------------------------------------------------------------------------
// Multi-stage canvas state + serialiser
// ---------------------------------------------------------------------------

describe('multi-stage serialiser', () => {
  it('defaultStage returns a single "main" stage', () => {
    const s = defaultStage();
    expect(s.stageId).toBe('main');
    expect(s.name).toBe('Main');
    expect(s.order).toBe(1);
    expect(s.nodes).toEqual([]);
    expect(s.edges).toEqual([]);
  });

  it('newStage allocates a unique slug and bumps the order', () => {
    const existing: BuilderStageState[] = [
      defaultStage(),
      { stageId: 'stage_2', name: 'Stage 2', order: 2, nodes: [], edges: [] },
    ];
    const next = newStage(existing);
    expect(next.stageId).toBe('stage_3');
    expect(next.order).toBe(3);
  });

  it('toBuilderRequestMultiStage emits stages[] preserving per-stage steps', () => {
    const s1: BuilderStageState = {
      stageId: 'discover', name: 'Discover', order: 1,
      nodes: [_node('s1', 'find_churning_customers')], edges: [],
    };
    const s2: BuilderStageState = {
      stageId: 'act', name: 'Act', order: 2,
      nodes: [_node('s2', 'assign_csm_outreach', { account_id: 'X' })], edges: [],
    };
    const req = toBuilderRequestMultiStage({
      stages: [s1, s2], name: 'demo',
    });
    expect(req.stages).toBeDefined();
    expect(req.stages!.length).toBe(2);
    expect(req.stages![0].stage_id).toBe('discover');
    expect(req.stages![0].order).toBe(1);
    expect(req.stages![0].steps.map((s) => s.id)).toEqual(['s1']);
    expect(req.stages![1].stage_id).toBe('act');
    expect(req.stages![1].steps.map((s) => s.id)).toEqual(['s2']);
  });

  it('multi-stage sequential mode forces empty connections AND edges on every stage', () => {
    const s1: BuilderStageState = {
      stageId: 'a', name: 'A', order: 1,
      nodes: [_node('s1', 'a'), _node('s2', 'b')],
      edges: [_edge({ source: 's1', from_key: 'results', target: 's2', to_param: 'x' })],
    };
    const req = toBuilderRequestMultiStage({
      stages: [s1], name: 'seq', executionMode: 'sequential',
    });
    expect(req.execution_mode).toBe('sequential');
    expect(req.stages![0].edges).toEqual([]);
    expect(req.stages![0].connections).toEqual([]);
  });

  it('multi-stage normalises out-of-order stage.order to 1..N', () => {
    const stages: BuilderStageState[] = [
      { stageId: 'c', name: 'C', order: 99, nodes: [], edges: [] },
      { stageId: 'a', name: 'A', order: 10, nodes: [], edges: [] },
      { stageId: 'b', name: 'B', order: 50, nodes: [], edges: [] },
    ];
    const req = toBuilderRequestMultiStage({ stages, name: 'reord' });
    expect(req.stages!.map((s) => s.stage_id)).toEqual(['a', 'b', 'c']);
    expect(req.stages!.map((s) => s.order)).toEqual([1, 2, 3]);
  });
});
