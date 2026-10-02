# Application Configuration Specification

## API Endpoints Configuration

### REST API Configuration
```typescript
interface APIConfiguration {
  primary: {
    baseUrl: string;
    version: 'v1' | 'v2';
    timeout: number;
    retryPolicy: {
      maxRetries: number;
      retryDelay: number;
      retryOn: number[];
    };
  };
  
  endpoints: {
    // Alert Management
    alerts: {
      list: 'GET /api/v1/alerts';
      get: 'GET /api/v1/alerts/:id';
      create: 'POST /api/v1/alerts';
      update: 'PUT /api/v1/alerts/:id';
      delete: 'DELETE /api/v1/alerts/:id';
      acknowledge: 'POST /api/v1/alerts/:id/acknowledge';
      resolve: 'POST /api/v1/alerts/:id/resolve';
    };
    
    // Correlation
    correlation: {
      patterns: 'GET /api/v1/correlation/patterns';
      analyze: 'POST /api/v1/correlation/analyze';
      history: 'GET /api/v1/correlation/history';
    };
    
    // Network Analysis
    network: {
      status: 'GET /api/v1/network/status';
      topology: 'GET /api/v1/network/topology';
      metrics: 'GET /api/v1/network/metrics';
      sites: 'GET /api/v1/network/sites';
    };
    
    // Root Cause Analysis
    rootCause: {
      analyze: 'POST /api/v1/root-cause/analyze';
      suggestions: 'GET /api/v1/root-cause/suggestions';
      history: 'GET /api/v1/root-cause/history';
    };
    
    // User Management
    users: {
      profile: 'GET /api/v1/users/profile';
      update: 'PUT /api/v1/users/profile';
      preferences: 'GET /api/v1/users/preferences';
      teams: 'GET /api/v1/users/teams';
    };
  };
}
```

### API Service Implementation
```typescript
// services/apiService.ts
class APIService {
  private baseUrl: string;
  private headers: Headers;
  private interceptors: Interceptor[];
  
  constructor(config: APIConfiguration) {
    this.baseUrl = config.primary.baseUrl;
    this.setupInterceptors();
    this.setupHeaders();
  }
  
  private setupHeaders(): void {
    this.headers = new Headers({
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-API-Version': 'v1',
      'X-Client-Version': process.env.VITE_APP_VERSION
    });
  }
  
  private setupInterceptors(): void {
    // Request interceptor
    this.interceptors.push({
      request: (config) => {
        const token = this.getAuthToken();
        if (token) {
          config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
      }
    });
    
    // Response interceptor
    this.interceptors.push({
      response: (response) => {
        if (response.status === 401) {
          this.handleUnauthorized();
        }
        return response;
      }
    });
  }
  
  async request<T>(
    method: string,
    endpoint: string,
    data?: any,
    options?: RequestOptions
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      method,
      headers: this.headers,
      body: data ? JSON.stringify(data) : undefined,
      signal: AbortSignal.timeout(options?.timeout || 30000)
    };
    
    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        throw new APIError(response.status, await response.text());
      }
      return await response.json();
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }
}
```

### Environment-Specific API Configurations
```javascript
// config/api.config.js
const API_CONFIGS = {
  development: {
    baseUrl: 'http://localhost:8000',
    timeout: 60000,
    mockDelay: 500,
    logRequests: true
  },
  
  staging: {
    baseUrl: 'https://api-stage.alertengine.com',
    timeout: 30000,
    mockDelay: 0,
    logRequests: false
  },
  
  production: {
    baseUrl: 'https://api.alertengine.com',
    timeout: 15000,
    mockDelay: 0,
    logRequests: false
  }
};

export const getAPIConfig = () => {
  const env = import.meta.env.VITE_APP_ENV || 'development';
  return API_CONFIGS[env];
};
```

## MCP Server Configuration

### MCP Server Endpoints
```typescript
interface MCPConfiguration {
  server: {
    baseUrl: string;
    protocol: 'http' | 'https' | 'ws' | 'wss';
    port: number;
    path: '/mcp';
  };
  
  tools: {
    discovery: '/tools/list';
    execute: '/tools/call';
    batch: '/tools/batch';
    schema: '/tools/schema';
  };
  
  authentication: {
    type: 'bearer' | 'api-key' | 'oauth2';
    tokenEndpoint?: string;
    refreshEndpoint?: string;
  };
  
  options: {
    timeout: number;
    maxConcurrentCalls: number;
    retryOnFailure: boolean;
    cacheResults: boolean;
    compressionEnabled: boolean;
  };
}
```

