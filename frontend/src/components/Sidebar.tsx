import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  ChevronLeft, ChevronDown, ChevronRight,
  Database, Layers, Zap, LayoutGrid, Sparkles,
  HeartPulse, Stethoscope,
  HelpCircle, Settings, BarChart3,
  FileText, LifeBuoy, Mail, ExternalLink,
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { getSimulatorConfig } from '@/services/simulatorLink';

const MENU = [
  {
    label: 'AI STACK', items: [
      { id: 'home', name: 'Home', icon: LayoutGrid, path: '/' },
      { id: 'dp', name: 'Data Plane', icon: Database, path: '/ai-stack/data-plane' },
      { id: 'cp', name: 'Control Plane', icon: Layers, path: '/ai-stack/control-plane' },
      { id: 'reason', name: 'Reasoning', icon: Zap, path: '/ai-stack/reasoning' },
    ]
  },
  {
    label: 'WORKSPACE', items: [
      { id: 'apps', name: 'Solutions', icon: LayoutGrid, path: '/workspace/apps' },
      { id: 'analytics', name: 'AI Analytics', icon: BarChart3, path: '/ai-analytics' },
      { id: 'automation', name: 'AI Automation', icon: Sparkles, path: '/workspace/automation' },
    ]
  },
  {
    label: 'AI OPS', items: [
      { id: 'diag', name: 'Diagnostics', icon: Stethoscope, path: '/operations/diagnostics' },
      { id: 'health', name: 'Health', icon: HeartPulse, path: '/operations/health' },
    ]
  },
];

