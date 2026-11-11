import React from 'react';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';

const ToolBuilderPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6 bg-background text-foreground min-h-screen">
        <div className="mb-8">
          <h1 className="text-lg font-semibold">Tool Builder</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create custom tools for the ReAct planning engine
          </p>
        </div>

        <div className="max-w-2xl space-y-6">
          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Tool Name</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Input placeholder="e.g. get_account" disabled className="border-border" />
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Description</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <Textarea placeholder="Describe what this tool does..." disabled className="border-border min-h-[80px]" />
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Parameters</CardTitle>
              <p className="text-sm text-muted-foreground">Define input parameters for the tool</p>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Name</Label>
                    <Input placeholder="param_name" disabled className="border-border mt-1" />
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Type</Label>
                    <Input placeholder="string" disabled className="border-border mt-1" />
                  </div>
                </div>
                <Button variant="outline" size="sm" disabled className="border-border">Add Parameter</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border bg-card/50">
            <CardHeader>
              <CardTitle className="text-base">Implementation</CardTitle>
              <p className="text-sm text-muted-foreground">Code or API configuration for the tool</p>
            </CardHeader>
            <CardContent className="pt-0">
              <Textarea placeholder="// Implementation code or config..." disabled className="border-border min-h-[120px] font-mono text-sm" />
            </CardContent>
          </Card>

          <Button className="w-full sm:w-auto">Create Tool</Button>
        </div>
      </div>
    </Layout>
  );
};

export default ToolBuilderPage;
