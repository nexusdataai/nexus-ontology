import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Settings,
  BarChart3,
  ShieldAlert,
  Coins,
  Mail,
  Bell,
  TrendingDown,
  Play,
  type LucideIcon,
} from 'lucide-react';
import type { AppConfig } from '@/config/appRegistry';

interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  status: 'Available' | 'Coming Soon';
  icon: LucideIcon;
  inputs: string[];
  outputs: string[];
}

// Per-Solution tool registry. Each app curates its own toolset, grounded in
// its ontology entities. Apps without an entry render the empty state.
const APP_TOOLS: Record<string, Tool[]> = {
  'order-to-cash': [
    {
      id: 'order-match-verifier',
      name: 'Order Match Verifier',
      description:
        'Three-way match between Opportunity, Delivery, and Invoice -- flags mismatches with reason codes.',
      category: 'Analysis',
      status: 'Available',
      icon: ShieldAlert,
      inputs: ['Opportunity', 'Delivery_Document', 'AR_Invoice'],
      outputs: ['match_status', 'mismatch_reason', 'discrepancy_amount'],
    },
    {
      id: 'order-anomaly-scorer',
      name: 'Order Anomaly Scorer',
      description:
        'Scores orders for cycle-time deviation, missing delivery, and missing invoice signals.',
      category: 'Analysis',
      status: 'Available',
      icon: BarChart3,
      inputs: ['Opportunity', 'Opportunity_Line_Item', 'Delivery_Document'],
      outputs: ['anomaly_score', 'risk_rank', 'flagged_dimensions'],
    },
    {
      id: 'ar-cash-flow-projector',
      name: 'AR Cash Flow Projector',
      description:
        'Projects cash inflows from open AR invoices using historical payment patterns and aging buckets.',
      category: 'Analysis',
      status: 'Available',
      icon: Coins,
      inputs: ['AR_Invoice', 'Account'],
      outputs: ['projected_inflow', 'payment_probability', 'dso_impact'],
    },
    {
      id: 'o2c-alert-generator',
      name: 'O2C Alert Generator',
      description:
        'Evaluates O2C alert rules (invoice mismatch > 5%, 3+ day delays, leakage thresholds) and emits alerts.',
      category: 'Automation',
      status: 'Available',
      icon: Bell,
      inputs: ['match_status', 'anomaly_score'],
      outputs: ['Alert', 'Action_Recommendation'],
    },
    {
      id: 'dunning-notice-composer',
      name: 'Dunning Notice Composer',
      description:
        'Generates aging-bucket-aware dunning notices for overdue invoices and logs communications.',
      category: 'Automation',
      status: 'Available',
      icon: Mail,
      inputs: ['Account', 'AR_Invoice', 'Aging_Bucket'],
      outputs: ['Dunning_Notice', 'Communication_Log'],
    },
    {
      id: 'dso-optimizer',
      name: 'DSO Optimizer',
      description:
        'Analyzes payment patterns and recommends levers to reduce Days Sales Outstanding.',
      category: 'Enhancement',
      status: 'Coming Soon',
      icon: TrendingDown,
      inputs: ['AR_Invoice', 'AR_Payment', 'Account'],
      outputs: ['Optimization_Plan', 'Recommended_Levers', 'DSO_Forecast'],
    },
  ],
};

interface Props {
  app: AppConfig;
}

export function AppToolsCatalogue({ app }: Props) {
  const tools = APP_TOOLS[app.id] || [];
  const categories = ['All', ...Array.from(new Set(tools.map((t) => t.category)))];
  const [activeCategory, setActiveCategory] = useState('All');
  const visible =
    activeCategory === 'All' ? tools : tools.filter((t) => t.category === activeCategory);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div
          className={`w-10 h-10 rounded-lg flex items-center justify-center bg-gradient-to-br ${app.color}`}
        >
          <Settings className="h-5 w-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            {app.shortName} Tools Catalogue
          </h1>
          <p className="text-sm text-muted-foreground">
            Tools curated for the {app.name} Solution -- each grounded in this app's ontology
            entities.
          </p>
        </div>
      </div>

      {tools.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground border border-dashed rounded-lg">
          No tools curated yet for the {app.shortName} Solution.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 border-b border-border pb-4">
            {categories.map((category) => (
              <Button
                key={category}
                variant={activeCategory === category ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveCategory(category)}
                className={
                  activeCategory === category
                    ? 'bg-[#802dc8] text-white hover:bg-[#6b25a8]'
                    : 'hover:bg-[#802dc8]/10'
                }
              >
                {category}
              </Button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visible.map((tool) => {
              const Icon = tool.icon;
              return (
                <Card
                  key={tool.id}
                  className="relative overflow-hidden hover:shadow-lg transition-shadow"
                >
                  <CardHeader className="space-y-4">
                    <div className="flex items-start justify-between">
                      <div className="w-12 h-12 bg-[#802dc8] rounded-lg flex items-center justify-center">
                        <Icon className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex gap-2">
                        <Badge
                          className={
                            tool.status === 'Available'
                              ? 'bg-[#802dc8] text-white'
                              : 'bg-gray-400 text-white'
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
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-foreground">⚡ Inputs</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {tool.inputs.map((input, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {input}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-sm font-medium text-foreground">▶ Outputs</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {tool.outputs.map((output, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {output}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      className={`w-full text-white ${
                        tool.status === 'Available'
                          ? 'bg-[#802dc8] hover:bg-[#6b25a8]'
                          : 'bg-gray-400 cursor-not-allowed'
                      }`}
                      disabled={tool.status === 'Coming Soon'}
                    >
                      <Play className="h-3 w-3 mr-2" />
                      {tool.status === 'Available' ? 'Try Tool' : 'Coming Soon'}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
