import type { ComponentType } from 'react';
import type { LucideIcon } from 'lucide-react';
import type { DataFrame } from '../types';

export interface PanelProps {
  data: DataFrame[];
  options: Record<string, unknown>;
  width: number;
  height: number;
  title: string;
  loading: boolean;
  error?: string;
}

export interface PanelOptionsEditorProps {
  options: Record<string, unknown>;
  onChange: (options: Record<string, unknown>) => void;
  data?: DataFrame[];
}

export interface PanelPluginMeta {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  category: 'stat' | 'chart' | 'table' | 'timeline' | 'graph' | 'misc';
  defaultOptions: Record<string, unknown>;
  optionsEditor: ComponentType<PanelOptionsEditorProps>;
}

export interface PanelPlugin {
  meta: PanelPluginMeta;
  component: ComponentType<PanelProps>;
}
