import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  ExternalLink, 
  MessageSquare, 
  Clock, 
  User, 
  FileText,
  Quote
} from 'lucide-react';

interface EvidenceItem {
  call_id?: string;
  transcript_source: string;
  speaker: string;
  timestamp: number;
  evidence_text: string;
  context: string;
  confidence_score: number;
}

interface EvidenceProps {
  evidence: {
    primary_evidence?: EvidenceItem[];
    supporting_evidence?: EvidenceItem[];
    confidence_level?: number;
    analysis_methodology?: string;
  };
  title?: string;
  compact?: boolean;
}

const Evidence: React.FC<EvidenceProps> = ({ evidence, title = "Evidence", compact = false }) => {
  const [selectedTranscript, setSelectedTranscript] = useState<string | null>(null);
  const [transcriptContent, setTranscriptContent] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const primaryEvidence = evidence.primary_evidence || [];
  const supportingEvidence = evidence.supporting_evidence || [];
  const allEvidence = [...primaryEvidence, ...supportingEvidence];

  const formatTimestamp = (timestamp: number) => {
    const minutes = Math.floor(timestamp / 60);
    const seconds = Math.floor(timestamp % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const openTranscript = async (transcriptSource: string, timestamp?: number) => {
    setLoading(true);
    try {
      const response = await fetch(`/transcripts/${transcriptSource}`);
      if (response.ok) {
        const content = await response.json();
        setTranscriptContent(content);
        setSelectedTranscript(transcriptSource);
      } else {
        console.error('Failed to load transcript:', transcriptSource);
      }
    } catch (error) {
      console.error('Error loading transcript:', error);
    } finally {
      setLoading(false);
    }
  };

  if (allEvidence.length === 0) {
    return null;
  }

  const EvidenceItem = ({ item, isPrimary }: { item: EvidenceItem; isPrimary: boolean }) => (
    <div className={`p-3 border rounded-lg ${isPrimary ? 'bg-blue-50 border-blue-200 dark:bg-blue-900/10' : 'bg-gray-50 border-gray-200 dark:bg-gray-900/10'}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge variant={isPrimary ? "default" : "secondary"}>
            {isPrimary ? "Primary" : "Supporting"}
          </Badge>
          <Badge variant="outline" className={getConfidenceColor(item.confidence_score)}>
            {(item.confidence_score * 100).toFixed(0)}% confidence
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => openTranscript(item.transcript_source, item.timestamp)}
            className="h-7 px-2"
          >
            <ExternalLink className="h-3 w-3 mr-1" />
            View
          </Button>
        </div>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <FileText className="h-3 w-3" />
          <span>{item.transcript_source}</span>
          <Clock className="h-3 w-3 ml-2" />
          <span>{formatTimestamp(item.timestamp)}</span>
          <User className="h-3 w-3 ml-2" />
          <span className="capitalize">{item.speaker}</span>
        </div>
        
        <div className="bg-white dark:bg-gray-800 p-2 rounded border-l-4 border-blue-500">
          <Quote className="h-4 w-4 text-blue-500 mb-1" />
          <p className="text-sm italic">"{item.evidence_text}"</p>
        </div>
        
        <p className="text-xs text-muted-foreground">
          <strong>Context:</strong> {item.context}
        </p>
      </div>
    </div>
  );

  if (compact) {
    return (
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <MessageSquare className="h-4 w-4 mr-2" />
            View Evidence ({allEvidence.length})
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>
              Evidence supporting this analysis with links to source conversations
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {primaryEvidence.map((item, index) => (
              <EvidenceItem key={index} item={item} isPrimary={true} />
            ))}
            {supportingEvidence.map((item, index) => (
              <EvidenceItem key={index} item={item} isPrimary={false} />
            ))}
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          {title}
        </CardTitle>
        <CardDescription>
          Evidence supporting this analysis • {evidence.confidence_level ? `${(evidence.confidence_level * 100).toFixed(0)}% confidence` : ''} • {evidence.analysis_methodology || 'AI Analysis'}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {primaryEvidence.map((item, index) => (
            <EvidenceItem key={index} item={item} isPrimary={true} />
          ))}
          {supportingEvidence.map((item, index) => (
            <EvidenceItem key={index} item={item} isPrimary={false} />
          ))}
        </div>
      </CardContent>

      {/* Transcript Viewer Dialog */}
      <Dialog open={!!selectedTranscript} onOpenChange={() => setSelectedTranscript(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Conversation Transcript: {selectedTranscript}</DialogTitle>
            <DialogDescription>
              Full conversation transcript with context
            </DialogDescription>
          </DialogHeader>
          {loading ? (
            <div className="text-center py-8">Loading transcript...</div>
          ) : transcriptContent ? (
            <div className="space-y-4">
              {/* Display transcript content - structure may vary */}
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                <pre className="whitespace-pre-wrap text-sm">
                  {JSON.stringify(transcriptContent, null, 2)}
                </pre>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Failed to load transcript
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default Evidence; 