### MCP Service Implementation
```typescript
// services/mcpService.ts
class MCPService {
  private config: MCPConfiguration;
  private websocket?: WebSocket;
  private toolCache: Map<string, ToolDefinition>;
  
  constructor(config: MCPConfiguration) {
    this.config = config;
    this.toolCache = new Map();
    this.initializeConnection();
  }
  
  private async initializeConnection(): Promise<void> {
    if (this.config.server.protocol.startsWith('ws')) {
      this.websocket = new WebSocket(
        `${this.config.server.protocol}://${this.config.server.baseUrl}:${this.config.server.port}${this.config.server.path}`
      );
      
      this.websocket.onopen = () => {
        console.log('MCP WebSocket connected');
        this.authenticate();
      };
      
      this.websocket.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
      };
    }
  }
  
  async discoverTools(): Promise<ToolDefinition[]> {
    const response = await this.request('GET', this.config.tools.discovery);
    const tools = response.tools;
    
    // Cache tools
    tools.forEach(tool => {
      this.toolCache.set(tool.name, tool);
    });
    
    return tools;
  }
  
  async executeTool(
    toolName: string,
    params: any,
    options?: ExecutionOptions
  ): Promise<ToolResult> {
    const tool = this.toolCache.get(toolName);
    if (!tool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    
    // Validate parameters
    this.validateParams(tool, params);
    
    // Execute tool
    const result = await this.request('POST', this.config.tools.execute, {
      tool: toolName,
      arguments: params,
      options
    });
    
    return result;
  }
  
  async batchExecute(
    requests: ToolRequest[]
  ): Promise<ToolResult[]> {
    return this.request('POST', this.config.tools.batch, { requests });
  }
}
```

### MCP Configuration by Environment
```javascript
// config/mcp.config.js
const MCP_CONFIGS = {
  development: {
    server: {
      baseUrl: 'localhost',
      protocol: 'ws',
      port: 8001,
      path: '/mcp'
    },
    options: {
      timeout: 60000,
      maxConcurrentCalls: 10,
      retryOnFailure: true,
      cacheResults: false
    }
  },
  
  staging: {
    server: {
      baseUrl: 'mcp-stage.alertengine.com',
      protocol: 'wss',
      port: 443,
      path: '/mcp'
    },
    options: {
      timeout: 30000,
      maxConcurrentCalls: 5,
      retryOnFailure: true,
      cacheResults: true
    }
  },
  
  production: {
    server: {
      baseUrl: 'mcp.alertengine.com',
      protocol: 'wss',
      port: 443,
      path: '/mcp'
    },
    options: {
      timeout: 15000,
      maxConcurrentCalls: 3,
      retryOnFailure: true,
      cacheResults: true
    }
  }
};
```

## Langflow Configuration

### Langflow Integration Settings
```typescript
interface LangflowConfiguration {
  server: {
    baseUrl: string;
    flowId: string;
    apiKey: string;
  };
  
  chat: {
    widget: {
      enabled: boolean;
      position: 'bottom-right' | 'bottom-left' | 'center';
      size: 'small' | 'medium' | 'large';
      theme: 'light' | 'dark' | 'auto';
    };
    
    behavior: {
      autoOpen: boolean;
      persistConversation: boolean;
      typingIndicator: boolean;
      soundNotifications: boolean;
      fileUpload: boolean;
    };
    
    customization: {
      primaryColor: string;
      fontFamily: string;
      borderRadius: string;
      welcomeMessage: string;
      placeholder: string;
      errorMessage: string;
    };
  };
  
  flows: {
    alertAnalysis: string;
    networkDiagnostics: string;
    incidentResponse: string;
    reportGeneration: string;
  };
  
  streaming: {
    enabled: boolean;
    chunkSize: number;
    timeout: number;
  };
}
```

### Langflow Service
```typescript
// services/langflowService.ts
class LangflowService {
  private config: LangflowConfiguration;
  private eventSource?: EventSource;
  
  constructor(config: LangflowConfiguration) {
    this.config = config;
  }
  
  async initializeChat(): Promise<void> {
    if (!this.config.chat.widget.enabled) {
      return;
    }
    
    // Load Langflow script
    const script = document.createElement('script');
    script.src = `${this.config.server.baseUrl}/embed.js`;
    script.async = true;
    script.onload = () => {
      this.configureWidget();
    };
    document.body.appendChild(script);
  }
  
  private configureWidget(): void {
    if (window.Langflow) {
      window.Langflow.init({
        flowId: this.config.server.flowId,
        apiKey: this.config.server.apiKey,
        ...this.config.chat.widget,
        ...this.config.chat.customization
      });
    }
  }
  
