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
  Code2,
  Users,
  Video,
  Mail,
  Calendar,
  MessageSquare,
  Settings,
  RefreshCw,
  Eye,
  EyeOff,
  Wifi,
  WifiOff,
  Activity,
  Clock
} from 'lucide-react';

interface Office365OAuthConfig {
  applicationId: string;
  clientSecret: string;
  tenantId: string;
  redirectUri: string;
  scope: string;
}

interface ConnectionStatus {
  isConnected: boolean;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastConnected?: Date;
  error?: string;
}

interface MockOffice365Data {
  meetings: MockTeamsMeeting[];
  emails: MockEmail[];
  calendarEvents: MockCalendarEvent[];
  teamChannels: MockTeamChannel[];
}

interface MockTeamsMeeting {
  id: string;
  subject: string;
  organizer: string;
  startTime: Date;
  endTime: Date;
  attendees: number;
  duration: number;
  recordingAvailable: boolean;
  chatMessages: number;
  status: 'Scheduled' | 'In Progress' | 'Completed';
}

interface MockEmail {
  id: string;
  from: string;
  to: string[];
  subject: string;
  receivedDateTime: Date;
  importance: 'Low' | 'Normal' | 'High';
  hasAttachments: boolean;
  conversationId: string;
}

interface MockCalendarEvent {
  id: string;
  subject: string;
  organizer: string;
  start: Date;
  end: Date;
  attendees: string[];
  location: string;
  isOnlineMeeting: boolean;
}

interface MockTeamChannel {
  id: string;
  teamName: string;
  channelName: string;
  memberCount: number;
  messagesCount: number;
  lastActivity: Date;
  description: string;
}

