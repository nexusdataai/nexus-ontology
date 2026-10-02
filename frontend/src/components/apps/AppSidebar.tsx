import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronLeft, ChevronRight, ArrowLeft, Bot, Wrench, AppWindow } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { AppConfig } from '@/config/appRegistry';
import type { Solution } from '@/lib/foundry/model';

interface Props {
  app: AppConfig;
  solution: Solution | null;
  activeSection: string;
  onSectionChange: (sectionId: string) => void;
}

const WORKSPACE_ITEMS = [
  { id: 'agent-builder', name: 'Agent Builder', icon: Bot },
  { id: 'tools-catalogue', name: 'Tools Catalogue', icon: Wrench },
];

export function AppSidebar({ app, solution, activeSection, onSectionChange }: Props) {
  const nav = useNavigate();
  const [mini, setMini] = useState(false);

  const Icon = app.icon;

  return (
    <div className={cn(
      'h-full flex flex-col border-r border-border bg-card transition-all duration-200',
      mini ? 'w-14' : 'w-[200px]',
    )}>
      {/* App header */}
      <div className="px-3 py-3 border-b border-border">
        {!mini && (
          <div className="flex items-center gap-2 mb-2">
            <div className={`p-1.5 rounded-lg bg-gradient-to-br ${app.color}`}>
              <Icon className="h-4 w-4 text-white" />
            </div>
            <span className="text-xs font-semibold truncate">{app.shortName}</span>
          </div>
        )}
        <button onClick={() => nav('/workspace/apps')}
          className="flex items-center gap-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors w-full">
          <ArrowLeft className="h-3 w-3" />
          {!mini && 'Back to Catalogue'}
        </button>
      </div>

      {/* Menu items */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* ANALYTICS section */}
        {!mini && (
          <div className="px-3 py-1.5 text-[9px] font-semibold text-amber-700 dark:text-amber-400/80 uppercase tracking-wider">
            Analytics
          </div>
        )}
        {app.sections.map(section => {
          const SIcon = section.icon;
          const isActive = activeSection === section.id;

          return (
            <button key={section.id}
              onClick={() => onSectionChange(section.id)}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors',
                isActive ? 'bg-primary/10 text-primary border-l-2 border-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
              )}
            >
              <SIcon className="h-3.5 w-3.5 shrink-0" />
              {!mini && <span className="flex-1 text-left truncate">{section.name}</span>}
            </button>
          );
        })}

        {/* VIEWS section (backend Solution -> Views) */}
        {solution && solution.views.length > 0 && (
          <>
            {!mini && (
              <div className="px-3 pt-3 pb-1.5 text-[9px] font-semibold text-amber-700 dark:text-amber-400/80 uppercase tracking-wider">
                Views
              </div>
            )}
            {mini && <div className="my-2 border-t border-border" />}
            {solution.views.map((link) => {
              const sectionId = `view:${link.viewId}`;
              const isActive = activeSection === sectionId;
              const label = link.displayName || link.name || link.viewId;
              return (
                <button
                  key={link.viewId}
                  onClick={() => onSectionChange(sectionId)}
                  className={cn(
                    'w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary border-l-2 border-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
                  )}
                  title={mini ? label : undefined}
                >
                  <AppWindow className="h-3.5 w-3.5 shrink-0" />
                  {!mini && <span className="flex-1 text-left truncate">{label}</span>}
                </button>
              );
            })}
          </>
        )}

        {/* WORKSPACE section */}
        {!mini && (
          <div className="px-3 pt-3 pb-1.5 text-[9px] font-semibold text-amber-700 dark:text-amber-400/80 uppercase tracking-wider">
            Workspace
          </div>
        )}
        {mini && <div className="my-2 border-t border-border" />}
        {WORKSPACE_ITEMS.map(item => {
          const WIcon = item.icon;
          const isActive = activeSection === item.id;
          return (
            <button key={item.id}
              onClick={() => onSectionChange(item.id)}
              className={cn(
                'w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors',
                isActive ? 'bg-primary/10 text-primary border-l-2 border-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
              )}
            >
              <WIcon className="h-3.5 w-3.5 shrink-0" />
              {!mini && <span className="flex-1 text-left truncate">{item.name}</span>}
            </button>
          );
        })}
      </div>

      {/* Collapse toggle */}
      <div className="border-t border-border p-1">
        <button onClick={() => setMini(m => !m)} className="w-full flex items-center justify-center p-1.5 rounded hover:bg-muted/50 text-muted-foreground">
          {mini ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  );
}
