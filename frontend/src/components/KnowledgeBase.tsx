import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { 
  Upload, 
  FileText, 
  Search, 
  Brain, 
  Zap, 
  Database,
  CheckCircle,
  AlertCircle,
  Clock,
  Trash2,
  Download,
  Eye
} from 'lucide-react';

interface UploadedDocument {
  id: string;
  name: string;
  size: string;
  type: string;
  uploadDate: Date;
  indexed: boolean;
  vectorCount: number;
}

interface QueryResult {
  id: string;
  content: string;
  similarity: number;
  source: string;
  metadata: any;
}

interface KnowledgeQuery {
  id: string;
  query: string;
  timestamp: Date;
  results: QueryResult[];
  responseTime: number;
}

const KnowledgeBase: React.FC = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocument[]>([
    {
      id: '1',
      name: 'Call Center Training Manual.pdf',
      size: '2.4 MB',
      type: 'PDF',
      uploadDate: new Date('2024-01-15'),
      indexed: true,
      vectorCount: 1247
    },
    {
      id: '2',
      name: 'Customer Service Scripts.docx',
      size: '850 KB',
      type: 'DOCX',
      uploadDate: new Date('2024-01-14'),
      indexed: true,
      vectorCount: 543
    },
    {
      id: '3',
      name: 'Product Knowledge Base.txt',
      size: '1.1 MB',
      type: 'TXT',
      uploadDate: new Date('2024-01-13'),
      indexed: false,
      vectorCount: 0
    }
  ]);

  const [indexingConfig, setIndexingConfig] = useState({
    chunkSize: '1000',
    overlap: '200',
    embeddingModel: 'text-embedding-ada-002',
    vectorDimensions: '1536'
  });

  const [queryText, setQueryText] = useState('');
  const [queryHistory, setQueryHistory] = useState<KnowledgeQuery[]>([
    {
      id: '1',
      query: 'How to handle customer complaints?',
      timestamp: new Date('2024-01-15T10:30:00'),
      responseTime: 245,
      results: [
        {
          id: '1',
          content: 'When handling customer complaints, first listen actively to understand the issue completely. Acknowledge their frustration and show empathy...',
          similarity: 0.92,
          source: 'Call Center Training Manual.pdf',
          metadata: { page: 23, section: 'Complaint Resolution' }
        },
        {
          id: '2',
          content: 'Step-by-step complaint resolution process: 1. Listen without interrupting 2. Ask clarifying questions 3. Apologize for the inconvenience...',
          similarity: 0.87,
          source: 'Customer Service Scripts.docx',
          metadata: { section: 'Complaints', template: 'Script-A' }
        }
      ]
    }
  ]);

  const [suggestions] = useState([
    'How to improve customer satisfaction scores?',
    'What are the best practices for call escalation?',
    'How to handle technical support requests?',
    'What information should be collected during initial contact?',
    'How to manage difficult customers effectively?'
  ]);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      Array.from(files).forEach(file => {
        const newDoc: UploadedDocument = {
          id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
          name: file.name,
          size: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
          type: file.name.split('.').pop()?.toUpperCase() || 'Unknown',
          uploadDate: new Date(),
          indexed: false,
          vectorCount: 0
        };
        setUploadedDocs(prev => [...prev, newDoc]);
      });
    }
  };

  const handleIndexDocument = (docId: string) => {
    setUploadedDocs(prev => prev.map(doc => 
      doc.id === docId 
        ? { ...doc, indexed: true, vectorCount: Math.floor(Math.random() * 1000) + 200 }
        : doc
    ));
  };

  const handleQuery = () => {
    if (!queryText.trim()) return;
    
    // Simulate query processing
    const mockResults: QueryResult[] = [
      {
        id: '1',
        content: `Based on your query "${queryText}", here are the most relevant knowledge base entries. This content provides comprehensive guidance and best practices...`,
        similarity: 0.94,
        source: uploadedDocs[0]?.name || 'Knowledge Base',
        metadata: { confidence: 'high', section: 'Guidelines' }
      },
      {
        id: '2',
        content: `Additional context related to "${queryText}" can be found in our training materials. This includes step-by-step procedures and examples...`,
        similarity: 0.81,
        source: uploadedDocs[1]?.name || 'Training Materials',
        metadata: { confidence: 'medium', section: 'Procedures' }
      }
    ];

    const newQuery: KnowledgeQuery = {
      id: Date.now().toString(),
      query: queryText,
      timestamp: new Date(),
      results: mockResults,
      responseTime: Math.floor(Math.random() * 500) + 100
    };

    setQueryHistory(prev => [newQuery, ...prev]);
    setQueryText('');
  };

  const handleDeleteDocument = (docId: string) => {
    setUploadedDocs(prev => prev.filter(doc => doc.id !== docId));
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <Brain className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">KnowledgeBase</h1>
            <p className="text-muted-foreground">
              Upload documents, create vector indexes, and test AI-powered knowledge queries
            </p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload">Document Upload</TabsTrigger>
          <TabsTrigger value="indexing">Vector Indexing</TabsTrigger>
          <TabsTrigger value="query">Query Testing</TabsTrigger>
          <TabsTrigger value="suggestions">AI Suggestions</TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Document Upload
              </CardTitle>
              <CardDescription>
                Upload documents and content files for knowledge base indexing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center space-y-2">
                <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                <div>
                  <p className="text-sm font-medium">Drop files here or click to upload</p>
                  <p className="text-xs text-muted-foreground">
                    Supports PDF, DOCX, TXT, MD files up to 10MB
                  </p>
                </div>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt,.md"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <Button asChild variant="outline">
                  <label htmlFor="file-upload" className="cursor-pointer">
                    Choose Files
                  </label>
                </Button>
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium">Uploaded Documents</h3>
                <ScrollArea className="h-64 border rounded-md">
                  <div className="p-4 space-y-3">
                    {uploadedDocs.map((doc) => (
                      <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <FileText className="h-8 w-8 text-primary" />
                          <div>
                            <p className="text-sm font-medium">{doc.name}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              <span>{doc.type}</span>
                              <span>•</span>
                              <span>{doc.size}</span>
                              <span>•</span>
                              <span>{doc.uploadDate.toLocaleDateString()}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {doc.indexed ? (
                            <Badge variant="default" className="gap-1">
                              <CheckCircle className="h-3 w-3" />
                              Indexed ({doc.vectorCount} vectors)
                            </Badge>
                          ) : (
                            <Badge variant="secondary" className="gap-1">
                              <Clock className="h-3 w-3" />
                              Pending
                            </Badge>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteDocument(doc.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="indexing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Vector Indexing Configuration
              </CardTitle>
              <CardDescription>
                Configure vector database settings and manage document indexing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="chunkSize">Chunk Size</Label>
                  <Input
                    id="chunkSize"
                    value={indexingConfig.chunkSize}
                    onChange={(e) => setIndexingConfig(prev => ({ ...prev, chunkSize: e.target.value }))}
                    placeholder="1000"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="overlap">Overlap</Label>
                  <Input
                    id="overlap"
                    value={indexingConfig.overlap}
                    onChange={(e) => setIndexingConfig(prev => ({ ...prev, overlap: e.target.value }))}
                    placeholder="200"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="embeddingModel">Embedding Model</Label>
                  <Input
                    id="embeddingModel"
                    value={indexingConfig.embeddingModel}
                    onChange={(e) => setIndexingConfig(prev => ({ ...prev, embeddingModel: e.target.value }))}
                    placeholder="text-embedding-ada-002"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vectorDimensions">Vector Dimensions</Label>
                  <Input
                    id="vectorDimensions"
                    value={indexingConfig.vectorDimensions}
                    onChange={(e) => setIndexingConfig(prev => ({ ...prev, vectorDimensions: e.target.value }))}
                    placeholder="1536"
                  />
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <h3 className="text-sm font-medium">Document Indexing Status</h3>
                {uploadedDocs.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5" />
                      <div>
                        <p className="text-sm font-medium">{doc.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.indexed ? `${doc.vectorCount} vectors indexed` : 'Not indexed'}
                        </p>
                      </div>
                    </div>
                    {!doc.indexed && (
                      <Button
                        size="sm"
                        onClick={() => handleIndexDocument(doc.id)}
                      >
                        <Database className="h-4 w-4 mr-2" />
                        Index Document
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Knowledge Base Query Testing
              </CardTitle>
              <CardDescription>
                Test queries against your indexed knowledge base and view results
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Textarea
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder="Enter your knowledge base query..."
                  className="flex-1"
                  rows={3}
                />
                <Button onClick={handleQuery} className="self-end">
                  <Search className="h-4 w-4 mr-2" />
                  Query
                </Button>
              </div>

              <Separator />

              <div className="space-y-3">
                <h3 className="text-sm font-medium">Query Results & History</h3>
                <ScrollArea className="h-96 border rounded-md">
                  <div className="p-4 space-y-4">
                    {queryHistory.map((query) => (
                      <div key={query.id} className="border rounded-lg p-4 space-y-3">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm">{query.query}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {query.responseTime}ms
                          </div>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {query.timestamp.toLocaleString()}
                        </p>
                        
                        <div className="space-y-2">
                          {query.results.map((result) => (
                            <div key={result.id} className="bg-muted/50 rounded-md p-3 space-y-2">
                              <div className="flex items-center justify-between">
                                <Badge variant="outline" className="text-xs">
                                  {(result.similarity * 100).toFixed(1)}% match
                                </Badge>
                                <p className="text-xs text-muted-foreground">{result.source}</p>
                              </div>
                              <p className="text-sm">{result.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="suggestions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                AI-Powered Suggestions
              </CardTitle>
              <CardDescription>
                Get intelligent query suggestions based on your knowledge base content
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3">
                <h3 className="text-sm font-medium">Suggested Queries</h3>
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                    onClick={() => setQueryText(suggestion)}
                  >
                    <p className="text-sm">{suggestion}</p>
                    <Button variant="ghost" size="sm">
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>

              <Separator />

              <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-primary" />
                  <h4 className="text-sm font-medium">Knowledge Base Statistics</h4>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-semibold text-primary">
                      {uploadedDocs.filter(doc => doc.indexed).length}
                    </p>
                    <p className="text-xs text-muted-foreground">Indexed Documents</p>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-primary">
                      {uploadedDocs.reduce((sum, doc) => sum + doc.vectorCount, 0).toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">Vector Embeddings</p>
                  </div>
                  <div>
                    <p className="text-2xl font-semibold text-primary">{queryHistory.length}</p>
                    <p className="text-xs text-muted-foreground">Queries Processed</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default KnowledgeBase;