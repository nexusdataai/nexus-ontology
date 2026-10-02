export interface SimulatorConfig {
  enabled: boolean;
  baseUrl: string;
  uiUrl: string;
}

let cached: SimulatorConfig | null = null;

export async function getSimulatorConfig(): Promise<SimulatorConfig> {
  if (cached) return cached;
  try {
    const res = await fetch('/api/v1/config/simulator', { cache: 'no-store' });
    if (res.ok) {
      cached = await res.json();
      if (cached && !cached.uiUrl) cached.uiUrl = 'http://localhost:8082';
      return cached!;
    }
  } catch {
    /* fall through */
  }
  cached = { enabled: true, baseUrl: '', uiUrl: 'http://localhost:8082' };
  return cached;
}

export async function uploadExternalDocument(
  type: string,
  file: File,
): Promise<{ success: boolean; row_id: string; confidence: number; filename: string; extracted_fields: Record<string, unknown> }> {
  const cfg = await getSimulatorConfig();
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${cfg.uiUrl}/api/v1/external-simulator/upload/${type}`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { detail?: string }).detail || `Upload failed: ${res.statusText}`);
  }
  return res.json();
}
