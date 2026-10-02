import { useState } from 'react';
import { cn } from '@/lib/utils';
import { BarChart3, TreePine, Map, FileText, Menu } from 'lucide-react';

interface NavigationProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const navItems = [
  { id: 'interactive', label: 'Interactive Graph', icon: BarChart3 },
  { id: 'hierarchical', label: 'Hierarchical View', icon: TreePine },
  { id: 'mapping', label: 'Mapping Dashboard', icon: Map },
  { id: 'analysis', label: 'Detailed Analysis', icon: FileText },
];

export default function Navigation({ activeTab, onTabChange }: NavigationProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <nav className={cn(
      "bg-card border-r border-border transition-all duration-300 flex flex-col",
      isCollapsed ? "w-16" : "w-64"
    )}>
      <div className="p-4 border-b border-border flex items-center justify-between">
        {!isCollapsed && (
          <h1 className="text-foreground font-semibold text-lg">TMF ODA Analytics</h1>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-muted-foreground hover:text-foreground transition-colors p-1"
        >
          <Menu size={20} />
        </button>
      </div>
      
      <div className="flex-1 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "w-full flex items-center px-4 py-3 text-left transition-all duration-200",
                "hover:bg-accent border-r-2 border-transparent",
                activeTab === item.id 
                  ? "bg-primary/10 border-r-primary text-primary" 
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon size={20} className="flex-shrink-0" />
              {!isCollapsed && (
                <span className="ml-3 font-medium">{item.label}</span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
