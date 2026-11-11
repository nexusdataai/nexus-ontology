import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Network, Database, GitBranch, BookOpen } from 'lucide-react';

const STATS = [
  { title: 'Graph Nodes', value: '12,847', icon: Network },
  { title: 'Vector Embeddings', value: '2.4M', icon: Database },
  { title: 'Relationships', value: '48,231', icon: GitBranch },
  { title: 'Ontology Coverage', value: '94%', icon: BookOpen },
];

const ENTITY_TYPES = [
  'Customer',
  'Product',
  'Organization',
  'Transaction',
  'Contract',
  'Event',
  'Document',
  'Location',
  'Person',
  'Account',
];

const SemanticLayerPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-lg font-semibold">Semantic Layer</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Unified view of your enterprise knowledge graph, vector embeddings, and entity relationships
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {STATS.map((s) => (
            <Card key={s.title} className="border-border bg-card/50">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{s.title}</CardTitle>
                <s.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold">{s.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="border-border bg-card/50">
          <CardHeader>
            <CardTitle className="text-lg">Entity Types</CardTitle>
            <p className="text-sm text-muted-foreground">Categories in your ontology</p>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {ENTITY_TYPES.map((type) => (
              <Badge key={type} variant="secondary" className="border-border">
                {type}
              </Badge>
            ))}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default SemanticLayerPage;
