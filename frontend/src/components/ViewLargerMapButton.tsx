
import React from 'react';
import { cn } from '@/lib/utils';

interface ViewLargerMapButtonProps {
  className?: string;
}

const ViewLargerMapButton: React.FC<ViewLargerMapButtonProps> = ({ className }) => {
  return (
    <button 
      className={cn(
        "absolute top-4 left-4 z-10 bg-secondary/80 backdrop-blur-sm py-2 px-4 rounded-md shadow-md hover:bg-secondary transition-colors text-primary font-medium border border-border/50",
        className
      )}
    >
      View larger map
    </button>
  );
};

export default ViewLargerMapButton;
