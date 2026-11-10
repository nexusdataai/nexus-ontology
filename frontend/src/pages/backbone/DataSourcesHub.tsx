import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';

const STRUCTURED_SOURCES = [
  { letter: 'S', color: 'bg-primary/20 text-primary', name: 'Salesforce CRM', desc: 'Customer and sales data', records: '2.4M records' },
  { letter: 'O', color: 'bg-warning/20 text-warning', name: 'Oracle ERP', desc: 'Finance and operations', records: '1.1M records' },
  { letter: 'S', color: 'bg-success/20 text-success', name: 'SAP', desc: 'ERP and supply chain', records: '890K records' },
];

const UNSTRUCTURED_SOURCES = [
  { letter: 'G', color: 'bg-primary/20 text-primary', name: 'Google Drive', desc: 'Documents and sheets', records: '24.8K docs' },
  { letter: 'F', color: 'bg-primary/20 text-primary', name: 'File Uploads', desc: 'Manual file ingestion', records: '1.2K files' },
  { letter: 'S', color: 'bg-destructive/20 text-destructive', name: 'Social Listening', desc: 'Social media mentions', records: '12.6M mentions' },
];

const DataSourcesHub: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-semibold">Data Sources Hub</h1>
              <Badge variant="secondary" className="border-border">0 / 6 sources connected</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Connect your enterprise data ecosystem — structured and unstructured sources
            </p>
          </div>
          <Button className="shrink-0">
            <Plus className="h-4 w-4 mr-2" />
            Add Data Source
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <h2 className="text-lg font-semibold mb-4 text-foreground">Structured Data</h2>
            <div className="space-y-4">
              {STRUCTURED_SOURCES.map((s) => (
                <Card key={s.name} className="border-border bg-card/50">
                  <CardHeader className="flex flex-row items-start gap-4 pb-2">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${s.color}`}>
                      {s.letter}
                    </div>
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base">{s.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{s.desc}</p>
                      <p className="text-xs text-muted-foreground mt-1">{s.records}</p>
                    </div>
                    <Button variant="secondary" size="sm" className="shrink-0">Connect</Button>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
          <div>
            <h2 className="text-lg font-semibold mb-4 text-foreground">Unstructured Data</h2>
            <div className="space-y-4">
              {UNSTRUCTURED_SOURCES.map((s) => (
                <Card key={s.name} className="border-border bg-card/50">
                  <CardHeader className="flex flex-row items-start gap-4 pb-2">
                    <div className={`h-10 w-10 rounded-lg flex items-center justify-center shrink-0 ${s.color}`}>
                      {s.letter}
                    </div>
                    <div className="flex-1 min-w-0">
                      <CardTitle className="text-base">{s.name}</CardTitle>
                      <p className="text-sm text-muted-foreground">{s.desc}</p>
                      <p className="text-xs text-muted-foreground mt-1">{s.records}</p>
                    </div>
                    <Button variant="secondary" size="sm" className="shrink-0">Connect</Button>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default DataSourcesHub;
