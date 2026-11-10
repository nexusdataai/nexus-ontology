import { useParams, useNavigate } from 'react-router-dom';
import { getAppConfig } from '@/config/appRegistry';
import { AppShell } from '@/components/apps/AppShell';
import Layout from '@/components/Layout';
import { EmptyState } from '@/components/ds/primitives';
import { Button } from '@/components/ui/button';

export default function AppPage() {
  const { appId } = useParams<{ appId: string }>();
  const nav = useNavigate();

  const app = appId ? getAppConfig(appId) : undefined;

  if (!app) {
    return (
      <Layout title="Solution not found">
        <div className="mx-auto w-full max-w-[720px] px-4 py-16 sm:px-6">
          <EmptyState
            icon="apps"
            title="This solution is not available"
            description={`There is no solution called "${appId}". It may not be installed yet, or the link is out of date.`}
            action={<Button onClick={() => nav('/workspace/apps')}>Back to Solutions</Button>}
          />
        </div>
      </Layout>
    );
  }

  return <AppShell app={app} />;
}
