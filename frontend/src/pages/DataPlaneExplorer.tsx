import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { dataPlaneService } from '@/services/dataPlaneService';
import Layout from '@/components/Layout';
import { Skeleton } from '@/components/ui/skeleton';
import { Icon } from '@/components/ds/Icon';
import { SystemLogo, resolveSystem } from '@/components/ds/SystemLogo';
import { StatusPill } from '@/components/ds/kit';
import { cn } from '@/lib/utils';
import { OntosWorkspace } from '@/components/ontos/OntosWorkspace';
import FileUploadsPanel from '@/components/data-source-panels/FileUploadsPanel';
import SocialListeningPanel from '@/components/data-source-panels/SocialListeningPanel';
import GoogleDrivePanel from '@/components/data-source-panels/GoogleDrivePanel';

const CUSTOM_PANELS: Record<string, React.ComponentType> = {
  'sample-drive': GoogleDrivePanel,
  'sample-files': FileUploadsPanel,
  'sample-social': SocialListeningPanel,
};

/** Name and one-line description of the built-in sources (same wording as the Data Plane page). */
const KNOWN_SOURCES: Record<string, { name: string; description: string }> = {
  'sample-crm': { name: 'Salesforce CRM', description: 'Customer accounts, pipeline and contracts, read in place from Salesforce.' },
  'sample-erp': { name: 'Oracle ERP', description: 'Finance, receivables, payables and general ledger, read in place from Oracle.' },
  'sample-sap': { name: 'SAP S/4HANA', description: 'Inventory, supply chain and production, read in place from SAP.' },
  'sample-drive': { name: 'Google Drive', description: 'Contracts, reports and documents held in Google Drive.' },
  'sample-files': { name: 'File uploads', description: 'Invoices, lab reports and CSV files uploaded to the platform.' },
  'sample-social': { name: 'Social listening', description: 'Market signals and sentiment from social channels.' },
};

function titleFromId(id?: string) {
  return id?.replace('sample-', '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Data source';
}

export default function DataPlaneExplorer() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const mode = searchParams.get('mode') || 'simulator';
  const source = searchParams.get('source') || (mode === 'simulator' ? 'simulator' : undefined);

  const { data: dp, isLoading } = useQuery({
    queryKey: ['data-plane', id],
    queryFn: () => dataPlaneService.get(id!),
    enabled: !!id,
    retry: false,
  });

  const known = id ? KNOWN_SOURCES[id] : undefined;
  const name = dp?.name || known?.name || titleFromId(id);
  const description = known?.description || (dp?.type ? `${dp.type} source connected to the Data Plane.` : 'Source connected to the Data Plane.');
  // Logo: the source id is the most reliable key; fall back to the name, then the simulator key.
  const logoSystem = [id, name, source].find(s => !!resolveSystem(s).def) || name;
  const CustomPanel = id ? CUSTOM_PANELS[id] : undefined;
  const isSimulator = mode === 'simulator';
  const showSourceKey = !!source && source !== 'real' && source !== 'simulator';

  return (
    <Layout>
      <header className={cn('px-4 pt-4 sm:px-6 lg:px-8', CustomPanel && 'border-b border-border pb-4')}>
        <Link
          to="/ai-stack/data-plane"
          className="inline-flex items-center gap-1 rounded-sm text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Icon name="chevron-left" className="h-3.5 w-3.5" />
          Data Plane
        </Link>

        {isLoading ? (
          <div className="mt-2 space-y-2" aria-busy="true">
            <Skeleton className="h-8 w-56" />
            <Skeleton className="h-4 w-80 max-w-full" />
          </div>
        ) : (
          <>
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
              <SystemLogo system={logoSystem} tile size="sm" />
              <h1 className="min-w-0 break-words text-lg font-medium tracking-tight text-foreground">{name}</h1>
              <StatusPill
                tone={isSimulator ? 'neutral' : 'success'}
                variant="soft"
                className="mt-0.5"
              >
                {isSimulator ? 'Simulator' : 'Real'}
              </StatusPill>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              {description}
              {isSimulator ? ' Showing simulated data.' : ' Showing data from the connected system.'}
              {showSourceKey && <> Source key <span className="mono-id">{source}</span>.</>}
            </p>
          </>
        )}
      </header>

      {CustomPanel ? <CustomPanel /> : <OntosWorkspace fdwSource={source} />}
    </Layout>
  );
}
