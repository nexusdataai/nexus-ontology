import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  FileText, FlaskConical, Upload, Loader2, RefreshCw,
  CheckCircle2, XCircle, AlertTriangle, Clock, ChevronRight,
} from 'lucide-react';
import { useExternalData } from './useExternalData';
import { uploadExternalDocument } from '@/services/simulatorLink';

type Tab = 'invoices' | 'lab_reports';

const STATUS_CONFIG: Record<string, { color: string; icon: React.ElementType }> = {
  Validated: { color: 'bg-success/20 text-success border-success/30', icon: CheckCircle2 },
  Rejected: { color: 'bg-destructive/20 text-destructive border-destructive/30', icon: XCircle },
  Needs_Review: { color: 'bg-warning/20 text-warning border-warning/30', icon: AlertTriangle },
  Pending: { color: 'bg-primary/20 text-primary border-primary/30', icon: Clock },
};

export default function FileUploadsPanel() {
  const [tab, setTab] = useState<Tab>('invoices');
  const [selected, setSelected] = useState<Record<string, unknown> | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const invoices = useExternalData('Invoice_Upload', 100);
  const labReports = useExternalData('Lab_Report_Upload', 100);

  const activeData = tab === 'invoices' ? invoices : labReports;
  const isInvoice = tab === 'invoices';

  const avgConfidence = activeData.rows.length > 0
    ? (activeData.rows.reduce((s, r) => s + (Number(r.Extraction_Confidence) || 0), 0) / activeData.rows.length).toFixed(1)
    : '0';

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    try {
      const docType = tab === 'invoices' ? 'invoice' : 'lab-report';
      const result = await uploadExternalDocument(docType, file);
      setUploadResult(`Extracted ${result.row_id} with ${result.confidence}% confidence`);
      invoices.refresh();
      labReports.refresh();
      setSelected(null);
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
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            File Uploads
          </h2>
          <p className="text-sm text-muted-foreground">
            {invoices.total} invoices, {labReports.total} lab reports -- OCR + LLM extraction pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right text-xs text-muted-foreground">
            <span>Avg Confidence: <strong className="text-foreground">{avgConfidence}%</strong></span>
          </div>
          <Button variant="outline" size="sm" onClick={() => { invoices.refresh(); labReports.refresh(); setSelected(null); }}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
          </Button>
          <Button size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <Upload className="h-3.5 w-3.5 mr-1" />}
            {uploading ? 'Extracting...' : `Upload ${isInvoice ? 'Invoice' : 'Lab Report'}`}
          </Button>
        </div>
      </div>

      {uploadResult && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${uploadResult.includes('failed') ? 'border-destructive/25 bg-destructive/20 text-destructive' : 'border-success/25 bg-success/20 text-success'}`}>
          {uploadResult}
        </div>
      )}

      <div className="flex gap-1 border-b">
        <button onClick={() => { setTab('invoices'); setSelected(null); }}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'invoices' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <FileText className="h-3.5 w-3.5" /> Invoices
          <Badge variant="outline" className="text-xs ml-1">{invoices.total}</Badge>
        </button>
        <button onClick={() => { setTab('lab_reports'); setSelected(null); }}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${tab === 'lab_reports' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
          <FlaskConical className="h-3.5 w-3.5" /> Lab Reports
          <Badge variant="outline" className="text-xs ml-1">{labReports.total}</Badge>
        </button>
      </div>

      {activeData.loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : activeData.error ? (
        <div className="text-center py-10 text-sm text-destructive">{activeData.error}</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ minHeight: 420 }}>
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Files ({activeData.total})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <ScrollArea className="h-[400px]">
                {activeData.rows.map((row, i) => {
                  const path = String(row.File_Path || '');
                  const fileName = path.split('/').pop() || path;
                  const confidence = Number(row.Extraction_Confidence) || 0;
                  const status = String(row.Validation_Status || row.Spec_Compliance || '');
                  const isSelected = selected === row;
                  const statusKey = isInvoice ? status : (row.Spec_Compliance === true ? 'Validated' : row.Spec_Compliance === false ? 'Rejected' : 'Pending');
                  const cfg = STATUS_CONFIG[statusKey] || STATUS_CONFIG.Pending;
                  const Icon = cfg.icon;

                  return (
                    <button key={i} onClick={() => setSelected(row)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 text-left border-b border-border/50 hover:bg-muted/30 transition-colors ${isSelected ? 'bg-primary/10 border-l-2 border-l-primary' : ''}`}>
                      <div className="shrink-0">
                        {isInvoice ? <FileText className="h-8 w-8 text-primary p-1.5 bg-primary/10 rounded" />
                          : <FlaskConical className="h-8 w-8 text-success p-1.5 bg-success/10 rounded" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate">{fileName}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Progress value={confidence} className="h-1 w-16" />
                          <span className="text-xs text-muted-foreground">{confidence}%</span>
                          <Badge variant="outline" className={`text-xs px-1 py-0 ${cfg.color}`}>
                            <Icon className="h-2.5 w-2.5 mr-0.5" />{statusKey}
                          </Badge>
                        </div>
                      </div>
                      <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0" />
                    </button>
                  );
                })}
              </ScrollArea>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">
                {selected ? `Extraction Details` : 'Select a file to view extraction results'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {selected ? (
                <ScrollArea className="h-[370px]">
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      {Object.entries(selected).map(([key, val]) => {
                        if (key === 'File_Path') return null;
                        const label = key.replace(/_/g, ' ');
                        const strVal = String(val ?? '');
                        const isConfidence = key.includes('Confidence');
                        const isStatus = key === 'Validation_Status';
                        const isCompliance = key === 'Spec_Compliance';
                        const isMoney = key.includes('Amount') || key.includes('Price');

                        return (
                          <div key={key} className={`rounded-lg border p-3 ${key.includes('ID') || key.includes('Upload_ID') ? 'col-span-2 bg-muted/20' : ''}`}>
                            <div className="text-xs text-muted-foreground mb-1">{label}</div>
                            {isConfidence ? (
                              <div className="flex items-center gap-2">
                                <Progress value={Number(val)} className="h-2 flex-1" />
                                <span className="text-sm font-mono font-semibold">{strVal}%</span>
                              </div>
                            ) : isStatus ? (
                              <Badge className={`${(STATUS_CONFIG[strVal] || STATUS_CONFIG.Pending).color}`}>{strVal}</Badge>
                            ) : isCompliance ? (
                              <Badge className={val ? 'bg-success/20 text-success' : 'bg-destructive/20 text-destructive'}>
                                {val ? 'Compliant' : 'Non-Compliant'}
                              </Badge>
                            ) : isMoney ? (
                              <span className="text-sm font-mono font-semibold">${Number(val).toLocaleString()}</span>
                            ) : (
                              <span className="text-sm font-medium">{strVal}</span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                    <div className="rounded-lg border p-3 bg-muted/10">
                      <div className="text-xs text-muted-foreground mb-1">Source File</div>
                      <span className="text-xs font-mono">{String(selected.File_Path)}</span>
                    </div>
                  </div>
                </ScrollArea>
              ) : (
                <div className="flex flex-col items-center justify-center h-[370px] text-muted-foreground">
                  <FileText className="h-10 w-10 opacity-20 mb-2" />
                  <span className="text-sm">Click a file on the left to view extracted data</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
