/**
 * Product icon.
 * ----------------------------------------------------------------------------
 * One icon family for the whole product: UIcons regular rounded by Freepik
 * (the family published on Magnific / Flaticon stock). The SVGs live in
 * src/assets/icons/magnific/ and are compiled into `icons.generated.ts` by
 * `npm run icons` (scripts/build-icons.mjs).
 * Licence: Flaticon licence. It needs either an active Freepik/Magnific
 * subscription or a visible credit to Flaticon. See manifest.json.
 *
 * Usage: <Icon name="database" className="h-4 w-4" />
 * Icons inherit the text colour (currentColor) and default to 16px.
 *
 * If a name is not in the generated set yet, a Lucide icon is used as a
 * stand-in so screens never break; add the missing icon to the set instead of
 * relying on the stand-in.
 */
import * as React from 'react';
import {
  Activity, AlertTriangle, ArrowUpRight, BarChart3, Bell, Bot, Boxes, Braces, Calendar, Check,
  ChevronDown, ChevronLeft, ChevronRight, Clock, Cloud, Copy, Database, Download, ExternalLink,
  Eye, FileText, Filter, FlaskConical, Folder, Globe, HeartPulse, HelpCircle, Home, Info, Key,
  Layers, LayoutDashboard, Lock, LogOut, Megaphone, Menu, Moon, Network, Pause, Pencil, Play,
  Plug, Plus, RefreshCw, Route, Search, Server, Settings, ShieldCheck, Shuffle, Sparkles,
  Stethoscope, Sun, Table2, Target, Trash2, Upload, User, Users, Workflow, Wrench, X, Zap, Box,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ICONS } from './icons.generated';

const FALLBACK: Record<string, LucideIcon> = {
  home: Home, database: Database, layers: Layers, 'brain-ai': Sparkles, apps: Boxes,
  'chart-bar': BarChart3, workflow: Workflow, stethoscope: Stethoscope, heartbeat: HeartPulse,
  flask: FlaskConical, settings: Settings, help: HelpCircle, search: Search, sun: Sun, moon: Moon,
  menu: Menu, close: X, plus: Plus, check: Check, 'chevron-right': ChevronRight,
  'chevron-down': ChevronDown, 'chevron-left': ChevronLeft, 'arrow-up-right': ArrowUpRight,
  'external-link': ExternalLink, user: User, users: Users, logout: LogOut, bell: Bell,
  'chat-bot': Bot, wrench: Wrench, target: Target, 'shield-check': ShieldCheck, plug: Plug,
  network: Network, cube: Box, table: Table2, shuffle: Shuffle, cloud: Cloud, server: Server,
  folder: Folder, 'megaphone-or-rss': Megaphone, upload: Upload, document: FileText, key: Key,
  lock: Lock, calendar: Calendar, clock: Clock, play: Play, pause: Pause, refresh: RefreshCw,
  'alert-triangle': AlertTriangle, info: Info, filter: Filter, download: Download, trash: Trash2,
  edit: Pencil, copy: Copy, eye: Eye, code: Braces, globe: Globe, activity: Activity, route: Route,
  dashboard: LayoutDashboard, bolt: Zap,
};

export type IconName = keyof typeof FALLBACK | (string & {});

interface IconProps extends Omit<React.SVGAttributes<SVGSVGElement>, 'name'> {
  name: IconName;
  /** Accessible label. Omit for decorative icons next to text. */
  label?: string;
}

export function Icon({ name, label, className, ...rest }: IconProps) {
  const a11y = label ? { role: 'img', 'aria-label': label } : { 'aria-hidden': true };
  const def = ICONS[name];

  if (def) {
    return (
      <svg
        viewBox={def.viewBox}
        fill="currentColor"
        focusable="false"
        className={cn('h-4 w-4 shrink-0', className)}
        {...a11y}
        {...rest}
        dangerouslySetInnerHTML={{ __html: def.body }}
      />
    );
  }

  const Fallback = FALLBACK[name] || HelpCircle;
  return <Fallback className={cn('h-4 w-4 shrink-0', className)} strokeWidth={1.6} {...(a11y as object)} />;
}

export default Icon;
