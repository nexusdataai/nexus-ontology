import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  AlertCircle,
  CheckCircle,
  Timer,
  Clock,
  Play,
  Settings,
  RefreshCw,
  Eye,
  EyeOff,
  Wifi,
  WifiOff,
  Activity,
  Calendar,
  PlayCircle,
  PauseCircle,
  StopCircle,
  TestTube,
  Zap,
  AlertTriangle,
  Info,
  Server
} from 'lucide-react';

interface LambdaConfig {
  apiUrl: string;
  httpMethod: string;
  timeout: number;
  retryCount: number;
  apiHeaders: string;
  apiPayload: string;
  apiToken: string;
  langflowApiKey: string;
  customUserAgent: string;
}

interface ScheduleConfig {
  enabled: boolean;
  cronExpression: string;
  preset: string;
  timezone: string;
}

interface ConnectionStatus {
  isConnected: boolean;
  status: 'connected' | 'disconnected' | 'error' | 'testing';
  lastTest?: Date;
  lastExecution?: Date;
}

interface TestResult {
  success: boolean;
  statusCode?: number;
  responseTime?: number;
  error?: string;
  response?: any;
  timestamp: Date;
}

interface ScheduleExecution {
  id: string;
  timestamp: Date;
  status: 'success' | 'failed' | 'running';
  duration?: number;
  statusCode?: number;
  error?: string;
}

