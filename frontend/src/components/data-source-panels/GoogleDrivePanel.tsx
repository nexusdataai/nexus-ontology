import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  FileText, Leaf, Loader2, RefreshCw, ChevronDown, ChevronRight, Globe, Upload,
} from 'lucide-react';
import { useExternalData } from './useExternalData';
import { uploadExternalDocument } from '@/services/simulatorLink';

type Tab = 'contracts' | 'sustainability';

const FRAMEWORK_COLORS: Record<string, string> = {
  GRI: 'bg-green-500/20 text-green-400 border-green-500/30',
  SASB: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  CDP: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  TCFD: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

export default function GoogleDrivePanel() {
  const [tab, setTab] = useState<Tab>('contracts');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const contracts = useExternalData('Contract_Document', 100);
  const reports = useExternalData('Sustainability_Report', 100);

  const loading = contracts.loading || reports.loading;

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const docType = tab === 'contracts' ? 'contract' : 'sustainability-report';
      const result = await uploadExternalDocument(docType, file);
      setUploadResult(`Extracted ${result.row_id} with ${result.confidence}% confidence`);
      contracts.refresh();
      reports.refresh();
      setExpandedRow(null);
    } catch (err: any) {
      setUploadResult(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="p-6 space-y-4">
      <input ref={fileInputRef} type="file" accept=".pdf,.xlsx,.xls,.csv" className="hidden" onChange={handleUpload} />

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Globe className="h-5 w-5 text-red-400" />
            Google Drive
          </h2>
          <p className="text-sm text-muted-foreground">
            {contracts.total} contracts, {reports.total} sustainability reports -- NLP-extracted documents
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => { contracts.refresh(); reports.refresh(); setExpandedRow(null); }}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
          </Button>
          <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Upload className="h-3.5 w-3.5 mr-1" />}
            {uploading ? 'Extracting...' : `Upload ${tab === 'contracts' ? 'Contract' : 'Report'}`}
          </Button>
        </div>
      </div>

      {uploadResult && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${uploadResult.includes('failed') ? 'border-red-300 bg-red-950/20 text-red-400' : 'border-green-300 bg-green-950/20 text-green-400'}`}>
          {uploadResult}
        </div>
      )}

      <div className="flex gap-1 border-b">
        <button onClick={() => { setTab('contracts'); setExpandedRow(null); }}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'contracts' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <FileText className="h-3.5 w-3.5" /> Contracts
          <Badge variant="outline" className="text-[10px] ml-1">{contracts.total}</Badge>
        </button>
        <button onClick={() => { setTab('sustainability'); setExpandedRow(null); }}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'sustainability' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <Leaf className="h-3.5 w-3.5" /> Sustainability Reports
          <Badge variant="outline" className="text-[10px] ml-1">{reports.total}</Badge>
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : tab === 'contracts' ? (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/30 sticky top-0">
                  <th className="w-8 px-2 py-2"></th>
                  <th className="px-2 py-2 text-left font-medium">Contract</th>
                  <th className="px-2 py-2 text-left font-medium">Document</th>
                  <th className="px-2 py-2 text-left font-medium">Vendor</th>
                  <th className="px-2 py-2 text-left font-medium">Effective</th>
                  <th className="px-2 py-2 text-left font-medium">Expiry</th>
                  <th className="px-2 py-2 text-right font-medium">Price</th>
                  <th className="px-2 py-2 text-right font-medium">Volume</th>
                  <th className="px-2 py-2 text-left font-medium">Confidence</th>
                </tr></thead>
                <tbody className="divide-y divide-border/50">
                  {contracts.rows.map((r, i) => {
                    const isExpanded = expandedRow === i;
                    const confidence = Number(r.Extraction_Confidence) || 0;
                    return (
                      <>
                        <tr key={i} className="hover:bg-muted/20 cursor-pointer" onClick={() => setExpandedRow(isExpanded ? null : i)}>
                          <td className="px-2 py-2">
                            {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                          </td>
                          <td className="px-2 py-2 font-mono font-medium">{String(r.Contract_ID)}</td>
                          <td className="px-2 py-2 max-w-[200px] truncate">{String(r.Document_Path).split('/').pop()}</td>
                          <td className="px-2 py-2">{String(r.Vendor_ID)}</td>
                          <td className="px-2 py-2">{String(r.Effective_Date)}</td>
                          <td className="px-2 py-2">{String(r.Expiry_Date)}</td>
                          <td className="px-2 py-2 text-right font-mono">${Number(r.Contracted_Price).toFixed(2)}</td>
                          <td className="px-2 py-2 text-right font-mono">{Number(r.Volume_Commitment).toLocaleString()}</td>
                          <td className="px-2 py-2">
                            <div className="flex items-center gap-1">
                              <Progress value={confidence} className="h-1.5 w-12" />
                              <span className="text-[10px]">{confidence}%</span>
                            </div>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${i}-detail`} className="bg-muted/10">
                            <td colSpan={9} className="px-6 py-3">
                              <div className="grid grid-cols-3 gap-4 text-xs">
                                <div>
                                  <span className="text-muted-foreground block mb-0.5">SLA Terms</span>
                                  <span className="font-medium">{String(r.SLA_Terms)}</span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground block mb-0.5">Penalty Clauses</span>
                                  <span className="font-medium">{String(r.Penalty_Clauses)}</span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground block mb-0.5">Auto Renewal</span>
                                  <Badge variant="outline" className={r.Auto_Renewal ? 'bg-green-500/10 text-green-400' : 'bg-muted'}>
                                    {r.Auto_Renewal ? 'Yes' : 'No'}
                                  </Badge>
                                </div>
                                <div className="col-span-3">
                                  <span className="text-muted-foreground block mb-0.5">Full Path</span>
                                  <span className="font-mono text-[10px]">{String(r.Document_Path)}</span>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </ScrollArea>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
                {reports.rows.map((r, i) => (
                  <Card key={i} className="border-border/50">
                    <CardHeader className="pb-2 pt-3 px-4">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-xs font-mono">{String(r.Report_ID)}</CardTitle>
                        <Badge variant="outline" className={FRAMEWORK_COLORS[String(r.Framework)] || 'bg-muted'}>
                          {String(r.Framework)}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="px-4 pb-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <Leaf className="h-3.5 w-3.5 text-green-400" />
                        <span className="text-xs font-medium">{String(r.Report_Type).replace(/_/g, ' ')}</span>
                        <Badge variant="outline" className="text-[9px] ml-auto">{String(r.Period)}</Badge>
                      </div>
                      <div className="text-[10px] space-y-1">
                        <div><span className="text-muted-foreground">KPIs:</span> {String(r.KPIs_Extracted)}</div>
                        <div><span className="text-muted-foreground">Targets:</span> <span className="text-blue-400">{String(r.Targets)}</span></div>
                        <div><span className="text-muted-foreground">Actuals:</span> <span className="text-green-400">{String(r.Actuals)}</span></div>
                      </div>
                      <div className="text-[9px] font-mono text-muted-foreground truncate">{String(r.Document_Path)}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
