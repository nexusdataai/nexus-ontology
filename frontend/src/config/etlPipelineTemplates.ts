import type { ETLSourceType, ETLPipelineConfig } from '@/services/etlPipelineService';

export interface ETLPipelineTemplate {
  id: string;
  name: string;
  description: string;
  sourceType: ETLSourceType;
  dataSourceId: string;
  targetEntities: string[];
  defaultConfig: ETLPipelineConfig;
}

export const ETL_PIPELINE_TEMPLATES: ETLPipelineTemplate[] = [
  {
    id: 'tpl-social-listening',
    name: 'Social Listening ETL',
    description: 'Ingest market signals, social mentions, and competitor alerts into the virtual data layer',
    sourceType: 'social_listening',
    dataSourceId: 'sample-social',
    targetEntities: ['Market_Signal', 'Social_Mention', 'Competitor_Alert'],
    defaultConfig: {
      mappingRuleId: '',
      sourceType: 'social_listening',
      mode: 'incremental',
      batchSize: 500,
      schedule: '0 */4 * * *',
    },
  },
  {
    id: 'tpl-file-uploads',
    name: 'File Uploads ETL',
    description: 'Parse and load invoices, lab reports, and CSV files into structured virtual entities',
    sourceType: 'file_uploads',
    dataSourceId: 'sample-files',
    targetEntities: ['Invoice', 'Lab_Report'],
    defaultConfig: {
      mappingRuleId: '',
      sourceType: 'file_uploads',
      mode: 'full',
      batchSize: 1000,
    },
  },
  {
    id: 'tpl-google-drive',
    name: 'Google Drive ETL',
    description: 'Extract and structure contracts and sustainability reports from Google Drive',
    sourceType: 'google_drive',
    dataSourceId: 'sample-drive',
    targetEntities: ['Contract_Document', 'Sustainability_Report'],
    defaultConfig: {
      mappingRuleId: '',
      sourceType: 'google_drive',
      mode: 'incremental',
      batchSize: 200,
      schedule: '0 */6 * * *',
    },
  },
];
