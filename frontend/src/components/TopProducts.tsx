import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Sample data - replace with your actual data
const data = [
  { name: 'Product A', sales: 4000 },
  { name: 'Product B', sales: 3000 },
  { name: 'Product C', sales: 2000 },
  { name: 'Product D', sales: 2780 },
  { name: 'Product E', sales: 1890 },
  { name: 'Product F', sales: 2390 },
  { name: 'Product G', sales: 3490 },
  { name: 'Product H', sales: 2000 },
  { name: 'Product I', sales: 2780 },
  { name: 'Product J', sales: 1890 },
];

const TopProducts = () => {
  return (
    <div className="p-6">
      <Card>
        <CardHeader>
          <CardTitle>Top 10 Best Selling Products</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="sales" fill="#8B5CF6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TopProducts; 