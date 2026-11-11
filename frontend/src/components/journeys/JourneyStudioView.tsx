/**
 * JourneyStudioView Component
 *
 * Journey Studio: the page of one journey (object page).
 *
 * Layout: back link and header (name, status, schedule in words, Run / Stop,
 * a "More" menu), the headline figures, then the pipeline as one stepper with
 * the selected step's detail and console below it, the results of the latest
 * run as a short report, recent runs and the schedules.
 *
 * The state, effects, polling and handlers are the logic of the original
 * studio. Presentational pieces live in ./studio.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Icon } from '../ds/Icon';
import { EmptyState } from '../ds/primitives';
import { InlineError, Meter, MetricStrip, StatusPill } from '../ds/kit';
import {
  CallProcessingJourney,
  JourneyStage,
  StageStep,
  JobExecution,
  LogEntry,
} from '../../types/callProcessingJourney';
import { callProcessingJourneyService } from '../../services/callProcessingJourneyService';
import { getKpiDefinition } from '../../config/journeyKpiCatalog';
import { 
  jobStreamService, 
  StepStatusEvent, 
  LogEvent, 
  TaskProgressEvent, 
  JobCompleteEvent,
  logEventToLogEntry 
} from '../../services/jobStreamService';
import { LogsModal } from './LogsModal';
import { StageJobsModal } from './StageJobsModal';
import { StageReportModal } from './StageReportModal';
import { StepConsole } from './StepConsole';
import { BatchScheduleDialog } from './BatchScheduleDialog';
import { BatchSchedulesPanel } from './BatchSchedulesPanel';
import { PendingStepCard } from '@/components/journey-builder/PendingStepCard';
import { StepPipeline, useIsWide, type PipelineStep, type StepStatus } from './studio/StepPipeline';
import { StepDetail } from './studio/StepDetail';
import { RunsTable } from './studio/RunsTable';
import { RunResults } from './studio/RunResults';
import { dayAndTime, humanize, scheduleInWords, sentenceCase, timeOfDay } from './studio/format';

export interface JourneyStudioViewProps {
  journeyId: string;
  onBack: () => void;
  hideBackButton?: boolean;
  hideStatsCards?: boolean;
  hideHeader?: boolean;
  extraHeaderButtons?: React.ReactNode;
  overrideReportButton?: React.ReactNode;
}

// Call Processing Steps Definition
const CALL_PROCESSING_STEPS = [
  {
    id: 'fetch_tasks',
    name: 'Fetch Tasks',
    description: 'Fetch pending call tasks from Webex CC API',
  },
  {
    id: 'deduplication',
    name: 'Deduplication Check',
    description: 'Check for already-processed tasks to avoid duplicates',
  },
  {
    id: 'process_recordings',
    name: 'Process Recordings',
    description: 'Download and transcribe call recordings',
  },
  {
    id: 'register_metadata',
    name: 'Register Metadata',
    description: 'Create metadata and register in AWS Glue catalog',
  },
  {
    id: 'ai_analysis',
    name: 'AI Analysis',
    description: 'Run GPT analysis on transcripts for insights',
  },
  {
    id: 'crm_actions',
    name: 'CRM Actions',
    description: 'Create/update Salesforce leads and opportunities',
  },
];

// Semantic RAG Steps Definition (matches backend SemanticRagStage.steps)
const SEMANTIC_RAG_STEPS = [
  { id: 'extract_unified_schema', name: 'Extract Unified Schema', description: 'Read canonical-entities.yaml into virtual entity docs' },
  { id: 'resolve_fdw_mapping', name: 'Resolve FDW Mapping', description: 'Match schema entities to live FDW + simulator tables' },
  { id: 'extract_mapping_rules', name: 'Extract Mapping Rules', description: 'Read active mapping rules and enrich schema docs' },
  { id: 'extract_policies', name: 'Extract Policies', description: 'Parse business policy documents' },
  { id: 'extract_workflows', name: 'Extract Workflows', description: 'Parse workflow definitions' },
  { id: 'extract_integrations', name: 'Extract Integrations', description: 'Parse integration mappings' },
  { id: 'normalize', name: 'Normalize (.onto)', description: 'Merge, deduplicate, produce .onto bundle' },
  { id: 'enrich', name: 'LLM Enrichment', description: 'Generate semantic descriptions with LLM' },
  { id: 'chunk_embed', name: 'Chunk & Embed', description: 'Semantic chunking + embedding generation' },
  { id: 'load_vector', name: 'Load Vector DB', description: 'Upsert embeddings into pgvector' },
  { id: 'index_nlq_exemplars', name: 'Index NLQ Exemplars', description: 'Generate NLP query exemplars from curated YAML + canonical schema templates and index for AI Query Builder' },
  { id: 'load_graph', name: 'Load Graph DB', description: 'Load relationships into graph DB' },
  { id: 'validate', name: 'Validate Quality', description: 'Run black-box test scenarios' },
];

// Stage definition for call processing (single stage)
const CALL_PROCESSING_STAGE = {
  id: 'call_processing',
  name: 'Call Processing',
  description: 'Process and analyze call recordings from Webex CC',
};

const SEMANTIC_RAG_STAGE = {
  id: 'semantic_rag',
  name: 'Knowledge Processor',
  description: 'Build enterprise knowledge graph from metadata, policies, workflows',
};

const O2C_STEPS = [
  { id: 'entity_resolution', name: 'Entity Resolution', description: 'Match orders across Salesforce, SAP, Oracle' },
  { id: 'three_way_match', name: 'Three-Way Match', description: 'Validate PO qty = delivered qty = invoiced qty' },
  { id: 'anomaly_scoring', name: 'Anomaly Scoring', description: 'Score each order for anomalies vs baselines' },
  { id: 'risk_prioritization', name: 'Risk Prioritization', description: 'Rank orders by composite risk score' },
  { id: 'workflow_actions', name: 'Workflow Actions', description: 'Execute credit holds, disputes, SLA escalations for at-risk orders' },
  { id: 'dunning_and_collections', name: 'Dunning & Collections', description: 'Send collection notices for overdue invoices by aging tier' },
  { id: 'action_summary', name: 'Action Summary', description: 'Summarize all workflow actions taken and generate audit log' },
  { id: 'cash_flow_projection', name: 'Cash Flow Projection', description: 'Project cash inflows from open AR' },
  { id: 'store_results', name: 'Store Results', description: 'Write order data, alerts, KPIs to S3 + simulator' },
  { id: 'verify_results', name: 'Verify Results', description: 'Read back result entities from VDL and display summary' },
];

const O2C_STAGE = {
  id: 'order_to_cash',
  name: 'Order-to-Cash Monitor',
  description: 'Entity resolution, three-way matching, anomaly detection, workflow actions, cash flow projection',
};

const DEMAND_FORECASTING_STEPS = [
  { id: 'feature_engineering', name: 'Feature Engineering', description: 'Aggregate sales history, inventory, promotions, market signals into feature matrix' },
  { id: 'model_ensemble', name: 'Model Ensemble', description: 'Run time-series + ML models in parallel; combine via weighted average' },
  { id: 'promotion_overlay', name: 'Promotion Overlay', description: 'Apply learned promotion response curves per mechanic x category x region' },
  { id: 'cannibalization_adjustment', name: 'Cannibalization Adjustment', description: 'Apply cross-product substitution factors from historical data' },
  { id: 'consensus_integration', name: 'Consensus Integration', description: 'Merge AI forecast with approved Forecast_Override entries from sales team' },
  { id: 'publish_forecast', name: 'Publish Forecast', description: 'Write forecast data, KPIs, alerts to S3 and simulator' },
];

const DEMAND_FORECASTING_STAGE = {
  id: 'demand_forecasting',
  name: 'Demand Forecasting Engine',
  description: 'AI-driven demand prediction across SKUs, regions, and channels',
};

const IO_STEPS = [
  { id: 'load_positions', name: 'Load Positions', description: 'Query inventory positions, materials, plants, batches' },
  { id: 'abc_classification', name: 'ABC Classification', description: 'Classify SKUs by volume and value into A/B/C categories' },
  { id: 'reorder_calculation', name: 'Reorder Calculation', description: 'Calculate safety stock, reorder points, days of supply' },
  { id: 'expiry_analysis', name: 'Expiry Analysis', description: 'Score batch-level shelf-life risk and expiry exposure' },
  { id: 'rebalance_recommendations', name: 'Rebalance Recommendations', description: 'Generate inter-plant transfer suggestions' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write inventory KPIs, alerts, position data to S3 and simulator' },
];
const IO_STAGE = { id: 'inventory_optimization', name: 'Inventory Optimization', description: 'Multi-echelon inventory optimization and distribution intelligence' };

const PA_STEPS = [
  { id: 'load_procurement_data', name: 'Load Procurement Data', description: 'Query purchase orders, invoices, vendors, goods receipts' },
  { id: 'spend_classification', name: 'Spend Classification', description: 'Categorize spending and detect maverick purchases' },
  { id: 'three_way_match', name: 'Three-Way Match', description: 'Reconcile PO vs goods receipt vs invoice' },
  { id: 'price_variance_analysis', name: 'Price Variance Analysis', description: 'Compare contract prices vs actual and identify anomalies' },
  { id: 'vendor_scorecard', name: 'Vendor Scorecard', description: 'Score vendors on delivery, quality, compliance' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write spend KPIs, alerts, analytics to S3 and simulator' },
];
const PA_STAGE = { id: 'procurement_analytics', name: 'Procurement & Spend Analytics', description: 'Spend visibility, maverick detection, intelligent invoice processing' };

const PQ_STEPS = [
  { id: 'load_production_data', name: 'Load Production Data', description: 'Query production orders, lines, BOM, batches, quality inspections' },
  { id: 'oee_calculation', name: 'OEE Calculation', description: 'Calculate Overall Equipment Effectiveness per production line' },
  { id: 'yield_analysis', name: 'Yield Analysis', description: 'Analyze planned vs actual quantities and defects' },
  { id: 'quality_scoring', name: 'Quality Scoring', description: 'Evaluate inspection lot results and first-pass rates' },
  { id: 'schedule_adherence', name: 'Schedule Adherence', description: 'Compare planned vs actual completion dates' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write production KPIs, quality alerts to S3 and simulator' },
];
const PQ_STAGE = { id: 'production_quality', name: 'Production & Quality Copilot', description: 'AI-assisted production scheduling, yield optimization, quality detection' };

const SCR_STEPS = [
  { id: 'load_supplier_data', name: 'Load Supplier Data', description: 'Query vendors, purchase orders, goods receipts, quality data' },
  { id: 'delivery_scoring', name: 'Delivery Scoring', description: 'Calculate on-time delivery rate per vendor' },
  { id: 'quality_scoring', name: 'Quality Scoring', description: 'Evaluate inspection pass rates and rejection history' },
  { id: 'financial_risk', name: 'Financial Risk', description: 'Assess payment terms, concentration, single-source exposure' },
  { id: 'market_signal_integration', name: 'Market Signal Integration', description: 'Integrate external disruption signals' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write risk scores, KPIs, alerts to S3 and simulator' },
];
const SCR_STAGE = { id: 'supply_chain_risk', name: 'Supply Chain Risk Radar', description: 'Real-time supplier risk scoring and early warning' };

const C360_STEPS = [
  { id: 'load_customer_data', name: 'Load Customer Data', description: 'Query accounts, opportunities, invoices, payments, sentiment' },
  { id: 'clv_calculation', name: 'CLV Calculation', description: 'Calculate customer lifetime value from revenue and frequency' },
  { id: 'churn_prediction', name: 'Churn Prediction', description: 'Score churn risk from behavioral signals and sentiment' },
  { id: 'wallet_share_analysis', name: 'Wallet Share Analysis', description: 'Estimate share of customer spend vs potential' },
  { id: 'cross_sell_scoring', name: 'Cross-Sell Scoring', description: 'Identify product affinity and whitespace opportunities' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write customer profiles, KPIs, alerts to S3 and simulator' },
];
const C360_STAGE = { id: 'customer_360', name: 'Customer 360 & Revenue Growth', description: 'Unified customer profiles with churn prediction and cross-sell' };

const ESG_STEPS = [
  { id: 'load_esg_data', name: 'Load ESG Data', description: 'Query plants, materials, production, sustainability reports' },
  { id: 'carbon_footprint', name: 'Carbon Footprint', description: 'Calculate production emissions, transport, energy usage' },
  { id: 'water_and_waste', name: 'Water & Waste', description: 'Analyze water consumption and waste generation per plant' },
  { id: 'packaging_analysis', name: 'Packaging Analysis', description: 'Evaluate recycled content vs sustainability targets' },
  { id: 'sentiment_integration', name: 'Sentiment Integration', description: 'Integrate brand sustainability perception' },
  { id: 'publish_results', name: 'Publish Results', description: 'Write ESG scores, KPIs, alerts to S3 and simulator' },
];
const ESG_STAGE = { id: 'esg_sustainability', name: 'ESG & Sustainability Tracker', description: 'Carbon footprint tracking, water monitoring, ESG compliance' };

const ETL_PIPELINE_STEPS = [
  { id: 'extract', name: 'Extract Source Data', description: 'Read data from source system (FDW, simulator, API)' },
  { id: 'validate_schema', name: 'Validate Schema', description: 'Validate source data against field definitions' },
  { id: 'transform', name: 'Transform Data', description: 'Apply field mappings and business logic transforms' },
  { id: 'load', name: 'Load Data', description: 'Write transformed data to virtual data layer' },
  { id: 'verify', name: 'Verify Results', description: 'Row count checks, null validation, data quality' },
];

const ETL_PIPELINE_STAGE = {
  id: 'etl_pipeline',
  name: 'ETL Pipeline',
  description: 'Extract, transform, and load data from external sources into the virtual data layer',
};

function isSemanticRag(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('semantic') || journey?.name?.toLowerCase().includes('rag')) return true;
  return stages.some(s =>
    s.id === 'semantic_rag' || s.stageId === 'semantic_rag' ||
    s.name?.includes('Semantic') || s.name?.includes('semantic_rag')
  );
}

function isO2C(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('order') && journey?.name?.toLowerCase().includes('cash')) return true;
  if (journey?.name?.toLowerCase().includes('o2c')) return true;
  return stages.some(s => s.id === 'order_to_cash' || s.stageId === 'order_to_cash');
}

function isDemandForecasting(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('demand') && journey?.name?.toLowerCase().includes('forecast')) return true;
  return stages.some(s => s.id === 'demand_forecasting' || s.stageId === 'demand_forecasting');
}

function isETLPipeline(stages: any[], journey?: any): boolean {
  if (journey?.odaComponentType === 'data-pipeline') return true;
  if (journey?.name?.toLowerCase().includes('etl')) return true;
  return stages.some(s => s.id === 'etl_pipeline' || s.stageId === 'etl_pipeline');
}

function isInventoryOpt(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('inventory')) return true;
  return stages.some(s => s.id === 'inventory_optimization' || s.stageId === 'inventory_optimization');
}

function isProcurementAnalytics(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('procurement') || journey?.name?.toLowerCase().includes('spend')) return true;
  return stages.some(s => s.id === 'procurement_analytics' || s.stageId === 'procurement_analytics');
}

function isProductionQuality(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('production') || journey?.name?.toLowerCase().includes('quality copilot')) return true;
  return stages.some(s => s.id === 'production_quality' || s.stageId === 'production_quality');
}

function isSupplyChainRisk(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('risk') && journey?.name?.toLowerCase().includes('supply')) return true;
  if (journey?.name?.toLowerCase().includes('risk radar')) return true;
  return stages.some(s => s.id === 'supply_chain_risk' || s.stageId === 'supply_chain_risk');
}

function isCustomer360(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('customer') && journey?.name?.toLowerCase().includes('360')) return true;
  if (journey?.name?.toLowerCase().includes('revenue growth')) return true;
  return stages.some(s => s.id === 'customer_360' || s.stageId === 'customer_360');
}

function isESG(stages: any[], journey?: any): boolean {
  if (journey?.name?.toLowerCase().includes('esg') || journey?.name?.toLowerCase().includes('sustainability')) return true;
  return stages.some(s => s.id === 'esg_sustainability' || s.stageId === 'esg_sustainability');
}

// ``copilotSavedDoc`` is the JourneyDoc shape returned by
// ``GET /api/v1/control-plane/journeys/{id}`` -- a Copilot-saved
// journey whose steps are user-defined ReAct tools, not registered
// transformation stages. When supplied, its ``stages[].steps[]``
// drive the studio stepper instead of the hard-coded catalogs.
// Step ids land verbatim from ``step_id`` so the LIVELOG path
// (``/jobs/{job_id}/logs?step_name=<step_id>``) round-trips
// without any name translation.
function projectCopilotStepsFromSavedDoc(savedDoc: any): typeof CALL_PROCESSING_STEPS {
  const stages = Array.isArray(savedDoc?.stages) ? savedDoc.stages : [];
  const out: any[] = [];
  for (const stage of stages) {
    for (const step of (stage.steps || [])) {
      const sid = step.step_id || step.id;
      if (!sid) continue;
      out.push({
        id: sid,
        name: step.name || sid,
        description: step.description || (step.tool ? `Tool: ${step.tool}` : ''),
      });
    }
  }
  return out as typeof CALL_PROCESSING_STEPS;
}

function projectCopilotStageFromSavedDoc(savedDoc: any) {
  const firstStage = (Array.isArray(savedDoc?.stages) && savedDoc.stages[0]) || null;
  return {
    id: firstStage?.stage_id || 'main',
    name: firstStage?.name || savedDoc?.title || 'Main',
    description: firstStage?.description || savedDoc?.description || 'Copilot-authored journey',
  };
}

function getStepsForJourney(
  stages: any[], journey?: any, copilotSavedDoc?: any,
): typeof CALL_PROCESSING_STEPS {
  // Copilot saved doc wins -- its step ids drive the LIVELOG path.
  if (copilotSavedDoc?.stages?.length) {
    const projected = projectCopilotStepsFromSavedDoc(copilotSavedDoc);
    if (projected.length > 0) return projected;
  }
  if (isETLPipeline(stages, journey)) return ETL_PIPELINE_STEPS;
  if (isO2C(stages, journey)) return O2C_STEPS;
  if (isDemandForecasting(stages, journey)) return DEMAND_FORECASTING_STEPS;
  if (isInventoryOpt(stages, journey)) return IO_STEPS;
  if (isProcurementAnalytics(stages, journey)) return PA_STEPS;
  if (isProductionQuality(stages, journey)) return PQ_STEPS;
  if (isSupplyChainRisk(stages, journey)) return SCR_STEPS;
  if (isCustomer360(stages, journey)) return C360_STEPS;
  if (isESG(stages, journey)) return ESG_STEPS;
  return isSemanticRag(stages, journey) ? SEMANTIC_RAG_STEPS : CALL_PROCESSING_STEPS;
}

function getStageForJourney(stages: any[], journey?: any, copilotSavedDoc?: any) {
  if (copilotSavedDoc?.stages?.length) {
    return projectCopilotStageFromSavedDoc(copilotSavedDoc);
  }
  if (isETLPipeline(stages, journey)) return ETL_PIPELINE_STAGE;
  if (isO2C(stages, journey)) return O2C_STAGE;
  if (isDemandForecasting(stages, journey)) return DEMAND_FORECASTING_STAGE;
  if (isInventoryOpt(stages, journey)) return IO_STAGE;
  if (isProcurementAnalytics(stages, journey)) return PA_STAGE;
  if (isProductionQuality(stages, journey)) return PQ_STAGE;
  if (isSupplyChainRisk(stages, journey)) return SCR_STAGE;
  if (isCustomer360(stages, journey)) return C360_STAGE;
  if (isESG(stages, journey)) return ESG_STAGE;
  return isSemanticRag(stages, journey) ? SEMANTIC_RAG_STAGE : CALL_PROCESSING_STAGE;
}

export function JourneyStudioView({ journeyId, onBack, hideBackButton, hideStatsCards, hideHeader, extraHeaderButtons, overrideReportButton }: JourneyStudioViewProps) {
  // Core State
  const [journey, setJourney] = useState<CallProcessingJourney | null>(null);
  const [stages, setStages] = useState<JourneyStage[]>([]);
  // Copilot-saved-journey doc (from GET /api/v1/control-plane/journeys/{id}).
  // When present, drives the step catalog and the Run handler. ``null``
  // for legacy hard-coded journeys. Determined inside loadJourneyData by
  // probing the control-plane endpoint; 404 = not a Copilot journey.
  const [copilotSavedDoc, setCopilotSavedDoc] = useState<any>(null);
  const isCopilotJourney = copilotSavedDoc !== null;
  // Phase-2: pending-step payload from the JobExecution row when the
  // Copilot engine pauses on awaiting_step_approval. Drives the
  // inline PendingStepCard rendered above the stepper.
  const [pendingStep, setPendingStep] = useState<any>(null);
  // The Copilot engine session_id corresponding to the current run.
  // Required to POST /copilot-journey/{session_id}/approve-step. We
  // capture it from the run response so approve/reject hit the right
  // session even across studio remounts.
  const [copilotSessionId, setCopilotSessionId] = useState<string | null>(null);
  const activeSteps = getStepsForJourney(stages, journey, copilotSavedDoc);
  const activeStage = getStageForJourney(stages, journey, copilotSavedDoc);
  // Refs mirroring the latest activeSteps / activeStage. Several long-lived
  // callbacks (handleJobStatusUpdate, pollers, SSE handlers) are wrapped in
  // useCallback with a narrow dependency list and therefore capture a stale
  // closure of these values from the first render — when the journey hasn't
  // loaded yet and getStepsForJourney falls back to CALL_PROCESSING_STEPS.
  // Using refs ensures every callback sees the current step catalog (e.g.
  // SEMANTIC_RAG_STEPS for Knowledge Processor), so per-step log fetches
  // fire for the right step ids.
  //
  // Assignment is done in the render body (not in useEffect) so callbacks
  // that fire between the render commit and the post-commit effects still
  // see the up-to-date value. Writes to refs do not cause re-renders, so
  // this is safe.
  const activeStepsRef = useRef(activeSteps);
  const activeStageRef = useRef(activeStage);
  activeStepsRef.current = activeSteps;
  activeStageRef.current = activeStage;
  const [jobHistory, setJobHistory] = useState<JobExecution[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  
  // Current Job Tracking State
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const currentJobIdRef = useRef<string | null>(null); // Ref for SSE callbacks
  const [currentJobStatus, setCurrentJobStatus] = useState<{
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    progress: number;
    currentStep: string | null;
    message?: string;
  } | null>(null);
  
  // Step states (tracks progress for each step)
  const [stepStates, setStepStates] = useState<Record<string, {
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    duration?: string;
    // Optional: a task_progress event can create an entry before any log arrives.
    logsCount?: number;
    itemsProcessed?: number;
    itemsTotal?: number;
  }>>({});
  
  // View state for selected (historical) job - when user clicks an old job in Recent Jobs
  const [viewedJobStatus, setViewedJobStatus] = useState<{
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
    progress: number;
    currentStep: string | null;
    message?: string;
  } | null>(null);
  const [viewedStepStates, setViewedStepStates] = useState<Record<string, {
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    duration?: string;
    logsCount: number;
    itemsProcessed?: number;
    itemsTotal?: number;
  }>>({});
  
  // Real-time step logs from SSE stream
  const [stepLogs, setStepLogs] = useState<Record<string, LogEntry[]>>({});
  
  // Task progress for currently running step
  const [taskProgress, setTaskProgress] = useState<{ current: number; total: number } | null>(null);
  
  // Expanded steps for console display
  const [expandedSteps, setExpandedSteps] = useState<string[]>([]);
  
  // Current step selection
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  
  // SSE connection status
  const [sseConnected, setSseConnected] = useState(false);
  
  // UI State
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRunningJob, setIsRunningJob] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  
  // Batch schedule state
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [activeSchedule, setActiveSchedule] = useState<any>(null);

  // Global WXCC Simulator status (for displaying effective mode when inherit_global)
  const [globalSimulatorEnabled, setGlobalSimulatorEnabled] = useState<boolean | null>(null);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  
  // Logs Modal State
  const [logsModalOpen, setLogsModalOpen] = useState(false);
  const [logsStepId, setLogsStepId] = useState('');
  
  // Polling refs
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const jobPollingRef = useRef<NodeJS.Timeout | null>(null);
  const logPollingRef = useRef<NodeJS.Timeout | null>(null);
  const schedulePollingRef = useRef<NodeJS.Timeout | null>(null);
  const activeStepRef = useRef<string | null>(null);
  
  // Track if job is actively running (ref to persist across callbacks)
  const isJobActiveRef = useRef<boolean>(false);
  // Track when job was completed (to preserve states after completion)
  const jobCompletedTimeRef = useRef<number | null>(null);
  // Track which steps have had logs fetched (to avoid duplicate fetches)
  const logsFetchedForStepsRef = useRef<Set<string>>(new Set());
  // Track previous step statuses to detect transitions
  const prevStepStatusesRef = useRef<Record<string, string>>({});

  // Initialize step states from stages
  const initializeStepStates = useCallback((stagesData: JourneyStage[]) => {
    const states: typeof stepStates = {};
    
    // Map stages to steps (each stage corresponds to a step). Ref read so the
    // useCallback (empty deps) sees the journey-specific catalog.
    activeStepsRef.current.forEach((step, index) => {
      const stage = stagesData.find(s => s.id === step.id);
      if (stage) {
        states[step.id] = {
          status: stage.status,
          progress: stage.progress,
          duration: formatDuration(stage.progress > 0 ? Math.floor(stage.progress * 0.5) : 0),
          logsCount: 0,
          itemsProcessed: stage.completedJobs || 0,
          itemsTotal: stage.jobCount || 0,
        };
      } else {
        // Default state
        states[step.id] = {
          status: index === 0 ? 'pending' : 'pending',
          progress: 0,
          logsCount: 0,
        };
      }
    });
    
    setStepStates(states);
  }, []);

  // Load journey data
  const loadJourneyData = useCallback(async (showLoading = true) => {
    if (showLoading) setIsLoading(true);
    setError(null);
    
    try {
      const [journeyResponse, stagesResponse, jobsResponse, copilotResp] = await Promise.all([
        callProcessingJourneyService.getJourney(journeyId),
        callProcessingJourneyService.getStages(journeyId),
        callProcessingJourneyService.getJobHistory(journeyId),
        // Best-effort probe of the foundry-workspace saved doc.
        // 404 => not a Copilot saved journey (legacy hard-coded
        // catalog path applies). 200 => use saved doc as the step
        // source. Wrapped in a defensive promise so the legacy
        // path never breaks if control-plane is unreachable.
        (async () => {
          try {
            const r = await fetch(
              `/api/v1/control-plane/journeys/${encodeURIComponent(journeyId)}`,
            );
            if (!r.ok) return null;
            const body = await r.json();
            return body?.journey || body || null;
          } catch {
            return null;
          }
        })(),
      ]);
      
      if (!journeyResponse.success || !journeyResponse.data) {
        setError('Journey not found');
        return;
      }
      
      setJourney(journeyResponse.data);
      const stagesData = stagesResponse.data || [];
      setStages(stagesData);
      setJobHistory(jobsResponse.data || []);
      // Set the Copilot saved doc (or null) so the step catalog +
      // Run handler pick the right path. NOTE: this drives a single
      // re-render via setState; the local ``getStepsForJourney`` call
      // below already uses the freshly-fetched copilotResp.
      setCopilotSavedDoc(copilotResp);
      setLastRefresh(new Date());
      
      // Only initialize step states from stages if no job is active
      // This prevents overwriting running/completed states from job polling
      const timeSinceCompletion = jobCompletedTimeRef.current ? Date.now() - jobCompletedTimeRef.current : null;
      const shouldSkipInit = isJobActiveRef.current || 
        (timeSinceCompletion !== null && timeSinceCompletion < 10000); // 10 seconds grace period
      
      if (!shouldSkipInit) {
        console.log('🔄 Initializing step states from stages data');
        initializeStepStates(stagesData);
        
        // Auto-fetch logs for the latest completed job
        const jobs = jobsResponse.data || [];
        const latestJob = jobs.find((j: any) => j.status === 'completed' || j.jobStatus === 'completed');
        if (latestJob) {
          const jid = latestJob.jobId || latestJob.job_id;
          if (jid) {
            console.log('📥 Auto-fetching logs for completed job:', jid);
            const currentSteps = getStepsForJourney(stagesData, journeyResponse.data, copilotResp);
            currentSteps.forEach((step: any) => {
              fetchLogsForStep(step.id, jid);
            });
          }
        }
      } else {
        console.log(`⏭️ Skipping initializeStepStates (jobActive=${isJobActiveRef.current}, timeSinceCompletion=${timeSinceCompletion}ms)`);
      }
    } catch (err) {
      setError('Failed to load journey data');
      console.error('Error loading journey:', err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [journeyId, initializeStepStates]);

  // Initial load
  useEffect(() => {
    loadJourneyData();
  }, [loadJourneyData]);

  // Load active schedule for this journey
  const loadActiveSchedule = useCallback(async () => {
    try {
      const res = await callProcessingJourneyService.listSchedules(journeyId);
      if (res.success && res.data && res.data.length > 0) {
        setActiveSchedule(res.data[0]);
      } else {
        setActiveSchedule(null);
      }
    } catch {
      setActiveSchedule(null);
    }
  }, [journeyId]);

  useEffect(() => {
    loadActiveSchedule();
  }, [loadActiveSchedule]);

  // Fetch global WXCC mode (reads fresh from SSM, not cached)
  useEffect(() => {
    const fetchGlobalWxccMode = async () => {
      try {
        // Load config to get API base URL
        const configRes = await fetch('/config.json');
        const config = await configRes.json();
        const baseUrl = config?.api?.baseUrl || '';
        
        // Call the dedicated wxcc-mode endpoint that reads directly from SSM
        const response = await fetch(`${baseUrl}/api/v1/config/wxcc-mode`);
        if (response.ok) {
          const data = await response.json();
          console.log('WXCC mode from API:', data);
          setGlobalSimulatorEnabled(data.simulator_enabled);
        } else {
          console.log('Failed to fetch WXCC mode, assuming real mode');
          setGlobalSimulatorEnabled(false);
        }
      } catch (err) {
        console.log('Could not fetch WXCC mode:', err);
        setGlobalSimulatorEnabled(false);
      }
    };
    fetchGlobalWxccMode();
  }, []);

  // Polling for running journeys
  useEffect(() => {
    if (journey?.status === 'running') {
      pollingRef.current = setInterval(() => {
        loadJourneyData(false);
      }, 5000);
    }
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [journey?.status, loadJourneyData]);

  // Auto-refresh when an active schedule is running
  useEffect(() => {
    if (activeSchedule?.enabled && !isRunningJob) {
      schedulePollingRef.current = setInterval(() => {
        loadJourneyData(false);
        loadActiveSchedule();
      }, 30000);
    }

    return () => {
      if (schedulePollingRef.current) {
        clearInterval(schedulePollingRef.current);
        schedulePollingRef.current = null;
      }
    };
  }, [activeSchedule?.enabled, isRunningJob, loadJourneyData, loadActiveSchedule]);

  // Handlers
  const handleRefresh = () => {
    setIsRefreshing(true);
    loadJourneyData(false);
  };

  // Update step states based on current job progress
  const updateStepStatesFromJob = useCallback((currentStep: string | null, jobStatus: string, progress: number) => {
    // Read step list via ref so the callback (created with empty deps) sees
    // the catalog for the currently-loaded journey instead of the
    // CALL_PROCESSING_STEPS fallback from the first render.
    const currentActiveSteps = activeStepsRef.current;
    const stepIndex = currentActiveSteps.findIndex(s => s.id === currentStep);
    
    // Normalize status: backend may send 'in_progress', frontend uses 'running'
    const normalizedStatus = jobStatus === 'in_progress' ? 'running' : jobStatus;
    const isRunning = normalizedStatus === 'running';
    
    console.log(`🔄 updateStepStatesFromJob: currentStep=${currentStep}, stepIndex=${stepIndex}, status=${normalizedStatus} (raw: ${jobStatus}), progress=${progress}`);
    
    // If currentStep is null or not found, use progress to estimate
    let effectiveStepIndex = stepIndex;
    if (effectiveStepIndex < 0 && isRunning) {
      // Estimate step from progress (each step is ~16.67% for 6 steps)
      effectiveStepIndex = Math.min(Math.floor(progress / (100 / currentActiveSteps.length)), currentActiveSteps.length - 1);
      console.log(`  -> Estimated step index from progress: ${effectiveStepIndex}`);
    }
    
    setStepStates(prev => {
      const newStates = { ...prev };
      
      currentActiveSteps.forEach((step, index) => {
        if (normalizedStatus === 'completed') {
          // All steps completed
          newStates[step.id] = {
            ...prev[step.id],
            status: 'completed',
            progress: 100,
          };
        } else if (normalizedStatus === 'failed') {
          // Mark current step as failed, previous as completed
          if (index < effectiveStepIndex) {
            newStates[step.id] = { ...prev[step.id], status: 'completed', progress: 100 };
          } else if (index === effectiveStepIndex) {
            newStates[step.id] = { ...prev[step.id], status: 'failed', progress: prev[step.id]?.progress || 0 };
          } else {
            newStates[step.id] = { ...prev[step.id], status: 'pending', progress: 0 };
          }
        } else if (isRunning) {
          if (index < effectiveStepIndex) {
            // Previous steps are completed
            newStates[step.id] = { ...prev[step.id], status: 'completed', progress: 100 };
          } else if (index === effectiveStepIndex) {
            // Current step is running - preserve task progress if set, otherwise use a small value
            // Task progress comes from onTaskProgress SSE events with actual task counts
            const existingProgress = prev[step.id]?.progress || 0;
            const existingItemsTotal = prev[step.id]?.itemsTotal;
            const hasTaskProgress = existingItemsTotal && existingItemsTotal > 0;
            const finalProgress = hasTaskProgress ? existingProgress : Math.max(existingProgress, 5);
            
            console.log(`  📊 Step ${step.id}: existingProgress=${existingProgress}, itemsTotal=${existingItemsTotal}, hasTaskProgress=${hasTaskProgress}, finalProgress=${finalProgress}`);
            
            newStates[step.id] = { 
              ...prev[step.id], 
              status: 'running', 
              // Keep existing progress if task progress is being tracked, otherwise show indeterminate (small value)
              progress: finalProgress
            };
          } else {
            // Future steps are pending
            newStates[step.id] = { ...prev[step.id], status: 'pending', progress: 0 };
          }
        }
      });
      
      console.log(`  -> New step states:`, Object.entries(newStates).map(([k, v]) => `${k}:${v.status}(${v.progress}%)`).join(', '));
      
      return newStates;
    });
    
    // Update current step index for UI
    if (stepIndex >= 0) {
      setCurrentStepIndex(stepIndex);
    }
  }, []);

  // Handle job status update from polling
  const handleJobStatusUpdate = useCallback((data: {
    status: string;
    progress: number;
    current_step?: string;
    currentStep?: string;
    current_step_index?: number;
    message?: string;
    pending_step?: any;
  }) => {
    const rawStatus = data.status || 'running';
    // ``awaiting_step_approval`` is non-terminal but distinct -- keep
    // polling, render the inline PendingStepCard. The UI's status
    // chip still maps in_progress -> running for visual continuity.
    const status = rawStatus === 'in_progress' ? 'running' : rawStatus;
    const progress = Math.round(data.progress || 0);
    const currentStep = data.current_step || data.currentStep || null;

    // Phase-2: surface the pending-step payload (when present) so the
    // inline PendingStepCard renders. The bridge stashes this on the
    // JobExecution row when the engine pauses on awaiting_step_approval.
    if (rawStatus === 'awaiting_step_approval' && data.pending_step) {
      setPendingStep(data.pending_step);
    } else if (rawStatus !== 'awaiting_step_approval') {
      setPendingStep(null);
    }
    
    console.log(`📊 Job update: status=${status} (raw: ${rawStatus}), progress=${progress}%, step=${currentStep}`);
    
    const jobId = currentJobIdRef.current;
    if (jobId && currentStep) {
      // Read step list via ref: this useCallback was created on the first
      // render (when journey was null and activeSteps fell back to
      // CALL_PROCESSING_STEPS). The ref always points at the catalog matching
      // the current journey (e.g. SEMANTIC_RAG_STEPS for Knowledge Processor).
      const currentActiveSteps = activeStepsRef.current;
      const currentStepIdx = currentActiveSteps.findIndex(s => s.id === currentStep);
      
      currentActiveSteps.forEach((step, index) => {
        if (index < currentStepIdx) {
          if (!logsFetchedForStepsRef.current.has(step.id)) {
            logsFetchedForStepsRef.current.add(step.id);
            setExpandedSteps(prev => prev.includes(step.id) ? prev : [...prev, step.id]);
            fetchLogsForStep(step.id, jobId);
          }
        } else if (index === currentStepIdx) {
          const prevStep = activeStepRef.current;
          activeStepRef.current = step.id;
          setExpandedSteps(prev => prev.includes(step.id) ? prev : [...prev, step.id]);
          if (prevStep !== step.id && jobId) {
            setTaskProgress(null);
            fetchLogsForStep(step.id, jobId);
          }
        }
      });
    }
    
    setCurrentJobStatus({
      status: status as any,
      progress,
      currentStep,
      message: data.message,
    });
    
    updateStepStatesFromJob(currentStep, status, progress);
    
    // Phase-2: include "rejected" in the terminal set so polling
    // stops when the user rejected the pending step. ``awaiting_step_
    // approval`` is intentionally NOT terminal -- the studio keeps
    // polling so the moment the user approves, the next poll picks
    // up the resumed in_progress state.
    if (status === 'completed' || status === 'failed' || status === 'cancelled' || status === 'rejected') {
      console.log(`✅ Job finished with status: ${status}`);
      if (jobPollingRef.current) {
        clearInterval(jobPollingRef.current);
        jobPollingRef.current = null;
      }
      if (logPollingRef.current) {
        clearInterval(logPollingRef.current);
        logPollingRef.current = null;
      }
      activeStepRef.current = null;
      setIsRunningJob(false);
      
      isJobActiveRef.current = false;
      jobCompletedTimeRef.current = Date.now();
      
      const jobId = currentJobIdRef.current;
      if (jobId) {
        const currentActiveSteps = activeStepsRef.current;
        setExpandedSteps(currentActiveSteps.map(s => s.id));
        currentActiveSteps.forEach(step => {
          fetchLogsForStep(step.id, jobId);
        });
      }
      
      setTimeout(() => {
        loadJourneyData(false);
      }, 500);
    }
  }, [updateStepStatesFromJob, loadJourneyData]);

  // Poll job status every 2 seconds
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await callProcessingJourneyService.getJobStatus(journeyId, jobId);
      
      // Handle not found - job not found, stop polling
      if (!response.success && response.error?.message?.includes('not found')) {
        console.warn(`⚠️ Job ${jobId} not found, stopping polling`);
        if (jobPollingRef.current) {
          clearInterval(jobPollingRef.current);
          jobPollingRef.current = null;
        }
        setCurrentJobId(null);
        currentJobIdRef.current = null; // Keep ref in sync
        setCurrentJobStatus(null);
        setIsRunningJob(false);
        isJobActiveRef.current = false;
        return;
      }
      
      if (response.success && response.data) {
        // Cast: the runtime shape of /jobs/{id}/status is wider than
        // the JobExecution TS type (carries status / progress /
        // current_step / pending_step). handleJobStatusUpdate's
        // signature documents the actual shape.
        handleJobStatusUpdate(response.data as any);
      }
    } catch (err) {
      console.error('Error polling job status:', err);
      // Stop polling on repeated errors
      if (jobPollingRef.current) {
        clearInterval(jobPollingRef.current);
        jobPollingRef.current = null;
      }
    }
  }, [journeyId, handleJobStatusUpdate]);

  // Start polling for job status (fallback when SSE fails)
  const startJobPolling = useCallback((jobId: string) => {
    // Clear any existing polling
    if (jobPollingRef.current) {
      clearInterval(jobPollingRef.current);
    }
    
    console.log(`🔄 Starting job polling for ${jobId} (fallback mode)`);
    
    // Initial poll immediately
    pollJobStatus(jobId);
    
    jobPollingRef.current = setInterval(() => {
      pollJobStatus(jobId);
    }, 1000);

    if (logPollingRef.current) {
      clearInterval(logPollingRef.current);
    }
    logPollingRef.current = setInterval(() => {
      const step = activeStepRef.current;
      if (step) {
        fetchLogsForStep(step, jobId);
      }
    }, 2000);
  }, [pollJobStatus]);

  // Start SSE stream for real-time job updates
  const startJobStream = useCallback((jobId: string) => {
    console.log(`📡 Starting SSE stream for job ${jobId}`);
    
    // Clear any existing polling (we're using SSE instead)
    if (jobPollingRef.current) {
      clearInterval(jobPollingRef.current);
      jobPollingRef.current = null;
    }
    
    // Reset step logs for new job
    setStepLogs({});
    setTaskProgress(null);
    logsFetchedForStepsRef.current = new Set(); // Clear fetched logs tracker
    
    // Start polling immediately as primary method (more reliable)
    // SSE will enhance with real-time logs when connected
    console.log(`🔄 Starting polling as primary update method for job ${jobId}`);
    startJobPolling(jobId);
    
    // Also try SSE for real-time logs (optional enhancement)
    console.log(`📡 Attempting SSE connection for journey=${journeyId}, job=${jobId}`);
    jobStreamService.connect(journeyId, jobId, {
      onConnected: () => {
        console.log('✅ SSE stream connected - real-time logs enabled!');
        setSseConnected(true);
      },
      
      onDisconnected: () => {
        console.log('📡 SSE stream disconnected');
        setSseConnected(false);
      },
      
      onStepStatus: (data: StepStatusEvent) => {
        // Normalize status: backend sends 'in_progress', frontend uses 'running'
        const normalizedStatus = data.status === 'in_progress' ? 'running' : data.status;
        const isRunning = normalizedStatus === 'running';
        
        console.log('📊 SSE step_status:', data.step_id, normalizedStatus, `(raw: ${data.status})`);
        
        // Ref read: SSE handler captured first-render activeSteps via the
        // stale useCallback closure; refs always point at the current value.
        const currentActiveSteps = activeStepsRef.current;
        const stepIndex = currentActiveSteps.findIndex(s => s.id === data.step_id);
        
        // Update step states - mark current step and set previous steps as completed
        setStepStates(prev => {
          const newStates = { ...prev };
          
          currentActiveSteps.forEach((step, index) => {
            if (index < stepIndex) {
              // Previous steps are completed
              newStates[step.id] = { ...prev[step.id], status: 'completed', progress: 100 };
            } else if (index === stepIndex) {
              // Current step - use the received status
              // Preserve task progress if it exists and is higher than event progress
              const existingProgress = prev[step.id]?.progress || 0;
              const hasTaskProgress = prev[step.id]?.itemsTotal && prev[step.id]?.itemsTotal > 0;
              const newProgress = hasTaskProgress ? Math.max(existingProgress, data.progress) : data.progress;
              
              newStates[step.id] = {
                ...prev[step.id],
                status: normalizedStatus as any,
                progress: normalizedStatus === 'completed' ? 100 : newProgress,
                logsCount: prev[step.id]?.logsCount || 0,
              };
            }
            // Future steps stay as-is (pending)
          });
          
          return newStates;
        });
        
        // Update current step index
        if (stepIndex >= 0) {
          setCurrentStepIndex(stepIndex);
        }
        
        // Update job status
        setCurrentJobStatus(prev => ({
          status: isRunning ? 'running' : prev?.status || 'running',
          progress: prev?.progress || 0,
          currentStep: data.step_id,
          message: data.message,
        }));
        
        // Auto-expand step when it starts running
        if (isRunning) {
          setExpandedSteps(prev => 
            prev.includes(data.step_id) ? prev : [...prev, data.step_id]
          );
        }
        
        // Clear task progress when step completes
        if (normalizedStatus === 'completed' || normalizedStatus === 'failed') {
          setTaskProgress(null);
          
          // Auto-fetch logs when step completes and expand to show them
          // jobId is from startJobStream parameter - always valid in this closure
          console.log(`🔄 Auto-fetching logs for completed step: ${data.step_id} (job: ${jobId})`);
          // Ensure step is expanded to show logs
          setExpandedSteps(prev => 
            prev.includes(data.step_id) ? prev : [...prev, data.step_id]
          );
          fetchLogsForStep(data.step_id, jobId);
        }
      },
      
      onLog: (data: LogEvent) => {
        console.log(`📝 SSE onLog received:`, data.step_id, data.level, data.message?.substring(0, 50));
        const logEntry = logEventToLogEntry(data);
        
        // Add log to step logs
        setStepLogs(prev => ({
          ...prev,
          [data.step_id]: [...(prev[data.step_id] || []), logEntry]
        }));
        
        // Update logs count
        setStepStates(prev => ({
          ...prev,
          [data.step_id]: {
            ...prev[data.step_id],
            logsCount: (prev[data.step_id]?.logsCount || 0) + 1,
          }
        }));
      },
      
      onTaskProgress: (data: TaskProgressEvent) => {
        console.log(`📈 SSE task_progress: ${data.step_id} ${data.current}/${data.total} = ${data.percentage}%`);
        setTaskProgress({ current: data.current, total: data.total });
        
        // Update step state with task progress - use functional update to ensure latest state
        setStepStates(prev => {
          const currentStepState = prev[data.step_id] || {};
          const newState = {
            ...prev,
            [data.step_id]: {
              ...currentStepState,
              status: 'running' as const,
              itemsProcessed: data.current,
              itemsTotal: data.total,
              progress: data.percentage,
            }
          };
          console.log(`📈 Updated ${data.step_id} progress to ${data.percentage}%`);
          return newState;
        });
      },
      
      onJobComplete: (data: JobCompleteEvent) => {
        console.log('🎉 SSE job_complete:', data);
        
        // Mark all steps as completed
        updateStepStatesFromJob(null, data.status, 100);
        
        setCurrentJobStatus({
          status: data.status,
          progress: 100,
          currentStep: null,
        });
        
        setIsRunningJob(false);
        setTaskProgress(null);
        setSseConnected(false);
        
        // Mark job as inactive but record completion time
        isJobActiveRef.current = false;
        jobCompletedTimeRef.current = Date.now();
        
        // Auto-expand all steps and fetch logs for each
        // jobId is from startJobStream parameter - always valid in this closure
        console.log(`📥 Auto-fetching logs for all steps (job: ${jobId})`);
        const currentActiveSteps = activeStepsRef.current;
        // Expand all steps
        setExpandedSteps(currentActiveSteps.map(s => s.id));
        // Fetch logs for each step
        currentActiveSteps.forEach(step => {
          fetchLogsForStep(step.id, jobId);
        });
        
        // Refresh journey data after a delay to preserve completed states
        setTimeout(() => {
          loadJourneyData(false);
        }, 500);
      },
      
      onError: (error: Error) => {
        console.error('❌ SSE error:', error);
        setSseConnected(false);
        // Polling is already running as primary method, no fallback needed
        console.log('SSE error - polling continues as primary method');
      },
    });
  }, [journeyId, loadJourneyData, startJobPolling]);

  // Clear stale job state on mount and cleanup on unmount
  useEffect(() => {
    // Clear any stale job state from previous sessions
    setCurrentJobId(null);
    currentJobIdRef.current = null; // Keep ref in sync
    setCurrentJobStatus(null);
    setIsRunningJob(false);
    setStepLogs({});
    setTaskProgress(null);
    setSseConnected(false);
    logsFetchedForStepsRef.current = new Set(); // Clear fetched logs tracker
    
    return () => {
      if (jobPollingRef.current) {
        clearInterval(jobPollingRef.current);
        jobPollingRef.current = null;
      }
      if (logPollingRef.current) {
        clearInterval(logPollingRef.current);
        logPollingRef.current = null;
      }
      jobStreamService.disconnect();
    };
  }, [journeyId]); // Reset when journey changes

  const handleRunJob = async () => {
    setIsRunningJob(true);
    isJobActiveRef.current = true;
    jobCompletedTimeRef.current = null;
    
    // Reset step states and set initial running state immediately for responsive UI
    setStepStates(prev => {
      const newStates = { ...prev };
      activeSteps.forEach(step => {
        newStates[step.id] = { ...prev[step.id], status: 'pending', progress: 0 };
      });
      return newStates;
    });
    
    // Show first step as running immediately
    const firstStep = activeSteps[0]?.id || 'extract_unified_schema';
    setCurrentJobStatus({ status: 'running', progress: 0, currentStep: firstStep });
    updateStepStatesFromJob(firstStep, 'running', 0);
    
    try {
      // Run job - backend returns immediately with job ID.
      // Copilot saved journeys dispatch via the control-plane
      // endpoint (the engine path that runs through ReAct tools);
      // the JourneyExecutorBridge writes the JobExecution row that
      // shows up in this same studio's recent-jobs table. Legacy
      // journeys go through the registered transformation stage.
      console.log('🚀 Starting job request...');
      let response: any;
      if (isCopilotJourney) {
        try {
          const r = await fetch(
            `/api/v1/control-plane/journeys/${encodeURIComponent(journeyId)}/run`,
            { method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ inputs: {} }) },
          );
          if (r.ok) {
            const body = await r.json();
            // Phase-2: the Copilot run endpoint now returns the
            // bridge-minted ``job_id`` directly (no need to poll
            // /jobs). Stash the session_id too so the inline
            // PendingStepCard's approve/reject can target the
            // right session.
            if (body?.session_id) setCopilotSessionId(body.session_id);
            response = { success: true, data: body };
          } else {
            response = { success: false };
          }
        } catch (e) {
          console.error('Copilot run dispatch failed:', e);
          response = { success: false };
        }
      } else {
        response = await callProcessingJourneyService.runStageJob(journeyId, activeStage.id);
      }
      console.log('📩 Job response received:', response);
      
      if (response.success && response.data) {
        const jobId = (response.data as any).job_id || (response.data as any).jobId;
        if (jobId) {
          console.log(`✅ Job created: ${jobId}, starting SSE stream...`);
          setCurrentJobId(jobId);
          currentJobIdRef.current = jobId; // Keep ref in sync
          setSelectedJobId(null);
          setViewedJobStatus(null);
          setViewedStepStates({});
          // Start SSE stream for real-time updates (with polling fallback)
          startJobStream(jobId);
          // Refresh journey data in background (non-blocking)
          loadJourneyData(false).catch(err => console.warn('Background refresh error:', err));
        } else if (isCopilotJourney) {
          // The Copilot run endpoint doesn't return the bridge-minted
          // job_id directly (it returns session_id). The bridge has
          // already written the JobExecution row server-side. Refresh
          // /jobs to find the newest job for this journey and treat
          // it as current. We poll briefly because the bridge write
          // may race with our refresh.
          console.log('🔄 Copilot run dispatched; polling /jobs for new row...');
          const startTs = Date.now();
          const findLatestJob = async (): Promise<string | null> => {
            try {
              const j = await callProcessingJourneyService.getJobHistory(journeyId);
              const rows = (j as any).data || [];
              if (rows.length === 0) return null;
              const latest = rows[0];
              return latest?.jobId || latest?.job_id || null;
            } catch { return null; }
          };
          (async () => {
            // up to 6 retries (~6 * 800ms = 4.8s) before giving up.
            for (let i = 0; i < 6; i++) {
              const jid = await findLatestJob();
              if (jid && jid !== currentJobIdRef.current) {
                console.log(`✅ Copilot job materialised as ${jid} (after ${Date.now() - startTs}ms)`);
                setCurrentJobId(jid);
                currentJobIdRef.current = jid;
                setSelectedJobId(null);
                setViewedJobStatus(null);
                setViewedStepStates({});
                startJobStream(jid);
                loadJourneyData(false).catch(() => undefined);
                return;
              }
              await new Promise(r => setTimeout(r, 800));
            }
            console.warn('Copilot job did not surface within 4.8s; user can refresh manually.');
            setIsRunningJob(false);
            setCurrentJobStatus(null);
            isJobActiveRef.current = false;
            loadJourneyData(false).catch(() => undefined);
          })();
        } else {
          console.error('❌ No job ID in response');
          setIsRunningJob(false);
          setCurrentJobStatus(null);
          isJobActiveRef.current = false;
        }
      } else {
        console.error('❌ Job start failed:', response);
        setIsRunningJob(false);
        setCurrentJobStatus(null);
        isJobActiveRef.current = false;
      }
    } catch (err) {
      console.error('❌ Error running job:', err);
      setIsRunningJob(false);
      setCurrentJobStatus(null);
      isJobActiveRef.current = false;
    }
  };

  // Phase-2: approve / reject the pending step. Hits the Copilot
  // engine's approve-step endpoint (same one the legacy AI Copilot
  // chat surface uses) so the bridge can resume / flip the JobExecution
  // row state. The studio's status polling picks up the resulting
  // transition on its next tick.
  const handleApprovePendingStep = useCallback(async (stepId: string) => {
    if (!copilotSessionId) return;
    try {
      const r = await fetch(
        `/api/v1/control-plane/copilot-journey/${encodeURIComponent(copilotSessionId)}/approve-step`,
        { method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step_id: stepId, approved: true }) },
      );
      if (!r.ok) throw new Error(`approve failed (${r.status})`);
      // Clear the inline card immediately so the user sees the
      // resume taking effect; polling will refresh the rest.
      setPendingStep(null);
    } catch (e) {
      console.error('approvePendingStep failed:', e);
    }
  }, [copilotSessionId]);

  const handleRejectPendingStep = useCallback(async (stepId: string) => {
    if (!copilotSessionId) return;
    try {
      const r = await fetch(
        `/api/v1/control-plane/copilot-journey/${encodeURIComponent(copilotSessionId)}/approve-step`,
        { method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step_id: stepId, approved: false }) },
      );
      if (!r.ok) throw new Error(`reject failed (${r.status})`);
      setPendingStep(null);
    } catch (e) {
      console.error('rejectPendingStep failed:', e);
    }
  }, [copilotSessionId]);

  const handleViewLogs = (stepId: string) => {
      setLogsStepId(stepId);
      setLogsModalOpen(true);
  };

  const handleJobSelection = useCallback(async (jobId: string) => {
    setSelectedJobId(jobId);
    setStepLogs({});
    setExpandedSteps([]);
    try {
      const res = await callProcessingJourneyService.getJobStatus(journeyId, jobId);
      const raw = (res as any).data ?? res;
      const status = (raw.status || 'unknown').toLowerCase();
      const normalizedStatus = (status === 'in_progress' ? 'running' : status) as 'pending' | 'running' | 'completed' | 'failed';
      const progress = typeof raw.progress === 'number' ? raw.progress : parseFloat(raw.progress) || 0;
      const currentStep = raw.current_step ?? raw.currentStep ?? null;
      setViewedJobStatus({
        status: normalizedStatus,
        progress,
        currentStep,
        message: raw.error,
      });
      const stepResults = raw.step_results || raw.stepResults || {};
      const nextViewed: typeof viewedStepStates = {};
      activeSteps.forEach((step, index) => {
        const sr = stepResults[step.id];
        const st = (sr?.status || 'pending').toLowerCase();
        const stepStatus = (st === 'in_progress' ? 'running' : st) as 'pending' | 'running' | 'completed' | 'failed';
        const stepProgress = typeof sr?.progress === 'number' ? sr.progress : parseFloat(sr?.progress) || 0;
        nextViewed[step.id] = {
          status: stepStatus,
          progress: stepProgress,
          logsCount: 0,
        };
      });
      setViewedStepStates(nextViewed);
      setExpandedSteps(activeSteps.map(s => s.id));

      if (normalizedStatus === 'running') {
        setCurrentJobId(jobId);
        currentJobIdRef.current = jobId;
        setIsRunningJob(true);
        isJobActiveRef.current = true;
        startJobPolling(jobId);
      }

      await Promise.all(activeSteps.map(step => fetchLogsForStep(step.id, jobId)));
      
      // Update logsCount in viewedStepStates after fetching
      setViewedStepStates(prev => {
        const updated = { ...prev };
        activeSteps.forEach(step => {
          if (updated[step.id]) {
            updated[step.id] = { ...updated[step.id] };
          }
        });
        return updated;
      });
    } catch (err) {
      console.error('Failed to load job details:', err);
      setViewedJobStatus({ status: 'failed', progress: 0, currentStep: null, message: String(err) });
      setViewedStepStates({});
    }
  }, [journeyId, startJobPolling, activeSteps]);

  // Toggle step console expansion
  const toggleStepConsole = (stepId: string) => {
    setExpandedSteps(prev => 
      prev.includes(stepId) 
        ? prev.filter(id => id !== stepId) 
        : [...prev, stepId]
    );
  };

  const handleCancelJob = async (jobId: string) => {
    if (jobPollingRef.current) {
      clearInterval(jobPollingRef.current);
      jobPollingRef.current = null;
    }
    if (logPollingRef.current) {
      clearInterval(logPollingRef.current);
      logPollingRef.current = null;
    }
    activeStepRef.current = null;
    setIsRunningJob(false);
    isJobActiveRef.current = false;
    setCurrentJobStatus(prev => prev ? { ...prev, status: 'cancelled' } : null);
    setViewedJobStatus(prev => prev ? { ...prev, status: 'cancelled' } : null);

    try {
      await callProcessingJourneyService.cancelJob(journeyId, jobId);
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
    loadJourneyData(false);
  };

  const cachedBaseUrlRef = useRef<string | null>(null);

  const fetchLogsForStep = async (stepId: string, jobId: string) => {
    try {
      if (cachedBaseUrlRef.current === null) {
        // /config.json is optional. In EKS deployments without runtime config
        // the path 404s and nginx falls back to index.html (HTML, not JSON);
        // letting `.json()` throw here would silently abort every log fetch.
        // Mirror apiClient.getApiConfig's behavior: fall back to '' so all
        // API calls go through the same-origin nginx proxy.
        try {
          const configRes = await fetch('/config.json', { cache: 'no-store' });
          const ct = configRes.headers.get('content-type') || '';
          if (configRes.ok && ct.includes('application/json')) {
            const config = await configRes.json();
            cachedBaseUrlRef.current = config?.api?.baseUrl || '';
          } else {
            cachedBaseUrlRef.current = '';
          }
        } catch {
          cachedBaseUrlRef.current = '';
        }
      }
      const baseUrl = cachedBaseUrlRef.current;
      
      // Dereference via ref so stale-closured callers (handleJobStatusUpdate,
      // SSE handlers, pollers) still send the current stage id.
      const currentStageId = activeStageRef.current?.id || activeStage?.id;
      const stageQs = currentStageId ? `&stage_name=${encodeURIComponent(currentStageId)}` : '';
      const url = `${baseUrl}/api/v1/journeys/${journeyId}/jobs/${jobId}/logs?step_name=${stepId}${stageQs}&limit=500`;
      
      const response = await fetch(url, { cache: 'no-store' });
      const json = await response.json();
      
      const logsArray = json?.data?.logs || [];
      
      if (logsArray.length > 0) {
        const mappedLogs = logsArray.map((log: any) => ({
          timestamp: log.timestamp,
          level: (log.level || 'info').toLowerCase(),
          message: log.message,
          step_id: log.step_id,
          job_id: log.job_id,
        }));
        setStepLogs(prevLogs => {
          const existing = prevLogs[stepId] || [];
          if (mappedLogs.length < existing.length) {
            return prevLogs;
          }
          return { ...prevLogs, [stepId]: mappedLogs };
        });

        const progressPattern = /\[(\d+)\/(\d+)\]/;
        let latestCurrent = 0;
        let latestTotal = 0;
        for (let i = mappedLogs.length - 1; i >= 0; i--) {
          const match = mappedLogs[i].message?.match(progressPattern);
          if (match) {
            latestCurrent = parseInt(match[1], 10);
            latestTotal = parseInt(match[2], 10);
            break;
          }
        }
        if (latestTotal > 0) {
          const stepProgress = Math.round((latestCurrent / latestTotal) * 100);
          setStepStates(prev => {
            const existing = prev[stepId];
            if (!existing || existing.status !== 'running') return prev;
            if (stepProgress <= (existing.progress || 0)) return prev;
            return { ...prev, [stepId]: { ...existing, progress: stepProgress, itemsProcessed: latestCurrent, itemsTotal: latestTotal } };
          });
          setTaskProgress({ current: latestCurrent, total: latestTotal });
        }

        return mappedLogs.length;
      }
      return 0;
    } catch (err) {
      console.error('Error fetching logs:', err);
      return 0;
    }
  };

  // Toggle logs with API fetch if no logs available
  const handleToggleLogs = async (stepId: string) => {
    console.log(`🔘 Logs button clicked for step: ${stepId}`);
    const isExpanding = !expandedSteps.includes(stepId);
    console.log(`  isExpanding: ${isExpanding}, current logs: ${stepLogs[stepId]?.length || 0}`);
    
    // Toggle expansion
    toggleStepConsole(stepId);
    
    // If expanding and no logs, fetch from API (use selected job when viewing one, else current)
    if (isExpanding && (!stepLogs[stepId] || stepLogs[stepId].length === 0)) {
      const jobId = selectedJobId ?? currentJobId ?? jobHistory[0]?.jobId ?? jobHistory[0]?.id;
      console.log(`  jobId: ${jobId}`);
      if (jobId) {
        await fetchLogsForStep(stepId, jobId);
      } else {
        console.warn('  No jobId available to fetch logs');
      }
    }
  };

  // Clear logs for a specific step
  const clearStepLogs = (stepId: string) => {
    setStepLogs(prev => ({
      ...prev,
      [stepId]: []
    }));
    setStepStates(prev => ({
      ...prev,
      [stepId]: {
        ...prev[stepId],
        logsCount: 0
      }
    }));
  };

  // Helper functions
  const formatDuration = (seconds: number): string => {
    if (!Number.isFinite(seconds) || seconds < 0) return '0s';
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  // When user selected a job, show that job's details (from viewed state we fetch on selection)
  const isViewingSelectedJob = selectedJobId != null;
  const effectiveJobStatus = isViewingSelectedJob ? viewedJobStatus : currentJobStatus;
  const effectiveStepStates = isViewingSelectedJob ? viewedStepStates : stepStates;
  const displayJobId = selectedJobId ?? currentJobId;

  // KPI catalog: drives the per-solution label and icon on the primary card.
  // Reads journey.solutionId (set on create or by the backfill script); falls
  // back to the catalog's _default row when unset / unknown.
  const kpiDefinition = getKpiDefinition(journey?.solutionId);

  // Returns a non-negative finite duration in seconds for a job, or null when
  // neither the backend's authoritative metrics.durationSeconds nor a parseable
  // wall-clock pair is available. This is the NaN-proof source for stats.avgDuration.
  const finiteSecs = (job: any): number | null => {
    const ds = job?.metrics?.durationSeconds ?? job?.durationSeconds;
    const dsNum = typeof ds === 'number' ? ds : parseFloat(ds);
    if (Number.isFinite(dsNum) && dsNum >= 0) return dsNum;

    const st = job?.startedAt ?? job?.startTime;
    const et = job?.completedAt ?? job?.endTime;
    if (!st || !et) return null;
    const s = st instanceof Date ? st.getTime() : new Date(st).getTime();
    const e = et instanceof Date ? et.getTime() : new Date(et).getTime();
    if (!Number.isFinite(s) || !Number.isFinite(e)) return null;
    const diff = (e - s) / 1000;
    return Number.isFinite(diff) && diff >= 0 ? diff : null;
  };

  // Calculate statistics: single job when viewing a selected job, else aggregate
  const selectedJob = selectedJobId ? jobHistory.find(j => (j.id || (j as any).jobId) === selectedJobId) : null;
  const stats = (() => {
    if (isViewingSelectedJob && selectedJob) {
      const durationSec = finiteSecs(selectedJob);
      return {
        primaryValue: selectedJob.itemsProcessed ?? (selectedJob as any).metrics?.itemsProcessed ?? (selectedJob as any).metrics?.processedSuccessfully ?? 0,
        successRate: selectedJob.status === 'completed' ? 100 : selectedJob.status === 'failed' ? 0 : 0,
        avgDuration: durationSec !== null && durationSec > 0 ? formatDuration(Math.round(durationSec)) : '0s',
        completedJobs: selectedJob.status === 'completed' ? 1 : 0,
        failedJobs: selectedJob.status === 'failed' ? 1 : 0,
        totalJobs: 1,
      };
    }
    const durations = jobHistory.map(finiteSecs).filter((d): d is number => d !== null);
    const avgSecs = durations.length > 0
      ? durations.reduce((a, b) => a + b, 0) / durations.length
      : 0;
    const finishedJobs = jobHistory.filter(j => !['running', 'in_progress', 'pending', 'queued'].includes(String(j.status)));
    return {
      primaryValue: jobHistory.reduce((acc, job) => acc + (job.itemsProcessed || (job as any).metrics?.itemsProcessed || 0), 0),
      // A run that is still going is neither a success nor a failure yet.
      successRate: finishedJobs.length > 0
        ? Math.round((finishedJobs.filter(j => j.status === 'completed').length / finishedJobs.length) * 100)
        : 0,
      avgDuration: formatDuration(Number.isFinite(avgSecs) ? Math.round(avgSecs) : 0),
      completedJobs: jobHistory.filter(j => j.status === 'completed').length,
      failedJobs: jobHistory.filter(j => j.status === 'failed').length,
      totalJobs: jobHistory.length,
    };
  })();

  // Current step
  const currentStep = activeSteps[currentStepIndex];
  const currentStepState = currentStep ? effectiveStepStates[currentStep.id] : undefined;

  // Stage status (derived from display job status or journey status)
  const stageStatus = effectiveJobStatus?.status || journey?.status || 'created';
  const stageStatusForDisplay = stageStatus === 'created' ? 'pending' : stageStatus;

  // Calculate stage duration (guard against NaN)
  const rawDuration = stats.avgDuration;
  const stageDuration = rawDuration && rawDuration !== '0s' && !rawDuration.includes('NaN') ? rawDuration : undefined;

  // ------------------------------------------------------------------
  // Presentation only below this line: values derived for the layout.
  // ------------------------------------------------------------------
  const isWide = useIsWide();
  // Open state of the two dialogs reached from the "More" menu.
  const [jobsModalOpen, setJobsModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="space-y-8" aria-label="Loading journey">
        {!hideHeader && (
          <div className="space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-72 max-w-full" />
            <Skeleton className="h-4 w-96 max-w-full" />
          </div>
        )}
        {!hideStatsCards && <Skeleton className="h-24 w-full rounded-xl" />}
        <Skeleton className="h-72 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <InlineError onRetry={() => loadJourneyData()}>
          {error === 'Journey not found' ? 'This journey could not be found. It may have been deleted.' : 'The journey could not be loaded.'}
        </InlineError>
        {!hideBackButton && (
          <Button variant="outline" onClick={onBack}>
            <Icon name="chevron-left" /> All journeys
          </Button>
        )}
      </div>
    );
  }

  const isStageRunning = stageStatusForDisplay === 'running';
  const runningStepId = effectiveJobStatus?.currentStep || null;
  const runningStepIndex = runningStepId ? activeSteps.findIndex(s => s.id === runningStepId) : -1;
  const runningStepName = runningStepIndex >= 0 ? activeSteps[runningStepIndex].name : runningStepId;
  const overallProgress = Math.max(0, Math.min(100, Math.round(effectiveJobStatus?.progress || 0)));
  const completedSteps = activeSteps.filter(s => effectiveStepStates[s.id]?.status === 'completed').length;

  const selectedIndex = currentStep ? currentStepIndex : 0;
  const selectedStep = currentStep || activeSteps[0];
  const selectedState = selectedStep ? effectiveStepStates[selectedStep.id] : currentStepState;
  const selectedStatus = (selectedState?.status || 'pending') as StepStatus;
  const selectedIsLive = !!selectedStep && selectedStatus === 'running' && selectedStep.id === currentJobStatus?.currentStep && !isViewingSelectedJob;

  const pipelineSteps: PipelineStep[] = activeSteps.map(step => {
    const st = effectiveStepStates[step.id];
    const status = (st?.status || 'pending') as StepStatus;
    return {
      id: step.id,
      name: step.name,
      description: step.description,
      status,
      meta: status === 'running' ? `${Math.round(st?.progress || 0)}%` : status === 'completed' && st?.duration ? st.duration : undefined,
    };
  });

  const sourceMode = journey?.config?.wxccMode && journey.config.wxccMode !== 'inherit_global'
    ? (journey.config.wxccMode === 'real' ? 'Real source data' : 'Simulator data')
    : globalSimulatorEnabled === null
      ? null
      : globalSimulatorEnabled ? 'Simulator data (global setting)' : 'Real source data (global setting)';
  const typeLabel = humanize(journey?.solutionId || journey?.type);
  const metaParts = [typeLabel, scheduleInWords(activeSchedule), sourceMode].filter(Boolean) as string[];

  // The journey stays "pending" between runs; say how the last run ended instead of "Not run yet".
  const lastRunStatus: string = stageStatusForDisplay === 'pending' ? String((jobHistory[0] as any)?.status || '') : '';
  const statusLabel = isStageRunning
    ? `Running, ${overallProgress}%`
    : stageStatusForDisplay === 'pending' ? (lastRunStatus ? `Idle, last run ${lastRunStatus}` : 'Not run yet') : stageStatusForDisplay;

  const backToLatest = () => {
    setSelectedJobId(null);
    setViewedJobStatus(null);
    setViewedStepStates({});
    setStepLogs({});
    setExpandedSteps([]);
  };

  const latestJob: any = jobHistory[0] || null;
  const resultsJob: any = (isViewingSelectedJob && selectedJob) ? selectedJob : latestJob;
  const resultsIndex = resultsJob ? Math.max(0, jobHistory.findIndex(j => (j.id || (j as any).jobId) === (resultsJob.id || resultsJob.jobId))) : 0;
  const totalRunsLabel = (() => {
    const firstJobId = (jobHistory[0]?.id || (jobHistory[0] as any)?.jobId || '') as string;
    const match = firstJobId.match(/JOB-(\d+)/);
    const total = match ? parseInt(match[1], 10) : jobHistory.length;
    return `${total.toLocaleString()} ${total === 1 ? 'run' : 'runs'} so far`;
  })();

  const primaryAction = isStageRunning && displayJobId ? (
    <Button variant="outline" className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive" onClick={() => handleCancelJob(displayJobId)}>
      <span className="h-2.5 w-2.5 rounded-[2px] bg-current" aria-hidden="true" /> Stop run
    </Button>
  ) : isStageRunning ? (
    <Button disabled>
      <Icon name="spinner" className="animate-spin" /> Starting
    </Button>
  ) : (
    <Button onClick={handleRunJob} disabled={isRunningJob}>
      <Icon name="play" /> {stageStatusForDisplay === 'pending' && !lastRunStatus ? 'Run now' : 'Run again'}
    </Button>
  );

  const stepDetail = selectedStep ? (
    <StepDetail
      index={selectedIndex}
      total={activeSteps.length}
      name={selectedStep.name}
      description={selectedStep.description}
      status={selectedStatus}
      progress={selectedState?.progress}
      duration={selectedState?.duration}
      taskProgress={selectedIsLive ? taskProgress : null}
      logsCount={stepLogs[selectedStep.id]?.length || selectedState?.logsCount || 0}
      logsOpen={expandedSteps.includes(selectedStep.id)}
      onToggleLogs={() => handleToggleLogs(selectedStep.id)}
      onOpenLogs={() => handleViewLogs(selectedStep.id)}
      onPrev={selectedIndex > 0 ? () => setCurrentStepIndex(selectedIndex - 1) : undefined}
      onNext={selectedIndex < activeSteps.length - 1 ? () => setCurrentStepIndex(selectedIndex + 1) : undefined}
      compact={!isWide}
    >
      {expandedSteps.includes(selectedStep.id) && (
        <StepConsole
          logs={stepLogs[selectedStep.id] || []}
          isExpanded
          onToggle={() => toggleStepConsole(selectedStep.id)}
          stepName={selectedStep.name}
          stepStatus={selectedStatus}
          taskProgress={selectedIsLive ? taskProgress : null}
          onClear={() => clearStepLogs(selectedStep.id)}
          showHeader={false}
          maxHeight="280px"
        />
      )}
    </StepDetail>
  ) : null;

  return (
    <div className="space-y-8 sm:space-y-10">
      {/* Header: what this is, its state, and the one primary action */}
      <header>
        {!hideHeader && !hideBackButton && (
          <button
            type="button"
            onClick={onBack}
            className="-ml-1 mb-3 inline-flex items-center gap-1 rounded-sm px-1 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Icon name="chevron-left" className="h-3.5 w-3.5" /> All journeys
          </button>
        )}
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
              {hideHeader
                ? <h2 className="text-md font-medium text-foreground">{activeStage.name}</h2>
                : <h1 className="text-lg font-medium tracking-tight text-foreground">{journey?.name || 'Journey'}</h1>}
              <StatusPill status={lastRunStatus || stageStatusForDisplay} variant="soft">{statusLabel}</StatusPill>
            </div>
            <p className="mt-1.5 text-sm text-muted-foreground">{metaParts.join(' · ')}</p>
            {!hideHeader && (
              <p className="mt-1 flex flex-wrap items-center gap-x-2 text-xs text-subtle-foreground">
                <span className="num">Updated {timeOfDay(lastRefresh)}</span>
                <span className="mono-id">{journeyId}</span>
                {sseConnected && <span className="inline-flex items-center gap-1.5 text-muted-foreground"><span className="dot-live text-primary dark:text-brand-hi" aria-hidden="true" /> Live output connected</span>}
              </p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {overrideReportButton}
            {extraHeaderButtons}
            <Button variant="outline" onClick={() => setScheduleDialogOpen(true)}>
              <Icon name="calendar" /> {activeSchedule ? 'Edit schedule' : 'Schedule'}
            </Button>
            {primaryAction}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="More actions">
                  <Icon name="more" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {!overrideReportButton && (
                  <DropdownMenuItem onSelect={() => setReportModalOpen(true)}>
                    <Icon name="document" /> View report
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem onSelect={() => setJobsModalOpen(true)}>
                  <Icon name="history" /> All runs
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={handleRefresh} disabled={isRefreshing}>
                  <Icon name="refresh" /> Refresh
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {!hideStatsCards && (
        <MetricStrip
          items={[
            {
              label: sentenceCase(kpiDefinition.primary.label),
              value: Number(stats.primaryValue || 0).toLocaleString(),
              hint: isViewingSelectedJob ? 'In this run' : 'Across all runs',
            },
            {
              label: 'Success rate',
              value: `${stats.successRate}%`,
              hint: isViewingSelectedJob ? 'This run' : (stats.totalJobs - stats.completedJobs - stats.failedJobs > 0 && isStageRunning ? `${stats.completedJobs} completed, 1 running` : `${stats.completedJobs} of ${stats.totalJobs} runs completed`),
            },
            {
              label: isViewingSelectedJob ? 'Duration' : 'Average duration',
              value: stageDuration || 'No data',
              hint: isViewingSelectedJob ? 'This run' : 'Per run',
            },
            {
              label: 'Runs',
              value: stats.totalJobs.toLocaleString(),
              hint: stats.failedJobs > 0 ? `${stats.failedJobs} failed` : 'None failed',
              tone: stats.failedJobs > 0 ? 'danger' : 'neutral',
              onClick: () => setJobsModalOpen(true),
            },
          ]}
        />
      )}

      {isViewingSelectedJob && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-border bg-surface-2/60 px-4 py-2.5 text-sm animate-fade-up">
          <Icon name="history" className="shrink-0 text-muted-foreground" />
          <p className="min-w-0 flex-1 text-foreground">
            Showing run <span className="mono-id text-foreground">{selectedJobId}</span>
            {selectedJob && dayAndTime((selectedJob as any).startedAt ?? (selectedJob as any).startTime) ? ` from ${dayAndTime((selectedJob as any).startedAt ?? (selectedJob as any).startTime)}` : ''}.
            <span className="text-muted-foreground"> The pipeline, output and results below are for this run.</span>
          </p>
          <Button variant="ghost" size="sm" onClick={backToLatest}>Back to latest</Button>
        </div>
      )}

      {/* Approval gate for Copilot saved journeys paused on awaiting_step_approval.
          Re-uses the PendingStepCard of the journey-builder approval flow, so
          approve / reject hit the Copilot engine and the bridge flips the run. */}
      {isCopilotJourney && pendingStep && copilotSessionId && (
        <PendingStepCard
          runId={copilotSessionId}
          pending={pendingStep}
          onApprove={handleApprovePendingStep}
          onReject={handleRejectPendingStep}
        />
      )}

      {/* The pipeline: one stepper, the selected step's detail below it */}
      <section aria-label="Pipeline" className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 px-4 pt-4 sm:px-6 sm:pt-5">
          <div className="min-w-0">
            <h2 className="text-md font-medium text-foreground">{hideHeader ? 'Pipeline' : activeStage.name}</h2>
            <p className="mt-0.5 max-w-3xl text-sm text-muted-foreground">{activeStage.description}</p>
          </div>
          <p className="num flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
            <span>{lastRunStatus && completedSteps === 0 ? `${activeSteps.length} steps, last run ${lastRunStatus}` : `${completedSteps} of ${activeSteps.length} steps done`}</span>
            {displayJobId && <span className="mono-id" title={displayJobId}>Run {displayJobId.slice(-8)}</span>}
          </p>
        </div>

        {effectiveJobStatus?.status === 'running' && (
          <div className="px-4 pt-4 sm:px-6" aria-live="polite">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm">
              <p className="min-w-0 text-foreground">
                {runningStepId
                  ? <>Running step {runningStepIndex + 1} of {activeSteps.length}: <span className="font-medium">{runningStepName}</span></>
                  : 'Starting the run'}
                {taskProgress && effectiveJobStatus.currentStep === currentJobStatus?.currentStep && (
                  <span className="num text-muted-foreground"> ({taskProgress.current.toLocaleString()} of {taskProgress.total.toLocaleString()})</span>
                )}
              </p>
              <span className="num text-xs text-muted-foreground">{overallProgress}%</span>
            </div>
            <Meter value={overallProgress} className="mt-2" label="Run progress" />
          </div>
        )}

        {/* Steps run top to bottom; on wide screens the selected step opens beside the list. */}
        <div className={isWide ? 'grid grid-cols-[minmax(260px,320px)_minmax(0,1fr)]' : ''}>
          <div className={isWide ? 'border-r border-border px-2 py-3' : 'px-3 py-5 sm:px-5 sm:py-6'}>
            <StepPipeline
              steps={pipelineSteps}
              selectedId={selectedStep?.id}
              onSelect={(_id, index) => setCurrentStepIndex(index)}
              wide={isWide}
              detail={!isWide ? stepDetail : undefined}
            />
          </div>

          {isWide && (
            <div key={selectedStep?.id} className="animate-fade-in min-w-0 bg-surface-2/30 px-5 py-5 sm:px-6">
              {stepDetail || <p className="text-sm text-muted-foreground">Select a step to see what it does and its output.</p>}
            </div>
          )}
        </div>
      </section>

      {/* Results of the latest (or the selected) run, as a short report */}
      <section aria-label="Results">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-md font-medium text-foreground">Results</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">{isViewingSelectedJob ? 'What the selected run did.' : 'What the latest run did.'}</p>
          </div>
        </div>
        {resultsJob ? (
          <div className="rounded-xl border border-border bg-card p-4 shadow-xs sm:p-6">
            <RunResults
              job={resultsJob}
              steps={activeSteps}
              fallbackNumber={jobHistory.length - resultsIndex}
              noun="records"
              actions={
                <>
                  {!overrideReportButton && (
                    <Button variant="outline" size="sm" onClick={() => setReportModalOpen(true)}>
                      <Icon name="document" /> Open full report
                    </Button>
                  )}
                  <span className="text-xs text-muted-foreground">The full report adds KPIs, alerts raised and actions taken across runs.</span>
                </>
              }
            />
          </div>
        ) : (
          <EmptyState
            icon="play"
            title="No runs yet"
            description="Run the journey to see what it read, what it changed and how long each step took."
            action={<Button onClick={handleRunJob} disabled={isRunningJob}><Icon name="play" /> Run now</Button>}
          />
        )}
      </section>

      {/* Recent runs */}
      {jobHistory.length > 0 && (
        <section aria-label="Recent runs">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-md font-medium text-foreground">Recent runs</h2>
              <p className="mt-0.5 text-sm text-muted-foreground">{totalRunsLabel}. Select a run to see its pipeline and output above.</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setJobsModalOpen(true)}>
              All runs <Icon name="arrow-right" />
            </Button>
          </div>
          <RunsTable
            jobs={jobHistory}
            steps={activeSteps}
            selectedJobId={selectedJobId}
            onSelect={handleJobSelection}
            onCancel={handleCancelJob}
          />
        </section>
      )}

      {/* Batch Schedules Panel */}
      <BatchSchedulesPanel journeyId={journeyId} journeyName={journey?.name} onScheduleChanged={loadActiveSchedule} />

      {/* All runs (opened from the header menu, the Runs figure and the table) */}
      <StageJobsModal
        journeyId={journeyId}
        journeyName={journey?.name}
        open={jobsModalOpen}
        onOpenChange={setJobsModalOpen}
        onJobAction={(jobId, action) => {
          if (action === 'repeat') {
            handleRunJob();
          }
        }}
        onViewJob={(jobId) => handleJobSelection(jobId)}
      />

      {/* Report (unless the host supplies its own report button) */}
      {!overrideReportButton && (
        <StageReportModal
          journeyId={journeyId}
          journeyName={journey?.name}
          open={reportModalOpen}
          onOpenChange={setReportModalOpen}
        />
      )}

      {/* Logs Modal */}
      {logsModalOpen && (
        <LogsModal
          journeyId={journeyId}
          jobId={currentJobId || selectedJobId || jobHistory[0]?.jobId || jobHistory[0]?.id}
          stepId={logsStepId}
          stepName={activeSteps.find(s => s.id === logsStepId)?.name || 'Step'}
          isOpen={logsModalOpen}
          onClose={() => setLogsModalOpen(false)}
        />
      )}

      {/* Batch Schedule Dialog */}
      <BatchScheduleDialog
        open={scheduleDialogOpen}
        onClose={() => setScheduleDialogOpen(false)}
        journeyId={journeyId}
        journeyName={journey?.name}
        stageId={activeStage.id}
        existingSchedule={activeSchedule}
        onSaved={loadActiveSchedule}
      />
    </div>
  );
}

export default JourneyStudioView;
