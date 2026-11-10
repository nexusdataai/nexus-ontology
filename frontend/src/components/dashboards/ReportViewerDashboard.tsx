import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { 
  FileText,
  Download,
  Printer,
  Share2,
  Eye,
  Calendar,
  Clock,
  Users,
  TrendingUp,
  BarChart3,
  RefreshCw,
  BookOpen,
  ChevronRight,
  Hash,
  Search,
  Bookmark,
  ExternalLink
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useRefresh } from '@/context/RefreshContext';

interface ReportViewerProps {
  className?: string;
}

interface ReportSection {
  id: string;
  title: string;
  level: number;
  line: number;
}

interface ReportMetadata {
  title: string;
  date: string;
  period: string;
  author: string;
  version: string;
  status: string;
  tags: string[];
}

const ReportViewerDashboard: React.FC<ReportViewerProps> = ({ className }) => {
  const [reportContent, setReportContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sections, setSections] = useState<ReportSection[]>([]);
  const [activeSection, setActiveSection] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [isTableOfContentsOpen, setIsTableOfContentsOpen] = useState(true);
  const { refreshTrigger } = useRefresh();

  useEffect(() => {
    loadReport();
  }, []);

  useEffect(() => {
    if (refreshTrigger > 0) {
      loadReport();
    }
  }, [refreshTrigger]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/results/report.md');
      if (!response.ok) {
        // Provide more specific error messages for common deployment issues
        if (response.status === 404) {
          throw new Error('Report file not found. Please ensure report.md is properly deployed to the results folder.');
        } else if (response.status === 403) {
          throw new Error('Access denied to report file. Please check CORS configuration.');
        } else {
          throw new Error(`Failed to fetch report: ${response.status} ${response.statusText}`);
        }
      }
      
      const content = await response.text();
      
      // Validate that we received actual markdown content, not HTML
      if (content.includes('<!DOCTYPE') || content.includes('<html')) {
        throw new Error('Received HTML instead of markdown. Please check file deployment and MIME type configuration.');
      }
      
      setReportContent(content);
      
      // Parse sections from markdown content
      const parsedSections = parseMarkdownSections(content);
      setSections(parsedSections);
      
      if (parsedSections.length > 0) {
        setActiveSection(parsedSections[0].id);
      }
    } catch (err) {
      console.error('Report loading error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const parseMarkdownSections = (content: string): ReportSection[] => {
    const lines = content.split('\n');
    const sections: ReportSection[] = [];
    
    lines.forEach((line, index) => {
      const match = line.match(/^(#{1,6})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const title = match[2].trim();
        const id = title.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-');
        
        sections.push({
          id,
          title,
          level,
          line: index
        });
      }
    });
    
    return sections;
  };

  const getReportMetadata = (): ReportMetadata => {
    return {
      title: "Call Center QA Analysis Report",
      date: new Date().toLocaleDateString(),
      period: "December 2024",
      author: "QA Analytics System",
      version: "v1.2",
      status: "Final",
      tags: ["Quality Assurance", "Call Analysis", "Performance", "Compliance"]
    };
  };

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setActiveSection(sectionId);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    const blob = new Blob([reportContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'qa-analysis-report.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = () => {
    if (navigator.share) {
      navigator.share({
        title: 'QA Analysis Report',
        text: 'Call Center Quality Assurance Analysis Report',
        url: window.location.href
      });
    } else {
      navigator.clipboard.writeText(window.location.href);
      // Could show a toast notification here
    }
  };

  const highlightSearchTerm = (text: string, searchTerm: string): string => {
    if (!searchTerm.trim()) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  };

  // Custom markdown components
  const markdownComponents = {
    h1: ({ children, ...props }: any) => {
      const id = `section-${children?.toString().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-')}`;
      return (
        <h1 id={id} className="text-2xl font-semibold mt-8 mb-4 text-foreground border-b pb-2" {...props}>
          {children}
        </h1>
      );
    },
    h2: ({ children, ...props }: any) => {
      const id = `section-${children?.toString().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-')}`;
      return (
        <h2 id={id} className="text-xl font-semibold mt-6 mb-3 text-foreground" {...props}>
          {children}
        </h2>
      );
    },
    h3: ({ children, ...props }: any) => {
      const id = `section-${children?.toString().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-')}`;
      return (
        <h3 id={id} className="text-lg font-medium mt-4 mb-2 text-foreground" {...props}>
          {children}
        </h3>
      );
    },
    p: ({ children, ...props }: any) => (
      <p className="mb-4 text-foreground leading-relaxed text-sm" {...props}>
        {children}
      </p>
    ),
    ul: ({ children, ...props }: any) => (
      <ul className="list-disc list-inside mb-4 space-y-1 text-foreground text-sm" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }: any) => (
      <ol className="list-decimal list-inside mb-4 space-y-1 text-foreground text-sm" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }: any) => (
      <li className="text-foreground text-sm" {...props}>
        {children}
      </li>
    ),
    blockquote: ({ children, ...props }: any) => (
      <blockquote className="border-l-4 border-primary/40 pl-4 my-4 italic text-muted-foreground text-sm" {...props}>
        {children}
      </blockquote>
    ),
    code: ({ children, ...props }: any) => (
      <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono" {...props}>
        {children}
      </code>
    ),
    pre: ({ children, ...props }: any) => (
      <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4 text-xs" {...props}>
        {children}
      </pre>
    ),
    table: ({ children, ...props }: any) => (
      <div className="overflow-x-auto mb-4">
        <table className="w-full border-collapse border border-border" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }: any) => (
      <th className="border border-border bg-muted p-2 text-left font-medium" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }: any) => (
      <td className="border border-border p-2" {...props}>
        {children}
      </td>
    ),
    strong: ({ children, ...props }: any) => (
      <strong className="font-semibold text-foreground" {...props}>
        {children}
      </strong>
    ),
    em: ({ children, ...props }: any) => (
      <em className="italic text-foreground" {...props}>
        {children}
      </em>
    ),
    a: ({ children, href, ...props }: any) => (
      <a 
        href={href} 
        className="text-primary hover:text-primary underline" 
        target="_blank" 
        rel="noopener noreferrer"
        {...props}
      >
        {children}
        <ExternalLink className="inline h-3 w-3 ml-1" />
      </a>
    )
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading Report...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <FileText className="h-4 w-4" />
        <AlertDescription>
          Error loading report: {error}
          <Button variant="outline" size="sm" onClick={loadReport} className="ml-2">
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  const metadata = getReportMetadata();

  return (
    <div className={`space-y-6 px-6 ${className}`}>
      {/* Action Bar */}
      <div className="flex justify-end">
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={() => setIsTableOfContentsOpen(!isTableOfContentsOpen)}>
            <BookOpen className="h-4 w-4 mr-2" />
            {isTableOfContentsOpen ? 'Hide' : 'Show'} TOC
          </Button>
          <Button variant="outline" size="sm" onClick={handlePrint}>
            <Printer className="h-4 w-4 mr-2" />
            Print
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button variant="outline" size="sm" onClick={handleShare}>
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>

        </div>
      </div>

      {/* Report Metadata */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                {metadata.title}
              </CardTitle>
              <CardDescription className="flex items-center space-x-4 mt-2">
                <span className="flex items-center">
                  <Calendar className="h-4 w-4 mr-1" />
                  {metadata.date}
                </span>
                <span className="flex items-center">
                  <Clock className="h-4 w-4 mr-1" />
                  {metadata.period}
                </span>
                <span className="flex items-center">
                  <Users className="h-4 w-4 mr-1" />
                  {metadata.author}
                </span>
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant="default">{metadata.version}</Badge>
              <Badge variant="secondary">{metadata.status}</Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {metadata.tags.map((tag, index) => (
              <Badge key={index} variant="outline">
                {tag}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Layout */}
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Table of Contents Sidebar */}
        {isTableOfContentsOpen && (
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <BookOpen className="h-4 w-4 mr-2" />
                Contents
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Search within report */}
              <div className="mb-4">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search in report..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-8 pr-4 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>
              
              <ScrollArea className="h-[600px]">
                <nav className="space-y-1">
                  {sections.map((section) => (
                    <button
                      key={section.id}
                      onClick={() => scrollToSection(section.id)}
                      className={`flex items-center w-full text-left px-2 py-1 text-sm rounded hover:bg-muted transition-colors ${
                        activeSection === section.id ? 'bg-muted font-medium' : ''
                      }`}
                      style={{ paddingLeft: `${section.level * 8 + 8}px` }}
                    >
                      <Hash className="h-3 w-3 mr-2 text-muted-foreground" />
                      <span className="truncate">{section.title}</span>
                    </button>
                  ))}
                </nav>
              </ScrollArea>
            </CardContent>
          </Card>
        )}

        {/* Report Content */}
        <Card className={isTableOfContentsOpen ? "lg:col-span-3" : "lg:col-span-4"}>
          <CardContent className="p-0">
            <ScrollArea className="h-[800px] p-6">
              <div className="prose prose-gray dark:prose-invert max-w-none">
                <div className="leading-relaxed">
                  <ReactMarkdown
                    components={markdownComponents}
                    remarkPlugins={[remarkGfm]}
                  >
                    {searchTerm ? 
                      reportContent.split('\n').map(line => 
                        highlightSearchTerm(line, searchTerm)
                      ).join('\n') :
                      reportContent
                    }
                  </ReactMarkdown>
                </div>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Quick Navigation Footer */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <span className="text-sm text-muted-foreground">Quick Navigation:</span>
              {sections.slice(0, 5).map((section) => (
                <Button
                  key={section.id}
                  variant="ghost"
                  size="sm"
                  onClick={() => scrollToSection(section.id)}
                  className="text-xs"
                >
                  {section.title}
                </Button>
              ))}
            </div>
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Eye className="h-4 w-4" />
              <span>Report last updated: {metadata.date}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Print Styles */}
      <style>{`
        @media print {
          .no-print {
            display: none !important;
          }
          
          .print-page-break {
            page-break-before: always;
          }
          
          body {
            font-size: 12pt;
            line-height: 1.4;
          }
          
          h1, h2, h3 {
            page-break-after: avoid;
          }
          
          table {
            page-break-inside: avoid;
          }
          
          .prose {
            max-width: none;
          }
        }
      `}</style>
    </div>
  );
};

export default ReportViewerDashboard;