import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, DollarSign, ShoppingCart, Users, ArrowUpRight } from 'lucide-react';

// Sample data - replace with your actual data
const analyticsData = [
  { month: 'Jan', revenue: 4000, orders: 240, customers: 180 },
  { month: 'Feb', revenue: 3000, orders: 139, customers: 150 },
  { month: 'Mar', revenue: 5000, orders: 380, customers: 220 },
  { month: 'Apr', revenue: 2780, orders: 290, customers: 200 },
  { month: 'May', revenue: 1890, orders: 480, customers: 250 },
  { month: 'Jun', revenue: 2390, orders: 380, customers: 210 },
];

const metrics = [
  {
    title: 'Total Revenue',
    value: '$45,231.89',
    change: '+20.1%',
    icon: DollarSign,
  },
  {
    title: 'Total Orders',
    value: '2,350',
    change: '+15.3%',
    icon: ShoppingCart,
  },
  {
    title: 'Total Customers',
    value: '1,234',
    change: '+12.5%',
    icon: Users,
  },
  {
    title: 'Growth Rate',
    value: '23.5%',
    change: '+5.2%',
    icon: TrendingUp,
  },
];

const Analytics = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {metric.title}
              </CardTitle>
              <metric.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">{metric.value}</div>
              <div className="flex items-center text-xs text-success">
                <ArrowUpRight className="h-4 w-4" />
                {metric.change}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Business Performance Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={analyticsData}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Area
                  yAxisId="left"
                  type="monotone"
                  dataKey="revenue"
                  stroke="#8B5CF6"
                  fill="#8B5CF6"
                  fillOpacity={0.2}
                  name="Revenue"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="orders"
                  stroke="#EC4899"
                  fill="#EC4899"
                  fillOpacity={0.2}
                  name="Orders"
                />
                <Area
                  yAxisId="right"
                  type="monotone"
                  dataKey="customers"
                  stroke="#F59E0B"
                  fill="#F59E0B"
                  fillOpacity={0.2}
                  name="Customers"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Analytics; 