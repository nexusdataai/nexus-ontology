import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Activity, Wifi, Shield, CheckCircle, Clock } from 'lucide-react';

interface MetricCard {
  title: string;
  icon: React.ReactNode;
  value: string;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  details: { label: string; value: string }[];
}

const METRICS: MetricCard[] = [
  {
    title: 'Performance',
    icon: <Activity className="h-5 w-5" />,
    value: '98.5',
    unit: '%',
    status: 'healthy',
    details: [
      { label: 'Response Time', value: '45ms' },
      { label: 'Throughput', value: '120 req/s' },
      { label: 'Error Rate', value: '0.2%' },
    ],
  },
  {
    title: 'Availability',
    icon: <Wifi className="h-5 w-5" />,
    value: '99.9',
    unit: '%',
    status: 'healthy',
    details: [
      { label: 'Uptime (30d)', value: '29d 23h' },
      { label: 'Last Downtime', value: 'None' },
      { label: 'Health Checks', value: 'All Pass' },
    ],
  },
  {
    title: 'Reliability',
    icon: <CheckCircle className="h-5 w-5" />,
    value: '99.7',
    unit: '%',
    status: 'healthy',
    details: [
      { label: 'Success Rate', value: '99.7%' },
      { label: 'Failed Jobs', value: '0' },
      { label: 'Retries', value: '3' },
    ],
  },
  {
    title: 'Security',
    icon: <Shield className="h-5 w-5" />,
    value: 'Secure',
    unit: '',
    status: 'healthy',
    details: [
      { label: 'Auth Method', value: 'Cognito + IRSA' },
      { label: 'TLS', value: 'Enabled' },
      { label: 'Last Scan', value: 'Today' },
    ],
  },
  {
    title: 'Compliance',
    icon: <Clock className="h-5 w-5" />,
    value: '100',
    unit: '%',
    status: 'healthy',
    details: [
      { label: 'PDPA', value: 'Compliant' },
      { label: 'Data Retention', value: '90 days' },
      { label: 'Audit Log', value: 'Enabled' },
    ],
  },
];

const statusColor = (s: string) =>
  s === 'healthy' ? 'bg-success' : s === 'warning' ? 'bg-warning' : 'bg-destructive';

export function MonitoringSection() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">System Monitoring</h2>
        <Badge variant="outline" className="text-xs">Mock Data</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {METRICS.map((m) => (
          <Card key={m.title}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  {m.icon}
                  {m.title}
                </span>
                <Badge className={statusColor(m.status)} variant="default">
                  {m.status}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold mb-3">
                {m.value}<span className="text-lg text-muted-foreground">{m.unit}</span>
              </div>
              <div className="space-y-1">
                {m.details.map((d) => (
                  <div key={d.label} className="flex justify-between text-xs text-muted-foreground">
                    <span>{d.label}</span>
                    <span className="font-medium">{d.value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Real-time monitoring data will be available in a future release.
      </p>
    </div>
  );
}
