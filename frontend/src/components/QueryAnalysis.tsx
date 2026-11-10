
import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { useTheme } from '@/hooks/use-theme';
import supabase from '@/utils/supabase';

interface QueryAnalysisProps {
  queryType: string | null;
  className?: string;
}

const QueryAnalysis: React.FC<QueryAnalysisProps> = ({ queryType, className }) => {
  const { theme } = useTheme();
  const [sentimentData, setSentimentData] = React.useState([
    { name: 'Very Positive', value: 0 },
    { name: 'Positive', value: 0 },
    { name: 'Neutral', value: 0 },
    { name: 'Negative', value: 0 },
    { name: 'Very Negative', value: 0 },
  ]);
  const [loadingSentiment, setLoadingSentiment] = React.useState(false);
  const [sentimentRows, setSentimentRows] = React.useState<any[]>([]);

  React.useEffect(() => {
    if (queryType !== 'sentiment') return;
    setLoadingSentiment(true);
    async function fetchSentiment() {
      const { data, error } = await supabase
        .from('customer_sentiment_analysis')
        .select('*')
        .order('created_at', { ascending: false });
      if (error) {
        setLoadingSentiment(false);
        return;
      }
      setSentimentRows(data);
      // Aggregate counts for each sentiment
      const counts = {
        'Very Positive': 0,
        'Positive': 0,
        'Neutral': 0,
        'Negative': 0,
        'Very Negative': 0,
      };
      data.forEach((row: { sentiment: string }) => {
        if (row.sentiment === 'positive') counts['Positive']++;
        else if (row.sentiment === 'very positive') counts['Very Positive']++;
        else if (row.sentiment === 'neutral') counts['Neutral']++;
        else if (row.sentiment === 'negative') counts['Negative']++;
        else if (row.sentiment === 'very negative') counts['Very Negative']++;
      });
      setSentimentData([
        { name: 'Very Positive', value: counts['Very Positive'] },
        { name: 'Positive', value: counts['Positive'] },
        { name: 'Neutral', value: counts['Neutral'] },
        { name: 'Negative', value: counts['Negative'] },
        { name: 'Very Negative', value: counts['Very Negative'] },
      ]);
      setLoadingSentiment(false);
    }
    fetchSentiment();
  }, [queryType]);
  
  // Colors for charts using CSS variables
  const CHART_COLORS = {
    primary: 'var(--chart-primary)',
    secondary: 'var(--chart-secondary)',
    accent: 'var(--chart-accent)',
    success: 'var(--chart-success)',
  };

  const [gapRows, setGapRows] = React.useState<any[]>([]);
  const [loadingGap, setLoadingGap] = React.useState(false);

  React.useEffect(() => {
    if (queryType !== 'gap') return;
    setLoadingGap(true);
    async function fetchGap() {
      const { data, error } = await supabase
        .from('demand_supply_gap_analysis')
        .select('*')
        .order('created_at', { ascending: false });
      if (!error) setGapRows(data);
      setLoadingGap(false);
    }
    fetchGap();
  }, [queryType]);

  const [performanceRows, setPerformanceRows] = React.useState<any[]>([]);
  const [loadingPerformance, setLoadingPerformance] = React.useState(false);

  React.useEffect(() => {
    if (queryType !== 'performance') return;
    setLoadingPerformance(true);
    async function fetchPerformance() {
      const { data, error } = await supabase
        .from('sales_performance_analysis')
        .select('*')
        .order('created_at', { ascending: false });
      if (!error) setPerformanceRows(data);
      setLoadingPerformance(false);
    }
    fetchPerformance();
  }, [queryType]);

  // Content based on query type
  const renderContent = () => {
    if (!queryType) return null;

    switch (queryType) {
      case 'sentiment':
        return (
          <Card className="w-full mt-6">
            <CardHeader>
              <CardTitle>Customer Sentiment Analysis</CardTitle>
              <CardDescription>Analysis of customer feedback and reviews</CardDescription>
            </CardHeader>
            <CardContent className="h-96">
              <div className="grid md:grid-cols-2 gap-6 h-full">
                <div className="flex items-center justify-center">
                  {loadingSentiment ? (
                    <div>Loading sentiment data...</div>
                  ) : (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={sentimentData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {sentimentData.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={[
                              '#40C057', // Very Positive - Green
                              '#4C6EF5', // Positive - Blue
                              '#868E96', // Neutral - Gray
                              '#FD7E14', // Negative - Orange
                              '#FA5252'  // Very Negative - Red
                            ][index % 5]} 
                          />
                        ))}
                      </Pie>
                      <Tooltip 
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            return (
                              <div className="p-2 border rounded-md shadow-sm"
                                  style={{ 
                                    backgroundColor: 'var(--chart-tooltip-bg)',
                                    borderColor: 'var(--chart-tooltip-border)'
                                  }}>
                                <p className="font-medium">{payload[0].name}</p>
                                <p>Value: {payload[0].value}</p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  )}
                </div>
                <div className="flex flex-col justify-center">
                  <h3 className="text-xl font-semibold mb-4">Key Insights</h3>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-success"></span>
                      <span>{sentimentData[0].value + sentimentData[1].value} positive experiences</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-muted-foreground"></span>
                      <span>{sentimentData[2].value} neutral feedbacks</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-destructive"></span>
                      <span>{sentimentData[3].value + sentimentData[4].value} negative feedbacks</span>
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
            {/* Table of feedbacks */}
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">Recent Customer Feedback</h3>
              {loadingSentiment ? (
                <div>Loading feedback table...</div>
              ) : (
                <div className="overflow-auto rounded-lg border bg-background">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-background">
                      <tr className="border-b">
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Customer Name</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Feedback</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Sentiment</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Score</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sentimentRows.map(row => (
                        <tr key={row.id} className="border-b hover:bg-muted/50 transition-colors">
                          <td className="text-xs py-2 px-3 font-medium">{row.customer_name}</td>
                          <td className="text-xs py-2 px-3 max-w-xs truncate" title={row.feedback}>{row.feedback}</td>
                          <td className="text-xs py-2 px-3 capitalize">
                            <span className={
                              row.sentiment === 'positive' ? 'text-success' :
                              row.sentiment === 'negative' ? 'text-destructive' :
                              row.sentiment === 'neutral' ? 'text-warning' :
                              ''
                            }>
                              {row.sentiment}
                            </span>
                          </td>
                          <td className="text-xs py-2 px-3">{row.score != null ? (row.score * 100).toFixed(0) + '%' : '-'}</td>
                          <td className="text-xs py-2 px-3">{row.created_at ? new Date(row.created_at).toLocaleDateString() : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        );
      case 'gap':
        return (
          <Card className="w-full mt-6">
            <CardHeader>
              <CardTitle>Demand and Supply Gap Analysis</CardTitle>
              <CardDescription>Analyzing product demand versus available inventory</CardDescription>
            </CardHeader>
            <CardContent className="h-96">
              <div className="grid md:grid-cols-2 gap-6 h-full">
                <div className="flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={gapRows}
                      margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                      <XAxis dataKey="product_name" stroke={theme === 'dark' ? "#888" : "#555"} />
                      <YAxis stroke={theme === 'dark' ? "#888" : "#555"} />
                      <Tooltip 
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const gap = payload[0].payload.demand - payload[0].payload.supply;
                            const gapPercentage = ((gap / payload[0].payload.demand) * 100).toFixed(1);
                            return (
                              <div className="p-2 border rounded-md shadow-sm"
                                  style={{ 
                                    backgroundColor: 'var(--chart-tooltip-bg)',
                                    borderColor: 'var(--chart-tooltip-border)'
                                  }}>
                                <p className="font-medium">{payload[0].payload.product_name}</p>
                                <p>Demand: {payload[0].payload.demand} kg</p>
                                <p>Supply: {payload[0].payload.supply} kg</p>
                                <p className={gap > 0 ? "text-destructive" : "text-success"}>
                                  Gap: {gap > 0 ? `${gap} kg short (${gapPercentage}%)` : `${Math.abs(gap)} kg excess (${Math.abs(Number(gapPercentage))}%)`}
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Legend />
                      <Bar dataKey="demand" fill={CHART_COLORS.accent} name="Demand" />
                      <Bar dataKey="supply" fill={CHART_COLORS.primary} name="Supply" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col justify-center">
                  <h3 className="text-xl font-semibold mb-4">Inventory Insights</h3>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-destructive"></span>
                      <span>Green Chilies are understocked by 20 kg (13%)</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-destructive"></span>
                      <span>Tomatoes need 20 more kg to meet demand</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-success"></span>
                      <span>Mangoes have 15 kg of excess inventory</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-primary"></span>
                      <span>Overall inventory efficiency is at 92%</span>
                    </li>
                    <li className="mt-4 text-muted-foreground">
                      Recommended: Increase supply of green chilies and tomatoes from local farmers
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
            {/* Table of demand/supply gap */}
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">Recent Demand & Supply Data</h3>
              {loadingGap ? (
                <div>Loading gap table...</div>
              ) : (
                <div className="overflow-auto rounded-lg border bg-background">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-background">
                      <tr className="border-b">
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Product</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Demand</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Supply</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Gap</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gapRows.map(row => {
                        const gap = row.demand - row.supply;
                        return (
                          <tr key={row.id} className="border-b hover:bg-muted/50 transition-colors">
                            <td className="text-xs py-2 px-3 font-medium">{row.product_name}</td>
                            <td className="text-xs py-2 px-3">{row.demand}</td>
                            <td className="text-xs py-2 px-3">{row.supply}</td>
                            <td className={`text-xs py-2 px-3 font-semibold ${gap > 0 ? 'text-destructive' : 'text-success'}`}>{gap > 0 ? `Short by ${gap}` : gap < 0 ? `Excess ${-gap}` : 'Balanced'}</td>
                            <td className="text-xs py-2 px-3">{row.created_at ? new Date(row.created_at).toLocaleDateString() : '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        );
      case 'performance':
        return (
          <Card className="w-full mt-6">
            <CardHeader>
              <CardTitle>Sales Performance Analysis</CardTitle>
              <CardDescription>Analysis of actual sales versus targets</CardDescription>
            </CardHeader>
            <CardContent className="h-96">
              <div className="grid md:grid-cols-2 gap-6 h-full">
                <div className="flex items-center justify-center">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart
                      data={performanceRows}
                      margin={{
                        top: 5,
                        right: 30,
                        left: 20,
                        bottom: 5,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                      <XAxis dataKey="month" stroke={theme === 'dark' ? "#888" : "#555"} />
                      <YAxis stroke={theme === 'dark' ? "#888" : "#555"} />
                      <Tooltip 
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const difference = payload[0].payload.actual - payload[0].payload.target;
                            const differencePercent = ((difference / payload[0].payload.target) * 100).toFixed(1);
                            return (
                              <div className="p-2 border rounded-md shadow-sm"
                                  style={{ 
                                    backgroundColor: 'var(--chart-tooltip-bg)',
                                    borderColor: 'var(--chart-tooltip-border)'
                                  }}>
                                <p className="font-medium">{payload[0].payload.month}</p>
                                <p>Actual Sales: ₹{payload[0].payload.actual}</p>
                                <p>Target: ₹{payload[0].payload.target}</p>
                                <p className={difference >= 0 ? "text-success" : "text-destructive"}>
                                  {difference >= 0 
                                    ? `${differencePercent}% above target (+₹${difference})` 
                                    : `${Math.abs(Number(differencePercent))}% below target (-₹${Math.abs(difference)})`
                                  }
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="actual" stroke={CHART_COLORS.accent} strokeWidth={2} name="Actual Sales" />
                      <Line type="monotone" dataKey="target" stroke={CHART_COLORS.primary} strokeWidth={2} name="Target" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col justify-center">
                  <h3 className="text-xl font-semibold mb-4">Performance Insights</h3>
                  <ul className="space-y-2">
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-success"></span>
                      <span>Most months exceeded sales targets</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-destructive"></span>
                      <span>February was below target by ₹4,000</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-primary"></span>
                      <span>July had the highest sales: ₹60,000</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-muted-foreground"></span>
                      <span>Consistent growth observed in Q2 and Q3</span>
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
            {/* Table of sales performance */}
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2">Recent Sales Performance</h3>
              {loadingPerformance ? (
                <div>Loading sales performance table...</div>
              ) : (
                <div className="overflow-auto rounded-lg border bg-background">
                  <table className="w-full">
                    <thead className="sticky top-0 bg-background">
                      <tr className="border-b">
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Month</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Actual Sales</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Target</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Difference</th>
                        <th className="text-xs text-muted-foreground text-left py-2 px-3">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {performanceRows.map(row => {
                        const diff = row.actual - row.target;
                        const diffPercent = row.target ? ((diff / row.target) * 100).toFixed(1) : '0';
                        return (
                          <tr key={row.id} className="border-b hover:bg-muted/50 transition-colors">
                            <td className="text-xs py-2 px-3 font-medium">{row.month}</td>
                            <td className="text-xs py-2 px-3">₹{row.actual.toLocaleString()}</td>
                            <td className="text-xs py-2 px-3">₹{row.target.toLocaleString()}</td>
                            <td className={`text-xs py-2 px-3 font-semibold ${diff >= 0 ? 'text-success' : 'text-destructive'}`}>{diff >= 0 ? `+₹${diff.toLocaleString()} (${diffPercent}% above)` : `-₹${Math.abs(diff).toLocaleString()} (${Math.abs(diffPercent)}% below)`}</td>
                            <td className="text-xs py-2 px-3">{row.created_at ? new Date(row.created_at).toLocaleDateString() : '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </Card>
        );
      default:
        return null;
    }
  };

  return (
    <div className={cn("w-full px-6", className)}>
      {renderContent()}
    </div>
  );
};

export default QueryAnalysis;
