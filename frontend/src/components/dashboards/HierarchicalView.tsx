import { useState, useEffect } from 'react';
import { fetchHierarchicalData, HierarchicalData } from '@/services/dataService';
import DashboardCard from '@/components/DashboardCard';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function HierarchicalView() {
  const [data, setData] = useState<HierarchicalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const hierarchicalData = await fetchHierarchicalData();
        setData(hierarchicalData);
      } catch (err) {
        console.error('Failed to load hierarchical data:', err);
        setError('Failed to load hierarchical data. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="text-red-500 p-4">{error}</div>;
  if (!data) return <div>No data available</div>;

  const TreemapBox = ({ item, width, height, color }: { 
    item: { name: string; count: number; percentage: number }, 
    width: number, 
    height: number, 
    color: string 
  }) => (
    <div 
      className="relative border border-border hover:border-primary/50 transition-colors cursor-pointer group"
      style={{ 
        width: `${width}%`, 
        height: `${height}px`, 
        backgroundColor: color,
        minHeight: '60px'
      }}
    >
      <div className="absolute inset-0 p-2 flex flex-col justify-center text-center">
        <div className="text-white font-semibold text-sm group-hover:text-blue-200 transition-colors">
          {item.name}
        </div>
        <div className="text-muted-foreground text-xs mt-1">
          {item.count} ({item.percentage}%)
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <DashboardCard 
        title="Legacy Schema to TMF ODA Mapping Overview"
        subtitle="View the hierarchical structure of your schema and its TMF mappings."
      >
        <div className="grid grid-cols-2 gap-8">
          {/* Legacy Schema Components */}
          <div>
            <h4 className="text-foreground font-semibold mb-4">Legacy Schema Components</h4>
            <div className="bg-card rounded-lg p-4 border border-border">
              <div className="space-y-2">
                {/* Tables - largest section */}
                <div className="flex flex-wrap gap-1">
                  <TreemapBox 
                    item={data.legacy_schema.tables[0]} 
                    width={100} 
                    height={120} 
                    color="#1e40af" 
                  />
                </div>
                
                {/* Smaller components in a grid */}
                <div className="grid grid-cols-2 gap-1">
                  {data.legacy_schema.tables.slice(1, 3).map((item, index) => (
                    <TreemapBox 
                      key={index}
                      item={item} 
                      width={100} 
                      height={60} 
                      color="#2563eb" 
                    />
                  ))}
                </div>
                
                <div className="grid grid-cols-3 gap-1">
                  {data.legacy_schema.tables.slice(3).concat(data.legacy_schema.procedures).map((item, index) => (
                    <TreemapBox 
                      key={index}
                      item={item} 
                      width={100} 
                      height={50} 
                      color={item.name === 'Procedures' ? '#059669' : '#3b82f6'} 
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* TMF ODA Component Mappings */}
          <div>
            <h4 className="text-foreground font-semibold mb-4">TMF ODA Component Mappings</h4>
            <div className="bg-card rounded-lg p-4 border border-border">
              <div className="space-y-2">
                {/* Party Management - largest */}
                <TreemapBox 
                  item={data.tmf_oda.components[0]} 
                  width={100} 
                  height={120} 
                  color="#047857" 
                />
                
                {/* Other components */}
                <div className="grid grid-cols-3 gap-1">
                  {data.tmf_oda.components.slice(1).map((item, index) => (
                    <TreemapBox 
                      key={index}
                      item={item} 
                      width={100} 
                      height={60} 
                      color="#10b981" 
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Summary Statistics */}
        <div className="mt-8 grid grid-cols-3 gap-6">
          <div className="bg-card rounded-lg p-4 border border-border text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">335</div>
            <div className="text-muted-foreground text-sm">Total Tables</div>
          </div>
          <div className="bg-card rounded-lg p-4 border border-border text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">35</div>
            <div className="text-muted-foreground text-sm">Procedures</div>
          </div>
          <div className="bg-card rounded-lg p-4 border border-border text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">4</div>
            <div className="text-muted-foreground text-sm">TMF Components</div>
          </div>
        </div>
      </DashboardCard>
    </div>
  );
}
