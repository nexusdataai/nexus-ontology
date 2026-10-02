
import React from 'react';
import { Plus, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MapActionsProps {
  className?: string;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
}

const MapActions: React.FC<MapActionsProps> = ({ className, onZoomIn, onZoomOut }) => {
  return (
    <div className={cn("absolute right-6 top-1/2 -translate-y-1/2 flex flex-col gap-2", className)}>
      <button 
        onClick={onZoomIn}
        className="bg-secondary/80 backdrop-blur-sm w-10 h-10 rounded-md shadow-md flex items-center justify-center hover:bg-secondary transition-colors border border-border/50"
      >
        <Plus className="h-5 w-5 text-foreground" />
      </button>
      <button 
        onClick={onZoomOut}
        className="bg-secondary/80 backdrop-blur-sm w-10 h-10 rounded-md shadow-md flex items-center justify-center hover:bg-secondary transition-colors border border-border/50"
      >
        <Minus className="h-5 w-5 text-foreground" />
      </button>
    </div>
  );
};

export default MapActions;