  async executeFlow(
    flowName: string,
    inputs: any,
    streaming: boolean = false
  ): Promise<any> {
    const flowId = this.config.flows[flowName];
    if (!flowId) {
      throw new Error(`Flow ${flowName} not configured`);
    }
    
    if (streaming && this.config.streaming.enabled) {
      return this.streamFlow(flowId, inputs);
    } else {
      return this.runFlow(flowId, inputs);
    }
  }
  
  private async runFlow(flowId: string, inputs: any): Promise<any> {
    const response = await fetch(
      `${this.config.server.baseUrl}/api/v1/run/${flowId}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': this.config.server.apiKey
        },
        body: JSON.stringify({ inputs })
      }
    );
    
    return response.json();
  }
  
  private streamFlow(flowId: string, inputs: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const url = `${this.config.server.baseUrl}/api/v1/stream/${flowId}`;
      this.eventSource = new EventSource(url);
      
      const chunks: any[] = [];
      
      this.eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        chunks.push(data);
        
        if (data.isComplete) {
          this.eventSource?.close();
          resolve(chunks);
        }
      };
      
      this.eventSource.onerror = (error) => {
        this.eventSource?.close();
        reject(error);
      };
      
      // Send inputs
      fetch(url, {
        method: 'POST',
        headers: {
          'x-api-key': this.config.server.apiKey
        },
        body: JSON.stringify({ inputs })
      });
    });
  }
}
```

### Langflow Environment Configurations
```javascript
// config/langflow.config.js
const LANGFLOW_CONFIGS = {
  development: {
    server: {
      baseUrl: 'http://localhost:7860',
      flowId: 'dev-flow-123',
      apiKey: 'dev-api-key'
    },
    chat: {
      widget: {
        enabled: true,
        position: 'bottom-right',
        theme: 'auto'
      }
    }
  },
  
  staging: {
    server: {
      baseUrl: 'https://langflow-stage.alertengine.com',
      flowId: 'stage-flow-456',
      apiKey: process.env.VITE_LANGFLOW_API_KEY_STAGE
    },
    chat: {
      widget: {
        enabled: true,
        position: 'bottom-right',
        theme: 'dark'
      }
    }
  },
  
  production: {
    server: {
      baseUrl: 'https://langflow.alertengine.com',
      flowId: 'prod-flow-789',
      apiKey: process.env.VITE_LANGFLOW_API_KEY_PROD
    },
    chat: {
      widget: {
        enabled: true,
        position: 'bottom-right',
        theme: 'auto'
      }
    }
  }
};
```

## Application Settings Management

### Settings Service
```typescript
// services/settingsService.ts
class SettingsService {
  private settings: Map<string, any>;
  private observers: Map<string, Function[]>;
  
  constructor() {
    this.settings = new Map();
    this.observers = new Map();
    this.loadSettings();
  }
  
  private loadSettings(): void {
    // Load from localStorage
    const stored = localStorage.getItem('app-settings');
    if (stored) {
      const parsed = JSON.parse(stored);
      Object.entries(parsed).forEach(([key, value]) => {
        this.settings.set(key, value);
      });
    }
    
    // Merge with defaults
    this.mergeDefaults();
  }
  
  private mergeDefaults(): void {
    const defaults = {
      theme: 'auto',
      language: 'en',
      timezone: 'UTC',
      dateFormat: 'MM/DD/YYYY',
      timeFormat: '12h',
      notifications: {
        desktop: true,
        sound: true,
        email: true
      },
      dashboard: {
        refreshInterval: 30000,
        chartType: 'line',
        showLegend: true
      }
    };
    
    Object.entries(defaults).forEach(([key, value]) => {
      if (!this.settings.has(key)) {
        this.settings.set(key, value);
      }
    });
  }
  
  get<T>(key: string, defaultValue?: T): T {
    return this.settings.get(key) ?? defaultValue;
  }
  
  set(key: string, value: any): void {
    this.settings.set(key, value);
    this.persist();
    this.notify(key, value);
  }
  
  subscribe(key: string, callback: Function): () => void {
    if (!this.observers.has(key)) {
      this.observers.set(key, []);
    }
    
    this.observers.get(key)!.push(callback);
    
    // Return unsubscribe function
    return () => {
      const callbacks = this.observers.get(key);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }
  
  private notify(key: string, value: any): void {
    const callbacks = this.observers.get(key);
    if (callbacks) {
      callbacks.forEach(cb => cb(value));
    }
  }
  
  private persist(): void {
    const obj = Object.fromEntries(this.settings);
    localStorage.setItem('app-settings', JSON.stringify(obj));
  }
}
```

## Configuration Validation

### Schema Validation
```typescript
// config/validation.ts
import { z } from 'zod';

const APIConfigSchema = z.object({
  baseUrl: z.string().url(),
  timeout: z.number().min(1000).max(60000),
  retryPolicy: z.object({
    maxRetries: z.number().min(0).max(10),
    retryDelay: z.number().min(100).max(5000),
    retryOn: z.array(z.number())
  })
});

const MCPConfigSchema = z.object({
  server: z.object({
    baseUrl: z.string(),
    protocol: z.enum(['http', 'https', 'ws', 'wss']),
    port: z.number().min(1).max(65535),
    path: z.string()
  }),
  options: z.object({
    timeout: z.number(),
    maxConcurrentCalls: z.number(),
    retryOnFailure: z.boolean(),
    cacheResults: z.boolean()
  })
});

const LangflowConfigSchema = z.object({
  server: z.object({
    baseUrl: z.string().url(),
    flowId: z.string(),
    apiKey: z.string()
  }),
  chat: z.object({
    widget: z.object({
      enabled: z.boolean(),
      position: z.enum(['bottom-right', 'bottom-left', 'center']),
      theme: z.enum(['light', 'dark', 'auto'])
    })
  })
});

export function validateConfig<T>(
  config: unknown,
  schema: z.ZodSchema<T>
): T {
  try {
    return schema.parse(config);
  } catch (error) {
    console.error('Configuration validation failed:', error);
    throw new Error('Invalid configuration');
  }
}
```

## Configuration Loading

### Bootstrap Configuration
```typescript
// config/bootstrap.ts
export async function bootstrapApplication(): Promise<AppConfig> {
  const env = import.meta.env.VITE_APP_ENV || 'development';
  
  // Load configuration based on environment
  const config: AppConfig = {
    environment: env,
    api: await loadAPIConfig(env),
    mcp: await loadMCPConfig(env),
    langflow: await loadLangflowConfig(env),
    features: await loadFeatureFlags(env),
    settings: await loadAppSettings(env)
  };
  
  // Validate configuration
  validateAppConfig(config);
  
  // Initialize services
  await initializeServices(config);
  
  return config;
}

async function loadAPIConfig(env: string): Promise<APIConfiguration> {
  const config = (await import(`./api/${env}.json`)).default;
  return validateConfig(config, APIConfigSchema);
}

async function initializeServices(config: AppConfig): Promise<void> {
  // Initialize API service
  window.apiService = new APIService(config.api);
  
  // Initialize MCP service
  window.mcpService = new MCPService(config.mcp);
  
  // Initialize Langflow service
  window.langflowService = new LangflowService(config.langflow);
  
  // Initialize settings service
  window.settingsService = new SettingsService();
}
```

## ✅ Configuration Checklist

### API Configuration
- [ ] Base URLs configured for all environments
- [ ] API versioning strategy defined
- [ ] Authentication headers configured
- [ ] Retry policies implemented
- [ ] Timeout values optimized
- [ ] Error handling configured

### MCP Server Configuration
- [ ] Server endpoints defined
- [ ] WebSocket connections configured
- [ ] Tool discovery working
- [ ] Authentication implemented
- [ ] Caching strategy defined
- [ ] Batch execution tested

### Langflow Configuration
- [ ] Flow IDs configured
- [ ] API keys secured
- [ ] Chat widget configured
- [ ] Streaming enabled where needed
- [ ] Custom flows defined
- [ ] Error messages customized

### General Configuration
- [ ] Environment detection working
- [ ] Configuration validation implemented
- [ ] Settings persistence working
- [ ] Feature flags configured
- [ ] Secrets management secure
- [ ] Configuration hot-reload (development)

### Security
- [ ] API keys encrypted
- [ ] Sensitive data not in code
- [ ] CORS configured properly
- [ ] Rate limiting implemented
- [ ] Authentication tokens secured
- [ ] Configuration access controlled

## 📝 Configuration Best Practices

1. **Environment Separation**: Never mix environment configurations
2. **Secrets Management**: Use environment variables or secret managers
3. **Validation**: Always validate configuration before use
4. **Defaults**: Provide sensible defaults for all settings
5. **Documentation**: Document all configuration options
6. **Version Control**: Don't commit sensitive configuration
7. **Hot Reload**: Support configuration changes without restart (development)
8. **Monitoring**: Log configuration load failures

---

