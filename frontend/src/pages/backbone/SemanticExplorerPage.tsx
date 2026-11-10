import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';

const SemanticExplorerPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold">Semantic Explorer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Search and explore your enterprise knowledge using natural language
          </p>
        </div>

        <div className="max-w-2xl mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search the knowledge graph..."
              className="pl-10 border-border bg-card/50"
            />
          </div>
        </div>

        <Card className="border-border bg-card/50 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-muted-foreground">Enter a query to explore the knowledge graph</p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default SemanticExplorerPage;
