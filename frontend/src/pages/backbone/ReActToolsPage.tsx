import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Wrench } from 'lucide-react';

const TOOLS = [
  { name: 'get_account', desc: 'Retrieve account details by ID', params: 1, usage: 1247 },
  { name: 'get_ar_balance', desc: 'Fetch accounts receivable balance', params: 2, usage: 892 },
  { name: 'propose_credit_change', desc: 'Propose credit limit changes', params: 3, usage: 156 },
  { name: 'create_customer', desc: 'Create a new customer record', params: 5, usage: 423 },
  { name: 'trigger_workflow', desc: 'Execute workflow by identifier', params: 2, usage: 312 },
  { name: 'search_enterprise_knowledge', desc: 'Search RAG-indexed knowledge base', params: 2, usage: 2891 },
];

const ReActToolsPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-2xl font-bold">ReAct Tools</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Browse and test tools available to the ReAct planning agent
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {TOOLS.map((t) => (
            <Card key={t.name} className="border-border bg-card/50">
              <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Wrench className="h-4 w-4 text-muted-foreground shrink-0" />
                  <CardTitle className="text-base font-mono truncate">{t.name}</CardTitle>
                </div>
                <Badge variant="secondary" className="border-border shrink-0">{t.usage} uses</Badge>
              </CardHeader>
              <CardContent className="pt-0">
                <p className="text-sm text-muted-foreground mb-3">{t.desc}</p>
                <p className="text-xs text-muted-foreground mb-4">{t.params} parameter{t.params !== 1 ? 's' : ''}</p>
                <Button variant="secondary" size="sm" className="w-full">Test Tool</Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </Layout>
  );
};

export default ReActToolsPage;
