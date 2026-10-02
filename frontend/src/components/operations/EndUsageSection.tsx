import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Users, Globe, Phone } from 'lucide-react';

export function EndUsageSection() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">End Usage</h2>
        <Badge variant="outline" className="text-xs">Mock Data</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* User Activity */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users className="h-5 w-5" />
              User Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">12</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Active Sessions</span><span className="font-medium">3</span></div>
              <div className="flex justify-between"><span>Logins Today</span><span className="font-medium">8</span></div>
              <div className="flex justify-between"><span>Unique Users (7d)</span><span className="font-medium">5</span></div>
              <div className="flex justify-between"><span>Avg Session Duration</span><span className="font-medium">24m</span></div>
            </div>
          </CardContent>
        </Card>

        {/* API Usage */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Globe className="h-5 w-5" />
              API Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">1,247</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Requests Today</span><span className="font-medium">1,247</span></div>
              <div className="flex justify-between"><span>Requests/min (avg)</span><span className="font-medium">12.3</span></div>
              <div className="flex justify-between"><span>Top Endpoint</span><span className="font-medium">/api/v1/journeys</span></div>
              <div className="flex justify-between"><span>Error Rate</span><span className="font-medium">0.8%</span></div>
            </div>
          </CardContent>
        </Card>

        {/* Calls Processed */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Phone className="h-5 w-5" />
              Calls Processed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold mb-3">37</div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between"><span>Total Processed</span><span className="font-medium">37</span></div>
              <div className="flex justify-between"><span>Today</span><span className="font-medium">3</span></div>
              <div className="flex justify-between"><span>With Transcription</span><span className="font-medium">34</span></div>
              <div className="flex justify-between"><span>With AI Analysis</span><span className="font-medium">31</span></div>
            </div>
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Real usage analytics will be available in a future release.
      </p>
    </div>
  );
}
