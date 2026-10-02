import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  BarChart3, Bell, Workflow, MessageSquare, ArrowRight,
  Clock, Database, Zap, CheckCircle2,
} from 'lucide-react';
import type { AppConfig } from '@/config/appRegistry';

interface Props {
  app: AppConfig;
  onNavigate: (section: string, tab?: string) => void;
}

export function AppOverview({ app, onNavigate }: Props) {
  const Icon = app.icon;

  return (
    <div className="p-6 space-y-6">
      {/* Hero */}
      <div className={`rounded-xl p-6 bg-gradient-to-r ${app.color} text-white`}>
        <div className="flex items-center gap-3 mb-3">
          <Icon className="h-8 w-8" />
          <div>
            <h1 className="text-xl font-bold">{app.name}</h1>
            <p className="text-sm opacity-80">{app.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 mt-4">
          {app.kpis.map(kpi => (
            <div key={kpi.label} className="bg-white/10 rounded-lg px-3 py-1.5">
              <span className="text-xs opacity-70">{kpi.label}</span>
              <span className="text-sm font-bold ml-1">{kpi.target}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card><CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div><p className="text-[10px] text-muted-foreground">Entities</p><p className="text-xl font-bold">{app.entities.length}</p></div>
            <Database className="h-5 w-5 text-blue-400 opacity-50" />
          </div>
        </CardContent></Card>
        <Card><CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div><p className="text-[10px] text-muted-foreground">KPI Targets</p><p className="text-xl font-bold">{app.kpis.length}</p></div>
            <Zap className="h-5 w-5 text-amber-400 opacity-50" />
          </div>
        </CardContent></Card>
        <Card><CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div><p className="text-[10px] text-muted-foreground">Status</p><p className="text-sm font-bold text-green-400">{app.status === 'available' ? 'Active' : 'Coming Soon'}</p></div>
            <CheckCircle2 className="h-5 w-5 text-green-400 opacity-50" />
          </div>
        </CardContent></Card>
        <Card><CardContent className="pt-4">
          <div className="flex items-center justify-between">
            <div><p className="text-[10px] text-muted-foreground">Use Case</p><p className="text-sm font-bold">{app.useCase}</p></div>
            <Clock className="h-5 w-5 text-purple-400 opacity-50" />
          </div>
        </CardContent></Card>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { id: 'dashboards', label: 'Dashboards', desc: 'KPIs, charts, and data analysis', icon: BarChart3, color: 'text-blue-400' },
          { id: 'alerts', label: 'Alerts', desc: 'Monitoring rules and triggered alerts', icon: Bell, color: 'text-amber-400' },
          { id: 'workflows', label: 'Workflows', desc: 'Associated journeys and automations', icon: Workflow, color: 'text-purple-400' },
          { id: 'chat', label: 'AI Assistant', desc: 'Ask questions about this domain', icon: MessageSquare, color: 'text-green-400' },
        ].map(item => (
          <Card key={item.id} className="cursor-pointer hover:border-primary/50 transition-all group" onClick={() => onNavigate(item.id)}>
            <CardContent className="pt-4">
              <item.icon className={`h-6 w-6 ${item.color} mb-2`} />
              <h3 className="text-sm font-semibold">{item.label}</h3>
              <p className="text-[10px] text-muted-foreground mt-0.5">{item.desc}</p>
              <div className="flex items-center gap-1 mt-2 text-[10px] text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                Open <ArrowRight className="h-2.5 w-2.5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Entity Coverage */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-semibold mb-3">Data Entities ({app.entities.length})</h3>
          <div className="flex flex-wrap gap-2">
            {app.entities.map(e => (
              <Badge key={e} variant="outline" className="text-xs">{e}</Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
