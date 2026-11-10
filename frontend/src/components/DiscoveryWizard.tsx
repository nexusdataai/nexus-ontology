import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  SkipForward,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  FileText,
  Download,
  Eye,
  Zap,
  Database,
  GitBranch,
  Upload,
  ShieldCheck,
  ClipboardList,
  Brain,
  RotateCcw
} from 'lucide-react';
import { DiscoverySession, DiscoveryStage } from '@/types/discoveryTypes';
import { discoveryWizardService } from '@/services/discoveryWizardService';
import { CustomerSchema } from '@/services/customerSchemaService';
import { SecondBrainPanel } from '@/components/SecondBrainPanel';
import { SecondBrainRule, TransformationStage } from '@/types/secondBrain';
import { transformationJourneyService } from '@/services/transformationJourneyService';
import { TransformationJourney } from '@/types/transformationJourney';

interface DiscoveryWizardProps {
  selectedSchema: CustomerSchema;
  resumingJourney?: TransformationJourney | null;
  onBack: () => void;
}

export default function DiscoveryWizard({ selectedSchema, resumingJourney, onBack }: DiscoveryWizardProps) {
  const navigate = useNavigate();
  const [session, setSession] = useState<DiscoverySession | null>(null);
  const [transformationJourney, setTransformationJourney] = useState<TransformationJourney | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [showStageReport, setShowStageReport] = useState(false);
  const [selectedStageForReport, setSelectedStageForReport] = useState<DiscoveryStage | null>(null);
  const [secondBrainCollapsed, setSecondBrainCollapsed] = useState(false);

  // Initialize session and transformation job
  useEffect(() => {
    const initializeSession = async () => {
      try {
        setIsInitializing(true);
        
        if (resumingJourney) {
          // Resuming existing journey - get fresh data to ensure latest state
          const freshJourney = transformationJourneyService.getJourney(resumingJourney.id);
          if (!freshJourney) {
            console.error('🌟 Journey not found when resuming:', resumingJourney.id);
            return;
          }
          
          console.log('🌟 Resuming transformation journey:', freshJourney.id, 'at stage index:', freshJourney.currentStageIndex);
          console.log('🌟 Current stage:', freshJourney.stages[freshJourney.currentStageIndex]?.name);
          setTransformationJourney(freshJourney);
          
          // Set current stage index based on journey's latest progress
          setCurrentStageIndex(freshJourney.currentStageIndex);
          
          // Create a mock session that matches the journey's current state
          const mockSession = await discoveryWizardService.createSession(
            'customer-1',
            selectedSchema.id,
            selectedSchema.name,
            {
              timeout: freshJourney.configuration.timeout,
              maxDepth: freshJourney.configuration.maxDepth,
              includeDocumentation: freshJourney.configuration.includeDocumentation,
              includeExamples: freshJourney.configuration.includeExamples,
              validateEndpoints: freshJourney.configuration.validateEndpoints,
              generateMigrationScripts: freshJourney.configuration.generateMigrationScripts,
              performDataSampling: freshJourney.configuration.performDataSampling,
              tmfSpecVersion: freshJourney.configuration.tmfSpecVersion,
              outputFormat: freshJourney.configuration.outputFormat
            }
          );
          
          // Sync session stages with journey stages
          if (mockSession) {
            console.log('🔄 Syncing session stages with journey state...');
            console.log('🚀 Journey status:', freshJourney.status, 'Current stage index:', freshJourney.currentStageIndex);
            
            mockSession.stages.forEach((stage, index) => {
              const journeyStage = freshJourney.stages[index];
              if (journeyStage) {
                // Map journey stage status to discovery stage status
                if (journeyStage.status === 'completed') {
                  stage.status = 'completed';
                } else if (journeyStage.status === 'running' || (freshJourney.status === 'running' && index === freshJourney.currentStageIndex)) {
                  stage.status = 'in_progress';
                  console.log('🏃 Stage', index, 'set to in_progress:', stage.name);
                } else if (index < freshJourney.currentStageIndex) {
                  // Previous stages should be completed if we're past them
                  stage.status = 'completed';
                } else {
                  stage.status = 'pending';
                }
                
                if (journeyStage.startTime) stage.startTime = journeyStage.startTime;
                if (journeyStage.endTime) stage.endTime = journeyStage.endTime;
                
                console.log(`📊 Stage ${index} (${stage.name}): ${stage.status}`);
              }
            });
            
            // If the journey is running, make sure we update the discovery service to reflect this
            if (freshJourney.status === 'running' && freshJourney.currentStageIndex >= 0) {
              const currentStage = mockSession.stages[freshJourney.currentStageIndex];
              if (currentStage && currentStage.status === 'in_progress') {
                console.log('🎯 Current running stage:', currentStage.name);
                // Update the discovery service session to reflect the running state
                mockSession.currentStage = currentStage.id;
                
                // Start the first substep if not already started
                if (currentStage.subSteps.length > 0 && currentStage.subSteps[0].status === 'pending') {
                  currentStage.subSteps[0].status = 'in_progress';
                  currentStage.subSteps[0].startTime = new Date();
                  console.log('🔄 Started first substep:', currentStage.subSteps[0].name);
                }
              }
            }
          }
          
          setSession(mockSession);
          
          // Update the discovery service with the synced session
          if (mockSession) {
            discoveryWizardService.updateSession(mockSession);
            console.log('💾 Discovery service updated with resumed session state');
          }
        } else {
          // Create new transformation
          // Create discovery session
          const newSession = await discoveryWizardService.createSession(
            'customer-1',
            selectedSchema.id,
            selectedSchema.name,
            {
              timeout: 300,
              maxDepth: 3,
              includeDocumentation: true,
              includeExamples: true,
              validateEndpoints: true,
              generateMigrationScripts: true,
              performDataSampling: true,
              tmfSpecVersion: '4.0.0',
              outputFormat: 'json'
            }
          );
          setSession(newSession);

          // Create transformation journey
          const journeyName = `${selectedSchema.name} Transformation`;
          const journeyDescription = `Complete transformation of ${selectedSchema.name} schema to TMF 629 Customer Management API`;
          
          const newJourney = transformationJourneyService.createJourney({
            name: journeyName,
            description: journeyDescription,
            priority: 'medium',
            source: {
              type: 'schema-based',
              schemaId: selectedSchema.id,
              schemaName: selectedSchema.name,
              schemaVersion: '1.0.0'
            },
            configuration: {
              timeout: 300,
              maxDepth: 3,
              includeDocumentation: true,
              includeExamples: true,
              validateEndpoints: true,
              generateMigrationScripts: true,
              performDataSampling: true,
              tmfSpecVersion: '4.0.0',
              outputFormat: 'json',
              retryAttempts: 3,
              notificationSettings: {
                emailOnCompletion: true,
                emailOnError: true
              }
            },
            metadata: {
              tags: ['schema-transformation', 'tmf-629', 'customer-management'],
              customerName: selectedSchema.name,
              projectCode: `TMF-${selectedSchema.id}`,
              environmentType: 'development'
            }
          });
          
          setTransformationJourney(newJourney);
          
          // Start the journey
          await transformationJourneyService.performJourneyAction({
            id: newJourney.id,
            action: 'start',
            reason: 'Transformation initiated by user'
          });
          
          console.log('🌟 Created and started transformation journey:', newJourney.id);
        }
      } catch (error) {
        console.error('Error initializing session:', error);
      } finally {
        setIsInitializing(false);
      }
    };

    initializeSession();
  }, [selectedSchema, resumingJourney]);

  // Periodic refresh when resuming a journey to get latest state
  useEffect(() => {
    if (!resumingJourney || !transformationJourney || !session) return;

    const refreshInterval = setInterval(() => {
      const freshJourney = transformationJourneyService.getJourney(transformationJourney.id);
      if (freshJourney) {
        // Check if journey state has changed
        const stageIndexChanged = freshJourney.currentStageIndex !== currentStageIndex;
        const statusChanged = freshJourney.status !== transformationJourney.status;
        
        if (stageIndexChanged || statusChanged) {
          console.log('🌟 Journey state updated:', {
            stageIndex: `${currentStageIndex} -> ${freshJourney.currentStageIndex}`,
            status: `${transformationJourney.status} -> ${freshJourney.status}`,
            currentStage: freshJourney.stages[freshJourney.currentStageIndex]?.name
          });
          
          setTransformationJourney(freshJourney);
          setCurrentStageIndex(freshJourney.currentStageIndex);
          
          // Update the discovery session to match the journey state
          const updatedSession = { ...session };
          updatedSession.stages.forEach((stage, index) => {
            const journeyStage = freshJourney.stages[index];
            if (journeyStage) {
              // Update stage status based on journey state
              if (journeyStage.status === 'completed') {
                stage.status = 'completed';
              } else if (journeyStage.status === 'running' || (freshJourney.status === 'running' && index === freshJourney.currentStageIndex)) {
                stage.status = 'in_progress';
              } else if (index < freshJourney.currentStageIndex) {
                stage.status = 'completed';
              } else {
                stage.status = 'pending';
              }
            }
          });
          
          setSession(updatedSession);
          discoveryWizardService.updateSession(updatedSession);
          console.log('🔄 Session updated to match journey state and synced to discovery service');
        }
      }
    }, 3000); // Check every 3 seconds for better responsiveness

    return () => clearInterval(refreshInterval);
  }, [resumingJourney, transformationJourney, currentStageIndex, session]);

  // Get current stage
  const currentStage = session?.stages[currentStageIndex];
  const isLastStage = currentStageIndex === (session?.stages.length || 0) - 1;

  // Calculate overall progress
  const completedStages = session?.stages.filter(s => s.status === 'completed').length || 0;
  const totalStages = session?.stages.length || 0;
  const overallProgress = totalStages > 0 ? (completedStages / totalStages) * 100 : 0;

  // Map discovery stages to Second Brain transformation stages
  const mapToTransformationStage = (discoveryStageId: string): TransformationStage => {
    const stageMapping: Record<string, TransformationStage> = {
      'raw_analysis': 'raw-analysis',
      'stripped_schema': 'schema-mapping',
      'tmf_mapping': 'tmf-mapping',
      'data_migration_planning': 'output-generation',
      'data_migration_execution': 'output-generation',
      'verification': 'validation'
    };
    return stageMapping[discoveryStageId] || 'raw-analysis';
  };

  // Handle Second Brain rule application
  const handleRuleApplied = (rule: SecondBrainRule) => {
    console.log('🧠 Applied rule in transformation workflow:', rule.title);
    // Here you can implement specific logic for how rules affect the transformation
    // For example, updating the current stage based on the rule, highlighting certain steps, etc.
    
    if (rule.type === 'field-mapping' && currentStage) {
      console.log('🎯 Field mapping rule applied during stage:', currentStage.name);
    }
  };

  // Handle stage start
  const handleStartStage = async () => {
    if (!session || !currentStage) return;

    try {
      console.log('🚀 Starting stage:', currentStage.id, '-', currentStage.name);
      console.log('📊 Current stage status:', currentStage.status);
      
      // If stage is already in progress (from resumed journey), we might need to restart the simulation
      if (currentStage.status === 'in_progress') {
        console.log('🔄 Stage already in progress, restarting simulation...');
        // Restart the simulation for this stage
        await discoveryWizardService.startStage(session.id, currentStage.id);
      } else {
        // Start the stage normally
        await discoveryWizardService.startStage(session.id, currentStage.id);
      }
      
      // Get the updated session immediately
      const updatedSession = discoveryWizardService.getSession(session.id);
      if (updatedSession) {
        console.log('✅ Stage started successfully, updating UI state');
        setSession(updatedSession);
        
        // Force a re-render by updating the current stage index if needed
        const updatedStage = updatedSession.stages.find(s => s.id === currentStage.id);
        if (updatedStage && updatedStage.status === 'in_progress') {
          console.log('📊 Stage is now in progress:', updatedStage.status);
        }
      }
      
      // Set up periodic refresh to show stage progress
      const refreshInterval = setInterval(() => {
        const freshSession = discoveryWizardService.getSession(session.id);
        if (freshSession) {
          setSession(freshSession);
          
          // Check if stage is completed
          const currentStageInSession = freshSession.stages.find(s => s.id === currentStage.id);
          if (currentStageInSession && currentStageInSession.status === 'completed') {
            console.log('🎉 Stage completed:', currentStageInSession.id);
            clearInterval(refreshInterval);
          }
        }
      }, 2000); // Check every 2 seconds
      
      // Clean up interval after 5 minutes to prevent memory leaks
      setTimeout(() => {
        clearInterval(refreshInterval);
      }, 300000); // 5 minutes
      
    } catch (error) {
      console.error('❌ Error starting stage:', error);
    }
  };

  // Handle stage repeat
  const handleRepeatStage = async () => {
    if (!session || !currentStage) return;

    try {
      console.log('🔄 Repeating stage:', currentStage.id, '-', currentStage.name);
      
      // Reset and start the stage again
      await discoveryWizardService.repeatStage(session.id, currentStage.id);
      
      // Get the updated session immediately
      const updatedSession = discoveryWizardService.getSession(session.id);
      if (updatedSession) {
        console.log('✅ Stage reset and started successfully');
        setSession(updatedSession);
        
        // Set up periodic refresh to show stage progress
        const refreshInterval = setInterval(() => {
          const freshSession = discoveryWizardService.getSession(session.id);
          if (freshSession) {
            setSession(freshSession);
            
            // Check if stage is completed
            const currentStageInSession = freshSession.stages.find(s => s.id === currentStage.id);
            if (currentStageInSession && currentStageInSession.status === 'completed') {
              console.log('🎉 Stage repeat completed:', currentStageInSession.id);
              clearInterval(refreshInterval);
            }
          }
        }, 2000); // Check every 2 seconds
        
        // Clean up interval after 5 minutes to prevent memory leaks
        setTimeout(() => {
          clearInterval(refreshInterval);
        }, 300000); // 5 minutes
      }
      
    } catch (error) {
      console.error('❌ Error repeating stage:', error);
    }
  };

  // Handle next stage
  const handleNextStage = () => {
    if (currentStageIndex < totalStages - 1) {
      setCurrentStageIndex(currentStageIndex + 1);
    }
  };

  // Handle previous stage
  const handlePreviousStage = () => {
    if (currentStageIndex > 0) {
      setCurrentStageIndex(currentStageIndex - 1);
    }
  };

  // Handle skip stage
  const handleSkipStage = async () => {
    if (!session || !currentStage || !currentStage.canSkip) return;

    try {
      await discoveryWizardService.skipStage(session.id, currentStage.id, 'User requested skip');
      const updatedSession = discoveryWizardService.getSession(session.id);
      if (updatedSession) {
        setSession(updatedSession);
        handleNextStage();
      }
    } catch (error) {
      console.error('Error skipping stage:', error);
    }
  };

  // View stage report
  const handleViewReport = (stage: DiscoveryStage) => {
    setSelectedStageForReport(stage);
    setShowStageReport(true);
  };

  // Get stage icon
  const getStageIcon = (stage: DiscoveryStage) => {
    const iconProps = { className: "h-5 w-5" };
    
    switch (stage.id) {
      case 'raw_analysis':
        return <Database {...iconProps} />;
      case 'stripped_schema':
        return <GitBranch {...iconProps} />;
      case 'tmf_mapping':
        return <Zap {...iconProps} />;
      case 'data_migration_planning':
        return <ClipboardList {...iconProps} />;
      case 'data_migration_execution':
        return <Upload {...iconProps} />;
      case 'verification':
        return <ShieldCheck {...iconProps} />;
      default:
        return <FileText {...iconProps} />;
    }
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'in_progress':
        return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case 'skipped':
        return <SkipForward className="h-4 w-4 text-muted-foreground" />;
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-success';
      case 'in_progress':
        return 'bg-primary';
      case 'failed':
        return 'bg-destructive';
      case 'skipped':
        return 'bg-border-strong';
      default:
        return 'bg-surface-3';
    }
  };

  if (isInitializing || !session) {
    return (
      <div className="h-full bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <p className="text-muted-foreground">
            {resumingJourney ? 'Loading Transformation Journey...' : 'Initializing Discovery Session...'}
          </p>
        </div>
      </div>
    );
  }

  if (showStageReport && selectedStageForReport) {
    return (
      <StageReportView 
        stage={selectedStageForReport}
        onBack={() => setShowStageReport(false)}
      />
    );
  }

  return (
    <div className="h-full bg-background">
      <div className="p-6">
        <div className="max-w-7xl mx-auto w-full">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button 
                variant="outline" 
                size="sm"
                onClick={onBack}
                className="p-2 h-9 w-9"
                title="Back to Schema Selection"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-4xl mb-2 font-semibold text-foreground">
                  {resumingJourney ? 'Resume Transformation' : 'MTN SA AI Native Transformation'}
                </h1>
                <p className="text-muted-foreground">
                  {resumingJourney 
                    ? `Continuing transformation: ${transformationJourney?.name}` 
                    : `Multi-stage analysis for ${selectedSchema.name}`
                  }
                </p>
                {transformationJourney && (
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="outline" className="text-xs">
                      Journey ID: {transformationJourney.id}
                    </Badge>
                    <Badge variant={transformationJourney.status === 'running' ? 'default' : 'secondary'} className="text-xs">
                      {transformationJourney.status === 'running' ? 'Running' : transformationJourney.status}
                    </Badge>
                    {resumingJourney && (
                      <Badge variant="outline" className="text-xs bg-warning/10 text-warning border-warning/25">
                        Resumed
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right space-y-2">
                <div className="text-sm text-muted-foreground">Overall Progress</div>
                <div className="flex items-center gap-2">
                  <Progress value={overallProgress} className="w-32" />
                  <span className="text-sm font-medium">{completedStages}/{totalStages}</span>
                </div>
              </div>
              
              {/* Second Brain Toggle when collapsed */}
              {secondBrainCollapsed && (
                <button
                  onClick={() => setSecondBrainCollapsed(false)}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                >
                  <Brain className="h-4 w-4" />
                  Second Brain
                  <Badge variant="secondary" className="text-xs">
                    AI
                  </Badge>
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Stage Navigation */}
            <div className="lg:col-span-1">
              <Card className="bg-card border-border sticky top-6">
                <CardHeader>
                  <CardTitle className="text-lg">Discovery Stages</CardTitle>
                  <CardDescription>
                    Track your progress through each stage
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {session.stages.map((stage, index) => (
                      <div
                        key={stage.id}
                        className={`p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                          index === currentStageIndex
                            ? 'bg-primary/10 border border-primary/30'
                            : 'bg-muted/50 hover:bg-muted/70'
                        }`}
                        onClick={() => setCurrentStageIndex(index)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex-shrink-0">
                            {getStageIcon(stage)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm truncate">
                                {stage.name}
                              </span>
                              {getStatusIcon(stage.status)}
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              <div className={`w-2 h-2 rounded-full ${getStatusColor(stage.status)}`} />
                              <span className="text-xs text-muted-foreground capitalize">
                                {stage.status.replace('_', ' ')}
                              </span>
                            </div>
                          </div>
                        </div>
                        {stage.status === 'completed' && stage.report && (
                          <div className="mt-2 space-y-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="w-full h-7 text-xs"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewReport(stage);
                              }}
                            >
                              <Eye className="h-3 w-3 mr-1" />
                              View Report
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="w-full h-7 text-xs"
                              onClick={(e) => {
                                e.stopPropagation();
                                // Set current stage to this stage and repeat it
                                const stageIndex = session.stages.findIndex(s => s.id === stage.id);
                                setCurrentStageIndex(stageIndex);
                                setTimeout(() => {
                                  handleRepeatStage();
                                }, 100);
                              }}
                            >
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Repeat
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Main Content */}
            <div className="lg:col-span-3 space-y-6">
              {/* Current Stage */}
              {currentStage && (
                <Card className="bg-card border-border">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          {getStageIcon(currentStage)}
                        </div>
                        <div>
                          <CardTitle className="text-xl">{currentStage.name}</CardTitle>
                          <CardDescription>{currentStage.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={currentStage.status === 'completed' ? 'default' : 'secondary'}>
                          {currentStage.status.replace('_', ' ')}
                        </Badge>
                        {currentStage.duration && (
                          <Badge variant="outline">
                            {currentStage.duration}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {/* Stage Controls */}
                    <div className="flex items-center gap-3 mb-6">
                      {currentStage.status === 'pending' && (
                        <Button onClick={handleStartStage} className="flex items-center gap-2">
                          <Play className="h-4 w-4" />
                          Start Stage
                        </Button>
                      )}
                      {currentStage.status === 'in_progress' && (
                        <Button variant="outline" disabled>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          In Progress
                        </Button>
                      )}
                      {currentStage.canSkip && currentStage.status === 'pending' && (
                        <Button variant="outline" onClick={handleSkipStage}>
                          <SkipForward className="h-4 w-4 mr-2" />
                          Skip Stage
                        </Button>
                      )}
                      {currentStage.status === 'completed' && currentStage.report && (
                        <Button variant="outline" onClick={() => handleViewReport(currentStage)}>
                          <FileText className="h-4 w-4 mr-2" />
                          View Report
                        </Button>
                      )}
                      {currentStage.status === 'completed' && (
                        <Button variant="outline" onClick={handleRepeatStage} className="flex items-center gap-2">
                          <RotateCcw className="h-4 w-4" />
                          Repeat Stage
                        </Button>
                      )}
                    </div>

                    {/* Sub-steps */}
                    <div className="space-y-3">
                      <h3 className="font-semibold text-foreground">Stage Steps</h3>
                      <div className="space-y-2">
                        {currentStage.subSteps.map((subStep, index) => (
                          <div
                            key={subStep.id}
                            className="flex items-center gap-3 p-3 bg-muted/30 rounded-lg"
                          >
                            <div className="flex-shrink-0">
                              {getStatusIcon(subStep.status)}
                            </div>
                            <div className="flex-1">
                              <div className="font-medium text-sm">{subStep.name}</div>
                              <div className="text-xs text-muted-foreground">{subStep.description}</div>
                              {subStep.duration && (
                                <div className="text-xs text-muted-foreground mt-1">
                                  Duration: {subStep.duration}
                                </div>
                              )}
                            </div>
                            {subStep.logs.length > 0 && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs"
                                onClick={() => navigate('/discovery/logs', { 
                                  state: { sessionId: session.id, stageId: currentStage.id, subStepId: subStep.id }
                                })}
                              >
                                <Eye className="h-3 w-3 mr-1" />
                                Logs ({subStep.logs.length})
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Navigation */}
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  onClick={handlePreviousStage}
                  disabled={currentStageIndex === 0}
                  className="flex items-center gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Previous Stage
                </Button>

                <div className="text-center">
                  <span className="text-sm text-muted-foreground">
                    Stage {currentStageIndex + 1} of {totalStages}
                  </span>
                </div>

                {!isLastStage ? (
                  <Button
                    onClick={handleNextStage}
                    className="flex items-center gap-2"
                    disabled={currentStage?.status !== 'completed' && currentStage?.status !== 'skipped'}
                  >
                    Next Stage
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={() => navigate('/analytics')}
                    className="flex items-center gap-2"
                    disabled={currentStage?.status !== 'completed'}
                  >
                    View Results
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Second Brain Panel */}
      <SecondBrainPanel
        currentStage={currentStage ? mapToTransformationStage(currentStage.id) : 'raw-analysis'}
        contextData={{
          table: selectedSchema.name,
          pattern: currentStage?.name
        }}
        onRuleApplied={handleRuleApplied}
        collapsed={secondBrainCollapsed}
        onToggleCollapsed={() => setSecondBrainCollapsed(!secondBrainCollapsed)}
      />
    </div>
  );
}

// Stage Report Component
interface StageReportViewProps {
  stage: DiscoveryStage;
  onBack: () => void;
}

function StageReportView({ stage, onBack }: StageReportViewProps) {
  const report = stage.report;

  if (!report) {
    return (
      <div className="h-full bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto" />
          <p className="text-muted-foreground">No report available for this stage</p>
          <Button onClick={onBack}>Go Back</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-background">
      <div className="p-6">
        <div className="max-w-6xl mx-auto w-full">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button 
                variant="outline" 
                size="sm"
                onClick={onBack}
                className="p-2 h-9 w-9"
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-4xl mb-2 font-semibold text-foreground">{stage.name} Report</h1>
                <p className="text-muted-foreground">{report.summary}</p>
              </div>
            </div>
            <Button variant="outline" className="flex items-center gap-2">
              <Download className="h-4 w-4" />
              Download Report
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Key Findings */}
            <Card>
              <CardHeader>
                <CardTitle>Key Findings</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {report.keyFindings.map((finding, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{finding}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>Stage Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(report.metrics).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-sm text-muted-foreground capitalize">
                        {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                      </span>
                      <span className="font-medium">
                        {typeof value === 'number' ? 
                          (key.includes('Rate') ? `${value.toFixed(1)}%` : value.toLocaleString()) 
                          : value
                        }
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {report.recommendations.map((recommendation, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <Zap className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            {/* Next Stage Readiness */}
            <Card>
              <CardHeader>
                <CardTitle>Next Stage Readiness</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${
                    report.nextStageReadiness === 'ready' ? 'bg-success' :
                    report.nextStageReadiness === 'needs_review' ? 'bg-warning' : 'bg-destructive'
                  }`} />
                  <span className="font-medium capitalize">
                    {report.nextStageReadiness.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-2">
                  {report.nextStageReadiness === 'ready' && 
                    'This stage is complete and the next stage can proceed.'}
                  {report.nextStageReadiness === 'needs_review' && 
                    'This stage requires review before proceeding to the next stage.'}
                  {report.nextStageReadiness === 'blocked' && 
                    'Issues were found that must be resolved before proceeding.'}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
} 