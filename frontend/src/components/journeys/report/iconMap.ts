/**
 * Icon-name string -> lucide-react component. The backend schemas
 * reference icons by name (e.g. ``icon: TrendingUp``); the UI maps
 * those strings into real React components here so YAML authors don't
 * need to touch TypeScript.
 *
 * Unknown icon names fall back to ``Activity`` so a typo can't crash
 * the modal.
 */

import {
  Activity, AlertTriangle, Award, BarChart3, Bell, Boxes, Brain,
  CheckCircle, Clock, Cloud, Database, Download, Droplet, Factory,
  FileBarChart, FileCheck, FileText, FileWarning, Gauge, GitBranch,
  GitMerge, Layers, Leaf, MessageSquare, Mic, Phone, RefreshCw,
  ShieldCheck, ShoppingCart, Shuffle, SkipForward, Sparkles, Target,
  TrendingUp, Upload, Users, Wallet, Workflow, Wrench, XCircle, Zap,
} from 'lucide-react';

const _MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  Bell,
  Boxes,
  Brain,
  CheckCircle,
  Clock,
  Cloud,
  Database,
  Download,
  Droplet,
  Factory,
  FileBarChart,
  FileCheck,
  FileText,
  FileWarning,
  Gauge,
  GitBranch,
  GitMerge,
  Layers,
  Leaf,
  MessageSquare,
  Mic,
  Phone,
  RefreshCw,
  ShieldCheck,
  ShoppingCart,
  Shuffle,
  SkipForward,
  Sparkles,
  Target,
  TrendingUp,
  Upload,
  Users,
  Wallet,
  Workflow,
  Wrench,
  XCircle,
  Zap,
};

export function getIcon(name?: string | null): React.ComponentType<{ className?: string }> {
  if (!name) return Activity;
  return _MAP[name] || Activity;
}
