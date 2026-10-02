import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { HardDrive, Database, RotateCcw, CheckCircle } from 'lucide-react';

export function DataProtectionSection() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Data Protection</h2>
        <Badge variant="outline" className="text-xs">Mock Data</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Cluster Backup */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <HardDrive className="h-5 w-5" />
              Cluster Backup
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Last backup successful</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Last Backup</span><span className="font-medium">2h ago</span></div>
              <div className="flex justify-between"><span>Backup Size</span><span className="font-medium">2.4 GB</span></div>
              <div className="flex justify-between"><span>Schedule</span><span className="font-medium">Every 6h</span></div>
              <div className="flex justify-between"><span>Retention</span><span className="font-medium">30 days</span></div>
            </div>
            <Button variant="outline" size="sm" className="w-full" disabled>
              Trigger Backup
            </Button>
          </CardContent>
        </Card>

        {/* Call Database Backup */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Database className="h-5 w-5" />
              Call Database Backup
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-sm font-medium">Glue/S3 data protected</span>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>DynamoDB Backup</span><span className="font-medium">PITR Enabled</span></div>
              <div className="flex justify-between"><span>S3 Versioning</span><span className="font-medium">Enabled</span></div>
              <div className="flex justify-between"><span>Glue Snapshots</span><span className="font-medium">Daily</span></div>
              <div className="flex justify-between"><span>Total Data</span><span className="font-medium">1.8 GB</span></div>
            </div>
            <Button variant="outline" size="sm" className="w-full" disabled>
              Create Snapshot
            </Button>
          </CardContent>
        </Card>

        {/* Recovery */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <RotateCcw className="h-5 w-5" />
              Recovery
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm font-medium">Restore Points</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Latest</span><span className="font-medium">Today 14:00</span></div>
              <div className="flex justify-between"><span>Yesterday</span><span className="font-medium">Feb 08 23:00</span></div>
              <div className="flex justify-between"><span>2 Days Ago</span><span className="font-medium">Feb 07 23:00</span></div>
              <div className="flex justify-between"><span>Recovery Time</span><span className="font-medium">~15 min</span></div>
            </div>
            <Button variant="outline" size="sm" className="w-full" disabled>
              Restore from Backup
            </Button>
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Backup and recovery operations will be available in a future release.
      </p>
    </div>
  );
}