const BSSStudioConnector: React.FC = () => {
  const [activeTab, setActiveTab] = useState('config');
  const [showSecrets, setShowSecrets] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  
  const [lambdaConfig, setLambdaConfig] = useState<LambdaConfig>({
    apiUrl: '',
    httpMethod: 'GET',
    timeout: 30,
    retryCount: 3,
    apiHeaders: '{}',
    apiPayload: '{}',
    apiToken: '',
    langflowApiKey: '',
    customUserAgent: 'BSS-Studio-Connector/1.0'
  });

  const [scheduleConfig, setScheduleConfig] = useState<ScheduleConfig>({
    enabled: false,
    cronExpression: '0 */5 * * * *',
    preset: '5min',
    timezone: 'UTC'
  });

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    isConnected: false,
    status: 'disconnected'
  });

  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // Mock execution history
  const [executionHistory] = useState<ScheduleExecution[]>([
    {
      id: '1',
      timestamp: new Date(Date.now() - 300000),
      status: 'success',
      duration: 1250,
      statusCode: 200
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 600000),
      status: 'success',
      duration: 980,
      statusCode: 200
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 900000),
      status: 'failed',
      duration: 30000,
      error: 'Request timeout'
    }
  ]);

  const cronPresets = [
    { value: '5min', label: 'Every 5 minutes', cron: '0 */5 * * * *' },
    { value: '10min', label: 'Every 10 minutes', cron: '0 */10 * * * *' },
    { value: '15min', label: 'Every 15 minutes', cron: '0 */15 * * * *' },
    { value: '30min', label: 'Every 30 minutes', cron: '0 */30 * * * *' },
    { value: '1hour', label: 'Every hour', cron: '0 0 * * * *' },
    { value: '6hours', label: 'Every 6 hours', cron: '0 0 */6 * * *' },
    { value: 'daily', label: 'Daily at midnight', cron: '0 0 0 * * *' },
    { value: 'custom', label: 'Custom expression', cron: '' }
  ];

  const handleLambdaConfigChange = (field: keyof LambdaConfig, value: string | number) => {
    setLambdaConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleScheduleConfigChange = (field: keyof ScheduleConfig, value: string | boolean) => {
    setScheduleConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handlePresetChange = (preset: string) => {
    const presetConfig = cronPresets.find(p => p.value === preset);
    if (presetConfig) {
      setScheduleConfig(prev => ({
        ...prev,
        preset,
        cronExpression: presetConfig.cron || prev.cronExpression
      }));
    }
  };

  const validateConfig = (): boolean => {
    return !!(lambdaConfig.apiUrl && lambdaConfig.httpMethod);
  };

  const validateJSON = (jsonString: string): boolean => {
    try {
      JSON.parse(jsonString);
      return true;
    } catch {
      return false;
    }
  };

  const handleTestInvocation = async () => {
    if (!validateConfig()) {
      setTestResult({
        success: false,
        error: 'Please configure API URL and HTTP method',
        timestamp: new Date()
      });
      return;
    }

    setIsTesting(true);
    setConnectionStatus(prev => ({ ...prev, status: 'testing' }));

    try {
      // Simulate API test call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Mock successful response
      const mockResult: TestResult = {
        success: true,
        statusCode: 200,
        responseTime: 1250,
        response: {
          message: 'API call completed successfully',
          timestamp: new Date().toISOString(),
          api_url: lambdaConfig.apiUrl,
          method: lambdaConfig.httpMethod,
          status_code: 200
        },
        timestamp: new Date()
      };

      setTestResult(mockResult);
      setConnectionStatus(prev => ({
        ...prev,
        status: 'connected',
        isConnected: true,
        lastTest: new Date()
      }));
    } catch (error) {
      const errorResult: TestResult = {
        success: false,
        error: 'Connection failed: Network timeout',
        timestamp: new Date()
      };
      
      setTestResult(errorResult);
      setConnectionStatus(prev => ({ ...prev, status: 'error' }));
    } finally {
      setIsTesting(false);
    }
  };

  const handleConnect = async () => {
    if (!validateConfig()) return;

    setIsConnecting(true);
    setConnectionStatus(prev => ({ ...prev, status: 'testing' }));

    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      setConnectionStatus({
        isConnected: true,
        status: 'connected',
        lastTest: new Date()
      });
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, status: 'error' }));
    } finally {
      setIsConnecting(false);
    }
  };

  const formatDuration = (ms: number): string => {
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'disconnected':
        return <WifiOff className="h-4 w-4 text-gray-400" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'testing':
        return <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />;
      default:
        return <WifiOff className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected': return 'Connected';
      case 'disconnected': return 'Disconnected';
      case 'error': return 'Error';
      case 'testing': return 'Testing...';
      default: return 'Disconnected';
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-violet-600 rounded-lg flex items-center justify-center">
            <Timer className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-foreground">Langflow Connector</h1>
            <p className="text-muted-foreground">Schedule BSS Flow jobs and monitor executions</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {getStatusIcon(connectionStatus.status)}
          <span className={`text-sm font-medium ${
            connectionStatus.status === 'connected' ? 'text-green-600' :
            connectionStatus.status === 'error' ? 'text-red-600' :
            connectionStatus.status === 'testing' ? 'text-blue-600' :
            'text-gray-500'
          }`}>
            {getStatusText(connectionStatus.status)}
          </span>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="schedule">Scheduling</TabsTrigger>
          <TabsTrigger value="test">Test Invocation</TabsTrigger>
          <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
          <TabsTrigger value="logs">Execution Logs</TabsTrigger>
        </TabsList>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Lambda Function Configuration
              </CardTitle>
              <CardDescription>
                Configure the AWS Lambda function parameters for BSS Flow API calls
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="apiUrl">API URL *</Label>
                  <Input
                    id="apiUrl"
                    placeholder="https://api.example.com/bss-flow"
                    value={lambdaConfig.apiUrl}
                    onChange={(e) => handleLambdaConfigChange('apiUrl', e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="httpMethod">HTTP Method</Label>
                  <Select 
                    value={lambdaConfig.httpMethod} 
                    onValueChange={(value) => handleLambdaConfigChange('httpMethod', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="GET">GET</SelectItem>
                      <SelectItem value="POST">POST</SelectItem>
                      <SelectItem value="PUT">PUT</SelectItem>
                      <SelectItem value="DELETE">DELETE</SelectItem>
                      <SelectItem value="PATCH">PATCH</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="timeout">Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min="1"
                    max="900"
                    value={lambdaConfig.timeout}
                    onChange={(e) => handleLambdaConfigChange('timeout', parseInt(e.target.value) || 30)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="retryCount">Retry Count</Label>
                  <Input
                    id="retryCount"
                    type="number"
                    min="0"
                    max="10"
                    value={lambdaConfig.retryCount}
                    onChange={(e) => handleLambdaConfigChange('retryCount', parseInt(e.target.value) || 3)}
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Authentication & Headers</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSecrets(!showSecrets)}
                  >
                    {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    {showSecrets ? 'Hide' : 'Show'}
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="apiToken">API Bearer Token</Label>
                    <Input
                      id="apiToken"
                      type={showSecrets ? "text" : "password"}
                      placeholder="Bearer token for authentication"
                      value={lambdaConfig.apiToken}
                      onChange={(e) => handleLambdaConfigChange('apiToken', e.target.value)}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="langflowApiKey">Langflow API Key</Label>
                    <Input
                      id="langflowApiKey"
                      type={showSecrets ? "text" : "password"}
                      placeholder="x-api-key for Langflow"
                      value={lambdaConfig.langflowApiKey}
                      onChange={(e) => handleLambdaConfigChange('langflowApiKey', e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="customUserAgent">Custom User-Agent</Label>
                  <Input
                    id="customUserAgent"
                    placeholder="Custom User-Agent header"
                    value={lambdaConfig.customUserAgent}
                    onChange={(e) => handleLambdaConfigChange('customUserAgent', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="apiHeaders">Additional Headers (JSON)</Label>
                  <Textarea
                    id="apiHeaders"
                    placeholder='{"Content-Type": "application/json", "X-Custom-Header": "value"}'
                    value={lambdaConfig.apiHeaders}
                    onChange={(e) => handleLambdaConfigChange('apiHeaders', e.target.value)}
                    className={!validateJSON(lambdaConfig.apiHeaders) ? 'border-red-500' : ''}
                  />
                  {!validateJSON(lambdaConfig.apiHeaders) && (
                    <p className="text-sm text-red-500">Invalid JSON format</p>
                  )}
                </div>

                {lambdaConfig.httpMethod !== 'GET' && (
                  <div className="space-y-2">
                    <Label htmlFor="apiPayload">Request Payload (JSON)</Label>
                    <Textarea
                      id="apiPayload"
                      placeholder='{"key": "value", "data": "payload"}'
                      value={lambdaConfig.apiPayload}
                      onChange={(e) => handleLambdaConfigChange('apiPayload', e.target.value)}
                      className={!validateJSON(lambdaConfig.apiPayload) ? 'border-red-500' : ''}
                    />
                    {!validateJSON(lambdaConfig.apiPayload) && (
                      <p className="text-sm text-red-500">Invalid JSON format</p>
                    )}
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button 
                  onClick={handleConnect} 
                  disabled={!validateConfig() || isConnecting}
                  className="flex items-center gap-2"
                >
                  {isConnecting ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Zap className="h-4 w-4" />
                  )}
                  {isConnecting ? 'Connecting...' : 'Save & Connect'}
                </Button>
                
                <Button 
                  variant="outline" 
                  onClick={handleTestInvocation}
                  disabled={!validateConfig() || isTesting}
                  className="flex items-center gap-2"
                >
                  {isTesting ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube className="h-4 w-4" />
                  )}
                  {isTesting ? 'Testing...' : 'Test Connection'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scheduling Tab */}
        <TabsContent value="schedule" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Job Scheduling Configuration
              </CardTitle>
              <CardDescription>
                Set up automated schedules for BSS Flow job executions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-1">
                  <Label className="text-base font-medium">Enable Scheduled Executions</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically execute BSS Flow jobs based on the configured schedule
                  </p>
                </div>
                <Switch
                  checked={scheduleConfig.enabled}
                  onCheckedChange={(checked) => handleScheduleConfigChange('enabled', checked)}
                />
              </div>

              {scheduleConfig.enabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="preset">Schedule Preset</Label>
                    <Select value={scheduleConfig.preset} onValueChange={handlePresetChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {cronPresets.map((preset) => (
                          <SelectItem key={preset.value} value={preset.value}>
                            {preset.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="cronExpression">Cron Expression</Label>
                    <Input
                      id="cronExpression"
                      placeholder="0 */5 * * * *"
                      value={scheduleConfig.cronExpression}
                      onChange={(e) => handleScheduleConfigChange('cronExpression', e.target.value)}
                      disabled={scheduleConfig.preset !== 'custom'}
                    />
                    <p className="text-sm text-muted-foreground">
                      Format: seconds minutes hours day-of-month month day-of-week
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="timezone">Timezone</Label>
                    <Select 
                      value={scheduleConfig.timezone} 
                      onValueChange={(value) => handleScheduleConfigChange('timezone', value)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="UTC">UTC</SelectItem>
                        <SelectItem value="America/New_York">Eastern Time</SelectItem>
                        <SelectItem value="America/Chicago">Central Time</SelectItem>
                        <SelectItem value="America/Denver">Mountain Time</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                        <SelectItem value="Europe/London">London</SelectItem>
                        <SelectItem value="Europe/Paris">Paris</SelectItem>
                        <SelectItem value="Asia/Tokyo">Tokyo</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-blue-900">Schedule Information</p>
                        <p className="text-sm text-blue-700 mt-1">
                          Next execution: {scheduleConfig.preset === '5min' ? 'Every 5 minutes' : 
                          scheduleConfig.preset === '10min' ? 'Every 10 minutes' :
                          scheduleConfig.preset === 'custom' ? 'Based on custom expression' :
                          cronPresets.find(p => p.value === scheduleConfig.preset)?.label}
                        </p>
                        <p className="text-sm text-blue-700">
                          Timezone: {scheduleConfig.timezone}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      disabled={!connectionStatus.isConnected}
                      className="flex items-center gap-2"
                    >
                      <PlayCircle className="h-4 w-4" />
                      Deploy Schedule
                    </Button>
                    
                    <Button 
                      variant="outline"
                      className="flex items-center gap-2"
                    >
                      <PauseCircle className="h-4 w-4" />
                      Pause Schedule
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Test Invocation Tab */}
        <TabsContent value="test" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TestTube className="h-5 w-5" />
                Test BSS Flow Invocation
              </CardTitle>
              <CardDescription>
                Manually test your BSS Flow API configuration and view real-time diagnostics
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button 
                  onClick={handleTestInvocation}
                  disabled={!validateConfig() || isTesting}
                  className="flex items-center gap-2"
                >
                  {isTesting ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  {isTesting ? 'Testing...' : 'Run Test'}
                </Button>
              </div>

              {testResult && (
                <div className={`p-4 border rounded-lg ${
                  testResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-start gap-2">
                    {testResult.success ? (
                      <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <p className={`font-medium ${
                          testResult.success ? 'text-green-900' : 'text-red-900'
                        }`}>
                          {testResult.success ? 'Test Successful' : 'Test Failed'}
                        </p>
                        <span className="text-sm text-muted-foreground">
                          {testResult.timestamp.toLocaleString()}
                        </span>
                      </div>
                      
                      {testResult.success && (
                        <div className="mt-2 space-y-1">
                          <p className="text-sm text-green-700">
                            Status Code: {testResult.statusCode}
                          </p>
                          <p className="text-sm text-green-700">
                            Response Time: {formatDuration(testResult.responseTime!)}
                          </p>
                        </div>
                      )}
                      
                      {testResult.error && (
                        <p className="text-sm text-red-700 mt-2">{testResult.error}</p>
                      )}
                      
                      {testResult.response && (
                        <details className="mt-3">
                          <summary className="text-sm font-medium cursor-pointer">
                            View Response
                          </summary>
                          <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                            {JSON.stringify(testResult.response, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Diagnostics Tab */}
        <TabsContent value="diagnostics" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                System Diagnostics
              </CardTitle>
              <CardDescription>
                Monitor the health and performance of your Langflow Connector
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Connection Status</span>
                    {getStatusIcon(connectionStatus.status)}
                  </div>
                  <p className="text-2xl font-bold mt-2">
                    {getStatusText(connectionStatus.status)}
                  </p>
                  {connectionStatus.lastTest && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Last tested: {connectionStatus.lastTest.toLocaleString()}
                    </p>
                  )}
                </div>
                
                <div className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Schedule Status</span>
                    {scheduleConfig.enabled ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <PauseCircle className="h-4 w-4 text-gray-400" />
                    )}
                  </div>
                  <p className="text-2xl font-bold mt-2">
                    {scheduleConfig.enabled ? 'Active' : 'Inactive'}
                  </p>
                  {scheduleConfig.enabled && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {cronPresets.find(p => p.value === scheduleConfig.preset)?.label}
                    </p>
                  )}
                </div>
              </div>

              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-3">Configuration Summary</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">API Endpoint:</span>
                    <span className="font-mono">{lambdaConfig.apiUrl || 'Not configured'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">HTTP Method:</span>
                    <span>{lambdaConfig.httpMethod}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Timeout:</span>
                    <span>{lambdaConfig.timeout}s</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Retry Count:</span>
                    <span>{lambdaConfig.retryCount}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Authentication:</span>
                    <span>{lambdaConfig.apiToken || lambdaConfig.langflowApiKey ? 'Configured' : 'None'}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Execution Logs Tab */}
        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                Execution History
              </CardTitle>
              <CardDescription>
                View the history of scheduled BSS Flow job executions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {executionHistory.map((execution) => (
                  <div key={execution.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      {execution.status === 'success' ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : execution.status === 'failed' ? (
                        <AlertCircle className="h-4 w-4 text-red-500" />
                      ) : (
                        <RefreshCw className="h-4 w-4 text-blue-500 animate-spin" />
                      )}
                      
                      <div>
                        <p className="text-sm font-medium">
                          {execution.timestamp.toLocaleString()}
                        </p>
                        {execution.error && (
                          <p className="text-sm text-red-600">{execution.error}</p>
                        )}
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <Badge variant={
                        execution.status === 'success' ? 'default' :
                        execution.status === 'failed' ? 'destructive' : 'secondary'
                      }>
                        {execution.status}
                      </Badge>
                      {execution.duration && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {formatDuration(execution.duration)}
                        </p>
                      )}
                      {execution.statusCode && (
                        <p className="text-sm text-muted-foreground">
                          Status: {execution.statusCode}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default BSSStudioConnector;
