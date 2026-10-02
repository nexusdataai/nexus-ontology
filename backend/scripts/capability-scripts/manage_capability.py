#!/usr/bin/env python3
"""
Comprehensive Business Capability Management Script
Handles all CRUD operations for business capabilities in DynamoDB
Following the single table design pattern as documented
"""

import boto3
import json
import uuid
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
from botocore.exceptions import ClientError

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from db_utils import (
    get_table_name,
    get_dynamodb_resource,
    format_decimal,
    print_with_flush,
    get_current_timestamp,
    check_auth
)


class CapabilityManager:
    """Comprehensive manager for Business Capability operations"""
    
    def __init__(self, dynamodb=None):
        """
        Initialize the Capability Manager
        
        Args:
            dynamodb: Optional DynamoDB resource (for dependency injection/testing)
        """
        if dynamodb is not None:
            # Dependency injection mode (for testing)
            self.dynamodb = dynamodb
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name) if hasattr(dynamodb, 'Table') else None
        else:
            # Normal operation - create AWS client
            self.dynamodb = get_dynamodb_resource()
            self.table_name = get_table_name()
            self.table = self.dynamodb.Table(self.table_name)
        
        # Valid values for various fields
        self.valid_statuses = ['planning', 'development', 'active', 'deprecated', 'retiring']
        self.valid_priorities = ['low', 'medium', 'high', 'critical']
        self.valid_business_domains = [
            'operations', 'customer', 'product', 'finance', 
            'hr', 'technology', 'sales', 'marketing', 'supply-chain',
            'analytics', 'security', 'compliance'
        ]
        self.valid_phases = ['planning', 'development', 'testing', 'production', 'sunset']
        
        # Component types
        self.valid_component_types = [
            'ui-dashboard', 'api-server', 'mcp-server', 'database',
            'message-queue', 'cache', 'scheduler', 'worker',
            'storage', 'gateway', 'service-mesh', 'monitoring'
        ]
        
        # Architecture patterns
        self.valid_architecture_patterns = [
            'microservices', 'monolithic', 'serverless', 'event-driven',
            'soa', 'layered', 'hexagonal', 'lambda'
        ]
        
        # Deployment models
        self.valid_deployment_models = [
            'single-region', 'multi-region', 'edge', 'hybrid', 'on-premise'
        ]
    
    # ==================== CAPABILITY CRUD OPERATIONS ====================
    
    def create_capability(self, capability_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new business capability
        
        Args:
            capability_data: Dictionary containing capability details
            
        Returns:
            Created capability with metadata
        """
        try:
            # Generate capability ID if not provided
            capability_id = capability_data.get('capabilityId') or f"CAP-{uuid.uuid4().hex[:8].upper()}"
            timestamp = get_current_timestamp()
            
            # Build the data structure according to the schema
            data = {
                'capabilityId': capability_id,
                'name': capability_data.get('name', ''),
                'description': capability_data.get('description', ''),
                'businessDomain': capability_data.get('businessDomain', 'operations'),
                'status': capability_data.get('status', 'planning'),
                'priority': capability_data.get('priority', 'medium'),
                'owner': capability_data.get('owner', 'unassigned'),
                'createdBy': capability_data.get('createdBy', 'system'),
                'version': capability_data.get('version', '1.0.0'),
                'tags': capability_data.get('tags', []),
                'businessMetrics': capability_data.get('businessMetrics', {
                    'sla': '99.9%',
                    'rto': '60 minutes',
                    'rpo': '15 minutes',
                    'criticalityLevel': 'tier-2'
                }),
                'architecture': capability_data.get('architecture', {
                    'pattern': 'microservices',
                    'deploymentModel': 'single-region',
                    'scalabilityType': 'horizontal',
                    'redundancy': 'active-passive'
                }),
                'compliance': capability_data.get('compliance', {
                    'standards': [],
                    'lastAudit': None,
                    'certificationStatus': 'pending'
                }),
                'aggregates': {
                    'totalComponents': 0,
                    'activeComponents': 0,
                    'healthScore': 100.0,
                    'totalDependencies': 0,
                    'totalJobs': 0,
                    'successfulJobs': 0,
                    'failedJobs': 0,
                    'averageDeploymentTime': '0m',
                    'totalIncidents': 0,
                    'totalRules': 0,
                    'activeRules': 0,
                    'lastDeployment': None,
                    'monthlyOperationalCost': 0,
                    'userCount': 0
                },
                'lifecycle': capability_data.get('lifecycle', {
                    'phase': 'planning',
                    'plannedRetirement': None,
                    'lastMajorUpdate': timestamp,
                    'nextReview': None
                })
            }
            
            # Create the DynamoDB item
            item = {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': 'METADATA',
                'EntityType': 'Capability',
                'GSI1PK': 'CAPABILITIES',
                'GSI1SK': f"{data['businessDomain']}#{data['priority'][:2]}#{data['name'].lower().replace(' ', '-')}",
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
                'Data': data
            }
            
            # Add GSI2 for domain-based queries
            if data['businessDomain']:
                item['GSI2PK'] = f"DOMAIN#{data['businessDomain']}"
                item['GSI2SK'] = f"{data['priority'][:2]}#{capability_id}"
            
            # Add GSI3 for health-based queries
            item['GSI3PK'] = f"HEALTH#{data['status']}"
            item['GSI3SK'] = f"{int(data['aggregates']['healthScore']):03d}#{capability_id}"
            
            # Put item in DynamoDB
            self.table.put_item(Item=item)
            
            print_with_flush(f"✅ Created capability: {capability_id}")
            return item
            
        except ClientError as e:
            print_with_flush(f"❌ Error creating capability: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def get_capability(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a capability by ID
        
        Args:
            capability_id: The capability ID
            
        Returns:
            Capability data or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'CAPABILITY#{capability_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' in response:
                return response['Item']
            else:
                print_with_flush(f"⚠️ Capability {capability_id} not found")
                return None
                
        except ClientError as e:
            print_with_flush(f"❌ Error getting capability: {e.response['Error']['Message']}")
            raise
    
    def update_capability(self, capability_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a capability
        
        Args:
            capability_id: The capability ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated capability
        """
        try:
            # Get current capability
            current = self.get_capability(capability_id)
            if not current:
                raise ValueError(f"Capability {capability_id} not found")
            
            # Merge updates with current data
            current_data = current['Data']
            for key, value in updates.items():
                if key in current_data:
                    if isinstance(current_data[key], dict) and isinstance(value, dict):
                        current_data[key].update(value)
                    else:
                        current_data[key] = value
            
            # Update timestamp
            timestamp = get_current_timestamp()
            
            # Update the item
            response = self.table.update_item(
                Key={
                    'PK': f'CAPABILITY#{capability_id}',
                    'SK': 'METADATA'
                },
                UpdateExpression='SET #data = :data, UpdatedAt = :timestamp',
                ExpressionAttributeNames={
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':data': current_data,
                    ':timestamp': timestamp
                },
                ReturnValues='ALL_NEW'
            )
            
            print_with_flush(f"✅ Updated capability: {capability_id}")
            return response['Attributes']
            
        except ClientError as e:
            print_with_flush(f"❌ Error updating capability: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def delete_capability(self, capability_id: str, cascade: bool = False) -> bool:
        """
        Delete a capability
        
        Args:
            capability_id: The capability ID
            cascade: If True, delete all related items (components, dependencies, etc.)
            
        Returns:
            True if successful
        """
        try:
            if cascade:
                # Delete all items with this capability's PK
                items_to_delete = []
                
                # Query all items for this capability
                response = self.table.query(
                    KeyConditionExpression='PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': f'CAPABILITY#{capability_id}'
                    }
                )
                
                items_to_delete.extend(response.get('Items', []))
                
                # Handle pagination
                while 'LastEvaluatedKey' in response:
                    response = self.table.query(
                        KeyConditionExpression='PK = :pk',
                        ExpressionAttributeValues={
                            ':pk': f'CAPABILITY#{capability_id}'
                        },
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                    items_to_delete.extend(response.get('Items', []))
                
                # Delete all items
                with self.table.batch_writer() as batch:
                    for item in items_to_delete:
                        batch.delete_item(
                            Key={
                                'PK': item['PK'],
                                'SK': item['SK']
                            }
                        )
                
                print_with_flush(f"✅ Deleted capability {capability_id} and {len(items_to_delete)} related items")
            else:
                # Delete only the metadata
                self.table.delete_item(
                    Key={
                        'PK': f'CAPABILITY#{capability_id}',
                        'SK': 'METADATA'
                    }
                )
                print_with_flush(f"✅ Deleted capability metadata: {capability_id}")
            
            return True
            
        except ClientError as e:
            print_with_flush(f"❌ Error deleting capability: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            return False
    
    def list_capabilities(self, 
                         status_filter: Optional[str] = None,
                         domain_filter: Optional[str] = None,
                         priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all capabilities with optional filters
        
        Args:
            status_filter: Filter by status
            domain_filter: Filter by business domain
            priority_filter: Filter by priority
            
        Returns:
            List of capabilities
        """
        try:
            capabilities = []
            
            # Use GSI1 to get all capabilities
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': 'CAPABILITIES'
                }
            )
            
            capabilities.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    IndexName='GSI1',
                    KeyConditionExpression='GSI1PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': 'CAPABILITIES'
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                capabilities.extend(response.get('Items', []))
            
            # Apply filters
            filtered = capabilities
            
            if status_filter:
                filtered = [c for c in filtered if c.get('Data', {}).get('status') == status_filter]
            
            if domain_filter:
                filtered = [c for c in filtered if c.get('Data', {}).get('businessDomain') == domain_filter]
            
            if priority_filter:
                filtered = [c for c in filtered if c.get('Data', {}).get('priority') == priority_filter]
            
            print_with_flush(f"📊 Found {len(filtered)} capabilities")
            return filtered
            
        except ClientError as e:
            print_with_flush(f"❌ Error listing capabilities: {e.response['Error']['Message']}")
            return []
    
    # ==================== DISPLAY FUNCTIONS ====================
    
    def display_capability(self, capability: Dict[str, Any]):
        """Display capability details in a formatted way"""
        data = capability.get('Data', {})
        
        print_with_flush("\n" + "="*100)
        print_with_flush(f"🎯 CAPABILITY: {data.get('name', 'Unknown')}")
        print_with_flush("="*100)
        
        # Basic Information
        print_with_flush("\n📋 BASIC INFORMATION:")
        print_with_flush(f"  ID: {data.get('capabilityId', 'N/A')}")
        print_with_flush(f"  Description: {data.get('description', 'N/A')}")
        print_with_flush(f"  Business Domain: {data.get('businessDomain', 'N/A')}")
        print_with_flush(f"  Status: {data.get('status', 'N/A')}")
        print_with_flush(f"  Priority: {data.get('priority', 'N/A')}")
        print_with_flush(f"  Owner: {data.get('owner', 'N/A')}")
        print_with_flush(f"  Version: {data.get('version', 'N/A')}")
        
        # Business Metrics
        metrics = data.get('businessMetrics', {})
        if metrics:
            print_with_flush("\n📈 BUSINESS METRICS:")
            print_with_flush(f"  SLA: {metrics.get('sla', 'N/A')}")
            print_with_flush(f"  RTO: {metrics.get('rto', 'N/A')}")
            print_with_flush(f"  RPO: {metrics.get('rpo', 'N/A')}")
            print_with_flush(f"  Criticality: {metrics.get('criticalityLevel', 'N/A')}")
        
        # Architecture
        arch = data.get('architecture', {})
        if arch:
            print_with_flush("\n🏗️ ARCHITECTURE:")
            print_with_flush(f"  Pattern: {arch.get('pattern', 'N/A')}")
            print_with_flush(f"  Deployment: {arch.get('deploymentModel', 'N/A')}")
            print_with_flush(f"  Scalability: {arch.get('scalabilityType', 'N/A')}")
            print_with_flush(f"  Redundancy: {arch.get('redundancy', 'N/A')}")
        
        # Aggregates (Operational Insights)
        agg = data.get('aggregates', {})
        if agg:
            print_with_flush("\n📊 OPERATIONAL INSIGHTS:")
            print_with_flush(f"  Components: {agg.get('totalComponents', 0)} total, {agg.get('activeComponents', 0)} active")
            print_with_flush(f"  Health Score: {agg.get('healthScore', 0)}%")
            print_with_flush(f"  Dependencies: {agg.get('totalDependencies', 0)}")
            print_with_flush(f"  Jobs: {agg.get('totalJobs', 0)} total, {agg.get('successfulJobs', 0)} successful")
            print_with_flush(f"  Monthly Cost: ${agg.get('monthlyOperationalCost', 0):,.2f}")
            print_with_flush(f"  User Count: {agg.get('userCount', 0):,}")
        
        # Compliance
        compliance = data.get('compliance', {})
        if compliance and compliance.get('standards'):
            print_with_flush("\n🔒 COMPLIANCE:")
            print_with_flush(f"  Standards: {', '.join(compliance.get('standards', []))}")
            print_with_flush(f"  Status: {compliance.get('certificationStatus', 'N/A')}")
            if compliance.get('lastAudit'):
                print_with_flush(f"  Last Audit: {compliance.get('lastAudit')}")
        
        # Tags
        if data.get('tags'):
            print_with_flush("\n🏷️ TAGS:")
            print_with_flush(f"  {', '.join(data.get('tags', []))}")
        
        print_with_flush("\n" + "="*100)
    
    def display_capabilities_table(self, capabilities: List[Dict[str, Any]]):
        """Display capabilities in a table format"""
        if not capabilities:
            print_with_flush("No capabilities found")
            return
        
        print_with_flush("\n" + "="*120)
        print_with_flush(f"{'ID':<20} {'Name':<30} {'Domain':<15} {'Status':<12} {'Priority':<10} {'Health':<8} {'Components':<10}")
        print_with_flush("="*120)
        
        for cap in capabilities:
            data = cap.get('Data', {})
            agg = data.get('aggregates', {})
            print_with_flush(
                f"{data.get('capabilityId', 'N/A'):<20} "
                f"{data.get('name', 'Unknown')[:29]:<30} "
                f"{data.get('businessDomain', 'N/A'):<15} "
                f"{data.get('status', 'N/A'):<12} "
                f"{data.get('priority', 'N/A'):<10} "
                f"{agg.get('healthScore', 0):<8.1f} "
                f"{agg.get('totalComponents', 0):<10}"
            )
        
        print_with_flush("="*120)
        print_with_flush(f"Total capabilities: {len(capabilities)}")
    
    # ==================== UTILITY FUNCTIONS ====================
    
    def validate_capability_data(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate capability data
        
        Args:
            data: Capability data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        if not data.get('name'):
            errors.append("Name is required")
        
        if not data.get('businessDomain'):
            errors.append("Business domain is required")
        
        # Valid values
        if data.get('status') and data['status'] not in self.valid_statuses:
            errors.append(f"Invalid status. Must be one of: {', '.join(self.valid_statuses)}")
        
        if data.get('priority') and data['priority'] not in self.valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {', '.join(self.valid_priorities)}")
        
        if data.get('businessDomain') and data['businessDomain'] not in self.valid_business_domains:
            errors.append(f"Invalid business domain. Must be one of: {', '.join(self.valid_business_domains)}")
        
        return errors
    
    def calculate_health_score(self, capability_id: str) -> float:
        """
        Calculate health score for a capability based on components and metrics
        
        Args:
            capability_id: The capability ID
            
        Returns:
            Health score (0-100)
        """
        try:
            # Get all components for the capability
            components = self.get_capability_components(capability_id)
            
            if not components:
                return 100.0  # No components = perfect health (nothing to break)
            
            total_score = 0
            component_count = 0
            
            for component in components:
                comp_data = component.get('Data', {})
                health = comp_data.get('health', {})
                
                # Calculate component score
                comp_score = 100.0
                
                # Deduct for availability
                availability = health.get('availability', 100)
                comp_score -= (100 - availability) * 0.5
                
                # Deduct for error rate
                error_rate = health.get('errorRate', 0)
                comp_score -= error_rate * 10
                
                # Deduct for active alerts
                active_alerts = health.get('activeAlerts', 0)
                comp_score -= active_alerts * 5
                
                # Ensure score doesn't go negative
                comp_score = max(0, comp_score)
                
                total_score += comp_score
                component_count += 1
            
            return round(total_score / component_count, 2) if component_count > 0 else 100.0
            
        except Exception as e:
            print_with_flush(f"⚠️ Error calculating health score: {str(e)}")
            return 0.0
    
    def get_capability_components(self, capability_id: str) -> List[Dict[str, Any]]:
        """
        Get all components for a capability
        
        Args:
            capability_id: The capability ID
            
        Returns:
            List of components
        """
        try:
            components = []
            
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'CAPABILITY#{capability_id}',
                    ':sk': 'COMPONENT#'
                }
            )
            
            components.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    ExpressionAttributeValues={
                        ':pk': f'CAPABILITY#{capability_id}',
                        ':sk': 'COMPONENT#'
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                components.extend(response.get('Items', []))
            
            return components
            
        except ClientError as e:
            print_with_flush(f"❌ Error getting components: {e.response['Error']['Message']}")
            return []
    
    def get_capabilities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all capabilities in a specific business domain
        
        Args:
            domain: Business domain
            
        Returns:
            List of capabilities
        """
        try:
            capabilities = []
            
            # Use GSI2 if available, otherwise filter from all capabilities
            if hasattr(self, 'has_gsi2') and self.has_gsi2:
                response = self.table.query(
                    IndexName='GSI2',
                    KeyConditionExpression='GSI2PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': f'DOMAIN#{domain}'
                    }
                )
                capabilities.extend(response.get('Items', []))
            else:
                # Fall back to filtering all capabilities
                all_caps = self.list_capabilities()
                capabilities = [c for c in all_caps if c.get('Data', {}).get('businessDomain') == domain]
            
            return capabilities
            
        except ClientError as e:
            print_with_flush(f"❌ Error getting capabilities by domain: {e.response['Error']['Message']}")
            return []
    
    def update_aggregates(self, capability_id: str):
        """
        Update aggregate statistics for a capability
        
        Args:
            capability_id: The capability ID
        """
        try:
            # Get components
            components = self.get_capability_components(capability_id)
            
            # Calculate aggregates
            total_components = len(components)
            active_components = len([c for c in components if c.get('Data', {}).get('status') == 'active'])
            
            # Calculate health score
            health_score = self.calculate_health_score(capability_id)
            
            # Update capability aggregates
            updates = {
                'aggregates': {
                    'totalComponents': total_components,
                    'activeComponents': active_components,
                    'healthScore': health_score
                }
            }
            
            self.update_capability(capability_id, updates)
            
        except Exception as e:
            print_with_flush(f"⚠️ Error updating aggregates: {str(e)}")


class InteractiveCapabilityWizard:
    """Interactive wizard for creating capabilities"""
    
    def __init__(self, manager: CapabilityManager = None):
        """Initialize wizard with optional manager (for unit test compatibility)"""
        self.manager = manager if manager is not None else CapabilityManager()
    
    def run(self) -> Optional[Dict[str, Any]]:
        """Run the interactive capability creation wizard"""
        print_with_flush("\n🧙 CAPABILITY CREATION WIZARD")
        print_with_flush("="*60)
        
        capability_data = {}
        
        # Basic Information
        print_with_flush("\n📝 BASIC INFORMATION:")
        capability_data['name'] = input("Capability name: ").strip()
        if not capability_data['name']:
            print_with_flush("❌ Name is required")
            return None
        
        capability_data['description'] = input("Description: ").strip()
        
        # Business Domain selection with numbered options
        print_with_flush("\n📦 Select Business Domain:")
        for idx, domain in enumerate(self.manager.valid_business_domains, 1):
            print_with_flush(f"  {idx}. {domain}")
        
        try:
            domain_choice = input("Select domain (number): ").strip()
            domain_idx = int(domain_choice) - 1
            if 0 <= domain_idx < len(self.manager.valid_business_domains):
                capability_data['businessDomain'] = self.manager.valid_business_domains[domain_idx]
            else:
                print_with_flush("❌ Invalid selection, using default: operations")
                capability_data['businessDomain'] = 'operations'
        except (ValueError, IndexError):
            print_with_flush("❌ Invalid input, using default: operations")
            capability_data['businessDomain'] = 'operations'
        
        # Priority selection
        print_with_flush("\n⚡ Select Priority:")
        for idx, priority in enumerate(self.manager.valid_priorities, 1):
            print_with_flush(f"  {idx}. {priority}")
        
        try:
            priority_choice = input("Select priority (number) [default: 2-medium]: ").strip()
            if priority_choice:
                priority_idx = int(priority_choice) - 1
                if 0 <= priority_idx < len(self.manager.valid_priorities):
                    capability_data['priority'] = self.manager.valid_priorities[priority_idx]
                else:
                    capability_data['priority'] = 'medium'
            else:
                capability_data['priority'] = 'medium'
        except (ValueError, IndexError):
            capability_data['priority'] = 'medium'
        
        # Owner and creator
        capability_data['owner'] = input("\nOwner team/person (default: unassigned): ").strip() or 'unassigned'
        capability_data['createdBy'] = input("Created by (default: system): ").strip() or 'system'
        
        # Business Metrics
        print_with_flush("\n📈 BUSINESS METRICS (press Enter for defaults):")
        sla = input("  SLA target (e.g., 99.9%): ").strip()
        rto = input("  RTO - Recovery Time Objective (e.g., 5 minutes): ").strip()
        rpo = input("  RPO - Recovery Point Objective (e.g., 1 minute): ").strip()
        
        if sla or rto or rpo:
            capability_data['businessMetrics'] = {}
            if sla:
                capability_data['businessMetrics']['sla'] = sla
            if rto:
                capability_data['businessMetrics']['rto'] = rto
            if rpo:
                capability_data['businessMetrics']['rpo'] = rpo
        
        # Architecture Pattern
        print_with_flush("\n🏗️ Select Architecture Pattern:")
        for idx, pattern in enumerate(self.manager.valid_architecture_patterns, 1):
            print_with_flush(f"  {idx}. {pattern}")
        
        try:
            pattern_choice = input("Select pattern (number) [default: 1-microservices]: ").strip()
            if pattern_choice:
                pattern_idx = int(pattern_choice) - 1
                if 0 <= pattern_idx < len(self.manager.valid_architecture_patterns):
                    arch_pattern = self.manager.valid_architecture_patterns[pattern_idx]
                else:
                    arch_pattern = 'microservices'
            else:
                arch_pattern = 'microservices'
            
            capability_data['architecture'] = {'pattern': arch_pattern}
        except (ValueError, IndexError):
            capability_data['architecture'] = {'pattern': 'microservices'}
        
        # Tags
        tags_input = input("\n🏷️ Tags (comma-separated, optional): ").strip()
        if tags_input:
            capability_data['tags'] = [tag.strip() for tag in tags_input.split(',')]
        
        # Confirmation
        print_with_flush("\n📋 SUMMARY:")
        print_with_flush(f"  Name: {capability_data['name']}")
        print_with_flush(f"  Domain: {capability_data['businessDomain']}")
        print_with_flush(f"  Priority: {capability_data['priority']}")
        print_with_flush(f"  Owner: {capability_data['owner']}")
        
        confirm = input("\n✅ Create capability? (Y/n): ").strip().lower()
        if confirm != 'n':
            return self.manager.create_capability(capability_data)
        else:
            print_with_flush("❌ Cancelled")
            return None


def main():
    """Main function for testing"""
    print_with_flush("\n🚀 BUSINESS CAPABILITY MANAGEMENT SYSTEM")
    print_with_flush("="*60)
    
    manager = CapabilityManager()
    
    while True:
        print_with_flush("\n📋 MAIN MENU:")
        print_with_flush("1. List all capabilities")
        print_with_flush("2. Create new capability")
        print_with_flush("3. View capability details")
        print_with_flush("4. Update capability")
        print_with_flush("5. Delete capability")
        print_with_flush("6. List capabilities by domain")
        print_with_flush("7. Interactive creation wizard")
        print_with_flush("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            # List capabilities
            print_with_flush("\n🔍 Filter Options (press Enter to skip):")
            status = input("Status filter: ").strip() or None
            domain = input("Domain filter: ").strip() or None
            priority = input("Priority filter: ").strip() or None
            
            capabilities = manager.list_capabilities(
                status_filter=status,
                domain_filter=domain,
                priority_filter=priority
            )
            manager.display_capabilities_table(capabilities)
            
        elif choice == '2':
            # Create capability
            print_with_flush("\n📝 Enter capability details:")
            data = {
                'name': input("Name: ").strip(),
                'description': input("Description: ").strip(),
                'businessDomain': input(f"Business Domain ({'/'.join(manager.valid_business_domains)}): ").strip(),
                'priority': input(f"Priority ({'/'.join(manager.valid_priorities)}): ").strip(),
                'owner': input("Owner: ").strip(),
                'createdBy': input("Created by: ").strip()
            }
            
            # Validate
            errors = manager.validate_capability_data(data)
            if errors:
                print_with_flush("❌ Validation errors:")
                for error in errors:
                    print_with_flush(f"  - {error}")
            else:
                capability = manager.create_capability(data)
                if capability:
                    manager.display_capability(capability)
                    
        elif choice == '3':
            # View capability
            cap_id = input("\nEnter capability ID: ").strip()
            capability = manager.get_capability(cap_id)
            if capability:
                manager.display_capability(capability)
                
        elif choice == '4':
            # Update capability
            cap_id = input("\nEnter capability ID: ").strip()
            print_with_flush("Enter updates (JSON format):")
            updates_str = input().strip()
            try:
                updates = json.loads(updates_str) if updates_str else {}
                updated = manager.update_capability(cap_id, updates)
                if updated:
                    manager.display_capability(updated)
            except json.JSONDecodeError:
                print_with_flush("❌ Invalid JSON format")
                
        elif choice == '5':
            # Delete capability
            cap_id = input("\nEnter capability ID: ").strip()
            cascade = input("Delete all related items? (y/N): ").strip().lower() == 'y'
            if manager.delete_capability(cap_id, cascade):
                print_with_flush("✅ Capability deleted")
                
        elif choice == '6':
            # List by domain
            domain = input("\nEnter business domain: ").strip()
            capabilities = manager.get_capabilities_by_domain(domain)
            manager.display_capabilities_table(capabilities)
            
        elif choice == '7':
            # Interactive wizard
            wizard = InteractiveCapabilityWizard(manager)
            capability = wizard.run()
            if capability:
                manager.display_capability(capability)
                
        elif choice == '0':
            print_with_flush("\n👋 Goodbye!")
            break
        else:
            print_with_flush("❌ Invalid choice")


if __name__ == "__main__":
    main()
