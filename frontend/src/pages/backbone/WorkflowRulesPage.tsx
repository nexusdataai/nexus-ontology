import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

const WORKFLOWS = [
  { id: 1, name: 'Credit Approval Flow', type: 'yaml' },
  { id: 2, name: 'Customer Onboarding', type: 'json' },
  { id: 3, name: 'Risk Assessment', type: 'yaml' },
];

const WorkflowRulesPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-semibold">Workflow Rules</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Define workflow rules and process automation triggers
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Workflow
          </Button>
        </div>

        <Card className="border-border bg-card/50">
          <CardHeader>
            <CardTitle className="text-lg">Workflows</CardTitle>
            <p className="text-sm text-muted-foreground">Configure automation flows</p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {WORKFLOWS.map((workflow) => (
                <li
                  key={workflow.id}
                  className="flex items-center justify-between py-3 px-4 rounded-md bg-background/50 border border-border/50 hover:border-border transition-colors"
                >
                  <span className="font-medium">{workflow.name}</span>
                  <Badge variant="secondary" className="border-border uppercase">
                    {workflow.type}
                  </Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default WorkflowRulesPage;
