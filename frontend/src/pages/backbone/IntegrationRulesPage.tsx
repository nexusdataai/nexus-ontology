import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

const INTEGRATIONS = [
  { id: 1, name: 'Salesforce-Oracle Sync', systems: ['Salesforce', 'Oracle'] },
  { id: 2, name: 'ERP-CRM Mapping', systems: ['ERP', 'CRM'] },
];

const IntegrationRulesPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-lg font-semibold">Integration Rules</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Configure field mappings and sync rules between enterprise systems
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Integration
          </Button>
        </div>

        <Card className="border-border bg-card/50">
          <CardHeader>
            <CardTitle className="text-lg">Integrations</CardTitle>
            <p className="text-sm text-muted-foreground">System connections and mapping rules</p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {INTEGRATIONS.map((integration) => (
                <li
                  key={integration.id}
                  className="flex items-center justify-between py-3 px-4 rounded-md bg-background/50 border border-border/50 hover:border-border transition-colors"
                >
                  <span className="font-medium">{integration.name}</span>
                  <div className="flex gap-2 flex-wrap justify-end">
                    {integration.systems.map((sys) => (
                      <Badge key={sys} variant="secondary" className="border-border">
                        {sys}
                      </Badge>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default IntegrationRulesPage;
