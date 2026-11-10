import React, { useState } from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const BackendDebugPage: React.FC = () => {
  const [url, setUrl] = useState('');

  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold">Backend Debug</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Debug API endpoints and MCP tool execution
          </p>
        </div>

        <div className="space-y-6 max-w-3xl">
          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">API Endpoint Tester</CardTitle>
              <p className="text-sm text-muted-foreground">Send requests to backend endpoints</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-2">
                <Select>
                  <SelectTrigger className="w-full sm:w-32 border-border shrink-0">
                    <SelectValue placeholder="Method" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="PATCH">PATCH</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://api.example.com/endpoint"
                  className="flex-1 border-border"
                />
                <Button className="shrink-0">Send Request</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Response</CardTitle>
              <p className="text-sm text-muted-foreground">Response body and headers</p>
            </CardHeader>
            <CardContent>
              <pre className=" rounded-md border border-border bg-muted/20 p-4 text-sm font-mono min-h-[200px] text-muted-foreground overflow-auto">
                {''}
              </pre>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default BackendDebugPage;
