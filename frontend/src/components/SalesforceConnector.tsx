import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  AlertCircle,
  CheckCircle,
  Building,
  Users,
  DollarSign,
  Calendar,
  Phone,
  Settings,
  RefreshCw,
  Eye,
  EyeOff,
  Wifi,
  WifiOff,
  Activity,
  Target
} from 'lucide-react';

interface SalesforceOAuthConfig {
  clientId: string;
  clientSecret: string;
  instanceUrl: string;
  redirectUri: string;
  sandbox: boolean;
}

interface ConnectionStatus {
  isConnected: boolean;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastConnected?: Date;
  error?: string;
}

interface MockSalesforceData {
  accounts: MockAccount[];
  contacts: MockContact[];
  opportunities: MockOpportunity[];
  activities: MockActivity[];
}

interface MockAccount {
  id: string;
  name: string;
  type: string;
  industry: string;
  phone: string;
  website: string;
  employees: number;
  annualRevenue: number;
}

interface MockContact {
  id: string;
  name: string;
  title: string;
  account: string;
  email: string;
  phone: string;
  lastActivity: Date;
}

interface MockOpportunity {
  id: string;
  name: string;
  account: string;
  stage: string;
  amount: number;
  closeDate: Date;
  probability: number;
}

interface MockActivity {
  id: string;
  type: 'Call' | 'Email' | 'Meeting' | 'Task';
  subject: string;
  account: string;
  contact: string;
  date: Date;
  duration?: number;
  status: 'Completed' | 'Scheduled' | 'In Progress';
}

