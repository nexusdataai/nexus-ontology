/**
 * Back-compat re-export.
 *
 * The original ``StageReportModal`` was hard-coded to the
 * call-processing report shape (Total Calls / Transcribed / Analyzed
 * etc.). The Phase-3 / React-Tool-improvement plan replaced it with a
 * schema-driven ``JourneyReportModal`` that renders whatever
 * ``enterprise-knowledge/report-schemas/{solution_id}.yaml`` declares.
 *
 * This module exists so legacy imports
 * (``import { StageReportModal } from '.../StageReportModal'``) keep
 * working while a per-call codemod is in flight. The actual component
 * lives at ``components/journeys/report/JourneyReportModal.tsx``.
 */

export { JourneyReportModal as StageReportModal } from './report/JourneyReportModal';
export { JourneyReportModal } from './report/JourneyReportModal';
export default {};
