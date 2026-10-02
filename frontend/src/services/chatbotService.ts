export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

export interface ChatbotResponse {
  message: string;
  action?: {
    type: 'navigate' | 'discover' | 'show' | 'filter' | 'highlight' | 'querySelect';
    target: string;
    data?: any;
    params?: any;
  };
  metadata?: {
    confidence?: number;
    processingTime?: number;
  };
}

class ChatbotService {
  private apiKey: string;
  private baseUrl: string = 'https://api.openai.com/v1/chat/completions';
  private agentInstructions: string | null = null;
  private instructionsLoaded: boolean = false;

  constructor() {
    this.apiKey = import.meta.env.VITE_OPENAI_API_KEY;
    console.log('API Key loaded:', this.apiKey ? 'YES' : 'NO');
    console.log('API Key length:', this.apiKey ? this.apiKey.length : 0);
    // Load agent instructions on initialization
    this.loadAgentInstructions();
  }

  /**
   * Load agent instructions from markdown file
   */
  private async loadAgentInstructions(): Promise<void> {
    try {
      const response = await fetch('/agent-instructions.md');
      if (response.ok) {
        this.agentInstructions = await response.text();
        this.instructionsLoaded = true;
        console.log('📝 Agent instructions loaded successfully');
      } else {
        console.warn('⚠️ Could not load agent instructions from /agent-instructions.md');
      }
    } catch (error) {
      console.warn('⚠️ Error loading agent instructions:', error);
    }
  }

  /**
   * Get the current agent instructions
   */
  getAgentInstructions(): string | null {
    return this.agentInstructions;
  }

  /**
   * Update agent instructions dynamically
   */
  updateAgentInstructions(instructions: string): void {
    this.agentInstructions = instructions;
    this.instructionsLoaded = true;
    console.log('📝 Agent instructions updated dynamically');
  }

  /**
   * Reload agent instructions from file
   */
  async reloadInstructions(): Promise<void> {
    await this.loadAgentInstructions();
  }

  /**
   * Check if agent instructions are loaded
   */
  isInstructionsLoaded(): boolean {
    return this.instructionsLoaded;
  }

