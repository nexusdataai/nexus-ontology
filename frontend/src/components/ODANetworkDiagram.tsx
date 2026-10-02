import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { 
  Activity,
  ArrowRight,
  Users,
  Package,
  ShoppingCart,
  CreditCard,
  Target,
  Shield,
  BarChart3,
  Network,
  Star,
  Award,
  Brain,
  Cloud
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ODAComponent {
  id: string;
  name: string;
  code: string;
}

interface ODACategory {
  id: string;
  name: string;
  color: string;
  icon: React.ComponentType<any>;
  components: ODAComponent[];
}

interface TMFAPIConnection {
  api: string;
  description: string;
  components: string[];
  applications: string[];
}



interface ODANetworkDiagramProps {
  categories: ODACategory[];
  selectedComponent: string | null;
  onComponentSelect: (componentId: string | null) => void;
}

// TMF API to Component mappings
const tmfAPIConnections: TMFAPIConnection[] = [
  {
    api: "TMF629",
    description: "Customer Management API",
    components: ["TMFC028", "TMFC023", "TMFC022"],
    applications: ["Customer Management & CRM"]
  },
  {
    api: "TMF620",
    description: "Product Catalog Management API",
    components: ["TMFC001", "TMFC027"],
    applications: ["Product & Service Management"]
  },
  {
    api: "TMF622",
    description: "Product Ordering API",
    components: ["TMFC002", "TMFC003"],
    applications: ["Order Management & Fulfillment"]
  },
  {
    api: "TMF678",
    description: "Customer Bill Management API",
    components: ["TMFC030", "TMFC031"],
    applications: ["Billing & Revenue Management"]
  },
  {
    api: "TMF639",
    description: "Resource Inventory API",
    components: ["TMFC012", "TMFC010"],
    applications: ["Network & Resource Management"]
  },
  {
    api: "TMF671",
    description: "Promotion Management API",
    components: ["TMFC057"],
    applications: ["Campaign & Offer Management"]
  },
  {
    api: "TMF650",
    description: "Recommendation Management API",
    components: ["TMFC050", "TMFC041"],
    applications: ["Analytics & Intelligence"]
  },
  {
    api: "TMF672",
    description: "User Role & Permission API",
    components: ["TMFC035"],
    applications: ["Security & Compliance"]
  }
];

// Application to Product mappings
const applicationProducts = {
  "Customer Management & CRM": [
    { name: "Amdocs CES", vendor: "Amdocs", tier: "Tier 1" },
    { name: "Oracle Communications", vendor: "Oracle", tier: "Tier 1" },
    { name: "Trilogy AI Customer", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Product & Service Management": [
    { name: "Amdocs Optima Catalog", vendor: "Amdocs", tier: "Tier 1" },
    { name: "Oracle Design Studio", vendor: "Oracle", tier: "Tier 1" },
    { name: "Trilogy AI Catalog", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Order Management & Fulfillment": [
    { name: "Amdocs Optima Order", vendor: "Amdocs", tier: "Tier 1" },
    { name: "Oracle OSM", vendor: "Oracle", tier: "Tier 1" },
    { name: "Trilogy AI Order", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Billing & Revenue Management": [
    { name: "Amdocs Optima Billing", vendor: "Amdocs", tier: "Tier 1" },
    { name: "Oracle BRM", vendor: "Oracle", tier: "Tier 1" },
    { name: "Trilogy AI Billing", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Network & Resource Management": [
    { name: "Nokia NetAct", vendor: "Nokia", tier: "Tier 1" },
    { name: "Ericsson Network Manager", vendor: "Ericsson", tier: "Tier 1" },
    { name: "Trilogy AI Network", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Campaign & Offer Management": [
    { name: "Amdocs Campaign Manager", vendor: "Amdocs", tier: "Tier 1" },
    { name: "Oracle Marketing", vendor: "Oracle", tier: "Tier 1" },
    { name: "Trilogy AI Campaign", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Analytics & Intelligence": [
    { name: "Amdocs Analytics", vendor: "Amdocs", tier: "Tier 1" },
    { name: "SAS Telco Analytics", vendor: "SAS", tier: "Tier 2" },
    { name: "Trilogy AI Analytics", vendor: "Trilogy", tier: "AI-Native" }
  ],
  "Security & Compliance": [
    { name: "Amdocs Security", vendor: "Amdocs", tier: "Tier 1" },
    { name: "IBM Security", vendor: "IBM", tier: "Tier 2" },
    { name: "Trilogy AI Security", vendor: "Trilogy", tier: "AI-Native" }
  ]
};

const getTierIcon = (tier: string) => {
  switch (tier) {
    case "Tier 1": return <Award className="h-3 w-3 text-yellow-500" />;
    case "Tier 2": return <Star className="h-3 w-3 text-blue-500" />;
    case "Cloud-Native": return <Cloud className="h-3 w-3 text-cyan-500" />;
    case "AI-Native": return <Brain className="h-3 w-3 text-purple-500" />;
    default: return null;
  }
};

export default function ODANetworkDiagram({ categories, selectedComponent, onComponentSelect }: ODANetworkDiagramProps) {
  const [selectedAPI, setSelectedAPI] = useState<string | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<string | null>(null);



  return (
    <div className="h-full flex">
      {/* Network Visualization */}
      <div className="flex-1 relative bg-muted/20 rounded-lg p-6 overflow-auto">
        <div className="text-center mb-6">
          <h3 className="text-lg font-semibold mb-2">ODA Component Network Flow</h3>
          <div className="flex justify-center items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span>ODA Components</span>
            </div>
            <ArrowRight className="h-4 w-4" />
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span>TMF APIs</span>
            </div>
            <ArrowRight className="h-4 w-4" />
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span>BSS/OSS Applications</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8 h-full">
          {/* ODA Components Column */}
          <div>
            <h4 className="font-semibold mb-4 text-center">ODA Components</h4>
            <ScrollArea className="h-[calc(100%-40px)]">
              <div className="space-y-2">
                {categories.map((category) => (
                  <div key={category.id} className="mb-4">
                    <div className="text-xs font-medium text-muted-foreground mb-2">
                      {category.name}
                    </div>
                    {category.components.slice(0, 3).map((component) => (
                      <div
                        key={component.id}
                        className={cn(
                          "p-2 rounded border cursor-pointer transition-all duration-200",
                          selectedComponent === component.id 
                            ? "bg-primary/20 border-primary" 
                            : "bg-card hover:bg-muted/50"
                        )}
                        onClick={() => onComponentSelect(
                          selectedComponent === component.id ? null : component.id
                        )}
                      >
                        <div className="text-xs font-medium">{component.name}</div>
                        <Badge variant="outline" className="text-xs mt-1">
                          {component.code}
                        </Badge>
                      </div>
                    ))}
                    {category.components.length > 3 && (
                      <div className="text-xs text-muted-foreground text-center mt-1">
                        +{category.components.length - 3} more
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* TMF APIs Column */}
          <div>
            <h4 className="font-semibold mb-4 text-center">TMF APIs</h4>
            <ScrollArea className="h-[calc(100%-40px)]">
              <div className="space-y-3">
                {tmfAPIConnections.map((apiConn) => (
                  <div
                    key={apiConn.api}
                    className={cn(
                      "p-3 rounded border cursor-pointer transition-all duration-200",
                      selectedAPI === apiConn.api 
                        ? "bg-blue-500/20 border-blue-500" 
                        : "bg-card hover:bg-muted/50"
                    )}
                    onClick={() => setSelectedAPI(
                      selectedAPI === apiConn.api ? null : apiConn.api
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4 text-blue-500" />
                      <span className="font-medium text-sm">{apiConn.api}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {apiConn.description}
                    </div>
                    <div className="text-xs mt-2">
                      <Badge variant="secondary" className="text-xs">
                        {apiConn.components.length} Components
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* BSS/OSS Applications Column */}
          <div>
            <h4 className="font-semibold mb-4 text-center">BSS/OSS Applications</h4>
            <ScrollArea className="h-[calc(100%-40px)]">
              <div className="space-y-3">
                {Object.entries(applicationProducts).map(([app, products]) => {
                  const Icon = app.includes("Customer") ? Users :
                             app.includes("Product") ? Package :
                             app.includes("Order") ? ShoppingCart :
                             app.includes("Billing") ? CreditCard :
                             app.includes("Campaign") ? Target :
                             app.includes("Network") ? Network :
                             app.includes("Analytics") ? BarChart3 : Shield;
                  
                  return (
                    <div
                      key={app}
                      className={cn(
                        "p-3 rounded border cursor-pointer transition-all duration-200",
                        selectedApplication === app 
                          ? "bg-green-500/20 border-green-500" 
                          : "bg-card hover:bg-muted/50"
                      )}
                      onClick={() => setSelectedApplication(
                        selectedApplication === app ? null : app
                      )}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className="h-4 w-4 text-green-500" />
                        <span className="font-medium text-sm">{app}</span>
                      </div>
                      
                      {selectedApplication === app && (
                        <div className="space-y-2 mt-3">
                          {products.map((product, idx) => (
                            <div key={idx} className="flex items-center justify-between p-2 bg-muted/50 rounded">
                              <div>
                                <div className="text-xs font-medium">{product.name}</div>
                                <div className="text-xs text-muted-foreground">{product.vendor}</div>
                              </div>
                              <div className="flex items-center gap-1">
                                {getTierIcon(product.tier)}
                                <Badge variant="outline" className="text-xs">
                                  {product.tier}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {selectedApplication !== app && (
                        <Badge variant="secondary" className="text-xs">
                          {products.length} Products
                        </Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>

      {/* Side Panel - Selected Details */}
      {(selectedAPI || selectedApplication) && (
        <div className="w-80 border-l border-border bg-card p-4">
          <ScrollArea className="h-full">
            {selectedAPI && (
              <div>
                <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-500" />
                  {selectedAPI}
                </h3>
                {tmfAPIConnections.find(api => api.api === selectedAPI) && (
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold mb-2">Description</h4>
                      <p className="text-sm text-muted-foreground">
                        {tmfAPIConnections.find(api => api.api === selectedAPI)?.description}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">Connected Components</h4>
                      <div className="space-y-1">
                        {tmfAPIConnections.find(api => api.api === selectedAPI)?.components.map(comp => (
                          <Badge key={comp} variant="outline" className="text-xs">
                            {comp}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4 className="font-semibold mb-2">Target Applications</h4>
                      <div className="space-y-1">
                        {tmfAPIConnections.find(api => api.api === selectedAPI)?.applications.map(app => (
                          <Badge key={app} variant="secondary" className="text-xs">
                            {app}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {selectedApplication && (
              <div>
                <h3 className="font-bold text-lg mb-4">
                  {selectedApplication}
                </h3>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold mb-2">Available Products</h4>
                    <div className="space-y-2">
                      {applicationProducts[selectedApplication as keyof typeof applicationProducts]?.map((product, idx) => (
                        <Card key={idx}>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center gap-2">
                              {product.name}
                              {getTierIcon(product.tier)}
                            </CardTitle>
                            <CardDescription className="text-xs">
                              {product.vendor} • {product.tier}
                            </CardDescription>
                          </CardHeader>
                        </Card>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </ScrollArea>
        </div>
      )}
    </div>
  );
} 