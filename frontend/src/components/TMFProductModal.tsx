import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { 
  Building2, 
  Layers, 
  Activity, 
  Star, 
  TrendingUp, 
  Zap,
  Brain,
  Cloud,
  Award
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TMFProduct {
  id: string;
  name: string;
  vendor: string;
  description: string;
  category: string;
  tmfAPIs: string[];
  odaComponents: string[];
  tier: "Tier 1" | "Tier 2" | "Cloud-Native" | "AI-Native";
  coverage: number;
}

interface TMFCategory {
  id: string;
  name: string;
  icon: React.ComponentType<any>;
  description: string;
  color: string;
  products: TMFProduct[];
}

interface TMFProductModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: TMFCategory;
}

// TMF API to ODA Component mapping based on TMF ODA Directory
const apiToComponentMap: Record<string, { name: string; description: string }> = {
  "TMF629": { name: "Party Management (TMFC028)", description: "Manage customer and business party information" },
  "TMF632": { name: "Party Management (TMFC028)", description: "Individual and organization management" },
  "TMF666": { name: "Billing Account Management (TMFC024)", description: "Manage billing accounts and relationships" },
  "TMF672": { name: "Party Roles Permissions Management (TMFC035)", description: "User roles and permissions management" },
  "TMF673": { name: "Location Management (TMFC014)", description: "Geographic address and location management" },
  "TMF674": { name: "Location Management (TMFC014)", description: "Geographic site and location management" },
  "TMF678": { name: "Bill Generation Management (TMFC030)", description: "Customer bill generation and management" },
  "TMF676": { name: "Payment Management (TMFC029)", description: "Payment processing and management" },
  "TMF654": { name: "Service Balance Management (TMFC013)", description: "Prepaid balance and account management" },
  "TMF635": { name: "Product Usage Management (TMFC040)", description: "Usage data collection and management" },
  "TMF631": { name: "Bill Calculation (TMFC031)", description: "Rating and billing calculation" },
  "TMF620": { name: "Product Catalog Management (TMFC001)", description: "Product catalog and offering management" },
  "TMF633": { name: "Service Catalog Management (TMFC006)", description: "Service catalog and specification management" },
  "TMF637": { name: "Product Inventory (TMFC005)", description: "Product inventory and instance management" },
  "TMF638": { name: "Service Inventory (TMFC008)", description: "Service inventory and instance management" },
  "TMF679": { name: "Product Offering Qualification (TMFC009)", description: "Product offering qualification and validation" },
  "TMF622": { name: "Product Order Capture & Validation (TMFC002)", description: "Product order capture and validation" },
  "TMF641": { name: "Service Order Management (TMFC007)", description: "Service order management and orchestration" },
  "TMF663": { name: "Product Order Capture & Validation (TMFC002)", description: "Shopping cart and order capture" },
  "TMF645": { name: "Service Qualification Management (TMFC009)", description: "Service qualification and feasibility" },
  "TMF640": { name: "Resource Configuration and Activation (TMFC062)", description: "Service activation and configuration" },
  "TMF639": { name: "Resource Inventory (TMFC012)", description: "Resource inventory and management" },
  "TMF642": { name: "Fault Management (TMFC043)", description: "Alarm and fault management" },
  "TMF671": { name: "Campaign Management (TMFC057)", description: "Marketing campaign management" },
  "TMF650": { name: "Recommendation Management (TMFC050)", description: "AI-powered recommendations and insights" },
  "TMF667": { name: "Anomaly Management (TMFC041)", description: "Anomaly detection and management" }
};

const getTierIcon = (tier: string) => {
  switch (tier) {
    case "Tier 1":
      return <Award className="h-4 w-4 text-yellow-500" />;
    case "Tier 2":
      return <Star className="h-4 w-4 text-blue-500" />;
    case "Cloud-Native":
      return <Cloud className="h-4 w-4 text-cyan-500" />;
    case "AI-Native":
      return <Brain className="h-4 w-4 text-purple-500" />;
    default:
      return <Building2 className="h-4 w-4" />;
  }
};

const getTierColor = (tier: string) => {
  switch (tier) {
    case "Tier 1":
      return "bg-yellow-500";
    case "Tier 2":
      return "bg-blue-500";
    case "Cloud-Native":
      return "bg-cyan-500";
    case "AI-Native":
      return "bg-purple-500";
    default:
      return "bg-gray-500";
  }
};

