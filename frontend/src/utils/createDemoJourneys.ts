/**
 * Demo Journeys Creator
 * 
 * This utility creates sample transformation journeys for testing the journey management system.
 */

import { transformationJourneyService } from '@/services/transformationJourneyService';
import { CreateJourneyRequest } from '@/types/transformationJourney';

/**
 * Create demo transformation journeys for testing
 */
export const createDemoJourneys = () => {
  const demoJourneys: CreateJourneyRequest[] = [
    {
      name: 'MTN SA Customer Database Transformation',
      description: 'Transform MTN South Africa customer database schema to TMF629 Customer Management API format. This journey includes data migration, validation, and integration with existing systems.',
      priority: 'high',
      source: {
        type: 'database-analysis',
        databaseId: 'mtn-sa-prod-db',
        databaseName: 'mtn_customer_db',
        databaseType: 'postgresql',
        connectionString: 'postgresql://mtn-sa-prod.database.azure.com:5432/customers'
      },
      configuration: {
        timeout: 72 * 60 * 60 * 1000, // 72 hours
        maxDepth: 5,
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
          emailOnError: true,
          slackWebhook: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
        }
      },
      metadata: {
        tags: ['mtn', 'south-africa', 'customer-database', 'tmf629', 'production'],
        customerName: 'MTN South Africa',
        projectCode: 'MTN-SA-2024-001',
        environmentType: 'production'
      }
    },
    {
      name: 'Vodacom Customer Schema Migration',
      description: 'Complete migration of Vodacom customer management schema to TMF629 standards. Includes legacy data transformation and API endpoint generation.',
      priority: 'medium',
      source: {
        type: 'schema-based',
        schemaId: 'vodacom-customer-v2',
        schemaName: 'Vodacom Customer Schema v2.1',
        schemaVersion: '2.1.0'
      },
      configuration: {
        timeout: 48 * 60 * 60 * 1000, // 48 hours
        maxDepth: 4,
        includeDocumentation: true,
        includeExamples: false,
        validateEndpoints: true,
        generateMigrationScripts: true,
        performDataSampling: false,
        tmfSpecVersion: '4.0.0',
        outputFormat: 'json',
        retryAttempts: 2,
        notificationSettings: {
          emailOnCompletion: true,
          emailOnError: true
        }
      },
      metadata: {
        tags: ['vodacom', 'customer-schema', 'migration', 'tmf629', 'staging'],
        customerName: 'Vodacom',
        projectCode: 'VOD-2024-003',
        environmentType: 'staging'
      }
    },
    {
      name: 'Telkom CRM Integration',
      description: 'Urgent integration project to align Telkom CRM system with TMF629 Customer Management API. Critical for Q4 digital transformation initiative.',
      priority: 'urgent',
      source: {
        type: 'database-analysis',
        databaseId: 'telkom-crm-main',
        databaseName: 'telkom_crm_system',
        databaseType: 'oracle',
        connectionString: 'oracle://telkom-crm-prod.oracle.com:1521/CRM'
      },
      configuration: {
        timeout: 24 * 60 * 60 * 1000, // 24 hours
        maxDepth: 6,
        includeDocumentation: true,
        includeExamples: true,
        validateEndpoints: true,
        generateMigrationScripts: true,
        performDataSampling: true,
        tmfSpecVersion: '4.0.0',
        outputFormat: 'json',
        retryAttempts: 5,
        notificationSettings: {
          emailOnCompletion: true,
          emailOnError: true,
          slackWebhook: 'https://hooks.slack.com/services/T11111111/B11111111/YYYYYYYYYYYYYYYYYYYYYYYY'
        }
      },
      metadata: {
        tags: ['telkom', 'crm', 'urgent', 'q4-initiative', 'tmf629', 'production'],
        customerName: 'Telkom',
        projectCode: 'TLK-Q4-2024-001',
        environmentType: 'production'
      }
    },
    {
      name: 'Cell C API Modernization',
      description: 'Modernize Cell C legacy customer APIs to TMF629 standards. Part of their digital transformation roadmap for 2024.',
      priority: 'medium',
      source: {
        type: 'schema-based',
        schemaId: 'cellc-legacy-api',
        schemaName: 'Cell C Legacy Customer API',
        schemaVersion: '1.5.2'
      },
      configuration: {
        timeout: 36 * 60 * 60 * 1000, // 36 hours
        maxDepth: 3,
        includeDocumentation: false,
        includeExamples: true,
        validateEndpoints: false,
        generateMigrationScripts: false,
        performDataSampling: true,
        tmfSpecVersion: '4.0.0',
        outputFormat: 'yaml',
        retryAttempts: 2,
        notificationSettings: {
          emailOnCompletion: false,
          emailOnError: true
        }
      },
      metadata: {
        tags: ['cellc', 'legacy-api', 'modernization', 'tmf629', 'development'],
        customerName: 'Cell C',
        projectCode: 'CELLC-MOD-2024-002',
        environmentType: 'development'
      }
    },
    {
      name: 'Rain Network Customer Data Analysis',
      description: 'Analyze Rain Network customer data structure and prepare transformation strategy for TMF629 compliance.',
      priority: 'low',
      source: {
        type: 'database-analysis',
        databaseId: 'rain-customer-db',
        databaseName: 'rain_customers',
        databaseType: 'mysql',
        connectionString: 'mysql://rain-db.cluster.amazonaws.com:3306/customers'
      },
      configuration: {
        timeout: 12 * 60 * 60 * 1000, // 12 hours
        maxDepth: 2,
        includeDocumentation: true,
        includeExamples: false,
        validateEndpoints: false,
        generateMigrationScripts: false,
        performDataSampling: true,
        tmfSpecVersion: '4.0.0',
        outputFormat: 'json',
        retryAttempts: 1,
        notificationSettings: {
          emailOnCompletion: false,
          emailOnError: false
        }
      },
      metadata: {
        tags: ['rain', 'network', 'analysis', 'tmf629', 'development'],
        customerName: 'Rain Network',
        projectCode: 'RAIN-ANALYSIS-2024-001',
        environmentType: 'development'
      }
    }
  ];

  // Create all demo journeys
  const createdJourneys = demoJourneys.map(journeyRequest => {
    const journey = transformationJourneyService.createJourney(journeyRequest);
    console.log(`🌟 Created demo journey: ${journey.name} (${journey.id})`);
    return journey;
  });

  // Start some journeys and put some in different states
  
  // Start the first journey
  if (createdJourneys.length > 0) {
    transformationJourneyService.performJourneyAction({
      id: createdJourneys[0].id,
      action: 'start',
      reason: 'Demo auto-start'
    });
    console.log(`▶️ Started demo journey: ${createdJourneys[0].name}`);
  }

  // Start and pause the second journey, but advance it to a different stage first
  if (createdJourneys.length > 1) {
    transformationJourneyService.performJourneyAction({
      id: createdJourneys[1].id,
      action: 'start',
      reason: 'Demo auto-start for pause test'
    });

    // Manually advance this journey to stage 2 to test resume functionality
    setTimeout(() => {
      const journey = transformationJourneyService.getJourney(createdJourneys[1].id);
      if (journey) {
        // Complete stage 1
        journey.stages[0].status = 'completed';
        journey.stages[0].progress = 100;
        journey.stages[0].completedSteps = journey.stages[0].totalSteps;
        journey.stages[0].endTime = new Date();

        // Move to stage 2 and set partial progress
        journey.currentStageIndex = 1;
        journey.stages[1].status = 'running';
        journey.stages[1].startTime = new Date();
        journey.stages[1].progress = 35; // Partial progress
        journey.stages[1].completedSteps = 1;

        // Update overall progress
        const totalSteps = journey.stages.reduce((sum, stage) => sum + stage.totalSteps, 0);
        const completedSteps = journey.stages.reduce((sum, stage) => sum + stage.completedSteps, 0);
        journey.overallProgress = (completedSteps / totalSteps) * 100;

        console.log(`🔄 Advanced demo journey to stage 2:`, journey.stages[1].name);
      }
    }, 100);

    // Then pause it
    setTimeout(() => {
      transformationJourneyService.performJourneyAction({
        id: createdJourneys[1].id,
        action: 'pause',
        reason: 'Demo pause for resume testing'
      });
      console.log(`⏸️ Paused demo journey: ${createdJourneys[1].name} at stage 2`);
    }, 200);
  }

  // Start the third journey (urgent) and advance it to stage 3
  if (createdJourneys.length > 2) {
    transformationJourneyService.performJourneyAction({
      id: createdJourneys[2].id,
      action: 'start',
      reason: 'Demo auto-start urgent journey'
    });

    // Advance this journey to stage 3 to test different resume points
    setTimeout(() => {
      const journey = transformationJourneyService.getJourney(createdJourneys[2].id);
      if (journey) {
        // Complete stages 1 and 2
        for (let i = 0; i < 2; i++) {
          journey.stages[i].status = 'completed';
          journey.stages[i].progress = 100;
          journey.stages[i].completedSteps = journey.stages[i].totalSteps;
          journey.stages[i].endTime = new Date();
        }

        // Move to stage 3 and set partial progress
        journey.currentStageIndex = 2;
        journey.stages[2].status = 'running';
        journey.stages[2].startTime = new Date();
        journey.stages[2].progress = 60; // Partial progress
        journey.stages[2].completedSteps = 2;

        // Update overall progress
        const totalSteps = journey.stages.reduce((sum, stage) => sum + stage.totalSteps, 0);
        const completedSteps = journey.stages.reduce((sum, stage) => sum + stage.completedSteps, 0);
        journey.overallProgress = (completedSteps / totalSteps) * 100;

        console.log(`🔄 Advanced urgent demo journey to stage 3:`, journey.stages[2].name);
      }
    }, 100);

    console.log(`🚨 Started urgent demo journey: ${createdJourneys[2].name}`);
  }

  // Leave the 4th and 5th journeys in 'created' state for testing
  
  console.log(`✅ Created ${createdJourneys.length} demo journeys`);
  return createdJourneys;
};

/**
 * Clear all demo journeys
 */
export const clearDemoJourneys = () => {
  transformationJourneyService.clear();
  console.log('🧹 Cleared all demo journeys');
};

/**
 * Get demo journey statistics
 */
export const getDemoJourneyStats = () => {
  return transformationJourneyService.getStatistics();
}; 