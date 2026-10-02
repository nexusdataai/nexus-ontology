/**
 * Ontos Dashboard Component
 *
 * Displays FDW health status and summary metrics.
 * When fdwSource is set, shows simulator-specific stats instead of real FDW health.
 */

import { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  Database,
  Globe,
  RefreshCw,
  Server,
  Table2,
  Rows3,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { fdwService } from '@/services/fdwService';
import type { FdwHealthResponse } from '@/types/fdwTypes';

interface SimStatus {
  enabled: boolean;
  loaded: boolean;
  schema: string;
  table_count: number;
  tables_with_data: number;
  total_rows: number;
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4" data-testid="dashboard-skeleton">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-4 rounded" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-16 mb-1" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

interface StatusCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ReactNode;
  statusColor?: 'green' | 'red' | 'amber';
}

function StatusCard({ title, value, description, icon, statusColor }: StatusCardProps) {
  return (
    <Card data-testid={`status-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          {statusColor && (
            <span className={`inline-block h-3 w-3 rounded-full ${
              statusColor === 'green' ? 'bg-green-500' : statusColor === 'amber' ? 'bg-amber-500' : 'bg-red-500'
            }`} />
          )}
          <div className="text-2xl font-bold">{value}</div>
        </div>
        {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
      </CardContent>
    </Card>
  );
}

export function OntosDashboard({ fdwSource }: { fdwSource?: string }) {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<FdwHealthResponse | null>(null);
  const [simStatus, setSimStatus] = useState<SimStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (fdwSource && fdwSource !== 'real') {
        const tables = await fdwService.listTables(undefined, fdwSource);
        setSimStatus({
          enabled: true,
          loaded: tables.length > 0,
          schema: tables[0]?.schemaName || '',
          table_count: tables.length,
          tables_with_data: tables.length,
          total_rows: 0,
        });
        setHealth(null);
      } else {
        const data = await fdwService.getHealth();
        setHealth(data);
        setSimStatus(null);
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to load status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, [fdwSource]);

  if (loading) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
        <DashboardSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-4">Dashboard</h2>
        <Card className="border-destructive">
          <CardHeader className="flex flex-row items-center gap-2 space-y-0 pb-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <CardTitle className="text-base">Connection Error</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className="h-4 w-4 mr-1" /> Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (simStatus) {
    const sourceLabel = fdwSource === 'oracle' ? 'Oracle ERP' : fdwSource === 'sap' ? 'SAP S/4HANA' : fdwSource === 'external' ? 'External Sources' : 'Salesforce';
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Dashboard</h2>
            <Badge className="bg-amber-500/20 text-amber-300 text-[10px]">Simulator</Badge>
            <Badge className="bg-blue-500/20 text-blue-300 text-[10px]">{sourceLabel}</Badge>
          </div>
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="h-4 w-4 mr-1" /> Refresh
          </Button>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatusCard
            title="Status"
            value={simStatus.loaded ? 'Loaded' : 'Not Loaded'}
            icon={<Globe className="h-4 w-4 text-muted-foreground" />}
            statusColor={simStatus.loaded ? 'green' : 'red'}
            description={`Schema: ${simStatus.schema || '—'}`}
          />
          <StatusCard
            title="Tables"
            value={simStatus.table_count.toLocaleString()}
            icon={<Table2 className="h-4 w-4 text-muted-foreground" />}
            description={`${simStatus.tables_with_data} with data`}
          />
          <StatusCard
            title="Total Rows"
            value={simStatus.total_rows.toLocaleString()}
            icon={<Rows3 className="h-4 w-4 text-muted-foreground" />}
            description="Simulated data rows"
          />
          <StatusCard
            title="Data Source"
            value={sourceLabel}
            icon={<Database className="h-4 w-4 text-muted-foreground" />}
            statusColor="amber"
            description="Simulator mode active"
          />
        </div>
      </div>
    );
  }

  const isHealthy = health?.status === 'healthy';
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Dashboard</h2>
          <Badge className="bg-green-500/20 text-green-300 text-[10px]">Real FDW</Badge>
        </div>
        {health?.latencyMs != null && (
          <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <Activity className="h-4 w-4" />
            <span>Latency: {health.latencyMs}ms</span>
          </div>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatusCard
          title="Connection Status"
          value={isHealthy ? 'Healthy' : health?.error ?? 'Error'}
          icon={<Globe className="h-4 w-4 text-muted-foreground" />}
          statusColor={isHealthy ? 'green' : 'red'}
          description={isHealthy ? 'FDW connection is active' : 'FDW connection has issues'}
        />
        <StatusCard
          title="Foreign Servers"
          value={health?.foreignServersCount ?? 0}
          icon={<Server className="h-4 w-4 text-muted-foreground" />}
          description="Configured foreign servers"
        />
        <StatusCard
          title="Foreign Tables"
          value={health?.foreignTablesCount ?? 0}
          icon={<Table2 className="h-4 w-4 text-muted-foreground" />}
          description="Available foreign tables"
        />
      </div>
    </div>
  );
}

export default OntosDashboard;
