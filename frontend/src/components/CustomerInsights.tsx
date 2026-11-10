import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Users, UserPlus, UserCheck, ArrowUpRight } from 'lucide-react';

// Sample data - replace with your actual data
const customerSegments = [
  { name: 'New Customers', value: 400 },
  { name: 'Returning', value: 300 },
  { name: 'Loyal', value: 200 },
  { name: 'VIP', value: 100 },
];

const metrics = [
  {
    title: 'Total Customers',
    value: '1,234',
    change: '+12.5%',
    icon: Users,
  },
  {
    title: 'New Customers',
    value: '156',
    change: '+8.2%',
    icon: UserPlus,
  },
  {
    title: 'Active Customers',
    value: '892',
    change: '+15.3%',
    icon: UserCheck,
  },
];

const COLORS = ['#d6eaffff', '#fff7edff', '#f3eafaff', '#f6f7f8ff'];

const CustomerInsights = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
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
          <CardTitle>Customer Segments</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={customerSegments}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={150}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {customerSegments.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CustomerInsights; 