  /**
   * Send a message to ChatGPT and get response with potential actions
   */
  async sendMessage(message: string, context?: any): Promise<ChatbotResponse> {
    try {
      console.log('=== Starting API call ===');
      console.log('Message:', message);
      console.log('API Key available:', !!this.apiKey);
      
      if (!this.apiKey) {
        console.log('❌ No API key found, using fallback');
        throw new Error('OpenAI API key not configured');
      }

      console.log('✅ API key found, making OpenAI request...');
      console.log('Sending message to ChatGPT:', message);

      const systemPrompt = `You are a friendly and knowledgeable AI assistant for the Totogi Telco Insights application - a comprehensive call center analytics platform. You have a warm, conversational personality but keep responses concise and to the point.

PERSONALITY TRAITS:
- Friendly and approachable - use casual, warm language
- Enthusiastic about helping - show genuine interest in user needs
- Knowledgeable but humble - share expertise without being condescending
- Conversational - use natural language, contractions, and casual expressions
- Concise - keep responses short and direct, avoid unnecessary verbosity
- Empathetic - acknowledge user feelings and provide supportive responses

CONVERSATIONAL STYLE:
- Use contractions: "I'll", "you're", "that's", "we've"
- Include brief conversational elements: "Hey!", "Great!", "Perfect!"
- Show enthusiasm but keep it brief: "Awesome!", "That's cool!"
- Use natural transitions: "By the way", "Speaking of"
- Acknowledge user input briefly: "I see you want to...", "That's a great idea!"
- Keep responses concise - only elaborate when explaining complex features

You can control the entire application and help users navigate between different dashboard sections to analyze call center data.

AVAILABLE DASHBOARD SECTIONS:

1. MAIN DASHBOARD (/)
   - Navigate to: "home", "/", "dashboard", "main page", "overview"
   - Shows: Overall call center metrics, key performance indicators
   - Features: Call quality scores, revenue at risk, retention rates, deals needing attention

2. CALL CENTER ANALYTICS SECTIONS:
   Available through dashboard filters and queries:
   
   a) CHURN RISK ANALYSIS ("churn-risk")
      - Navigate to: "churn risk", "customer churn", "churn analysis", "retention"
      - Shows: Customers at risk of churning, retention strategies
   
   b) AGENT PERFORMANCE ("agent-performance") 
      - Navigate to: "agent performance", "agent metrics", "staff performance", "team performance"
      - Shows: Individual agent metrics, training needs, performance scores
   
   c) REVENUE AT RISK ("revenue-risk")
      - Navigate to: "revenue risk", "revenue at risk", "deals at risk", "financial risk"
      - Shows: Accounts requiring attention to prevent revenue loss
   
   d) CONVERSION FUNNEL ("conversion-funnel")
      - Navigate to: "conversion", "funnel", "sales funnel", "conversion rates"
      - Shows: Call-to-demo, demo-to-proposal, proposal-to-close rates
   
   e) TRAINING NEEDS ("training-needs")
      - Navigate to: "training", "training needs", "knowledge gaps", "skill development"
      - Shows: Agent knowledge gaps, recommended training priorities
   
   f) CALL QUALITY METRICS ("call-quality")
      - Navigate to: "call quality", "quality metrics", "call scores", "quality analysis"
      - Shows: Audio quality, sentiment analysis, conversation effectiveness
   
   g) DEALS AT RISK ("deals-at-risk")
      - Navigate to: "deals at risk", "high risk deals", "urgent deals", "deal alerts"
      - Shows: High-priority deals requiring immediate intervention

CURRENT CONTEXT: ${JSON.stringify(context)}

RESPONSE GUIDELINES:
- For dashboard section requests, use JSON format with action field and querySelect type
- For general questions, respond naturally and conversationally
- Keep responses friendly, concise, and helpful
- Show enthusiasm for helping users explore call center insights
- ONLY reference the dashboard sections listed above - no other pages exist

EXAMPLES:

For greetings: "Hey! 👋 I'm here to help you explore Totogi Telco Insights. What call center data would you like to analyze today?"

For dashboard sections: {"message": "Great! I'll show you the churn risk analysis.", "action": {"type": "querySelect", "target": "churn-risk"}}

For main dashboard: {"message": "Perfect! I'll take you to the main dashboard.", "action": {"type": "navigate", "target": "/"}}

For general questions: "Totogi Telco Insights helps you analyze call center performance, identify at-risk customers, and optimize agent training. It's really powerful for improving customer retention and revenue!"

For complex explanations: "Call quality analysis examines audio quality, sentiment, and conversation effectiveness to help improve customer interactions. Want me to show you the quality metrics dashboard?"`;

      const response = await fetch(this.baseUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({
          model: 'gpt-3.5-turbo',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: message }
          ],
          temperature: 0.7,
          max_tokens: 500
        })
      });

      console.log('OpenAI API response status:', response.status);
      console.log('Response OK:', response.ok);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('❌ OpenAI API error:', response.status, errorData);
        throw new Error(`OpenAI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
      }

      console.log('✅ OpenAI API call successful!');
      const data = await response.json();
      console.log('OpenAI API response data:', data);
      
      const assistantMessage = data.choices[0].message.content;
      console.log('Assistant message:', assistantMessage);

      // Try to parse JSON response - handle cases where AI adds extra text
      try {
        // First, try to extract JSON from the response - look for JSON anywhere in the text
        let jsonString = assistantMessage.trim();
        
        // Look for JSON object anywhere in the response
        const jsonStartIndex = jsonString.indexOf('{');
        if (jsonStartIndex !== -1) {
          // Find the matching closing brace
          let braceCount = 0;
          let endIndex = -1;
          
          for (let i = jsonStartIndex; i < jsonString.length; i++) {
            if (jsonString[i] === '{') braceCount++;
            if (jsonString[i] === '}') {
              braceCount--;
              if (braceCount === 0) {
                endIndex = i;
                break;
              }
            }
          }
          
          if (endIndex !== -1) {
            jsonString = jsonString.substring(jsonStartIndex, endIndex + 1);
          }
        }
        
        console.log('Attempting to parse JSON:', jsonString);
        const parsedResponse = JSON.parse(jsonString);
        console.log('✅ Successfully parsed JSON response:', parsedResponse);
        
        return {
          message: parsedResponse.message,
          action: parsedResponse.action,
          metadata: {
            confidence: 0.9,
            processingTime: Date.now()
          }
        };
      } catch (parseError) {
        console.log('❌ Failed to parse JSON, but API worked - using AI response directly');
        console.log('Parse error:', parseError);
        console.log('Raw response was:', assistantMessage);
        
        // API worked but JSON parsing failed - use the AI response directly
        return {
          message: assistantMessage,
          metadata: {
            confidence: 0.7,
            processingTime: Date.now()
          }
        };
      }

    } catch (error) {
      console.error('❌ API call failed completely, using fallback:', error);
      console.log('🔄 Switching to fallback response system (API unavailable)');
      return this.getFallbackResponse(message, context);
    }
  }

  /**
   * Fallback response logic for when OpenAI API fails
   */
  private getFallbackResponse(message: string, context?: any): ChatbotResponse {
    const lowerMessage = message.toLowerCase();
    const currentPath = context?.currentPath || '';

    // Handle general questions about Totogi Telco Insights
    if (lowerMessage.includes('what is totogi') || lowerMessage.includes('what is telco insights') || lowerMessage.includes('totogi telco')) {
      return {
        message: "Totogi Telco Insights is a comprehensive call center analytics platform. It helps you analyze call performance, identify at-risk customers, optimize agent training, and improve customer retention through AI-powered insights.",
        metadata: {
          confidence: 0.8,
          processingTime: Date.now()
        }
      };
    }

    // Handle questions about the application
    if (lowerMessage.includes('what can you do') || lowerMessage.includes('how can you help') || lowerMessage.includes('what are your capabilities')) {
      return {
        message: "I can help you navigate the Totogi Telco Insights dashboard! I can show you call center analytics, churn risk analysis, agent performance metrics, revenue insights, and much more. Just ask me to show you any section!",
        metadata: {
          confidence: 0.8,
          processingTime: Date.now()
        }
      };
    }

    // Handle questions about call center analytics
    if (lowerMessage.includes('what is call center') || lowerMessage.includes('how does analytics work') || lowerMessage.includes('what are analytics')) {
      return {
        message: "Call center analytics helps you understand customer interactions, agent performance, and business outcomes. You can see call quality scores, identify customers at risk of churning, track revenue opportunities, and optimize training programs.",
        metadata: {
          confidence: 0.8,
          processingTime: Date.now()
        }
      };
    }

    // Handle questions about specific analytics
    if (lowerMessage.includes('what is churn') || lowerMessage.includes('churn risk') || lowerMessage.includes('customer retention')) {
      return {
        message: "Churn risk analysis identifies customers likely to cancel their service. It helps you proactively reach out with retention strategies. Want me to show you the churn risk dashboard?",
        action: {
          type: 'querySelect',
          target: 'churn-risk'
        },
        metadata: {
          confidence: 0.8,
          processingTime: Date.now()
        }
      };
    }

    // Handle greeting questions
    if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
      return {
        message: "Hey! 👋 I'm here to help you explore Totogi Telco Insights. What call center data would you like to analyze today?",
        metadata: {
          confidence: 0.9,
          processingTime: Date.now()
        }
      };
    }

    // Handle "how are you" type questions
    if (lowerMessage.includes('how are you') || lowerMessage.includes('how do you do')) {
      return {
        message: "I'm doing great! Ready to help you dive into your call center analytics. What insights are you looking for?",
        metadata: {
          confidence: 0.9,
          processingTime: Date.now()
        }
      };
    }

    // Handle questions about available sections
    if (lowerMessage.includes('what sections') || lowerMessage.includes('what can i see') || lowerMessage.includes('what analytics')) {
      return {
        message: "You can explore churn risk analysis, agent performance, revenue at risk, conversion funnels, training needs, call quality metrics, and deals requiring attention. Which would you like to see?",
        metadata: {
          confidence: 0.8,
          processingTime: Date.now()
        }
      };
    }

    // Handle questions about the current page
    if (lowerMessage.includes('where am i') || lowerMessage.includes('what page is this') || lowerMessage.includes('what am i looking at')) {
      const currentPage = currentPath === '/' ? 'main dashboard' : 
                         currentPath === '/analytics' ? 'analytics page' :
                         currentPath.includes('customer') ? 'customer analytics' :
                         currentPath.includes('product') ? 'product analytics' :
                         'analytics section';
      return {
        message: `You're currently on the ${currentPage}. I can help you navigate to other sections or explain what you can do here.`,
        metadata: {
          confidence: 0.9,
          processingTime: Date.now()
        }
      };
    }

    // Navigation patterns for dashboard sections
    if (lowerMessage.includes('churn') || lowerMessage.includes('retention')) {
      return {
        message: "Great! I'll show you the churn risk analysis.",
        action: {
          type: 'querySelect',
          target: 'churn-risk'
        }
      };
    }

    if (lowerMessage.includes('agent') || lowerMessage.includes('performance') || lowerMessage.includes('staff')) {
      return {
        message: "Perfect! Let me show you the agent performance metrics.",
        action: {
          type: 'querySelect',
          target: 'agent-performance'
        }
      };
    }

    if (lowerMessage.includes('revenue') || lowerMessage.includes('financial') || lowerMessage.includes('money')) {
      return {
        message: "Sure! I'll show you the revenue at risk analysis.",
        action: {
          type: 'querySelect',
          target: 'revenue-risk'
        }
      };
    }

    if (lowerMessage.includes('conversion') || lowerMessage.includes('funnel') || lowerMessage.includes('sales')) {
      return {
        message: "Awesome! Let me show you the conversion funnel analysis.",
        action: {
          type: 'querySelect',
          target: 'conversion-funnel'
        }
      };
    }

    if (lowerMessage.includes('training') || lowerMessage.includes('knowledge') || lowerMessage.includes('skills')) {
      return {
        message: "Great! I'll show you the training needs analysis.",
        action: {
          type: 'querySelect',
          target: 'training-needs'
        }
      };
    }

    if (lowerMessage.includes('call quality') || lowerMessage.includes('quality') || lowerMessage.includes('call scores')) {
      return {
        message: "Perfect! Let me show you the call quality metrics.",
        action: {
          type: 'querySelect',
          target: 'call-quality'
        }
      };
    }

    if (lowerMessage.includes('deals') || lowerMessage.includes('urgent') || lowerMessage.includes('high risk')) {
      return {
        message: "Sure! I'll show you the deals at risk that need attention.",
        action: {
          type: 'querySelect',
          target: 'deals-at-risk'
        }
      };
    }

    // Navigation patterns for main pages
    if (lowerMessage.includes('home') || lowerMessage.includes('main') || lowerMessage.includes('dashboard')) {
      return {
        message: "Hey! I'll take you to the main dashboard.",
        action: {
          type: 'navigate',
          target: '/'
        }
      };
    }

    // Default response for unrecognized questions
    return {
      message: "That's an interesting question! I'm here to help you navigate Totogi Telco Insights. I can show you call center analytics sections like churn risk, agent performance, revenue at risk, conversion funnel, training needs, call quality, and deals at risk. What would you like to explore?",
      metadata: {
        confidence: 0.5,
        processingTime: Date.now()
      }
    };
  }

  /**
   * Get conversation history (for future implementation)
   */
  async getConversationHistory(): Promise<ChatMessage[]> {
    // TODO: Implement conversation history retrieval
    return [];
  }

  /**
   * Clear conversation history (for future implementation)
   */
  async clearConversationHistory(): Promise<void> {
    // TODO: Implement conversation history clearing
    console.log('Clearing conversation history');
  }

  /**
   * Initialize the chatbot with specific context
   * @param context - Initial context for the AI agent
   */
  async initialize(context?: any): Promise<void> {
    try {
      // TODO: Initialize Langflow agent with context
      console.log('Initializing chatbot with context:', context);
    } catch (error) {
      console.error('Error initializing chatbot:', error);
    }
  }

  /**
   * Get suggested questions based on current context
   */
  async getSuggestedQuestions(): Promise<string[]> {
    return [
      "Show me the main dashboard",
      "Take me to churn risk analysis",
      "I want to see agent performance metrics",
      "Show me revenue at risk",
      "Display the conversion funnel",
      "Show training needs analysis",
      "Take me to call quality metrics",
      "Show me deals at risk"
    ];
  }
}

// Export singleton instance
export const chatbotService = new ChatbotService(); 