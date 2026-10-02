
import React from 'react';
import { 
  AlertTriangle, 
  Users, 
  Target, 
  SlidersHorizontal, 
  TrendingDown, 
  DollarSign,
  Zap,
  PhoneCall
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from './ui/dropdown-menu';

interface QueryOption {
  id: string;
  name: string;
  icon: React.ReactNode;
  color: string;
}

interface QueryFiltersProps {
  className?: string;
  onQuerySelect?: (queryId: string | null) => void;
}

const queryOptions: QueryOption[] = [
  {
    id: 'churn-risk',
    name: 'Churn Risk Analysis',
    icon: <TrendingDown className="h-4 w-4" />,
    color: 'text-red-500',
  },
  {
    id: 'agent-performance',
    name: 'Agent Performance',
    icon: <Users className="h-4 w-4" />,
    color: 'text-blue-500',
  },
  {
    id: 'revenue-risk',
    name: 'Revenue at Risk',
    icon: <DollarSign className="h-4 w-4" />,
    color: 'text-orange-500',
  },
  {
    id: 'conversion-funnel',
    name: 'Conversion Funnel',
    icon: <Target className="h-4 w-4" />,
    color: 'text-green-500',
  },
  {
    id: 'training-needs',
    name: 'Training Needs',
    icon: <Zap className="h-4 w-4" />,
    color: 'text-purple-500',
  },
  {
    id: 'call-quality',
    name: 'Call Quality Metrics',
    icon: <PhoneCall className="h-4 w-4" />,
    color: 'text-indigo-500',
  },
  {
    id: 'deals-at-risk',
    name: 'Deals at Risk',
    icon: <AlertTriangle className="h-4 w-4" />,
    color: 'text-amber-500',
  },
];

const QueryFilters: React.FC<QueryFiltersProps> = ({ className, onQuerySelect }) => {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className={cn(
            // Match ThemeToggle button style
            'p-2 rounded-full transition-colors',
            'bg-secondary/80 text-foreground hover:bg-secondary',
            'border border-border',
            className
          )}
          aria-label="Show call analytics filters"
          title="Show call analytics filters"
        >
          <SlidersHorizontal className="h-[1.2rem] w-[1.2rem]" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {queryOptions.map((query) => (
          <DropdownMenuItem
            key={query.id}
            onClick={() => onQuerySelect?.(query.id)}
            className="cursor-pointer"
          >
            <span className={cn(query.color, 'mr-2')}>{query.icon}</span>
            <span>{query.name}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default QueryFilters;
