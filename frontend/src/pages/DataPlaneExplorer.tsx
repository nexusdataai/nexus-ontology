import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { dataPlaneService } from '@/services/dataPlaneService';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft } from 'lucide-react';
import Layout from '@/components/Layout';
import { OntosWorkspace } from '@/components/ontos/OntosWorkspace';
import FileUploadsPanel from '@/components/data-source-panels/FileUploadsPanel';
import SocialListeningPanel from '@/components/data-source-panels/SocialListeningPanel';
import GoogleDrivePanel from '@/components/data-source-panels/GoogleDrivePanel';

const CUSTOM_PANELS: Record<string, React.ComponentType> = {
  'sample-drive': GoogleDrivePanel,
  'sample-files': FileUploadsPanel,
  'sample-social': SocialListeningPanel,
};

export default function DataPlaneExplorer() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get('mode') || 'simulator';
  const source = searchParams.get('source') || (mode === 'simulator' ? 'simulator' : undefined);

  const { data: dp, isLoading } = useQuery({
    queryKey: ['data-plane', id],
    queryFn: () => dataPlaneService.get(id!),
    enabled: !!id,
    retry: false,
  });

  if (isLoading) return <Layout><p className="p-6">Loading...</p></Layout>;

  const name = dp?.name || id?.replace('sample-', '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Data Source';
  const CustomPanel = id ? CUSTOM_PANELS[id] : undefined;

  return (
    <Layout>
      <div className="flex items-center gap-3 px-6 pt-4 pb-2">
        <Button variant="ghost" size="icon" onClick={() => navigate('/ai-stack/data-plane')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold">{name} - Runtime Explorer</h1>
        <Badge className={`text-xs ${mode === 'simulator' ? 'bg-warning/20 text-warning' : 'bg-success/20 text-success'}`}>
          {mode === 'simulator' ? 'Simulator' : 'Real FDW'}
        </Badge>
        {source && source !== 'real' && source !== 'simulator' && (
          <Badge className="text-xs bg-primary/20 text-primary">{source}</Badge>
        )}
      </div>
      {CustomPanel ? <CustomPanel /> : <OntosWorkspace fdwSource={source} />}
    </Layout>
  );
}
