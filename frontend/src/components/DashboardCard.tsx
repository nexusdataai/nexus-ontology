
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface DashboardCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export default function DashboardCard({ title, subtitle, children, className }: DashboardCardProps) {
  return (
    <div className={cn(
      "bg-card rounded-lg border border-border shadow-lg",
      "hover:shadow-xl transition-shadow duration-300",
      className
    )}>
      <div className="p-6 border-b border-border">
        <h3 className="text-xl font-semibold text-foreground">{title}</h3>
        {subtitle && (
          <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
        )}
      </div>
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}
