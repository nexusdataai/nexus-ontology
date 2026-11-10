import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart2, TrendingUp, Users, ShoppingCart, DollarSign, RefreshCw } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { cn } from '@/lib/utils';
import { useTheme } from '@/hooks/use-theme';
import { Button } from './ui/button';

interface DynamicDashboardProps {
  className?: string;
  chatData?: string; // JSON string from chat response
  onDataUpdate?: (data: any) => void;
}

interface DashboardData {
  dailySales?: Array<{ name: string; sales: number; revenue: number }>;
  productSales?: Array<{ name: string; value: number }>;
  locationData?: Array<{ name: string; value: number }>;
  summary?: {
    totalSales?: number;
    totalRevenue?: number;
    averageOrder?: number;
    growth?: string;
  };
  chartTitle?: string;
  chartDescription?: string;
}

const DynamicDashboard: React.FC<DynamicDashboardProps> = ({ 
  className, 
  chatData, 
  onDataUpdate 
}) => {
  const { theme } = useTheme();
  const [dashboardData, setDashboardData] = useState<DashboardData>({});
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Parse JSON data from chat response
  useEffect(() => {
    if (chatData) {
      try {
        const parsedData = JSON.parse(chatData);
        setDashboardData(parsedData);
        setLastUpdate(new Date());
        if (onDataUpdate) {
          onDataUpdate(parsedData);
        }
      } catch (error) {
        console.error('Error parsing chat data:', error);
      }
    }
  }, [chatData, onDataUpdate]);

  // Default data if no dynamic data is provided
  const defaultDailySales = [
    { name: '00:00', sales: 12, revenue: 4800 },
    { name: '03:00', sales: 5, revenue: 2500 },
    { name: '06:00', sales: 8, revenue: 4000 },
    { name: '09:00', sales: 25, revenue: 12500 },
    { name: '12:00', sales: 45, revenue: 22500 },
    { name: '15:00', sales: 50, revenue: 25000 },
    { name: '18:00', sales: 60, revenue: 30000 },
    { name: '21:00', sales: 38, revenue: 19000 },
  ];

  const defaultProductSales = [
    { name: 'Fresh Tomatoes', value: 1200 },
    { name: 'Basmati Rice', value: 900 },
    { name: 'Green Chilies', value: 800 },
    { name: 'Fresh Mangoes', value: 750 },
    { name: 'Mustard Oil', value: 650 },
  ];

  const defaultLocationData = [
    { name: 'Cyberabad', value: 40 },
    { name: 'HITEC City', value: 30 },
    { name: 'Gachibowli', value: 20 },
    { name: 'Madhapur', value: 15 },
    { name: 'Kondapur', value: 10 },
  ];

  // Use dynamic data or fall back to defaults
  const dailySalesData = dashboardData.dailySales || defaultDailySales;
  const productSalesData = dashboardData.productSales || defaultProductSales;
  const locationData = dashboardData.locationData || defaultLocationData;

  // Calculate totals
  const todayTotalSales = dashboardData.summary?.totalSales || dailySalesData.reduce((acc, item) => acc + item.sales, 0);
  const todayTotalRevenue = dashboardData.summary?.totalRevenue || dailySalesData.reduce((acc, item) => acc + item.revenue, 0);
  const averageOrderSize = dashboardData.summary?.averageOrder || (todayTotalRevenue / todayTotalSales);
  const growthRate = dashboardData.summary?.growth || "+23.5%";

  const CHART_COLORS = {
    primary: theme === 'dark' ? '#8B5CF6' : '#7C3AED',
    secondary: theme === 'dark' ? '#4C1D95' : '#5B21B6',
    accent: theme === 'dark' ? '#A78BFA' : '#8B5CF6',
    success: theme === 'dark' ? '#10B981' : '#059669',
  };

  const handleRefresh = () => {
    setIsLoading(true);
    // Simulate refresh - in real app, this would fetch new data
    setTimeout(() => {
      setIsLoading(false);
      setLastUpdate(new Date());
    }, 1000);
  };

  return (
    <div className={cn("p-6 space-y-6", className)}>
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">
            {dashboardData.chartTitle || "Dynamic Analytics Dashboard"}
          </h2>
          <p className="text-muted-foreground">
            {dashboardData.chartDescription || "Real-time data visualization from chat interactions"}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdate && (
            <p className="text-sm text-muted-foreground">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </p>
          )}
          <Button 
            onClick={handleRefresh} 
            disabled={isLoading}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Sales</p>
                <h2 className="text-2xl font-semibold mt-1">{todayTotalSales}</h2>
                <p className="text-sm text-muted-foreground mt-1">Today's orders</p>
              </div>
              <div className={cn(
                "p-3 rounded-full",
                theme === 'dark' ? "bg-primary/20" : "bg-primary/10"
              )}>
                <ShoppingCart className={cn(
                  "h-6 w-6",
                  theme === 'dark' ? "text-primary" : "text-primary"
                )} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Revenue</p>
                <h2 className="text-2xl font-semibold mt-1">₹{todayTotalRevenue.toLocaleString()}</h2>
                <p className="text-sm text-muted-foreground mt-1">Today's earnings</p>
              </div>
              <div className={cn(
                "p-3 rounded-full",
                theme === 'dark' ? "bg-success/20" : "bg-success/10"
              )}>
                <DollarSign className={cn(
                  "h-6 w-6",
                  theme === 'dark' ? "text-success" : "text-success"
                )} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Average Order</p>
                <h2 className="text-2xl font-semibold mt-1">₹{averageOrderSize.toFixed(2)}</h2>
                <p className="text-sm text-muted-foreground mt-1">Per transaction</p>
              </div>
              <div className={cn(
                "p-3 rounded-full",
                theme === 'dark' ? "bg-secondary/20" : "bg-secondary/10"
              )}>
                <BarChart2 className={cn(
                  "h-6 w-6",
                  theme === 'dark' ? "text-secondary" : "text-secondary"
                )} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Growth</p>
                <h2 className="text-2xl font-semibold mt-1">{growthRate}</h2>
                <p className="text-sm text-muted-foreground mt-1">vs last month</p>
              </div>
              <div className={cn(
                "p-3 rounded-full",
                theme === 'dark' ? "bg-accent/20" : "bg-accent/10"
              )}>
                <TrendingUp className={cn(
                  "h-6 w-6",
                  theme === 'dark' ? "text-accent" : "text-accent"
                )} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Sales Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Sales Overview</CardTitle>
            <CardDescription>Sales and revenue by hour</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailySalesData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis yAxisId="left" className="text-xs" />
                <YAxis yAxisId="right" orientation="right" className="text-xs" />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="p-2 border rounded-md shadow-sm bg-background">
                          <p className="font-medium">{payload[0].payload.name}</p>
                          <p className="text-sm">Sales: {payload[0].value}</p>
                          <p className="text-sm">Revenue: ₹{payload[1].value.toLocaleString()}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend />
                <Bar 
                  yAxisId="left"
                  dataKey="sales" 
                  fill={CHART_COLORS.primary} 
                  name="Sales"
                />
                <Bar 
                  yAxisId="right"
                  dataKey="revenue" 
                  fill={CHART_COLORS.success} 
                  name="Revenue"
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Top Products Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Top Products</CardTitle>
            <CardDescription>Best selling products by volume</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={productSalesData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {productSalesData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={[
                        CHART_COLORS.primary,
                        CHART_COLORS.secondary,
                        CHART_COLORS.accent,
                        CHART_COLORS.success,
                        '#9b59b6'
                      ][index % 5]} 
                    />
                  ))}
                </Pie>
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="p-2 border rounded-md shadow-sm bg-background">
                          <p className="font-medium">{payload[0].payload.name}</p>
                          <p className="text-sm">Sales: {payload[0].value}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Location Distribution Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Location Distribution</CardTitle>
            <CardDescription>Customer distribution by area</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={locationData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {locationData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={[
                        CHART_COLORS.primary,
                        CHART_COLORS.secondary,
                        CHART_COLORS.accent,
                        CHART_COLORS.success,
                        '#9b59b6'
                      ][index % 5]} 
                    />
                  ))}
                </Pie>
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="p-2 border rounded-md shadow-sm bg-background">
                          <p className="font-medium">{payload[0].payload.name}</p>
                          <p className="text-sm">Customers: {payload[0].value}%</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Sales Trend Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Sales Trend</CardTitle>
            <CardDescription>Daily sales trend over time</CardDescription>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailySalesData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="p-2 border rounded-md shadow-sm bg-background">
                          <p className="font-medium">{payload[0].payload.name}</p>
                          <p className="text-sm">Sales: {payload[0].value}</p>
                          <p className="text-sm">Revenue: ₹{payload[0].payload.revenue.toLocaleString()}</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="sales" 
                  stroke={CHART_COLORS.primary} 
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  name="Sales"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default DynamicDashboard; 