export default function TMFProductModal({ isOpen, onClose, category }: TMFProductModalProps) {
  const Icon = category.icon;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${category.color} text-white`}>
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <span className="text-xl">{category.name}</span>
              <DialogDescription className="mt-1">
                {category.description}
              </DialogDescription>
            </div>
          </DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="products" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="products">Products ({category.products.length})</TabsTrigger>
            <TabsTrigger value="apis">TMF APIs</TabsTrigger>
            <TabsTrigger value="components">ODA Components</TabsTrigger>
          </TabsList>

          <TabsContent value="products" className="mt-6">
            <ScrollArea className="h-[60vh]">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {category.products.map((product) => (
                  <Card key={product.id} className="h-fit">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-lg flex items-center gap-2">
                            {product.name}
                            {getTierIcon(product.tier)}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            <span className="font-semibold">{product.vendor}</span>
                          </CardDescription>
                        </div>
                        <Badge 
                          variant={product.tier === "AI-Native" ? "default" : "secondary"}
                          className={cn(
                            "text-xs",
                            product.tier === "AI-Native" && "bg-purple-500 text-white"
                          )}
                        >
                          {product.tier}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-sm text-muted-foreground">{product.description}</p>
                      
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">TMF API Coverage</span>
                          <span className="text-sm font-semibold">{product.coverage}%</span>
                        </div>
                        <Progress value={product.coverage} className="h-2" />
                      </div>

                      <div className="space-y-3">
                        <div>
                          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                            <Activity className="h-4 w-4 text-blue-500" />
                            TMF APIs ({product.tmfAPIs.length})
                          </h4>
                          <div className="flex flex-wrap gap-1">
                            {product.tmfAPIs.map((api) => (
                              <Badge key={api} variant="outline" className="text-xs">
                                {api}
                              </Badge>
                            ))}
                          </div>
                        </div>

                        <div>
                          <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                            <Layers className="h-4 w-4 text-green-500" />
                            ODA Components ({product.odaComponents.length})
                          </h4>
                          <div className="flex flex-wrap gap-1">
                            {product.odaComponents.map((component) => (
                              <Badge key={component} variant="secondary" className="text-xs">
                                {component}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="apis" className="mt-6">
            <ScrollArea className="h-[60vh]">
              <div className="space-y-4">
                {Array.from(new Set(category.products.flatMap(p => p.tmfAPIs))).sort().map((api) => (
                  <Card key={api}>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Activity className="h-5 w-5 text-blue-500" />
                        {api}
                      </CardTitle>
                      <CardDescription>
                        {apiToComponentMap[api]?.description || "TMF API specification"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Mapped ODA Component</h4>
                          <Badge variant="secondary" className="text-sm">
                            {apiToComponentMap[api]?.name || "Component mapping available"}
                          </Badge>
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Supporting Products</h4>
                          <div className="flex flex-wrap gap-2">
                            {category.products
                              .filter(p => p.tmfAPIs.includes(api))
                              .map(p => (
                                <Badge key={p.id} variant="outline" className="text-xs">
                                  {p.vendor} {p.name.split(' ').slice(-1)[0]}
                                </Badge>
                              ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="components" className="mt-6">
            <ScrollArea className="h-[60vh]">
              <div className="space-y-4">
                {Array.from(new Set(category.products.flatMap(p => p.odaComponents))).sort().map((component) => (
                  <Card key={component}>
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Layers className="h-5 w-5 text-green-500" />
                        {component}
                      </CardTitle>
                      <CardDescription>
                        {Object.entries(apiToComponentMap)
                          .find(([_, comp]) => comp.name.includes(component))?.[1]?.description || 
                          "TMF ODA Component"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Implemented by TMF APIs</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(apiToComponentMap)
                              .filter(([_, comp]) => comp.name.includes(component))
                              .map(([api, _]) => (
                                <Badge key={api} variant="outline" className="text-xs">
                                  {api}
                                </Badge>
                              ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold mb-2">Supporting Products</h4>
                          <div className="flex flex-wrap gap-2">
                            {category.products
                              .filter(p => p.odaComponents.includes(component))
                              .map(p => (
                                <Badge key={p.id} variant="outline" className="text-xs">
                                  {p.vendor} {p.name.split(' ').slice(-1)[0]}
                                </Badge>
                              ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
} 