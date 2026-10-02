import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Pencil, Trash2, Plus } from 'lucide-react';

const POLICIES = [
  { id: 1, name: 'Credit Limit Policy' },
  { id: 2, name: 'Customer Lifecycle Policy' },
  { id: 3, name: 'SOX Compliance' },
];

const PolicyBuilderPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold">Policy Builder</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Define and manage business policies that govern AI operations
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Policy
          </Button>
        </div>

        <Card className="border-border bg-card/50">
          <CardHeader>
            <CardTitle className="text-lg">Policies</CardTitle>
            <p className="text-sm text-muted-foreground">Configure business rules and governance</p>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {POLICIES.map((policy) => (
                <li
                  key={policy.id}
                  className="flex items-center justify-between py-3 px-4 rounded-md bg-background/50 border border-border/50 hover:border-border transition-colors"
                >
                  <span className="font-medium">{policy.name}</span>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <Trash2 className="h-4 w-4 text-red-400" />
                    </Button>
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

export default PolicyBuilderPage;
