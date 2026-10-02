#!/usr/bin/env python3
"""
Create Complete TMF ODA Transformation Journey

This script creates a comprehensive transformation journey with metadata, all six stages,
and Second Brain rules system for enhanced AI guidance during transformation.

Journey Structure:
1. Raw Input Analysis
2. Create Stripped Document
3. TMF Schema Mapping
4. Data Migration Planning
5. Data Migration
6. Verification & Validation

Second Brain Rules System:
- JSON-based rules for each stage
- Multiple rule types: Field Mapping, Contextual Recommendations, Data Interpretation, etc.
- Priority levels: low, medium, high, critical
- Context-aware rule application
- Scope management: global, project-specific, stage-specific
"""

import boto3
import sys
import traceback
import uuid
from datetime import datetime, timezone
from decimal import Decimal


def print_with_flush(message):
    """Print message and flush stdout immediately"""
    print(message)
    sys.stdout.flush()


def get_default_rules_for_stage(stage_id, journey_id):
    """Get default Second Brain rules for a specific stage"""
    
    base_rules = {
        'raw_analysis': [
            {
                'ruleId': f'rule-{stage_id}-context-001',
                'title': 'Business partner data maps to customer entity',
                'description': 'Business partner information should be classified and mapped to either customer or organization entities based on context',
                'type': 'data_interpretation',
                'priority': 'high',
                'scope': 'global',
                'context': {
                    'appliesTo': ['tables', 'columns'],
                    'conditions': [
                        {
                            'field': 'table_name',
                            'operator': 'contains',
                            'value': ['business_partner', 'bp_', 'partner', 'customer', 'organization']
                        }
                    ]
                },
                'content': {
                    'naturalLanguage': 'When I see a table with business partner information, it should be mapped to the TMF629 Customer entity. Look for fields like customer_id, customer_name, and customer_email as key indicators. Consider organization vs individual customer types.',
                    'jsonRule': {
                        'conditions': {
                            'table_patterns': ['*business_partner*', '*bp_*', '*customer*', '*organization*'],
                            'field_indicators': ['customer_id', 'customer_name', 'customer_email', 'organization_name']
                        },
                        'actions': {
                            'classify_as': 'customer_entity',
                            'tmf_mapping': 'TMF629_Customer',
                            'entity_type': 'determine_individual_or_organization'
                        }
                    }
                }
            },
            {
                'ruleId': f'rule-{stage_id}-field-mapping-001',
                'title': 'Customer table always maps to TMF Customer entity',
                'description': 'Any table containing customer information should be mapped to TMF629 Customer entity',
                'type': 'field_mapping',
                'priority': 'high',
                'scope': 'global',
                'context': {
                    'appliesTo': ['tables'],
                    'conditions': [
                        {
                            'field': 'table_name',
                            'operator': 'contains',
                            'value': ['customer', 'client', 'account_holder']
                        }
                    ]
                },
                'content': {
                    'naturalLanguage': 'Customer tables should always map to TMF629 Customer entity. Look for standard customer fields and ensure proper entity classification.',
                    'jsonRule': {
                        'conditions': {
                            'table_patterns': ['*customer*', '*client*', '*account_holder*']
                        },
                        'actions': {
                            'map_to_tmf': 'TMF629_Customer',
                            'validate_fields': ['id', 'name', 'email', 'phone'],
                            'entity_classification': 'customer'
                        }
                    }
                }
            },
            {
                'ruleId': f'rule-{stage_id}-contextual-001',
                'title': 'Identify primary business entities first',
                'description': 'Focus on identifying core business entities (Customer, Product, Order, Service) during analysis',
                'type': 'contextual_recommendations',
                'priority': 'medium',
                'scope': 'global',
                'context': {
                    'appliesTo': ['analysis_process'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'During raw analysis, prioritize identification of primary business entities like Customer, Product, Order, Service, and Account. These form the foundation for TMF mapping.',
                    'jsonRule': {
                        'priority_entities': ['customer', 'product', 'order', 'service', 'account'],
                        'analysis_order': ['tables', 'relationships', 'constraints', 'business_rules'],
                        'focus_areas': ['primary_keys', 'foreign_keys', 'unique_constraints']
                    }
                }
            }
        ],
        'stripped_schema': [
            {
                'ruleId': f'rule-{stage_id}-stripping-001',
                'title': 'Preserve TMF-relevant tables and relationships',
                'description': 'When stripping schema, preserve all tables and relationships relevant to TMF APIs',
                'type': 'data_interpretation',
                'priority': 'critical',
                'scope': 'global',
                'context': {
                    'appliesTo': ['tables', 'relationships'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'During schema stripping, preserve tables related to Customer (TMF629), Product (TMF620), Order (TMF622), Service (TMF633), and their relationships. Remove audit, logging, and system tables.',
                    'jsonRule': {
                        'preserve_patterns': ['*customer*', '*product*', '*order*', '*service*', '*account*'],
                        'remove_patterns': ['*audit*', '*log*', '*temp*', '*backup*', '*system*'],
                        'preserve_relationships': ['customer_to_account', 'product_to_catalog', 'order_to_customer']
                    }
                }
            },
            {
                'ruleId': f'rule-{stage_id}-simplification-001',
                'title': 'Simplify complex many-to-many relationships',
                'description': 'Convert complex many-to-many relationships to simplified references where appropriate',
                'type': 'field_mapping',
                'priority': 'medium',
                'scope': 'global',
                'context': {
                    'appliesTo': ['relationships'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'Simplify complex many-to-many relationships by creating direct references or using TMF standard relationship patterns.',
                    'jsonRule': {
                        'simplify_patterns': ['many_to_many'],
                        'convert_to': 'tmf_references',
                        'maintain_integrity': True
                    }
                }
            }
        ],
        'tmf_mapping': [
            {
                'ruleId': f'rule-{stage_id}-api-mapping-001',
                'title': 'Map customer entities to TMF629 Customer Management',
                'description': 'All customer-related entities should be mapped to TMF629 Customer Management API',
                'type': 'field_mapping',
                'priority': 'critical',
                'scope': 'global',
                'context': {
                    'appliesTo': ['entities'],
                    'conditions': [
                        {
                            'field': 'entity_type',
                            'operator': 'equals',
                            'value': 'customer'
                        }
                    ]
                },
                'content': {
                    'naturalLanguage': 'Customer entities must be mapped to TMF629 Customer Management API. Ensure all customer attributes are properly mapped to TMF629 schema.',
                    'jsonRule': {
                        'target_api': 'TMF629_Customer_Management',
                        'mapping_rules': {
                            'customer_id': 'id',
                            'customer_name': 'name',
                            'customer_email': 'contactMedium.emailAddress',
                            'customer_phone': 'contactMedium.phoneNumber'
                        }
                    }
                }
            },
            {
                'ruleId': f'rule-{stage_id}-coverage-001',
                'title': 'Ensure complete API coverage analysis',
                'description': 'Perform comprehensive coverage analysis for all TMF APIs',
                'type': 'contextual_recommendations',
                'priority': 'high',
                'scope': 'global',
                'context': {
                    'appliesTo': ['coverage_analysis'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'Ensure complete coverage analysis includes all relevant TMF APIs: TMF629 (Customer), TMF620 (Product), TMF622 (Order), TMF633 (Service), etc.',
                    'jsonRule': {
                        'required_apis': ['TMF629', 'TMF620', 'TMF622', 'TMF633', 'TMF637', 'TMF641'],
                        'coverage_threshold': Decimal('0.8'),
                        'gap_analysis': True
                    }
                }
            }
        ],
        'migration_planning': [
            {
                'ruleId': f'rule-{stage_id}-strategy-001',
                'title': 'Plan incremental migration strategy',
                'description': 'Use incremental migration approach for large datasets',
                'type': 'contextual_recommendations',
                'priority': 'high',
                'scope': 'global',
                'context': {
                    'appliesTo': ['migration_strategy'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'For large datasets, plan incremental migration with proper rollback procedures. Start with core entities like Customer, then related entities.',
                    'jsonRule': {
                        'migration_order': ['customer', 'product', 'order', 'service'],
                        'batch_size': 1000,
                        'rollback_points': True
                    }
                }
            }
        ],
        'data_migration': [
            {
                'ruleId': f'rule-{stage_id}-validation-001',
                'title': 'Validate data integrity during migration',
                'description': 'Implement comprehensive data validation during migration process',
                'type': 'data_interpretation',
                'priority': 'critical',
                'scope': 'global',
                'context': {
                    'appliesTo': ['data_transfer'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'Validate data integrity at each migration step. Check for referential integrity, data type compliance, and TMF schema validation.',
                    'jsonRule': {
                        'validation_steps': ['referential_integrity', 'data_types', 'tmf_compliance'],
                        'error_handling': 'log_and_continue',
                        'validation_threshold': Decimal('0.95')
                    }
                }
            }
        ],
        'verification_validation': [
            {
                'ruleId': f'rule-{stage_id}-compliance-001',
                'title': 'Comprehensive TMF compliance validation',
                'description': 'Perform thorough TMF API compliance validation',
                'type': 'contextual_recommendations',
                'priority': 'critical',
                'scope': 'global',
                'context': {
                    'appliesTo': ['compliance_check'],
                    'conditions': []
                },
                'content': {
                    'naturalLanguage': 'Perform comprehensive TMF API compliance validation including schema validation, API endpoint testing, and data integrity checks.',
                    'jsonRule': {
                        'compliance_checks': ['schema_validation', 'api_testing', 'data_integrity'],
                        'pass_threshold': Decimal('0.9'),
                        'required_apis': ['TMF629', 'TMF620', 'TMF622']
                    }
                }
            }
        ]
    }
    
    return base_rules.get(stage_id, [])


def create_rules_for_journey(journey_id, stages):
    """Create Second Brain rules for all stages in the journey"""
    rules_items = []
    
    for stage in stages:
        stage_id = stage['Data']['stageId']
        default_rules = get_default_rules_for_stage(stage_id, journey_id)
        
        for rule_idx, rule in enumerate(default_rules):
            rule_item = {
                'PK': f'JOURNEY#{journey_id}',
                'SK': f'RULE#{stage_id}#{rule_idx:03d}#{rule["ruleId"]}',
                'EntityType': 'SecondBrainRule',
                'GSI1PK': f'JOURNEY#{journey_id}#RULES',
                'GSI1SK': f'{stage_id}#{rule["priority"]}#{rule_idx:03d}',
                'CreatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'UpdatedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'Data': {
                    'ruleId': rule['ruleId'],
                    'journeyId': journey_id,
                    'stageId': stage_id,
                    'title': rule['title'],
                    'description': rule['description'],
                    'type': rule['type'],  # field_mapping, contextual_recommendations, data_interpretation, etc.
                    'priority': rule['priority'],  # low, medium, high, critical
                    'scope': rule['scope'],  # global, project, stage
                    'status': 'active',
                    'context': rule['context'],
                    'content': rule['content'],
                    'metadata': {
                        'createdBy': 'system',
                        'version': '1.0',
                        'tags': [stage_id, rule['type'], rule['priority']],
                        'applicableStages': [stage_id],
                        'ruleEngine': 'second_brain_v1'
                    }
                }
            }
            rules_items.append(rule_item)
    
    return rules_items


def create_complete_transformation_journey(journey_name=None, oda_component_type="customer-management"):
    """Create a complete transformation journey with all six stages and Second Brain rules"""
    print_with_flush('🚀 Starting complete transformation journey creation...')

    try:
        print_with_flush('🔗 Creating DynamoDB resource...')
        
        # Import AWS client utilities  
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import create_aws_resource
        
        # Get table name from config provider
        try:
            from src.config.config_provider import get_config
            config = get_config()
            table_name = config.dynamodb_transformation_table
            print_with_flush(f'📋 Using table from config: {table_name}')
        except Exception as e:
            table_name = os.environ.get('DYNAMODB_TABLE', 'TransformationSystem')
            print_with_flush(f'📋 Using table from env/default: {table_name}')
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Using role ARN: {role_arn}')
            dynamodb = create_aws_resource('dynamodb', role_arn=role_arn)
        else:
            print_with_flush('🔑 Using default credential chain')
            dynamodb = boto3.resource('dynamodb')
        
        table = dynamodb.Table(table_name)
        print_with_flush('✅ DynamoDB resource created successfully')
    except Exception as e:
        print_with_flush(f'❌ Failed to create DynamoDB resource: {str(e)}')
        traceback.print_exc()
        return None

    # Generate unique journey ID
    journey_id = f'JRN-{str(uuid.uuid4()).upper().replace("-", "")[:12]}'
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Use provided name or generate default
    if not journey_name:
        journey_name = f'Complete {oda_component_type.replace("-", " ").title()} Transformation'

    print_with_flush(f'📝 Creating complete journey with ID: {journey_id}')

    # 1. Journey Metadata with Second Brain configuration
    journey_item = {
        'PK': f'JOURNEY#{journey_id}',
        'SK': 'METADATA',
        'EntityType': 'Journey',
        'GSI1PK': 'JOURNEYS',
        'GSI1SK': timestamp,
        'CreatedAt': timestamp,
        'UpdatedAt': timestamp,
        'Data': {
            'journeyId': journey_id,
            'name': journey_name,
            'description': f'Complete TMF ODA transformation journey for {oda_component_type} with Second Brain AI assistance',
            'status': 'pending',
            'createdBy': 'system',
            'priority': 'high',
            'odaComponentType': oda_component_type,
            'source': {
                'type': 'schema-based',
                'schemaId': f'schema-{oda_component_type}-001',
                'schemaName': f'{oda_component_type.replace("-", " ").title()} Database',
                'schemaVersion': '1.0.0',
            },
            'configuration': {
                'timeout': 1800,  # 30 minutes for complete journey
                'maxDepth': 5,
                'tmfSpecVersion': '4.0.0',
                'outputFormat': 'json',
                'retryAttempts': 3,
                'enableDetailedLogging': True,
                'validateAtEachStage': True,
                'secondBrainEnabled': True,
                'ruleEngineVersion': 'v1.0',
            },
            'currentStageIndex': 0,
            'currentStageId': 'raw_analysis',
            'overallProgress': 0,
            'currentJobs': {},
            'aggregates': {
                'totalJobs': 0,
                'completedJobs': 0,
                'failedJobs': 0,
                'totalExecutionTime': '0m',
                'totalLogs': 0,
                'totalErrors': 0,
                'totalWarnings': 0,
                'totalRules': 0,
                'activeRules': 0,
            },
            'stageSummary': {
                'raw_analysis': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
                'stripped_schema': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
                'tmf_mapping': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
                'migration_planning': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
                'data_migration': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
                'verification_validation': {'totalExecutions': 0, 'lastStatus': 'pending', 'rulesCount': 0},
            },
            'secondBrainConfig': {
                'enabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation', 'validation_rules'],
                'priorityLevels': ['low', 'medium', 'high', 'critical'],
                'scopes': ['global', 'project', 'stage'],
                'defaultScope': 'global',
                'autoApplyRules': True,
                'customRulesEnabled': True,
            },
        },
    }

    # 2. Complete Stage Definitions with Second Brain integration
    stages = [
        # Stage 0: Raw Input Analysis
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#00#raw_analysis',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '00',
            'Data': {
                'stageId': 'raw_analysis',
                'name': 'Raw Input Analysis',
                'description': 'Analyze the raw database schema and structure with AI-guided insights',
                'order': 0,
                'canSkip': False,
                'estimatedDuration': '15m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations', 'data_interpretation'],
                'steps': [
                    {
                        'id': 'schema_parsing',
                        'name': 'Schema File Parsing',
                        'description': 'Parse SQL schema files and extract structure',
                        'order': 0,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations', 'data_interpretation'],
                    },
                    {
                        'id': 'relationship_discovery',
                        'name': 'Relationship Discovery',
                        'description': 'Identify table relationships and foreign keys',
                        'order': 1,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'contextual_recommendations'],
                    },
                    {
                        'id': 'data_type_analysis',
                        'name': 'Data Type Analysis',
                        'description': 'Analyze column data types and constraints',
                        'order': 2,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation'],
                    },
                    {
                        'id': 'business_rules_extraction',
                        'name': 'Business Rules Extraction',
                        'description': 'Extract business rules from schema constraints',
                        'order': 3,
                        'estimatedDuration': '2m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations', 'data_interpretation'],
                    },
                ],
            },
        },
        # Stage 1: Create Stripped Document/Schema
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#01#stripped_schema',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '01',
            'Data': {
                'stageId': 'stripped_schema',
                'name': 'Create Stripped Document',
                'description': 'Create TMF-focused simplified schema removing unnecessary complexity',
                'order': 1,
                'canSkip': False,
                'estimatedDuration': '12m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['field_mapping', 'data_interpretation'],
                'steps': [
                    {
                        'id': 'schema_stripping',
                        'name': 'Schema Stripping',
                        'description': 'Remove non-TMF relevant tables and columns',
                        'order': 0,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation'],
                    },
                    {
                        'id': 'core_structure_extraction',
                        'name': 'Core Structure Extraction',
                        'description': 'Extract core business entities and relationships',
                        'order': 1,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'data_interpretation'],
                    },
                    {
                        'id': 'data_model_simplification',
                        'name': 'Data Model Simplification',
                        'description': 'Simplify complex relationships for TMF mapping',
                        'order': 2,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping'],
                    },
                ],
            },
        },
        # Stage 2: TMF Schema Mapping
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#02#tmf_mapping',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '02',
            'Data': {
                'stageId': 'tmf_mapping',
                'name': 'TMF Schema Mapping',
                'description': 'Map the stripped schema to TMF ODA standards and APIs',
                'order': 2,
                'canSkip': False,
                'estimatedDuration': '20m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['field_mapping', 'contextual_recommendations'],
                'steps': [
                    {
                        'id': 'tmf_api_matching',
                        'name': 'TMF API Matching',
                        'description': 'Match entities to appropriate TMF API specifications',
                        'order': 0,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'contextual_recommendations'],
                    },
                    {
                        'id': 'attribute_mapping',
                        'name': 'Attribute Mapping',
                        'description': 'Map database columns to TMF API attributes',
                        'order': 1,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping'],
                    },
                    {
                        'id': 'relationship_mapping',
                        'name': 'Relationship Mapping',
                        'description': 'Map database relationships to TMF API relationships',
                        'order': 2,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['field_mapping', 'contextual_recommendations'],
                    },
                    {
                        'id': 'api_coverage_analysis',
                        'name': 'API Coverage Analysis',
                        'description': 'Analyze coverage of TMF API specifications',
                        'order': 3,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                    {
                        'id': 'gap_identification',
                        'name': 'Gap Identification',
                        'description': 'Identify gaps and missing mappings',
                        'order': 4,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                ],
            },
        },
        # Stage 3: Data Migration Planning
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#03#migration_planning',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '03',
            'Data': {
                'stageId': 'migration_planning',
                'name': 'Data Migration Planning',
                'description': 'Plan and prepare data migration strategies and scripts',
                'order': 3,
                'canSkip': False,
                'estimatedDuration': '18m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['contextual_recommendations', 'validation_rules'],
                'steps': [
                    {
                        'id': 'migration_strategy_planning',
                        'name': 'Migration Strategy Planning',
                        'description': 'Plan the overall data migration approach',
                        'order': 0,
                        'estimatedDuration': '6m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                    {
                        'id': 'etl_script_generation',
                        'name': 'ETL Script Generation',
                        'description': 'Generate Extract, Transform, Load scripts',
                        'order': 1,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                    {
                        'id': 'data_validation_rules',
                        'name': 'Data Validation Rules',
                        'description': 'Create validation rules for data integrity',
                        'order': 2,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules'],
                    },
                    {
                        'id': 'rollback_procedures',
                        'name': 'Rollback Procedures',
                        'description': 'Prepare rollback and recovery procedures',
                        'order': 3,
                        'estimatedDuration': '3m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                ],
            },
        },
        # Stage 4: Data Migration
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#04#data_migration',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '04',
            'Data': {
                'stageId': 'data_migration',
                'name': 'Data Migration',
                'description': 'Execute the actual data migration from legacy systems to TMF-compliant structure',
                'order': 4,
                'canSkip': False,
                'estimatedDuration': '25m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['data_interpretation', 'validation_rules'],
                'steps': [
                    {
                        'id': 'candidate_dataset_selection',
                        'name': 'Candidate Dataset Selection',
                        'description': 'Select and prepare candidate datasets for migration',
                        'order': 0,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['data_interpretation'],
                    },
                    {
                        'id': 'data_transfer',
                        'name': 'Data Transfer',
                        'description': 'Execute the actual data transfer from legacy to TMF systems',
                        'order': 1,
                        'estimatedDuration': '12m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules'],
                    },
                    {
                        'id': 'tmf_api_compliance_test',
                        'name': 'TMF API Compliance Test',
                        'description': 'Test migrated data against TMF API compliance requirements',
                        'order': 2,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules'],
                    },
                    {
                        'id': 'mark_completion',
                        'name': 'Mark Completion',
                        'description': 'Mark migration tasks as completed and update status',
                        'order': 3,
                        'estimatedDuration': '3m',
                        'aiAssisted': False,
                        'applicableRules': [],
                    },
                ],
            },
        },
        # Stage 5: Verification & Validation
        {
            'PK': f'JOURNEY#{journey_id}',
            'SK': 'STAGE#05#verification_validation',
            'EntityType': 'StageDefinition',
            'GSI1PK': f'JOURNEY#{journey_id}#STAGES',
            'GSI1SK': '05',
            'Data': {
                'stageId': 'verification_validation',
                'name': 'Verification & Validation',
                'description': 'Validate the mapping and migration results against TMF standards',
                'order': 5,
                'canSkip': False,
                'estimatedDuration': '22m',
                'status': 'pending',
                'secondBrainEnabled': True,
                'ruleTypes': ['contextual_recommendations', 'validation_rules'],
                'steps': [
                    {
                        'id': 'mapping_validation',
                        'name': 'Mapping Validation',
                        'description': 'Validate the accuracy of schema mappings',
                        'order': 0,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules'],
                    },
                    {
                        'id': 'api_compliance_check',
                        'name': 'API Compliance Check',
                        'description': 'Check compliance with TMF API standards',
                        'order': 1,
                        'estimatedDuration': '5m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules', 'contextual_recommendations'],
                    },
                    {
                        'id': 'data_integrity_verification',
                        'name': 'Data Integrity Verification',
                        'description': 'Verify data integrity and consistency',
                        'order': 2,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['validation_rules'],
                    },
                    {
                        'id': 'performance_assessment',
                        'name': 'Performance Assessment',
                        'description': 'Assess performance implications of the mapping',
                        'order': 3,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                    {
                        'id': 'final_report_generation',
                        'name': 'Final Report Generation',
                        'description': 'Generate comprehensive final report',
                        'order': 4,
                        'estimatedDuration': '4m',
                        'aiAssisted': True,
                        'applicableRules': ['contextual_recommendations'],
                    },
                ],
            },
        },
    ]

    # 3. Create Second Brain Rules
    print_with_flush('🧠 Creating Second Brain rules...')
    rules_items = create_rules_for_journey(journey_id, stages)
    
    # Update journey metadata with rules count
    total_rules = len(rules_items)
    journey_item['Data']['aggregates']['totalRules'] = total_rules
    journey_item['Data']['aggregates']['activeRules'] = total_rules
    
    # Update stage summary with rules count
    rules_by_stage = {}
    for rule_item in rules_items:
        stage_id = rule_item['Data']['stageId']
        if stage_id not in rules_by_stage:
            rules_by_stage[stage_id] = 0
        rules_by_stage[stage_id] += 1
    
    for stage_id, count in rules_by_stage.items():
        journey_item['Data']['stageSummary'][stage_id]['rulesCount'] = count

    try:
        # Insert journey metadata
        print_with_flush('💾 Inserting journey metadata...')
        table.put_item(Item=journey_item)
        print_with_flush(f'✅ Created complete journey: {journey_id}')

        # Insert all stages
        print_with_flush('📋 Inserting stage definitions...')
        for stage in stages:
            table.put_item(Item=stage)
            stage_name = stage["Data"]["name"]
            step_count = len(stage["Data"]["steps"])
            duration = stage["Data"]["estimatedDuration"]
            ai_steps = sum(1 for step in stage["Data"]["steps"] if step.get("aiAssisted", False))
            print_with_flush(f'✅ Created stage: {stage_name} ({step_count} steps, {ai_steps} AI-assisted, ~{duration})')

        # Insert all Second Brain rules
        print_with_flush('🧠 Inserting Second Brain rules...')
        for rule_item in rules_items:
            table.put_item(Item=rule_item)
        
        rules_by_type = {}
        for rule_item in rules_items:
            rule_type = rule_item['Data']['type']
            if rule_type not in rules_by_type:
                rules_by_type[rule_type] = 0
            rules_by_type[rule_type] += 1
        
        print_with_flush(f'✅ Created {total_rules} Second Brain rules:')
        for rule_type, count in rules_by_type.items():
            print_with_flush(f'   • {rule_type}: {count} rules')

        print_with_flush('')
        print_with_flush('🎉 Complete transformation journey with Second Brain created successfully!')
        print_with_flush(f'📊 Journey Summary:')
        print_with_flush(f'   🆔 Journey ID: {journey_id}')
        print_with_flush(f'   📝 Name: {journey_name}')
        print_with_flush(f'   🏗️  Component Type: {oda_component_type}')
        print_with_flush(f'   📋 Total Stages: 6')
        print_with_flush(f'   🧠 Total Rules: {total_rules}')
        print_with_flush(f'   ⏱️  Estimated Duration: ~112 minutes')
        print_with_flush(f'   🤖 AI-Assisted Steps: Enabled')
        print_with_flush('')

        return journey_id

    except Exception as e:
        print_with_flush(f'❌ Error creating complete journey: {str(e)}')
        traceback.print_exc()
        return None


