import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, PieChart, Pie, Cell, ScatterChart, Scatter } from 'recharts';
import { fetchMappingData, MappingData } from '@/services/dataService';
import DashboardCard from '@/components/DashboardCard';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function MappingDashboard() {
  const [data, setData] = useState<MappingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const mappingData = await fetchMappingData();
        setData(mappingData);
      } catch (err) {
        console.error('Failed to load mapping data:', err);
        setError('Failed to load mapping data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="text-red-500 p-4">{error}</div>;
  if (!data) return <div>No data available</div>;

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-foreground mb-2">TMF ODA Mapping Dashboard</h2>
        <p className="text-muted-foreground">Detailed view of TMF component mappings and confidence scores.</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Mapping Confidence Distribution */}
        <DashboardCard title="Mapping Confidence Distribution">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.confidence_distribution}>
              <CartesianGrid strokeDasharray="3,3" stroke="hsl(var(--border))" />
              <XAxis dataKey="confidence" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
              <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </DashboardCard>

        {/* TMF API Coverage */}
        <DashboardCard title="TMF API Coverage">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data.api_coverage}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="percentage"
                label={({ component, percentage }) => `${component}: ${percentage}%`}
              >
                {data.api_coverage.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </DashboardCard>

        {/* Legacy Assets by Type */}
        <DashboardCard title="Legacy Assets by Type">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.legacy_assets} layout="horizontal">
              <CartesianGrid strokeDasharray="3,3" stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
              <YAxis dataKey="type" type="category" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
              <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </DashboardCard>

        {/* Procedure to ODA Mapping */}
        <DashboardCard title="Procedure to ODA Mapping">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart data={data.procedure_mapping}>
              <CartesianGrid strokeDasharray="3,3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="procedure" 
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} 
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis 
                dataKey="confidence" 
                tick={{ fill: 'hsl(var(--muted-foreground))' }}
                domain={[0, 1.2]}
              />
              <Scatter dataKey="confidence" fill="hsl(var(--primary))" />
            </ScatterChart>
          </ResponsiveContainer>
        </DashboardCard>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-card rounded-lg p-4 border border-border text-center">
          <div className="text-3xl font-bold text-primary mb-2">90%</div>
          <div className="text-muted-foreground text-sm">Average Confidence</div>
        </div>
        <div className="bg-card rounded-lg p-4 border border-border text-center">
          <div className="text-3xl font-bold text-green-600 dark:text-green-400 mb-2">42</div>
          <div className="text-muted-foreground text-sm">Total Mappings</div>
        </div>
        <div className="bg-card rounded-lg p-4 border border-border text-center">
          <div className="text-3xl font-bold text-purple-600 dark:text-purple-400 mb-2">4</div>
          <div className="text-muted-foreground text-sm">TMF APIs</div>
        </div>
        <div className="bg-card rounded-lg p-4 border border-border text-center">
          <div className="text-3xl font-bold text-orange-600 dark:text-orange-400 mb-2">100%</div>
          <div className="text-muted-foreground text-sm">Coverage</div>
        </div>
      </div>
    </div>
  );
}
