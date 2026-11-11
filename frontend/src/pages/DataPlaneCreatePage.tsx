import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { dataPlaneService, CreateDataPlaneRequest } from '@/services/dataPlaneService';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowLeft } from 'lucide-react';
import Layout from '@/components/Layout';

type DPType = 'FDW' | 'CDC' | 'ETL';

const typeFields: Record<DPType, { key: string; label: string; type?: string }[]> = {
  FDW: [
    { key: 'host', label: 'Host' },
    { key: 'port', label: 'Port', type: 'number' },
    { key: 'database', label: 'Database' },
    { key: 'user', label: 'User' },
    { key: 'password', label: 'Password', type: 'password' },
  ],
  CDC: [
    { key: 'bootstrapServers', label: 'Bootstrap Servers' },
    { key: 'topicPrefix', label: 'Topic Prefix' },
    { key: 'sourceDatabase', label: 'Source Database' },
  ],
  ETL: [
    { key: 'sourceType', label: 'Source Type' },
    { key: 'schedule', label: 'Schedule (cron)' },
    { key: 'transformationEngine', label: 'Transformation Engine' },
  ],
};

export default function DataPlaneCreatePage() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [type, setType] = useState<DPType>('FDW');
  const [config, setConfig] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CreateDataPlaneRequest) => dataPlaneService.create(data),
    onSuccess: () => navigate('/data-plane'),
    onError: (err: any) => setError(err?.data?.detail || err?.message || 'Creation failed'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) { setError('Name is required'); return; }
    const connectionConfig = { ...config };
    if (type === 'FDW' && connectionConfig.port) {
      connectionConfig.port = Number(connectionConfig.port);
    }
    mutation.mutate({ name: name.trim(), type, connectionConfig });
  };

  return (
    <Layout>
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" size="icon" onClick={() => navigate('/data-plane')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">Create Data Plane</h1>
      </div>

      <Card>
        <CardHeader><CardTitle>Configuration</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Name</label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="my-data-plane" />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">Type</label>
              <Select value={type} onValueChange={v => { setType(v as DPType); setConfig({}); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="FDW">FDW (Foreign Data Wrapper)</SelectItem>
                  <SelectItem value="CDC">CDC (Change Data Capture)</SelectItem>
                  <SelectItem value="ETL">ETL (Extract, Transform, Load)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-3">
              <label className="text-sm font-medium block">Connection Config</label>
              {typeFields[type].map(f => (
                <div key={f.key}>
                  <label className="text-xs text-muted-foreground mb-1 block">{f.label}</label>
                  <Input
                    type={f.type || 'text'}
                    value={config[f.key] || ''}
                    onChange={e => setConfig(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.label}
                  />
                </div>
              ))}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Creating...' : 'Create'}
              </Button>
              <Button type="button" variant="outline" onClick={() => navigate('/data-plane')}>Cancel</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
    </Layout>
  );
}
