import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Workflow, Play, Clock, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { AppConfig } from '@/config/appRegistry';

interface Props { app: AppConfig; }

export function AppWorkflows({ app }: Props) {
  const nav = useNavigate();

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold flex items-center gap-2"><Workflow className="h-5 w-5 text-primary" /> Workflows</h2>
        <p className="text-xs text-muted-foreground">Associated journeys and automations for {app.name}</p>
      </div>

      {app.journeyStageId ? (
        <Card className="hover:border-primary/50 transition-all">
          <CardContent className="pt-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Workflow className="h-5 w-5 text-primary" />
                  <h3 className="font-semibold">{app.name} Journey</h3>
                  <Badge className="bg-success/20 text-success text-xs">Available</Badge>
                </div>
                <p className="text-xs text-muted-foreground">Automated {app.useCase} pipeline using ReAct tools and Virtual Data Layer</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> Stage: {app.journeyStageId}</span>
                  <span>{app.entities.length} entities</span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => nav('/operations/journeys')}>
                  <Play className="h-3.5 w-3.5 mr-1" /> Run
                </Button>
                <Button size="sm" variant="outline" onClick={() => nav('/operations/journeys')}>
                  <ArrowRight className="h-3.5 w-3.5 mr-1" /> Open in Studio
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="pt-4 text-center py-10">
            <Workflow className="h-8 w-8 mx-auto mb-2 opacity-20" />
            <p className="text-sm text-muted-foreground">No workflows configured yet</p>
            <p className="text-xs text-muted-foreground mt-1">Create a journey for this app using the Journey Builder</p>
            <Button size="sm" variant="outline" className="mt-3" onClick={() => nav('/workspace/automation')}>
              Open Journey Builder
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Related automations */}
      <Card>
        <CardContent className="pt-4">
          <h3 className="text-sm font-semibold mb-3">Available Automations</h3>
          <div className="space-y-2">
            {[
              { name: 'Copilot Journey', desc: 'AI-guided dynamic automation', path: '/workspace/automation' },
              { name: 'Journey Builder', desc: 'Design custom step sequences', path: '/workspace/automation' },
              { name: 'Plugin Framework', desc: 'Register YAML-defined plugins', path: '/workspace/tools' },
            ].map(a => (
              <div key={a.name} className="flex items-center justify-between p-2 rounded hover:bg-muted/30 cursor-pointer" onClick={() => nav(a.path)}>
                <div>
                  <span className="text-xs font-medium">{a.name}</span>
                  <p className="text-xs text-muted-foreground">{a.desc}</p>
                </div>
                <ArrowRight className="h-3 w-3 text-muted-foreground" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
