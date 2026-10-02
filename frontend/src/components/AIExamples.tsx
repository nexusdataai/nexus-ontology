import React from 'react';
import { Lightbulb } from 'lucide-react';

interface AIExamplesProps {
  onExampleClick?: (example: string) => void;
}

const AIExamples: React.FC<AIExamplesProps> = ({ onExampleClick }) => {
  const examples = [
    "Show me churn risk analysis",
    "Take me to agent performance metrics",
    "Display revenue at risk analysis", 
    "Show conversion funnel analysis",
    "Take me to training needs assessment",
    "Show call quality metrics"
  ];

  return (
    <div className="p-4 bg-muted/50 rounded-lg mb-4">
      <div className="flex items-center gap-2 mb-3">
        <Lightbulb className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-medium">Try asking me:</h3>
      </div>
      <div className="space-y-2">
        {examples.slice(0, 6).map((example, index) => (
          <button
            key={index}
            onClick={() => onExampleClick?.(example)}
            className="text-left text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 p-2 rounded-md transition-colors cursor-pointer w-full"
            title={`Ask: ${example}`}
          >
            • {example}
          </button>
        ))}
      </div>
    </div>
  );
};

export default AIExamples; 