const Office365Connector: React.FC = () => {
  const [activeTab, setActiveTab] = useState('config');
  const [showSecret, setShowSecret] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  
  const [oauthConfig, setOauthConfig] = useState<Office365OAuthConfig>({
    applicationId: '',
    clientSecret: '',
    tenantId: '',
    redirectUri: 'https://localhost:8081/office365/callback',
    scope: 'https://graph.microsoft.com/User.Read https://graph.microsoft.com/Mail.Read https://graph.microsoft.com/Calendars.Read https://graph.microsoft.com/OnlineMeetings.Read'
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    status: 'disconnected'
  });

  // Mock Office 365 data
  const [mockData] = useState<MockOffice365Data>({
    meetings: [
      {
        id: 'TM-001',
        subject: 'Weekly Product Review',
        organizer: 'alice.smith@company.com',
        startTime: new Date(Date.now() - 7200000),
        endTime: new Date(Date.now() - 3600000),
        attendees: 8,
        duration: 60,
        recordingAvailable: true,
        chatMessages: 24,
        status: 'Completed'
      },
      {
        id: 'TM-002',
        subject: 'Customer Onboarding Session',
        organizer: 'bob.jones@company.com',
        startTime: new Date(),
        endTime: new Date(Date.now() + 3600000),
        attendees: 12,
        duration: 60,
        recordingAvailable: false,
        chatMessages: 18,
        status: 'In Progress'
      },
      {
        id: 'TM-003',
        subject: 'Q4 Strategy Planning',
        organizer: 'carol.davis@company.com',
        startTime: new Date(Date.now() + 86400000),
        endTime: new Date(Date.now() + 90000000),
        attendees: 6,
        duration: 60,
        recordingAvailable: true,
        chatMessages: 0,
        status: 'Scheduled'
      }
    ],
    emails: [
      {
        id: 'EM-001',
        from: 'customer.support@clientcompany.com',
        to: ['support@company.com'],
        subject: 'Urgent: System Integration Issue',
        receivedDateTime: new Date(Date.now() - 1800000),
        importance: 'High',
        hasAttachments: true,
        conversationId: 'CONV-001'
      },
      {
        id: 'EM-002',
        from: 'newsletter@techupdate.com',
        to: ['team@company.com'],
        subject: 'Weekly Tech Newsletter - AI Trends',
        receivedDateTime: new Date(Date.now() - 86400000),
        importance: 'Normal',
        hasAttachments: false,
        conversationId: 'CONV-002'
      }
    ],
    calendarEvents: [
      {
        id: 'CAL-001',
        subject: 'Client Demo Preparation',
        organizer: 'demo.team@company.com',
        start: new Date(Date.now() + 3600000),
        end: new Date(Date.now() + 7200000),
        attendees: ['alice.smith@company.com', 'bob.jones@company.com'],
        location: 'Conference Room A',
        isOnlineMeeting: true
      },
      {
        id: 'CAL-002',
        subject: 'Vendor Meeting',
        organizer: 'procurement@company.com',
        start: new Date(Date.now() + 172800000),
        end: new Date(Date.now() + 176400000),
        attendees: ['procurement@company.com', 'vendor@suppliercompany.com'],
        location: 'Microsoft Teams Meeting',
        isOnlineMeeting: true
      }
    ],
    teamChannels: [
      {
        id: 'TC-001',
        teamName: 'Product Development',
        channelName: 'General',
        memberCount: 15,
        messagesCount: 342,
        lastActivity: new Date(Date.now() - 3600000),
        description: 'Main channel for product development discussions'
      },
      {
        id: 'TC-002',
        teamName: 'Customer Success',
        channelName: 'Support Cases',
        memberCount: 8,
        messagesCount: 156,
        lastActivity: new Date(Date.now() - 7200000),
        description: 'Channel for tracking and discussing customer support cases'
      }
    ]
  });

  const handleConfigChange = (field: keyof Office365OAuthConfig, value: string) => {
    setOauthConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const validateConfig = (): boolean => {
    return !!(oauthConfig.applicationId && oauthConfig.clientSecret && oauthConfig.tenantId);
  };

  const handleConnect = async () => {
    if (!validateConfig()) {
      setConnectionStatus({
        isConnected: false,
        status: 'error',
        error: 'Please fill in all required Office 365 configuration fields'
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
      const success = Math.random() > 0.2; // 80% success rate for demo
      
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
          error: 'Failed to authenticate with Microsoft Graph API. Please check your app registration and permissions.'
        });
      }
      setIsConnecting(false);
    }, 2000);
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

  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  const getStatusIcon = (status: ConnectionStatus['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-success" />;
      case 'connecting':
        return <RefreshCw className="h-5 w-5 text-primary animate-spin" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-destructive" />;
      default:
        return <WifiOff className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getMeetingStatusBadge = (status: MockTeamsMeeting['status']) => {
    switch (status) {
      case 'In Progress':
        return <Badge variant="default" className="bg-success text-white">Live</Badge>;
      case 'Completed':
        return <Badge variant="secondary">Completed</Badge>;
      case 'Scheduled':
        return <Badge variant="outline">Scheduled</Badge>;
    }
  };

  const getImportanceBadge = (importance: MockEmail['importance']) => {
    switch (importance) {
      case 'High':
        return <Badge variant="destructive">High</Badge>;
      case 'Normal':
        return <Badge variant="secondary">Normal</Badge>;
      case 'Low':
        return <Badge variant="outline">Low</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <Code2 className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-lg font-semibold text-foreground">Office 365 Connector</h1>
            <p className="text-muted-foreground">
              Integrate with Microsoft Office 365 and Teams for communication analytics
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
          <TabsTrigger value="data" disabled={!connectionStatus.isConnected}>Office 365 Data</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Microsoft App Registration
              </CardTitle>
              <CardDescription>
                Configure your Azure AD app registration to connect with Microsoft Graph API
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="o365-appId">Application (Client) ID *</Label>
                  <Input
                    id="o365-appId"
                    placeholder="Enter your Azure AD Application ID"
                    value={oauthConfig.applicationId}
                    onChange={(e) => handleConfigChange('applicationId', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="o365-clientSecret">Client Secret *</Label>
                  <div className="relative">
                    <Input
                      id="o365-clientSecret"
                      type={showSecret ? "text" : "password"}
                      placeholder="Enter your Azure AD Client Secret"
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
                <Label htmlFor="o365-tenantId">Directory (Tenant) ID *</Label>
                <Input
                  id="o365-tenantId"
                  placeholder="Enter your Azure AD Tenant ID"
                  value={oauthConfig.tenantId}
                  onChange={(e) => handleConfigChange('tenantId', e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="o365-redirectUri">Redirect URI</Label>
                <Input
                  id="o365-redirectUri"
                  placeholder="https://your-app.com/office365/callback"
                  value={oauthConfig.redirectUri}
                  onChange={(e) => handleConfigChange('redirectUri', e.target.value)}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="o365-scope">Permissions (Scope)</Label>
                <Input
                  id="o365-scope"
                  placeholder="User.Read Mail.Read Calendars.Read OnlineMeetings.Read"
                  value={oauthConfig.scope}
                  onChange={(e) => handleConfigChange('scope', e.target.value)}
                />
              </div>

              {connectionStatus.error && (
                <div className="p-3 bg-destructive/10 border border-destructive/25 rounded-md">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-destructive" />
                    <span className="text-sm text-destructive">{connectionStatus.error}</span>
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
                    {isConnecting ? 'Connecting...' : 'Connect to Office 365'}
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
                Office 365 Connection Diagnostics
              </CardTitle>
              <CardDescription>
                Test and troubleshoot your Microsoft Graph API connection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold">App Registration Status</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>Application ID</span>
                      {oauthConfig.applicationId ? (
                        <CheckCircle className="h-4 w-4 text-success" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      )}
                    </div>
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>Client Secret</span>
                      {oauthConfig.clientSecret ? (
                        <CheckCircle className="h-4 w-4 text-success" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      )}
                    </div>
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>Tenant ID</span>
                      {oauthConfig.tenantId ? (
                        <CheckCircle className="h-4 w-4 text-success" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold">Microsoft Graph API</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>Graph Endpoint</span>
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>SSL Certificate</span>
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                    <div className="flex items-center justify-between p-2 bg-surface-2 rounded">
                      <span>Azure AD Status</span>
                      <CheckCircle className="h-4 w-4 text-success" />
                    </div>
                  </div>
                </div>
              </div>

              {connectionStatus.lastConnected && (
                <div className="p-3 bg-success/10 border border-success/25 rounded-md">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-success" />
                    <span className="text-sm text-success">
                      Last successful connection: {connectionStatus.lastConnected.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Office 365 Data Tab */}
        <TabsContent value="data" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Teams Meetings */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Video className="h-5 w-5" />
                  Teams Meetings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.meetings.map((meeting) => (
                  <div key={meeting.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{meeting.subject}</h3>
                      {getMeetingStatusBadge(meeting.status)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                      <div>Organizer: {meeting.organizer}</div>
                      <div>Attendees: {meeting.attendees}</div>
                      <div>Duration: {formatDuration(meeting.duration)}</div>
                      <div>Chat Messages: {meeting.chatMessages}</div>
                      <div>Recording: {meeting.recordingAvailable ? 'Yes' : 'No'}</div>
                      <div>Time: {meeting.startTime.toLocaleTimeString()}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Emails */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  Recent Emails
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.emails.map((email) => (
                  <div key={email.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-sm">{email.subject}</h3>
                      {getImportanceBadge(email.importance)}
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div>From: {email.from}</div>
                      <div>To: {email.to.join(', ')}</div>
                      <div>Received: {email.receivedDateTime.toLocaleString()}</div>
                      <div className="flex items-center gap-2">
                        <span>Attachments: {email.hasAttachments ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Calendar Events */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Calendar Events
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.calendarEvents.map((event) => (
                  <div key={event.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{event.subject}</h3>
                      {event.isOnlineMeeting && (
                        <Badge variant="outline" className="text-primary">Online</Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div>Organizer: {event.organizer}</div>
                      <div>Start: {event.start.toLocaleString()}</div>
                      <div>End: {event.end.toLocaleString()}</div>
                      <div>Location: {event.location}</div>
                      <div>Attendees: {event.attendees.length}</div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Teams Channels */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Teams Channels
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {mockData.teamChannels.map((channel) => (
                  <div key={channel.id} className="border rounded-lg p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{channel.teamName}</h3>
                      <Badge variant="outline">{channel.channelName}</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground space-y-1">
                      <div>Members: {channel.memberCount}</div>
                      <div>Messages: {channel.messagesCount}</div>
                      <div>Last Activity: {channel.lastActivity.toLocaleString()}</div>
                      <div className="italic">{channel.description}</div>
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
                Office 365 Connection Logs
              </CardTitle>
              <CardDescription>
                View detailed logs and debugging information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-muted dark:bg-card text-foreground p-4 rounded-lg font-mono text-sm space-y-1">
                <div className="text-success">[{new Date().toISOString()}] INFO: Office 365 Connector initialized</div>
                <div className="text-primary">[{new Date().toISOString()}] DEBUG: Azure AD app registration loaded</div>
                <div className="text-primary">[{new Date().toISOString()}] DEBUG: Microsoft Graph API endpoint configured</div>
                <div className="text-warning">[{new Date().toISOString()}] WARN: Using mock data for demonstration</div>
                {connectionStatus.isConnected && (
                  <div className="text-success">[{new Date().toISOString()}] INFO: Successfully connected to Microsoft Graph API</div>
                )}
                {connectionStatus.error && (
                  <div className="text-destructive">[{new Date().toISOString()}] ERROR: {connectionStatus.error}</div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Office365Connector;