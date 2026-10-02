import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Users, 
  Package, 
  ShoppingCart, 
  CreditCard, 
  Target, 
  Network, 
  BarChart3, 
  Shield,
  ChevronRight,
  Building2,
  Layers,
  Activity,
  Zap
} from "lucide-react";
import { cn } from "@/lib/utils";
import TMFProductModal from "./TMFProductModal";

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

const tmfCategories: TMFCategory[] = [
  {
    id: "customer-crm",
    name: "Customer Management & CRM",
    icon: Users,
    description: "Customer lifecycle, party management, and relationship management applications",
    color: "bg-blue-500",
    products: [
      {
        id: "salesforce-comm",
        name: "Salesforce Communications Cloud",
        vendor: "Salesforce",
        description: "Complete customer lifecycle management platform",
        category: "customer-crm",
        tmfAPIs: ["TMF629", "TMF632", "TMF666", "TMF672", "TMF673"],
        odaComponents: ["TMFC028", "TMFC023", "TMFC024", "TMFC022", "TMFC035"],
        tier: "Tier 1",
        coverage: 95
      },
      {
        id: "oracle-comm-billing",
        name: "Oracle Communications Billing & Revenue Management",
        vendor: "Oracle",
        description: "Customer data management and billing platform",
        category: "customer-crm",
        tmfAPIs: ["TMF629", "TMF632", "TMF666", "TMF678", "TMF676"],
        odaComponents: ["TMFC028", "TMFC024", "TMFC030", "TMFC025", "TMFC029"],
        tier: "Tier 1",
        coverage: 90
      },
      {
        id: "amdocs-ces",
        name: "Amdocs CES (Customer Experience Systems)",
        vendor: "Amdocs",
        description: "360-degree customer view and experience management",
        category: "customer-crm",
        tmfAPIs: ["TMF629", "TMF632", "TMF666", "TMF672", "TMF674"],
        odaComponents: ["TMFC028", "TMFC023", "TMFC024", "TMFC035", "TMFC014"],
        tier: "Tier 1",
        coverage: 95
      },
      {
        id: "trilogy-customer-ai",
        name: "Trilogy AI Native Customer Management",
        vendor: "Trilogy",
        description: "AI-powered customer management with predictive analytics",
        category: "customer-crm",
        tmfAPIs: ["TMF629", "TMF632", "TMF666", "TMF672", "TMF650"],
        odaComponents: ["TMFC028", "TMFC023", "TMFC024", "TMFC035", "TMFC050"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "product-service",
    name: "Product & Service Management",
    icon: Package,
    description: "Product catalog, service catalog, and inventory management",
    color: "bg-green-500",
    products: [
      {
        id: "amdocs-optima-catalog",
        name: "Amdocs Optima Product Catalog",
        vendor: "Amdocs",
        description: "Comprehensive product catalog management platform",
        category: "product-service",
        tmfAPIs: ["TMF620", "TMF633", "TMF637", "TMF638", "TMF679"],
        odaComponents: ["TMFC001", "TMFC006", "TMFC005", "TMFC008", "TMFC009"],
        tier: "Tier 1",
        coverage: 95
      },
      {
        id: "oracle-design-studio",
        name: "Oracle Communications Design Studio",
        vendor: "Oracle",
        description: "Service design and catalog management",
        category: "product-service",
        tmfAPIs: ["TMF620", "TMF633", "TMF637", "TMF638", "TMF645"],
        odaComponents: ["TMFC001", "TMFC006", "TMFC005", "TMFC008", "TMFC009"],
        tier: "Tier 1",
        coverage: 85
      },
      {
        id: "ericsson-service-manager",
        name: "Ericsson Service Manager",
        vendor: "Ericsson",
        description: "Service lifecycle management platform",
        category: "product-service",
        tmfAPIs: ["TMF633", "TMF638", "TMF641", "TMF645", "TMF640"],
        odaComponents: ["TMFC006", "TMFC008", "TMFC007", "TMFC009", "TMFC062"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "trilogy-catalog-ai",
        name: "Trilogy AI Native Product Catalog",
        vendor: "Trilogy",
        description: "AI-driven product catalog with intelligent recommendations",
        category: "product-service",
        tmfAPIs: ["TMF620", "TMF633", "TMF637", "TMF638", "TMF679", "TMF650"],
        odaComponents: ["TMFC001", "TMFC006", "TMFC005", "TMFC008", "TMFC009", "TMFC050"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "order-management",
    name: "Order Management & Fulfillment",
    icon: ShoppingCart,
    description: "Order capture, orchestration, and fulfillment systems",
    color: "bg-purple-500",
    products: [
      {
        id: "amdocs-optima-order",
        name: "Amdocs Optima Order Management",
        vendor: "Amdocs",
        description: "End-to-end order orchestration platform",
        category: "order-management",
        tmfAPIs: ["TMF622", "TMF641", "TMF663", "TMF679", "TMF645"],
        odaComponents: ["TMFC002", "TMFC007", "TMFC003", "TMFC009", "TMFC061"],
        tier: "Tier 1",
        coverage: 95
      },
      {
        id: "oracle-osm",
        name: "Oracle Communications Order and Service Management",
        vendor: "Oracle",
        description: "Order fulfillment and service activation",
        category: "order-management",
        tmfAPIs: ["TMF622", "TMF641", "TMF663", "TMF640", "TMF645"],
        odaComponents: ["TMFC002", "TMFC007", "TMFC003", "TMFC062", "TMFC009"],
        tier: "Tier 1",
        coverage: 90
      },
      {
        id: "ericsson-order-care",
        name: "Ericsson Order Care",
        vendor: "Ericsson",
        description: "Order management and tracking system",
        category: "order-management",
        tmfAPIs: ["TMF622", "TMF641", "TMF663", "TMF679"],
        odaComponents: ["TMFC002", "TMFC007", "TMFC003", "TMFC009"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "trilogy-order-ai",
        name: "Trilogy AI Native Order Management",
        vendor: "Trilogy",
        description: "AI-powered order orchestration with predictive fulfillment",
        category: "order-management",
        tmfAPIs: ["TMF622", "TMF641", "TMF663", "TMF679", "TMF645", "TMF650"],
        odaComponents: ["TMFC002", "TMFC007", "TMFC003", "TMFC009", "TMFC061", "TMFC050"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "billing-revenue",
    name: "Billing & Revenue Management",
    icon: CreditCard,
    description: "Billing, charging, payment, and revenue management systems",
    color: "bg-orange-500",
    products: [
      {
        id: "amdocs-optima-billing",
        name: "Amdocs Optima Billing",
        vendor: "Amdocs",
        description: "Convergent billing and revenue management platform",
        category: "billing-revenue",
        tmfAPIs: ["TMF678", "TMF676", "TMF654", "TMF635", "TMF666"],
        odaComponents: ["TMFC030", "TMFC029", "TMFC013", "TMFC040", "TMFC024"],
        tier: "Tier 1",
        coverage: 95
      },
      {
        id: "oracle-brm",
        name: "Oracle Communications Billing and Revenue Management",
        vendor: "Oracle",
        description: "Real-time billing and revenue management",
        category: "billing-revenue",
        tmfAPIs: ["TMF678", "TMF676", "TMF654", "TMF635", "TMF631"],
        odaComponents: ["TMFC030", "TMFC029", "TMFC013", "TMFC040", "TMFC031"],
        tier: "Tier 1",
        coverage: 90
      },
      {
        id: "ericsson-charging",
        name: "Ericsson Charging System",
        vendor: "Ericsson",
        description: "Online and offline charging system",
        category: "billing-revenue",
        tmfAPIs: ["TMF678", "TMF635", "TMF654", "TMF631"],
        odaComponents: ["TMFC030", "TMFC040", "TMFC013", "TMFC031"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "trilogy-billing-ai",
        name: "Trilogy AI Native Billing Management",
        vendor: "Trilogy",
        description: "AI-powered billing with fraud detection and revenue optimization",
        category: "billing-revenue",
        tmfAPIs: ["TMF678", "TMF676", "TMF654", "TMF635", "TMF666", "TMF650"],
        odaComponents: ["TMFC030", "TMFC029", "TMFC013", "TMFC040", "TMFC024", "TMFC041"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "campaign-offer",
    name: "Campaign & Offer Management",
    icon: Target,
    description: "Marketing campaigns, promotions, and offer management",
    color: "bg-pink-500",
    products: [
      {
        id: "amdocs-optima-campaign",
        name: "Amdocs Optima Campaign Manager",
        vendor: "Amdocs",
        description: "Marketing campaign management and automation",
        category: "campaign-offer",
        tmfAPIs: ["TMF671", "TMF672", "TMF673", "TMF629", "TMF632"],
        odaComponents: ["TMFC057", "TMFC035", "TMFC014", "TMFC028", "TMFC049"],
        tier: "Tier 1",
        coverage: 90
      },
      {
        id: "oracle-marketing",
        name: "Oracle Communications Marketing",
        vendor: "Oracle",
        description: "Offer management and campaign orchestration",
        category: "campaign-offer",
        tmfAPIs: ["TMF671", "TMF672", "TMF629", "TMF632"],
        odaComponents: ["TMFC057", "TMFC035", "TMFC028", "TMFC049"],
        tier: "Tier 1",
        coverage: 85
      },
      {
        id: "ericsson-marketing-engine",
        name: "Ericsson Marketing Engine",
        vendor: "Ericsson",
        description: "Campaign orchestration and offer management",
        category: "campaign-offer",
        tmfAPIs: ["TMF671", "TMF629", "TMF632", "TMF673"],
        odaComponents: ["TMFC057", "TMFC028", "TMFC014", "TMFC049"],
        tier: "Tier 1",
        coverage: 75
      },
      {
        id: "trilogy-campaign-ai",
        name: "Trilogy AI Native Campaign Management",
        vendor: "Trilogy",
        description: "AI-driven campaign management with predictive targeting",
        category: "campaign-offer",
        tmfAPIs: ["TMF671", "TMF672", "TMF673", "TMF629", "TMF632", "TMF650"],
        odaComponents: ["TMFC057", "TMFC035", "TMFC014", "TMFC028", "TMFC049", "TMFC050"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "network-resource",
    name: "Network & Resource Management",
    icon: Network,
    description: "Network operations, resource management, and OSS applications",
    color: "bg-indigo-500",
    products: [
      {
        id: "amdocs-optima-network",
        name: "Amdocs Optima Network",
        vendor: "Amdocs",
        description: "Network resource management and optimization",
        category: "network-resource",
        tmfAPIs: ["TMF639", "TMF640", "TMF645", "TMF641", "TMF674"],
        odaComponents: ["TMFC012", "TMFC062", "TMFC009", "TMFC007", "TMFC014"],
        tier: "Tier 1",
        coverage: 90
      },
      {
        id: "nokia-netact",
        name: "Nokia NetAct",
        vendor: "Nokia",
        description: "Network management and optimization system",
        category: "network-resource",
        tmfAPIs: ["TMF639", "TMF640", "TMF645", "TMF642"],
        odaComponents: ["TMFC012", "TMFC062", "TMFC009", "TMFC043"],
        tier: "Tier 1",
        coverage: 85
      },
      {
        id: "ericsson-network-manager",
        name: "Ericsson Network Manager",
        vendor: "Ericsson",
        description: "Network operations and management platform",
        category: "network-resource",
        tmfAPIs: ["TMF639", "TMF640", "TMF645", "TMF642", "TMF674"],
        odaComponents: ["TMFC012", "TMFC062", "TMFC009", "TMFC043", "TMFC014"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "trilogy-network-ai",
        name: "Trilogy AI Native Network Management",
        vendor: "Trilogy",
        description: "AI-powered network optimization and predictive maintenance",
        category: "network-resource",
        tmfAPIs: ["TMF639", "TMF640", "TMF645", "TMF641", "TMF674", "TMF650"],
        odaComponents: ["TMFC012", "TMFC062", "TMFC009", "TMFC007", "TMFC014", "TMFC041"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "analytics-intelligence",
    name: "Analytics & Intelligence",
    icon: BarChart3,
    description: "Business intelligence, analytics, and data management platforms",
    color: "bg-cyan-500",
    products: [
      {
        id: "amdocs-optima-analytics",
        name: "Amdocs Optima Analytics",
        vendor: "Amdocs",
        description: "Customer analytics and business intelligence",
        category: "analytics-intelligence",
        tmfAPIs: ["TMF632", "TMF629", "TMF635", "TMF678", "TMF650"],
        odaComponents: ["TMFC028", "TMFC040", "TMFC037", "TMFC058", "TMFC050"],
        tier: "Tier 1",
        coverage: 85
      },
      {
        id: "oracle-analytics",
        name: "Oracle Communications Analytics",
        vendor: "Oracle",
        description: "Business intelligence and analytics platform",
        category: "analytics-intelligence",
        tmfAPIs: ["TMF632", "TMF629", "TMF635", "TMF678"],
        odaComponents: ["TMFC028", "TMFC040", "TMFC037", "TMFC058"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "sas-telco-analytics",
        name: "SAS Telecommunications Analytics",
        vendor: "SAS",
        description: "Advanced analytics and machine learning platform",
        category: "analytics-intelligence",
        tmfAPIs: ["TMF632", "TMF629", "TMF635", "TMF650"],
        odaComponents: ["TMFC028", "TMFC040", "TMFC037", "TMFC050"],
        tier: "Tier 2",
        coverage: 75
      },
      {
        id: "trilogy-analytics-ai",
        name: "Trilogy AI Native Analytics & Intelligence",
        vendor: "Trilogy",
        description: "AI-powered analytics with real-time insights and predictive modeling",
        category: "analytics-intelligence",
        tmfAPIs: ["TMF632", "TMF629", "TMF635", "TMF678", "TMF650", "TMF667"],
        odaComponents: ["TMFC028", "TMFC040", "TMFC037", "TMFC058", "TMFC050", "TMFC041"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  },
  {
    id: "security-compliance",
    name: "Security & Compliance",
    icon: Shield,
    description: "Security, identity management, and compliance applications",
    color: "bg-red-500",
    products: [
      {
        id: "amdocs-optima-security",
        name: "Amdocs Optima Security",
        vendor: "Amdocs",
        description: "Identity and access management platform",
        category: "security-compliance",
        tmfAPIs: ["TMF672", "TMF674", "TMF629", "TMF632"],
        odaComponents: ["TMFC035", "TMFC014", "TMFC028", "TMFC022"],
        tier: "Tier 1",
        coverage: 80
      },
      {
        id: "oracle-identity",
        name: "Oracle Identity Cloud Service",
        vendor: "Oracle",
        description: "Identity management and security platform",
        category: "security-compliance",
        tmfAPIs: ["TMF672", "TMF674", "TMF629"],
        odaComponents: ["TMFC035", "TMFC014", "TMFC028"],
        tier: "Tier 1",
        coverage: 75
      },
      {
        id: "ibm-security",
        name: "IBM Security Suite",
        vendor: "IBM",
        description: "Comprehensive security and compliance platform",
        category: "security-compliance",
        tmfAPIs: ["TMF672", "TMF674", "TMF629", "TMF632"],
        odaComponents: ["TMFC035", "TMFC014", "TMFC028", "TMFC022"],
        tier: "Tier 2",
        coverage: 70
      },
      {
        id: "trilogy-security-ai",
        name: "Trilogy AI Native Security & Compliance",
        vendor: "Trilogy",
        description: "AI-powered security with threat detection and automated compliance",
        category: "security-compliance",
        tmfAPIs: ["TMF672", "TMF674", "TMF629", "TMF632", "TMF650", "TMF667"],
        odaComponents: ["TMFC035", "TMFC014", "TMFC028", "TMFC022", "TMFC041", "TMFC060"],
        tier: "AI-Native",
        coverage: 98
      }
    ]
  }
];

interface TMFCanvasProps {
  className?: string;
}

export default function TMFCanvas({ className }: TMFCanvasProps) {
  const [selectedCategory, setSelectedCategory] = useState<TMFCategory | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCategoryClick = (category: TMFCategory) => {
    setSelectedCategory(category);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCategory(null);
  };

  return (
    <>
      <div className={cn("bg-card border-r border-border", className)}>
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-primary/20 to-primary/10 rounded-lg">
              <Layers className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="font-bold text-lg text-foreground">TMF Canvas</h2>
              <p className="text-sm text-muted-foreground">BSS/OSS Application Catalogue</p>
            </div>
          </div>
        </div>
        
        <ScrollArea className="h-[calc(100vh-120px)]">
          <div className="p-4 space-y-3">
            {tmfCategories.map((category) => {
              const Icon = category.icon;
              return (
                <Card 
                  key={category.id}
                  className="cursor-pointer hover:shadow-md transition-all duration-200 hover:border-primary/20"
                  onClick={() => handleCategoryClick(category)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${category.color} text-white`}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="flex-1">
                          <CardTitle className="text-sm font-semibold leading-tight">
                            {category.name}
                          </CardTitle>
                          <CardDescription className="text-xs mt-1">
                            {category.description}
                          </CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {category.products.length} Products
                        </Badge>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Product Modal */}
      {selectedCategory && (
        <TMFProductModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          category={selectedCategory}
        />
      )}
    </>
  );
} 