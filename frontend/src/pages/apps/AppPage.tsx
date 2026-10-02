import { useParams, useNavigate } from 'react-router-dom';
import { getAppConfig } from '@/config/appRegistry';
import { AppShell } from '@/components/apps/AppShell';

export default function AppPage() {
  const { appId } = useParams<{ appId: string }>();
  const nav = useNavigate();

  const app = appId ? getAppConfig(appId) : undefined;

  if (!app) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold mb-2">App Not Found</h2>
          <p className="text-muted-foreground mb-4">The application "{appId}" does not exist.</p>
          <button onClick={() => nav('/workspace/apps')} className="text-primary hover:underline">
            Back to App Catalogue
          </button>
        </div>
      </div>
    );
  }

  return <AppShell app={app} />;
}