const Sidebar = () => {
  const nav = useNavigate();
  const loc = useLocation();
  const [mini, setMini] = useState(false);
  const [simulatorUiUrl, setSimulatorUiUrl] = useState('http://localhost:8082');

  useEffect(() => {
    getSimulatorConfig().then(cfg => {
      if (cfg.uiUrl) setSimulatorUiUrl(cfg.uiUrl);
    }).catch(() => {});
  }, []);
  const active = (p: string) => {
    if (p === '/') return loc.pathname === '/';
    if (p === '/ai-analytics') {
      return (
        loc.pathname.startsWith('/ai-analytics')
        || loc.pathname === '/dashboards'
        || loc.pathname.startsWith('/dashboard/')
        || loc.pathname === '/views'
        || loc.pathname.startsWith('/views/')
      );
    }
    return loc.pathname === p || loc.pathname.startsWith(p + '/');
  };

  const initOpen: Record<string, boolean> = {};
  MENU.forEach(s => {
    initOpen[s.label] = s.items.some(i => active(i.path));
  });
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    const o: Record<string, boolean> = {};
    MENU.forEach(s => { o[s.label] = s.items.some(i => active(i.path)) || true; });
    return o;
  });

  const toggle = (label: string) => setOpenSections(prev => ({ ...prev, [label]: !prev[label] }));

  return (
    <aside className={cn(
      'h-full flex flex-col shrink-0 transition-all duration-200 border-r relative',
      'bg-slate-100 dark:bg-[#141b2d] border-slate-200 dark:border-[#1e2740]',
      mini ? 'w-14' : 'w-[190px]'
    )}>
      {/* Header */}
      <div className={cn('flex items-center gap-2 px-3 pt-4 pb-3', mini && 'justify-center px-2')}>
        <div className="w-7 h-7 flex items-center justify-center shrink-0">
          <svg viewBox="0 0 32 32" className="w-7 h-7">
            <defs>
              <linearGradient id="sidebarLogo" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#7c3aed"/>
                <stop offset="100%" stopColor="#4f46e5"/>
              </linearGradient>
            </defs>
            <path d="M16 1 L29 8.5 L29 23.5 L16 31 L3 23.5 L3 8.5 Z" fill="url(#sidebarLogo)"/>
            <path d="M16 7 L12 12 L16 17 L20 12 Z" fill="white" opacity="0.9"/>
            <path d="M12 14 L9 19 L16 25 L12 18 Z" fill="white" opacity="0.7"/>
            <path d="M20 14 L23 19 L16 25 L20 18 Z" fill="white" opacity="0.7"/>
          </svg>
        </div>
        {!mini && (
          <>
            <div className="leading-tight flex-1">
              <div className="text-[13px] font-bold text-slate-900 dark:text-white">Nexus AI</div>
            </div>
            <button onClick={() => setMini(true)} className="text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors p-0.5 rounded hover:bg-slate-200 dark:hover:bg-white/5">
              <ChevronLeft className="h-4 w-4" />
            </button>
          </>
        )}
        {mini && (
          <button onClick={() => setMini(false)} className="absolute right-1.5 top-4 text-slate-400 dark:text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors p-0.5 rounded hover:bg-slate-200 dark:hover:bg-white/5">
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Main navigation */}
      <div className="flex-1 overflow-y-auto px-2 pb-2 scrollbar-hide">
        {MENU.map(s => {
          const isOpen = openSections[s.label] ?? true;
          const sectionActive = s.items.some(i => active(i.path));
          return (
            <div key={s.label} className="mb-1">
              {!mini ? (
                <button
                  onClick={() => toggle(s.label)}
                  className={cn(
                    'flex items-center w-full px-2 pt-3 pb-1 group',
                    'text-[10px] font-semibold tracking-widest uppercase transition-colors',
                    'text-amber-700 dark:text-amber-400/80',
                  )}
                >
                  <span className="flex-1 text-left">{s.label}</span>
                  <ChevronDown className={cn('h-3 w-3 transition-transform opacity-0 group-hover:opacity-100', !isOpen && '-rotate-90')} />
                </button>
              ) : (
                <div className="my-2 border-t border-slate-200 dark:border-[#1e2740]" />
              )}
              {(mini || isOpen) && (
                <div className="space-y-0.5">
                  {s.items.map(item => {
                    const Icon = item.icon;
                    const on = active(item.path);
                    return (
                      <button key={item.id} onClick={() => nav(item.path)} title={mini ? item.name : undefined}
                        className={cn(
                          'flex items-center w-full rounded-md transition-colors relative',
                          mini ? 'justify-center px-2 py-2' : 'gap-2.5 px-3 py-[7px]',
                          on ? 'bg-purple-600/10 text-purple-600 dark:text-purple-400' : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/5',
                        )}>
                        {on && !mini && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-purple-600 dark:bg-purple-500" />}
                        <Icon className="h-4 w-4 shrink-0" />
                        {!mini && <span className="text-[13px] truncate">{item.name}</span>}
                      </button>
                    );
                  })}
                  {s.label === 'AI OPS' && (
                    <a
                      href={simulatorUiUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={mini ? 'Enterprise Simulator' : undefined}
                      className={cn(
                        'flex items-center w-full rounded-md transition-colors',
                        mini ? 'justify-center px-2 py-2' : 'gap-2.5 px-3 py-[7px]',
                        'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/5',
                      )}
                    >
                      <ExternalLink className="h-4 w-4 shrink-0" />
                      {!mini && <span className="text-[13px] truncate">Enterprise Simulator</span>}
                    </a>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom: Settings & Help */}
      <div className={cn(
        'px-2 py-2.5 space-y-0.5',
        'border-t-2 border-slate-200/80 dark:border-[#253354]',
        'bg-slate-50 dark:bg-[#111827]',
      )}>
        <button onClick={() => nav('/settings')} title={mini ? 'Settings' : undefined}
          className={cn(
            'flex items-center w-full rounded-md transition-colors',
            mini ? 'justify-center px-2 py-2' : 'gap-2.5 px-3 py-[7px]',
            active('/settings') ? 'bg-purple-600/10 text-purple-600 dark:text-purple-400' : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/5',
          )}>
          <Settings className="h-4 w-4 shrink-0" />
          {!mini && <span className="text-[13px]">Settings</span>}
        </button>
        <Popover>
          <PopoverTrigger asChild>
            <button title={mini ? 'Help' : undefined}
              className={cn(
                'flex items-center w-full rounded-md transition-colors',
                mini ? 'justify-center px-2 py-2' : 'gap-2.5 px-3 py-[7px]',
                'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/5',
              )}>
              <HelpCircle className="h-4 w-4 shrink-0" />
              {!mini && <span className="text-[13px]">Help</span>}
            </button>
          </PopoverTrigger>
          <PopoverContent side="right" align="end" sideOffset={8} className="w-48 p-1.5">
            {[
              { icon: FileText, label: 'Documentation', href: '/docs/' },
              { icon: LifeBuoy, label: 'Support', href: 'mailto:support@ptrtechnology.com' },
              { icon: Mail, label: 'Contact', href: 'mailto:contact@ptrtechnology.com' },
            ].map(item => (
              <a key={item.label} href={item.href} target={item.href.startsWith('http') ? '_blank' : undefined}
                rel={item.href.startsWith('http') ? 'noopener noreferrer' : undefined}
                className="flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white transition-colors">
                <item.icon className="h-4 w-4 shrink-0" />
                {item.label}
              </a>
            ))}
          </PopoverContent>
        </Popover>
      </div>
    </aside>
  );
};

export default Sidebar;
