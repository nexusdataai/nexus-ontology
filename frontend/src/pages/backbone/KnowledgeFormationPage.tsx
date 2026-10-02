import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Play, CheckCircle2, Loader2, XCircle } from 'lucide-react';

const RECENT_RUNS = [
  { id: 1, timestamp: '2025-02-27 14:32', status: 'completed' },
  { id: 2, timestamp: '2025-02-27 10:15', status: 'running' },
  { id: 3, timestamp: '2025-02-26 18:45', status: 'completed' },
  { id: 4, timestamp: '2025-02-26 09:20', status: 'failed' },
  { id: 5, timestamp: '2025-02-25 16:00', status: 'completed' },
];

const KnowledgeFormationPage: React.FC = () => {
  const StatusIcon = ({ status }: { status: string }) => {
    if (status === 'completed') return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    if (status === 'running') return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Knowledge Formation</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Build and manage your enterprise knowledge graph from connected data sources
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-lg">Pipeline Status</CardTitle>
              <p className="text-sm text-muted-foreground">Trigger knowledge extraction and graph build</p>
            </CardHeader>
            <CardContent>
              <Button>
                <Play className="h-4 w-4 mr-2" />
                Run Knowledge Pipeline
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-lg">Recent Runs</CardTitle>
              <p className="text-sm text-muted-foreground">Latest pipeline executions</p>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {RECENT_RUNS.map((run) => (
                  <li key={run.id} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                    <div className="flex items-center gap-2">
                      <StatusIcon status={run.status} />
                      <span className="text-sm">{run.timestamp}</span>
                    </div>
                    <Badge
                      variant={run.status === 'failed' ? 'destructive' : run.status === 'running' ? 'default' : 'secondary'}
                    >
                      {run.status}
                    </Badge>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default KnowledgeFormationPage;
