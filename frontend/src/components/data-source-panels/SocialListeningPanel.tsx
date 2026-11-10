import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Radio, AlertTriangle, TrendingUp, TrendingDown, Minus,
  Loader2, RefreshCw, ChevronDown, ChevronUp, BarChart3, Newspaper, MessageSquare,
} from 'lucide-react';
import { useExternalData } from './useExternalData';

const SEVERITY_STYLE: Record<string, string> = {
  Critical: 'bg-destructive/20 text-destructive border-destructive/30',
  High: 'bg-warning/20 text-warning border-warning/30',
  Medium: 'bg-warning/20 text-warning border-warning/30',
  Low: 'bg-success/20 text-success border-success/30',
};

function SentimentBar({ score }: { score: number }) {
  const pct = ((score + 1) / 2) * 100;
  const color = score > 0.3 ? 'bg-success' : score < -0.3 ? 'bg-destructive' : 'bg-warning';
  return (
    <div className="flex items-center gap-2 w-32">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-10 text-right">{score.toFixed(2)}</span>
    </div>
  );
}

function Section({ title, icon: Icon, count, children, defaultOpen = true }: {
  title: string; icon: React.ElementType; count: number; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <CardHeader className="pb-2 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Icon className="h-4 w-4" /> {title}
            <Badge variant="outline" className="text-xs ml-1">{count}</Badge>
          </CardTitle>
          {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </div>
      </CardHeader>
      {open && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  );
}

export default function SocialListeningPanel() {
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const signals = useExternalData('Market_Signal', 200);
  const sentiment = useExternalData('Brand_Sentiment', 300);
  const prices = useExternalData('Commodity_Price', 200);

  const loading = signals.loading || sentiment.loading || prices.loading;

  const filteredSignals = severityFilter === 'all'
    ? signals.rows
    : signals.rows.filter(r => r.Severity === severityFilter);

  const avgSentiment = sentiment.rows.length > 0
    ? (sentiment.rows.reduce((s, r) => s + (Number(r.Sentiment_Score) || 0), 0) / sentiment.rows.length).toFixed(2)
    : '0';

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Radio className="h-5 w-5 text-primary" />
            Social Listening
          </h2>
          <p className="text-sm text-muted-foreground">
            {signals.total} market signals, {sentiment.total} sentiment records, {prices.total} commodity prices
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right text-xs text-muted-foreground">
            Avg Sentiment: <strong className={`${Number(avgSentiment) > 0 ? 'text-success' : 'text-destructive'}`}>{avgSentiment}</strong>
          </div>
          <Button variant="outline" size="sm" onClick={() => { signals.refresh(); sentiment.refresh(); prices.refresh(); }}>
            <RefreshCw className="h-3.5 w-3.5 mr-1" /> Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <div className="space-y-4">
          <Section title="Market Signals" icon={Newspaper} count={signals.total}>
            <div className="flex gap-1 mb-3">
              {['all', 'Critical', 'High', 'Medium', 'Low'].map(s => (
                <Button key={s} variant={severityFilter === s ? 'default' : 'outline'} size="sm" className="text-xs h-7"
                  onClick={() => setSeverityFilter(s)}>{s === 'all' ? 'All' : s}</Button>
              ))}
            </div>
            <ScrollArea className="h-[250px]">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/30 sticky top-0">
                  <th className="px-2 py-1.5 text-left font-medium">Signal</th>
                  <th className="px-2 py-1.5 text-left font-medium">Event Type</th>
                  <th className="px-2 py-1.5 text-left font-medium">Location</th>
                  <th className="px-2 py-1.5 text-left font-medium">Commodity</th>
                  <th className="px-2 py-1.5 text-left font-medium">Severity</th>
                  <th className="px-2 py-1.5 text-left font-medium">Source</th>
                  <th className="px-2 py-1.5 text-left font-medium">Time</th>
                </tr></thead>
                <tbody className="divide-y divide-border/50">
                  {filteredSignals.map((r, i) => (
                    <tr key={i} className="hover:bg-muted/20">
                      <td className="px-2 py-1.5 font-mono">{String(r.Signal_ID)}</td>
                      <td className="px-2 py-1.5">{String(r.Event_Type).replace(/_/g, ' ')}</td>
                      <td className="px-2 py-1.5">{String(r.Location)}</td>
                      <td className="px-2 py-1.5">{String(r.Affected_Commodity)}</td>
                      <td className="px-2 py-1.5">
                        <Badge variant="outline" className={`text-xs ${SEVERITY_STYLE[String(r.Severity)] || ''}`}>
                          {String(r.Severity)}
                        </Badge>
                      </td>
                      <td className="px-2 py-1.5">{String(r.Source).replace(/_/g, ' ')}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{String(r.Timestamp).substring(0, 16)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          </Section>

          <Section title="Brand Sentiment" icon={MessageSquare} count={sentiment.total}>
            <ScrollArea className="h-[250px]">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/30 sticky top-0">
                  <th className="px-2 py-1.5 text-left font-medium">Brand</th>
                  <th className="px-2 py-1.5 text-left font-medium">Category</th>
                  <th className="px-2 py-1.5 text-left font-medium">Platform</th>
                  <th className="px-2 py-1.5 text-left font-medium">Topic</th>
                  <th className="px-2 py-1.5 text-left font-medium">Sentiment</th>
                  <th className="px-2 py-1.5 text-right font-medium">Mentions</th>
                  <th className="px-2 py-1.5 text-left font-medium">Period</th>
                </tr></thead>
                <tbody className="divide-y divide-border/50">
                  {sentiment.rows.map((r, i) => (
                    <tr key={i} className="hover:bg-muted/20">
                      <td className="px-2 py-1.5 font-medium">{String(r.Brand)}</td>
                      <td className="px-2 py-1.5">{String(r.Product_Category)}</td>
                      <td className="px-2 py-1.5">{String(r.Platform).replace(/_/g, ' ')}</td>
                      <td className="px-2 py-1.5">{String(r.Topic)}</td>
                      <td className="px-2 py-1.5"><SentimentBar score={Number(r.Sentiment_Score)} /></td>
                      <td className="px-2 py-1.5 text-right font-mono">{Number(r.Mention_Count).toLocaleString()}</td>
                      <td className="px-2 py-1.5 text-muted-foreground">{String(r.Period)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollArea>
          </Section>

          <Section title="Commodity Prices" icon={BarChart3} count={prices.total}>
            <ScrollArea className="h-[250px]">
              <table className="w-full text-xs">
                <thead><tr className="bg-muted/30 sticky top-0">
                  <th className="px-2 py-1.5 text-left font-medium">Commodity</th>
                  <th className="px-2 py-1.5 text-right font-medium">Price/Unit</th>
                  <th className="px-2 py-1.5 text-left font-medium">Currency</th>
                  <th className="px-2 py-1.5 text-left font-medium">Unit</th>
                  <th className="px-2 py-1.5 text-right font-medium">30D Change</th>
                  <th className="px-2 py-1.5 text-left font-medium">Source</th>
                  <th className="px-2 py-1.5 text-left font-medium">Date</th>
                </tr></thead>
                <tbody className="divide-y divide-border/50">
                  {prices.rows.map((r, i) => {
                    const change = Number(r.Change_Pct_30D);
                    const ChangeIcon = change > 0 ? TrendingUp : change < 0 ? TrendingDown : Minus;
                    const changeColor = change > 0 ? 'text-success' : change < 0 ? 'text-destructive' : 'text-muted-foreground';
                    return (
                      <tr key={i} className="hover:bg-muted/20">
                        <td className="px-2 py-1.5 font-medium">{String(r.Commodity).replace(/_/g, ' ')}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{Number(r.Price_Per_Unit).toFixed(2)}</td>
                        <td className="px-2 py-1.5">{String(r.Currency)}</td>
                        <td className="px-2 py-1.5">{String(r.Unit)}</td>
                        <td className={`px-2 py-1.5 text-right font-mono ${changeColor}`}>
                          <span className="inline-flex items-center gap-0.5">
                            <ChangeIcon className="h-3 w-3" />{change > 0 ? '+' : ''}{change.toFixed(1)}%
                          </span>
                        </td>
                        <td className="px-2 py-1.5">{String(r.Source)}</td>
                        <td className="px-2 py-1.5 text-muted-foreground">{String(r.Date)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </ScrollArea>
          </Section>
        </div>
      )}
    </div>
  );
}
