import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { useRole } from '@/hooks/useRole';
import { Permission } from '@/types/auth';
import {
  Search,
  Database,
  Scissors,
  Code2,
  MapPin,
  Zap,
  BarChart3,
  Globe,
  Users,
  Building,
  FileText,
  Settings,
  CheckCircle,
  Clock,
  Brain,
  Timer
} from 'lucide-react';
import SalesforceConnector from './SalesforceConnector';
import Office365Connector from './Office365Connector';
import KnowledgeBase from './KnowledgeBase';
import BSSStudioConnector from './BSSStudioConnector';

interface Tool {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: string;
  status: 'Available' | 'Coming Soon';
  inputs?: string[];
  outputs?: string[];
  backgroundColor: string;
}

interface ToolsCatalogueProps {
  onToolSelect?: (toolId: string) => void;
}

const ToolsCatalogue: React.FC<ToolsCatalogueProps> = ({ onToolSelect }) => {
  const { profile, hasPermission } = useEnterpriseAuth();
  const { isExecutive, isSalesManager, isRep } = useRole();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [activeCategory, setActiveCategory] = useState('');
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  
  // Support deep-linking to a specific tool via ?tool=<tool-id> query parameter
  useEffect(() => {
    const toolParam = searchParams.get('tool');
    if (toolParam && ['salesforce-connector', 'office365-connector', 'knowledge-base', 'bss-studio-connector'].includes(toolParam)) {
      setSelectedTool(toolParam);
    }
  }, [searchParams]);

  const categories = [
    'Analysis', 'Transformation', 'Processing', 'Mapping',
    'Enhancement', 'Migration', 'Validation', 'Monitoring'
  ];

  const tools: Tool[] = [
    {
      id: 'customer-segmentation',
      name: 'Customer Segmentation Analyzer',
      description: 'Segment customers based on behavior patterns and demographics for targeted analysis.',
      icon: <Users className="h-6 w-6 text-white" />,
      category: 'Analysis',
      status: 'Available',
      inputs: ['Customer Data', 'Behavior Logs', 'Demographics'],
      outputs: ['Segment Groups', 'Behavior Patterns', 'Recommendations'],
      backgroundColor: 'bg-primary'
    },
    {
      id: 'performance-optimizer',
      name: 'Performance Optimizer',
      description: 'Optimize agent performance through data-driven insights and recommendations.',
      icon: <Zap className="h-6 w-6 text-white" />,
      category: 'Enhancement',
      status: 'Available',
      inputs: ['Performance Metrics', 'Call Data', 'Training Records'],
      outputs: ['Optimization Plan', 'Training Recommendations', 'KPI Improvements'],
      backgroundColor: 'bg-primary'
    },
    {
      id: 'data-quality-enhancer',
      name: 'Data Quality Enhancer',
      description: 'Improve data quality through validation, cleaning, and enrichment processes.',
      icon: <CheckCircle className="h-6 w-6 text-white" />,
      category: 'Enhancement',
      status: 'Coming Soon',
      inputs: ['Raw Data', 'Quality Rules', 'Reference Data'],
      outputs: ['Cleaned Data', 'Quality Reports', 'Enrichment Logs'],
      backgroundColor: 'bg-border-strong'
    },
  
  ];

  // Get all tools available for user role (without category filtering)
  const getAllowedTools = () => {
    if (isRep) {
      // Reps can only see KnowledgeBase tool
      return tools.filter(tool => 
        tool.id === 'knowledge-base' && hasPermission(Permission.ACCESS_KNOWLEDGE_BASE)
      );
    } else if (isSalesManager) {
      // Sales Managers see Analysis and Enhancement tools, but NO Integration tools
      return tools.filter(tool => {
        if (tool.category === 'Analysis' && hasPermission(Permission.ACCESS_ANALYSIS_TOOLS)) return true;
        if (tool.category === 'Enhancement' && hasPermission(Permission.ACCESS_ENHANCEMENT_TOOLS)) return true;
        if (tool.id === 'knowledge-base' && hasPermission(Permission.ACCESS_KNOWLEDGE_BASE)) return true;
        return false;
      });
    } else if (isExecutive) {
      // Executives see all tools they have permission for
      return tools.filter(tool => {
        if (tool.category === 'Analysis' && hasPermission(Permission.ACCESS_ANALYSIS_TOOLS)) return true;
        if (tool.category === 'Enhancement' && hasPermission(Permission.ACCESS_ENHANCEMENT_TOOLS)) return true;
        if (tool.category === 'Integration' && hasPermission(Permission.ACCESS_INTEGRATION_TOOLS)) return true;
        if (tool.id === 'knowledge-base' && hasPermission(Permission.ACCESS_KNOWLEDGE_BASE)) return true;
        return false;
      });
    }
    return [];
  };

  // Role-based tool filtering with category support
  const getFilteredTools = () => {
    const allowedTools = getAllowedTools();
    
    // If no active category is set, return all allowed tools
    if (!activeCategory) {
      return allowedTools;
    }
    
    // Filter by active category
    if (activeCategory === 'Analysis') {
      // Analysis view shows Analysis, Enhancement, and Integration tools together
      return allowedTools.filter(tool => ['Analysis', 'Integration', 'Enhancement'].includes(tool.category));
    } else {
      // Specific category view
      return allowedTools.filter(tool => tool.category === activeCategory);
    }
  };

  // Get categories that have tools available for this role
  const getAvailableCategories = () => {
    const allowedTools = getAllowedTools();
    const availableCategories = [...new Set(allowedTools.map(tool => tool.category))];
    
    // For roles with multiple categories, include 'Analysis' as a combined view
    if (availableCategories.length > 1 && !availableCategories.includes('Analysis')) {
      availableCategories.unshift('Analysis');
    }
    
    return categories.filter(cat => 
      cat === 'Analysis' || availableCategories.includes(cat)
    );
  };

  const availableCategories = getAvailableCategories();
  const filteredTools = getFilteredTools();

  // Set default active category if not set
  React.useEffect(() => {
    if (!activeCategory && availableCategories.length > 0) {
      setActiveCategory(availableCategories[0]);
    }
  }, [activeCategory, availableCategories]);

  const handleTryTool = (toolId: string) => {
    if (['salesforce-connector', 'office365-connector', 'knowledge-base', 'bss-studio-connector'].includes(toolId)) {
      setSelectedTool(toolId);
    } else {
      console.log(`Trying tool: ${toolId}`);
      // Add tool-specific logic here
    }
  };

  const handleBackToCatalogue = () => {
    setSelectedTool(null);
    // Clear the tool query parameter when going back
    if (searchParams.has('tool')) {
      searchParams.delete('tool');
      setSearchParams(searchParams);
    }
  };

  if (selectedTool === 'salesforce-connector') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-6 pb-0">
          <Button
            variant="outline"
            onClick={handleBackToCatalogue}
            className="flex items-center gap-2"
          >
            ← Back to Catalogue
          </Button>
        </div>
        <SalesforceConnector />
      </div>
    );
  }

  if (selectedTool === 'office365-connector') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-6 pb-0">
          <Button
            variant="outline"
            onClick={handleBackToCatalogue}
            className="flex items-center gap-2"
          >
            ← Back to Catalogue
          </Button>
        </div>
        <Office365Connector />
      </div>
    );
  }

  if (selectedTool === 'knowledge-base') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-6 pb-0">
          <Button
            variant="outline"
            onClick={handleBackToCatalogue}
            className="flex items-center gap-2"
          >
            ← Back to Catalogue
          </Button>
        </div>
        <KnowledgeBase />
      </div>
    );
  }

  if (selectedTool === 'bss-studio-connector') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4 p-6 pb-0">
          <Button
            variant="outline"
            onClick={handleBackToCatalogue}
            className="flex items-center gap-2"
          >
            ← Back to Catalogue
          </Button>
        </div>
        <BSSStudioConnector />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <Settings className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Totogi Tools Catalogue</h1>
            <p className="text-muted-foreground">
              Explore and interact with our comprehensive suite of call center analytics and transformation tools
            </p>
          </div>
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-4">
        {availableCategories.map((category) => (
          <Button
            key={category}
            variant={activeCategory === category ? "default" : "ghost"}
            size="sm"
            onClick={() => setActiveCategory(category)}
            className={activeCategory === category ? "bg-primary text-white hover:bg-primary/90" : "hover:bg-primary/10"}
          >
            {category}
          </Button>
        ))}
      </div>

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredTools.map((tool) => (
          <Card key={tool.id} className="relative overflow-hidden hover:shadow-lg transition-shadow">
            <CardHeader className="space-y-4">
              <div className="flex items-start justify-between">
                <div className={`w-12 h-12 ${tool.backgroundColor} rounded-lg flex items-center justify-center`}>
                  {tool.icon}
                </div>
                <div className="flex gap-2">
                  <Badge
                    variant={tool.status === 'Available' ? 'default' : 'secondary'}
                    className={tool.status === 'Available'
                      ? 'bg-primary text-white'
                      : 'bg-border-strong text-white'
                    }
                  >
                    {tool.status}
                  </Badge>
                  <Badge variant="outline">{tool.category}</Badge>
                </div>
              </div>
              <div>
                <CardTitle className="text-lg">{tool.name}</CardTitle>
                <CardDescription className="text-sm mt-2">
                  {tool.description}
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Inputs */}
              {tool.inputs && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-4 h-4 text-primary">⚡</div>
                    <span className="text-sm font-medium text-foreground">Inputs</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {tool.inputs.map((input, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {input}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Outputs */}
              {tool.outputs && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-4 h-4 text-accent">▶</div>
                    <span className="text-sm font-medium text-foreground">Outputs</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {tool.outputs.map((output, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {output}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Try Tool Button */}
              <Button
                className={`w-full text-white ${
                  tool.status === 'Available' 
                    ? 'bg-primary hover:bg-primary/90' 
                    : 'bg-border-strong cursor-not-allowed'
                }`}
                onClick={() => handleTryTool(tool.id)}
                disabled={tool.status === 'Coming Soon'}
              >
                <span className="mr-2">▶</span>
                {tool.status === 'Available' ? 'Try Tool' : 'Coming Soon'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredTools.length === 0 && (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No tools available in this category yet.</p>
        </div>
      )}
    </div>
  );
};

export default ToolsCatalogue; 