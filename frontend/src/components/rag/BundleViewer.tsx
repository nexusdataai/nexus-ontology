import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Package, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ontoApi } from '@/services/ontoApi';

const BundleViewer: React.FC = () => {
  const [bundles, setBundles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<any>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [bundleRes, statsRes] = await Promise.all([
        ontoApi.listBundles(),
        ontoApi.getStats(),
      ]);
      setBundles(bundleRes.bundles || []);
      setStats(statsRes);
    } catch (e) {
      console.error('Failed to load bundle data:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  return (
    <div className="space-y-4">
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Package className="h-5 w-5" />
              Knowledge Index
            </CardTitle>
            <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
              {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {stats && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-md border p-3">
                <div className="text-2xl font-bold">{stats.total_embeddings}</div>
                <div className="text-muted-foreground">Total Embeddings</div>
              </div>
              <div className="rounded-md border p-3">
                <div className="text-2xl font-bold">{stats.onto_documents}</div>
                <div className="text-muted-foreground">Onto Documents</div>
              </div>
              {Object.entries(stats.by_content_type || {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between px-2">
                  <span className="text-xs text-muted-foreground capitalize">{type.replace('onto_', '')}</span>
                  <Badge variant="secondary" className="text-xs">{count as number}</Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {bundles.length > 0 && (
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">.onto Bundles</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {bundles.map((b, i) => (
              <div key={i} className="flex items-center justify-between text-sm border rounded-md p-2">
                <span className="font-mono text-xs">{b.job_id}</span>
                <Badge variant="outline" className="text-xs">bundle</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default BundleViewer;
