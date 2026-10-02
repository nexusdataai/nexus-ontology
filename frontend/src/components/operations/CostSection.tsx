import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { DollarSign, Cloud, HardDrive } from 'lucide-react';

export function CostSection() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cost Management</h2>
        <Badge variant="outline" className="text-xs">Mock Data</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* AWS Resources */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Cloud className="h-5 w-5" />
              AWS Resource Costs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">
              $<span>142</span><span className="text-lg text-muted-foreground">/mo</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>EKS Cluster</span><span className="font-medium">$73.00</span></div>
              <div className="flex justify-between"><span>EC2 Nodes (2x)</span><span className="font-medium">$45.00</span></div>
              <div className="flex justify-between"><span>ALB</span><span className="font-medium">$16.20</span></div>
              <div className="flex justify-between"><span>NAT Gateway</span><span className="font-medium">$7.80</span></div>
            </div>
          </CardContent>
        </Card>

        {/* Storage */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <HardDrive className="h-5 w-5" />
              Storage Costs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">
              $<span>8.50</span><span className="text-lg text-muted-foreground">/mo</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>S3 (4 buckets)</span><span className="font-medium">$3.20</span></div>
              <div className="flex justify-between"><span>DynamoDB</span><span className="font-medium">$2.50</span></div>
              <div className="flex justify-between"><span>ECR Images</span><span className="font-medium">$1.80</span></div>
              <div className="flex justify-between"><span>CloudWatch Logs</span><span className="font-medium">$1.00</span></div>
            </div>
          </CardContent>
        </Card>

        {/* AI/Compute */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <DollarSign className="h-5 w-5" />
              AI / Compute Costs
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">
              $<span>24</span><span className="text-lg text-muted-foreground">/mo</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>OpenAI (GPT-4o)</span><span className="font-medium">$18.00</span></div>
              <div className="flex justify-between"><span>Athena Queries</span><span className="font-medium">$3.50</span></div>
              <div className="flex justify-between"><span>Glue Catalog</span><span className="font-medium">$1.50</span></div>
              <div className="flex justify-between"><span>Cognito</span><span className="font-medium">$1.00</span></div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="p-4 bg-muted/30 rounded-lg">
        <div className="flex justify-between items-center">
          <div>
            <div className="text-sm font-medium">Estimated Monthly Total</div>
            <div className="text-xs text-muted-foreground">Based on current usage patterns</div>
          </div>
          <div className="text-2xl font-bold">$174.50<span className="text-sm text-muted-foreground">/mo</span></div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Real cost data from AWS Cost Explorer will be available in a future release.
      </p>
    </div>
  );
}