def main():
    """Main function with user-friendly options"""
    print_with_flush('🚀 TMF ODA Complete Transformation Journey Creator')
    print_with_flush('=' * 60)

    # Parse command line arguments for customization
    import argparse
    parser = argparse.ArgumentParser(description='Create a complete TMF ODA transformation journey')
    parser.add_argument('--name', type=str, help='Custom journey name')
    parser.add_argument('--component-type', type=str, default='customer-management',
                       choices=['customer-management', 'product-catalog', 'order-management', 
                               'billing', 'resource-inventory', 'service-catalog'],
                       help='ODA component type')
    
    args = parser.parse_args()

    # Test AWS credentials
    try:
        print_with_flush('🔐 Testing AWS credentials...')
        
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from src.utils.aws_client_utils import test_aws_credentials
        
        role_arn = os.environ.get('AWS_ROLE_ARN')
        if role_arn:
            print_with_flush(f'🔑 Testing credentials with role ARN: {role_arn}')
            identity = test_aws_credentials(role_arn=role_arn)
        else:
            print_with_flush('🔑 Testing credentials with default credential chain')
            identity = test_aws_credentials()
        
        print_with_flush(f'✅ AWS Identity: {identity["Arn"]}')
        print_with_flush(f'✅ AWS Account: {identity["Account"]}')

    except Exception as e:
        print_with_flush(f'❌ AWS authentication failed: {str(e)}')
        traceback.print_exc()
        return False

    print_with_flush('=' * 60)

    # Create complete journey
    journey_id = create_complete_transformation_journey(
        journey_name=args.name,
        oda_component_type=args.component_type
    )
    
    if journey_id:
        print_with_flush('=' * 60)
        print_with_flush('✅ SUCCESS: Complete transformation journey created!')
        print_with_flush(f'🆔 Use this Journey ID: {journey_id}')
        print_with_flush('=' * 60)
        print_with_flush('')
        print_with_flush('🚀 Next Steps:')
        print_with_flush('   1. Use the TMF ODA MCP tools to execute stages')
        print_with_flush('   2. Start with: raw-analysis tool')
        print_with_flush('   3. Progress through all 6 stages sequentially')
        print_with_flush('   4. Monitor progress with: journeys tool')
        print_with_flush('')
        return True
    else:
        print_with_flush('❌ Failed to create complete journey')
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_with_flush('\n⚠️  Journey creation interrupted by user')
        sys.exit(1)
    except Exception as e:
        print_with_flush(f'\n❌ Unexpected error: {str(e)}')
        traceback.print_exc()
        sys.exit(1) 