const SalesforceConnector: React.FC = () => {
  const [activeTab, setActiveTab] = useState('config');
  const [showSecret, setShowSecret] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  
  const [oauthConfig, setOauthConfig] = useState<SalesforceOAuthConfig>({
    clientId: '',
    clientSecret: '',
    instanceUrl: 'https://yourcompany.my.salesforce.com',
    redirectUri: 'https://localhost:8081/salesforce/callback',
    sandbox: false
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    status: 'disconnected'
  });

  // Mock Salesforce data
  const [mockData] = useState<MockSalesforceData>({
    accounts: [
      {
        id: 'ACC-001',
        name: 'Acme Corporation',
        type: 'Customer',
        industry: 'Technology',
        phone: '+1-555-0199',
        website: 'www.acme.com',
        employees: 5000,
        annualRevenue: 50000000
      },
      {
        id: 'ACC-002',
        name: 'Global Solutions Inc',
        type: 'Prospect',
        industry: 'Consulting',
        phone: '+1-555-0298',
        website: 'www.globalsolutions.com',
        employees: 1200,
        annualRevenue: 15000000
      }
    ],
    contacts: [
      {
        id: 'CON-001',
        name: 'John Smith',
        title: 'CEO',
        account: 'Acme Corporation',
        email: 'john.smith@acme.com',
        phone: '+1-555-0199',
        lastActivity: new Date(Date.now() - 86400000)
      },
      {
        id: 'CON-002',
        name: 'Sarah Johnson',
        title: 'CTO',
        account: 'Global Solutions Inc',
        email: 'sarah.johnson@globalsolutions.com',
        phone: '+1-555-0298',
        lastActivity: new Date(Date.now() - 172800000)
      }
    ],
    opportunities: [
      {
        id: 'OPP-001',
        name: 'Q1 Software Renewal',
        account: 'Acme Corporation',
        stage: 'Negotiation',
        amount: 250000,
        closeDate: new Date(Date.now() + 2592000000),
        probability: 75
      },
      {
        id: 'OPP-002',
        name: 'Digital Transformation Project',
        account: 'Global Solutions Inc',
        stage: 'Proposal',
        amount: 500000,
        closeDate: new Date(Date.now() + 5184000000),
        probability: 60
      }
    ],
    activities: [
      {
        id: 'ACT-001',
        type: 'Call',
        subject: 'Follow-up on renewal discussion',
        account: 'Acme Corporation',
        contact: 'John Smith',
        date: new Date(Date.now() - 3600000),
        duration: 30,
        status: 'Completed'
      },
      {
        id: 'ACT-002',
        type: 'Meeting',
        subject: 'Demo presentation',
        account: 'Global Solutions Inc',
        contact: 'Sarah Johnson',
        date: new Date(Date.now() + 86400000),
        status: 'Scheduled'
      }
    ]
  });

  const handleConfigChange = (field: keyof SalesforceOAuthConfig, value: string | boolean) => {
    setOauthConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const validateConfig = (): boolean => {
    return !!(oauthConfig.clientId && oauthConfig.clientSecret && oauthConfig.instanceUrl);
  };

  const handleConnect = async () => {
    if (!validateConfig()) {
      setConnectionStatus({
        isConnected: false,
        status: 'error',
        error: 'Please fill in all required Salesforce configuration fields'
      });
      return;
    }

    setIsConnecting(true);
    setConnectionStatus({
      isConnected: false,
      status: 'connecting'
    });

    // Simulate API connection
    setTimeout(() => {
      const success = Math.random() > 0.25; // 75% success rate for demo
      
      if (success) {
        setConnectionStatus({
          isConnected: true,
          status: 'connected',
          lastConnected: new Date()
        });
        setActiveTab('data'); // Auto-switch to data tab on successful connection
      } else {
        setConnectionStatus({
          isConnected: false,
          status: 'error',
          error: 'Failed to authenticate with Salesforce API. Please check your credentials and instance URL.'
        });
      }
      setIsConnecting(false);
    }, 2500);
  };

  const handleDisconnect = () => {
    setConnectionStatus({
      isConnected: false,
      status: 'disconnected'
    });
  };

  const runDiagnostics = () => {
    setActiveTab('diagnostics');
  };

  const formatCurrency = (amount: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getStatusIcon = (status: ConnectionStatus['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'connecting':
        return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <WifiOff className="h-5 w-5 text-gray-400" />;
    }
  };

  const getActivityStatusBadge = (status: MockActivity['status']) => {
    switch (status) {
      case 'Completed':
        return <Badge variant="secondary">Completed</Badge>;
      case 'Scheduled':
        return <Badge variant="default" className="bg-blue-500 text-white">Scheduled</Badge>;
      case 'In Progress':
        return <Badge variant="default" className="bg-orange-500 text-white">In Progress</Badge>;
    }
  };

  const getOpportunityStageColor = (stage: string) => {
    switch (stage) {
      case 'Negotiation':
        return 'bg-orange-100 text-orange-800';
      case 'Proposal':
        return 'bg-blue-100 text-blue-800';
      case 'Closed Won':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
            <Building className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-foreground">Salesforce Connector</h1>
            <p className="text-muted-foreground">
              Connect to Salesforce CRM to sync customer data and call records
            </p>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon(connectionStatus.status)}
            <span className="text-sm font-medium">
              {connectionStatus.status === 'connected' ? 'Connected' : 
               connectionStatus.status === 'connecting' ? 'Connecting...' :
               connectionStatus.status === 'error' ? 'Connection Error' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
          <TabsTrigger value="data" disabled={!connectionStatus.isConnected}>Salesforce Data</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Salesforce OAuth Configuration
              </CardTitle>
              <CardDescription>
                Configure your Salesforce connected app credentials to establish a secure connection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="sf-clientId">Consumer Key (Client ID) *</Label>
                  <Input
                    id="sf-clientId"
                    placeholder="Enter your Salesforce Consumer Key"
                    value={oauthConfig.clientId}
                    onChange={(e) => handleConfigChange('clientId', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sf-clientSecret">Consumer Secret *</Label>
                  <div className="relative">
                    <Input
                      id="sf-clientSecret"
                      type={showSecret ? "text" : "password"}
                      placeholder="Enter your Salesforce Consumer Secret"
                      value={oauthConfig.clientSecret}
                      onChange={(e) => handleConfigChange('clientSecret', e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                      onClick={() => setShowSecret(!showSecret)}
                    >
                      {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="sf-instanceUrl">Instance URL *</Label>
                <Input
                  id="sf-instanceUrl"
                  placeholder="https://yourcompany.my.salesforce.com"
                  value={oauthConfig.instanceUrl}
                  onChange={(e) => handleConfigChange('instanceUrl', e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="sf-redirectUri">Callback URL</Label>
                <Input
                  id="sf-redirectUri"
                  placeholder="https://your-app.com/salesforce/callback"
                  value={oauthConfig.redirectUri}
                  onChange={(e) => handleConfigChange('redirectUri', e.target.value)}
                />
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="sf-sandbox"
                  checked={oauthConfig.sandbox}
                  onChange={(e) => handleConfigChange('sandbox', e.target.checked)}
                  className="rounded border-gray-300"
                />
                <Label htmlFor="sf-sandbox">Use Sandbox Environment</Label>
              </div>

              {connectionStatus.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <span className="text-sm text-red-700">{connectionStatus.error}</span>
                  </div>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                {!connectionStatus.isConnected ? (
                  <Button 
                    onClick={handleConnect} 
                    disabled={isConnecting || !validateConfig()}
                    className="flex items-center gap-2"
                  >
                    {isConnecting ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Wifi className="h-4 w-4" />
                    )}
                    {isConnecting ? 'Connecting...' : 'Connect to Salesforce'}
                  </Button>
                ) : (
                  <Button 
                    onClick={handleDisconnect}
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <WifiOff className="h-4 w-4" />
                    Disconnect
                  </Button>
                )}
                
                <Button 
                  onClick={runDiagnostics}
                  variant="outline"
                  className="flex items-center gap-2"
                >
                  <Activity className="h-4 w-4" />
                  Run Diagnostics
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Diagnostics Tab */}
        <TabsContent value="diagnostics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Salesforce Connection Diagnostics
              </CardTitle>
              <CardDescription>
                Test and troubleshoot your Salesforce connection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold">Configuration Status</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>Consumer Key</span>
                      {oauthConfig.clientId ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>Consumer Secret</span>
                      {oauthConfig.clientSecret ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>Instance URL</span>
                      {oauthConfig.instanceUrl ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold">Connection Health</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>Salesforce API</span>
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>SSL Certificate</span>
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    </div>
                    <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span>Environment</span>
                      <Badge variant="outline">{oauthConfig.sandbox ? 'Sandbox' : 'Production'}</Badge>
                    </div>
                  </div>
                </div>
              </div>

              {connectionStatus.lastConnected && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-sm text-green-700">
                      Last successful connection: {connectionStatus.lastConnected.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Salesforce Data Tab */}
        <TabsContent value="data" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Accounts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building className="h-5 w-5" />
                  Accounts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.accounts.map((account) => (
                  <div key={account.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{account.name}</h3>
                      <Badge variant="outline">{account.type}</Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                      <div>Industry: {account.industry}</div>
                      <div>Employees: {account.employees.toLocaleString()}</div>
                      <div>Phone: {account.phone}</div>
                      <div>Revenue: {formatCurrency(account.annualRevenue)}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Opportunities */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Opportunities
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.opportunities.map((opp) => (
                  <div key={opp.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{opp.name}</h3>
                      <Badge className={getOpportunityStageColor(opp.stage)}>{opp.stage}</Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                      <div>Amount: {formatCurrency(opp.amount)}</div>
                      <div>Probability: {opp.probability}%</div>
                      <div>Account: {opp.account}</div>
                      <div>Close Date: {opp.closeDate.toLocaleDateString()}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Contacts */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Contacts
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.contacts.map((contact) => (
                  <div key={contact.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{contact.name}</h3>
                      <Badge variant="outline">{contact.title}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div>Account: {contact.account}</div>
                      <div>Email: {contact.email}</div>
                      <div>Phone: {contact.phone}</div>
                      <div>Last Activity: {contact.lastActivity.toLocaleDateString()}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Activities */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Recent Activities
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.activities.map((activity) => (
                  <div key={activity.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-muted-foreground" />
                        <span className="font-semibold">{activity.type}</span>
                      </div>
                      {getActivityStatusBadge(activity.status)}
                    </div>
                    <div className="text-sm">
                      <div className="font-medium">{activity.subject}</div>
                      <div className="text-muted-foreground space-y-1">
                        <div>Account: {activity.account}</div>
                        <div>Contact: {activity.contact}</div>
                        <div>Date: {activity.date.toLocaleString()}</div>
                        {activity.duration && <div>Duration: {activity.duration} minutes</div>}
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Salesforce Connection Logs
              </CardTitle>
              <CardDescription>
                View detailed logs and debugging information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-muted dark:bg-gray-900 text-foreground p-4 rounded-lg font-mono text-sm space-y-1">
                <div className="text-green-400">[{new Date().toISOString()}] INFO: Salesforce Connector initialized</div>
                <div className="text-blue-400">[{new Date().toISOString()}] DEBUG: OAuth configuration loaded</div>
                <div className="text-blue-400">[{new Date().toISOString()}] DEBUG: Environment: {oauthConfig.sandbox ? 'Sandbox' : 'Production'}</div>
                <div className="text-yellow-400">[{new Date().toISOString()}] WARN: Using mock data for demonstration</div>
                {connectionStatus.isConnected && (
                  <div className="text-green-400">[{new Date().toISOString()}] INFO: Successfully connected to Salesforce API</div>
                )}
                {connectionStatus.error && (
                  <div className="text-red-400">[{new Date().toISOString()}] ERROR: {connectionStatus.error}</div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SalesforceConnector;