#!/usr/bin/env python3
"""
Software Component Management Script
Handles all CRUD operations for software components within business capabilities
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
    get_current_timestamp
)


class ComponentManager:
    """Manager for Software Component operations"""
    
    def __init__(self, dynamodb=None):
        """
        Initialize the Component Manager
        
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
        
        # Component types
        self.component_types = [
            'ui-dashboard', 'api-server', 'mcp-server', 'database',
            'message-queue', 'cache', 'scheduler', 'worker',
            'storage', 'gateway', 'service-mesh', 'monitoring'
        ]
        
        # Layers
        self.layers = ['presentation', 'business', 'data', 'infrastructure']
        
        # Deployment types
        self.deployment_types = ['container', 'serverless', 'vm', 'bare-metal']
        
        # Platforms
        self.platforms = ['kubernetes', 'ecs', 'lambda', 'ec2', 'on-premise']
        
        # Component statuses
        self.statuses = ['planning', 'development', 'testing', 'active', 'maintenance', 'deprecated']
    
    # ==================== COMPONENT CRUD OPERATIONS ====================
    
    def create_component(self, capability_id: str, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new software component for a capability
        
        Args:
            capability_id: The capability ID
            component_data: Dictionary containing component details
            
        Returns:
            Created component with metadata
        """
        try:
            # Generate component ID if not provided
            component_id = component_data.get('componentId') or f"comp-{uuid.uuid4().hex[:8]}"
            timestamp = get_current_timestamp()
            
            # Determine order (priority/criticality)
            order = component_data.get('order', 99)
            
            # Build the data structure
            data = {
                'componentId': component_id,
                'capabilityId': capability_id,
                'name': component_data.get('name', ''),
                'description': component_data.get('description', ''),
                'componentType': component_data.get('componentType', 'api-server'),
                'order': order,
                'layer': component_data.get('layer', 'business'),
                'status': component_data.get('status', 'planning'),
                'version': component_data.get('version', '1.0.0'),
                'technology': component_data.get('technology', {
                    'stack': 'unknown',
                    'framework': 'unknown',
                    'language': 'unknown',
                    'runtime': 'unknown',
                    'dependencies': []
                }),
                'deployment': component_data.get('deployment', {
                    'type': 'container',
                    'platform': 'kubernetes',
                    'image': f"{component_id}:latest",
                    'replicas': 1,
                    'resources': {
                        'cpu': '100m',
                        'memory': '256Mi'
                    },
                    'endpoints': []
                }),
                'configuration': component_data.get('configuration', {
                    'environment': 'development',
                    'configMap': f"{component_id}-config",
                    'secrets': [],
                    'featureFlags': {}
                }),
                'health': component_data.get('health', {
                    'status': 'unknown',
                    'lastCheck': None,
                    'availability': 0,
                    'responseTime': 0,
                    'errorRate': 0,
                    'activeAlerts': 0
                }),
                'sla': component_data.get('sla', {
                    'availability': 99.0,
                    'responseTime': 1000,
                    'errorRate': 1.0
                }),
                'ownership': component_data.get('ownership', {
                    'team': 'unassigned',
                    'leadEngineer': 'unassigned',
                    'oncallRotation': 'unassigned',
                    'slackChannel': '#general'
                }),
                'repository': component_data.get('repository', {
                    'type': 'github',
                    'url': '',
                    'branch': 'main',
                    'cicdPipeline': ''
                })
            }
            
            # Create the DynamoDB item
            item = {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': f'COMPONENT#{order:02d}#{component_id}',
                'EntityType': 'SoftwareComponent',
                'GSI1PK': f"COMPONENT#{data['componentType']}",
                'GSI1SK': f"{capability_id}#{component_id}",
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
                'Data': data
            }
            
            # Put item in DynamoDB
            self.table.put_item(Item=item)
            
            print_with_flush(f"✅ Created component: {component_id} for capability: {capability_id}")
            return item
            
        except ClientError as e:
            print_with_flush(f"❌ Error creating component: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def get_component(self, capability_id: str, component_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            
        Returns:
            Component data or None if not found
        """
        try:
            # We need to search for the component as we don't know the exact SK
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
                FilterExpression='#data.componentId = :comp_id',
                ExpressionAttributeNames={
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':pk': f'CAPABILITY#{capability_id}',
                    ':sk_prefix': 'COMPONENT#',
                    ':comp_id': component_id
                }
            )
            
            items = response.get('Items', [])
            if items:
                return items[0]
            else:
                print_with_flush(f"⚠️ Component {component_id} not found in capability {capability_id}")
                return None
                
        except ClientError as e:
            print_with_flush(f"❌ Error getting component: {e.response['Error']['Message']}")
            raise
    
    def update_component(self, capability_id: str, component_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            updates: Dictionary of fields to update
            
        Returns:
            Updated component
        """
        try:
            # First get the component to find its SK
            current = self.get_component(capability_id, component_id)
            if not current:
                raise ValueError(f"Component {component_id} not found")
            
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
                    'PK': current['PK'],
                    'SK': current['SK']
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
            
            print_with_flush(f"✅ Updated component: {component_id}")
            return response['Attributes']
            
        except ClientError as e:
            print_with_flush(f"❌ Error updating component: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def delete_component(self, capability_id: str, component_id: str) -> bool:
        """
        Delete a component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            
        Returns:
            True if successful
        """
        try:
            # Get the component to find its SK
            component = self.get_component(capability_id, component_id)
            if not component:
                print_with_flush(f"⚠️ Component {component_id} not found")
                return False
            
            # Delete the component
            self.table.delete_item(
                Key={
                    'PK': component['PK'],
                    'SK': component['SK']
                }
            )
            
            # Also delete any dependencies involving this component
            self.delete_component_dependencies(capability_id, component_id)
            
            print_with_flush(f"✅ Deleted component: {component_id}")
            return True
            
        except ClientError as e:
            print_with_flush(f"❌ Error deleting component: {e.response['Error']['Message']}")
            return False
    
    def list_components(self, capability_id: str, 
                       type_filter: Optional[str] = None,
                       status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all components for a capability
        
        Args:
            capability_id: The capability ID
            type_filter: Filter by component type
            status_filter: Filter by status
            
        Returns:
            List of components
        """
        try:
            components = []
            
            # Query components for the capability
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
            
            # Apply filters
            if type_filter:
                components = [c for c in components if c.get('Data', {}).get('componentType') == type_filter]
            
            if status_filter:
                components = [c for c in components if c.get('Data', {}).get('status') == status_filter]
            
            print_with_flush(f"📊 Found {len(components)} components for capability {capability_id}")
            return components
            
        except ClientError as e:
            print_with_flush(f"❌ Error listing components: {e.response['Error']['Message']}")
            return []
    
    def list_components_by_type(self, component_type: str) -> List[Dict[str, Any]]:
        """
        List all components of a specific type across all capabilities
        
        Args:
            component_type: The component type
            
        Returns:
            List of components
        """
        try:
            components = []
            
            # Use GSI1 to query by component type
            response = self.table.query(
                IndexName='GSI1',
                KeyConditionExpression='GSI1PK = :pk',
                ExpressionAttributeValues={
                    ':pk': f'COMPONENT#{component_type}'
                }
            )
            
            components.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    IndexName='GSI1',
                    KeyConditionExpression='GSI1PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': f'COMPONENT#{component_type}'
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                components.extend(response.get('Items', []))
            
            print_with_flush(f"📊 Found {len(components)} {component_type} components")
            return components
            
        except ClientError as e:
            print_with_flush(f"❌ Error listing components by type: {e.response['Error']['Message']}")
            return []
    
    # ==================== DEPENDENCY OPERATIONS ====================
    
    def create_dependency(self, capability_id: str, dependency_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a dependency between components
        
        Args:
            capability_id: The capability ID
            dependency_data: Dictionary containing dependency details
            
        Returns:
            Created dependency
        """
        try:
            timestamp = get_current_timestamp()
            
            source_id = dependency_data.get('sourceComponentId')
            target_id = dependency_data.get('targetComponentId')
            
            if not source_id or not target_id:
                raise ValueError("Source and target component IDs are required")
            
            # Build the data structure
            data = {
                'sourceComponentId': source_id,
                'sourceComponentName': dependency_data.get('sourceComponentName', source_id),
                'targetComponentId': target_id,
                'targetComponentName': dependency_data.get('targetComponentName', target_id),
                'dependencyType': dependency_data.get('dependencyType', 'runtime'),
                'criticality': dependency_data.get('criticality', 'medium'),
                'interface': dependency_data.get('interface', {}),
                'requirements': dependency_data.get('requirements', {}),
                'fallback': dependency_data.get('fallback', {
                    'strategy': 'none',
                    'timeout': '30s',
                    'retries': 3,
                    'backupComponent': None
                }),
                'contract': dependency_data.get('contract', {}),
                'monitoring': dependency_data.get('monitoring', {
                    'sliEnabled': False,
                    'alertThreshold': {}
                })
            }
            
            # Determine criticality order
            criticality_order = {
                'critical': 1,
                'high': 2,
                'medium': 3,
                'low': 4
            }.get(data['criticality'], 5)
            
            # Create the DynamoDB item
            item = {
                'PK': f'CAPABILITY#{capability_id}',
                'SK': f'DEPENDENCY#{source_id}#{target_id}',
                'EntityType': 'ComponentDependency',
                'GSI1PK': f'CAPABILITY#{capability_id}#DEPENDENCIES',
                'GSI1SK': f"{criticality_order:02d}#{source_id}#{target_id}",
                'CreatedAt': timestamp,
                'UpdatedAt': timestamp,
                'Data': data
            }
            
            # Put item in DynamoDB
            self.table.put_item(Item=item)
            
            print_with_flush(f"✅ Created dependency: {source_id} → {target_id}")
            return item
            
        except ClientError as e:
            print_with_flush(f"❌ Error creating dependency: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            print_with_flush(f"❌ Unexpected error: {str(e)}")
            raise
    
    def list_dependencies(self, capability_id: str) -> List[Dict[str, Any]]:
        """
        List all dependencies for a capability
        
        Args:
            capability_id: The capability ID
            
        Returns:
            List of dependencies
        """
        try:
            dependencies = []
            
            # Query dependencies for the capability
            response = self.table.query(
                KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                ExpressionAttributeValues={
                    ':pk': f'CAPABILITY#{capability_id}',
                    ':sk': 'DEPENDENCY#'
                }
            )
            
            dependencies.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
                    ExpressionAttributeValues={
                        ':pk': f'CAPABILITY#{capability_id}',
                        ':sk': 'DEPENDENCY#'
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                dependencies.extend(response.get('Items', []))
            
            print_with_flush(f"📊 Found {len(dependencies)} dependencies for capability {capability_id}")
            return dependencies
            
        except ClientError as e:
            print_with_flush(f"❌ Error listing dependencies: {e.response['Error']['Message']}")
            return []
    
    def delete_component_dependencies(self, capability_id: str, component_id: str):
        """
        Delete all dependencies involving a component
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
        """
        try:
            # Get all dependencies
            dependencies = self.list_dependencies(capability_id)
            
            # Find dependencies involving this component
            to_delete = []
            for dep in dependencies:
                data = dep.get('Data', {})
                if data.get('sourceComponentId') == component_id or data.get('targetComponentId') == component_id:
                    to_delete.append(dep)
            
            # Delete them
            if to_delete:
                with self.table.batch_writer() as batch:
                    for dep in to_delete:
                        batch.delete_item(
                            Key={
                                'PK': dep['PK'],
                                'SK': dep['SK']
                            }
                        )
                
                print_with_flush(f"✅ Deleted {len(to_delete)} dependencies for component {component_id}")
                
        except Exception as e:
            print_with_flush(f"⚠️ Error deleting dependencies: {str(e)}")
    
    # ==================== HEALTH & METRICS ====================
    
    def update_component_health(self, capability_id: str, component_id: str, health_data: Dict[str, Any]):
        """
        Update component health metrics
        
        Args:
            capability_id: The capability ID
            component_id: The component ID
            health_data: Health metrics data
        """
        try:
            updates = {
                'health': {
                    'status': health_data.get('status', 'unknown'),
                    'lastCheck': get_current_timestamp(),
                    'availability': health_data.get('availability', 0),
                    'responseTime': health_data.get('responseTime', 0),
                    'errorRate': health_data.get('errorRate', 0),
                    'activeAlerts': health_data.get('activeAlerts', 0)
                }
            }
            
            self.update_component(capability_id, component_id, updates)
            print_with_flush(f"✅ Updated health for component: {component_id}")
            
        except Exception as e:
            print_with_flush(f"❌ Error updating component health: {str(e)}")
    
    # ==================== DISPLAY FUNCTIONS ====================
    
    def display_component(self, component: Dict[str, Any]):
        """Display component details in a formatted way"""
        data = component.get('Data', {})
        
        print_with_flush("\n" + "="*80)
        print_with_flush(f"🔧 COMPONENT: {data.get('name', 'Unknown')}")
        print_with_flush("="*80)
        
        # Basic Information
        print_with_flush("\n📋 BASIC INFORMATION:")
        print_with_flush(f"  ID: {data.get('componentId', 'N/A')}")
        print_with_flush(f"  Type: {data.get('componentType', 'N/A')}")
        print_with_flush(f"  Layer: {data.get('layer', 'N/A')}")
        print_with_flush(f"  Status: {data.get('status', 'N/A')}")
        print_with_flush(f"  Version: {data.get('version', 'N/A')}")
        print_with_flush(f"  Order/Priority: {data.get('order', 'N/A')}")
        
        # Technology Stack
        tech = data.get('technology', {})
        if tech:
            print_with_flush("\n💻 TECHNOLOGY:")
            print_with_flush(f"  Stack: {tech.get('stack', 'N/A')}")
            print_with_flush(f"  Framework: {tech.get('framework', 'N/A')}")
            print_with_flush(f"  Language: {tech.get('language', 'N/A')}")
            print_with_flush(f"  Runtime: {tech.get('runtime', 'N/A')}")
            if tech.get('dependencies'):
                print_with_flush(f"  Dependencies: {', '.join(tech.get('dependencies', []))}")
        
        # Deployment
        deploy = data.get('deployment', {})
        if deploy:
            print_with_flush("\n🚀 DEPLOYMENT:")
            print_with_flush(f"  Type: {deploy.get('type', 'N/A')}")
            print_with_flush(f"  Platform: {deploy.get('platform', 'N/A')}")
            print_with_flush(f"  Image: {deploy.get('image', 'N/A')}")
            print_with_flush(f"  Replicas: {deploy.get('replicas', 'N/A')}")
            if deploy.get('resources'):
                res = deploy['resources']
                print_with_flush(f"  Resources: CPU={res.get('cpu', 'N/A')}, Memory={res.get('memory', 'N/A')}")
        
        # Health
        health = data.get('health', {})
        if health:
            print_with_flush("\n❤️ HEALTH:")
            print_with_flush(f"  Status: {health.get('status', 'N/A')}")
            print_with_flush(f"  Availability: {health.get('availability', 0)}%")
            print_with_flush(f"  Response Time: {health.get('responseTime', 0)}ms")
            print_with_flush(f"  Error Rate: {health.get('errorRate', 0)}%")
            print_with_flush(f"  Active Alerts: {health.get('activeAlerts', 0)}")
        
        # SLA
        sla = data.get('sla', {})
        if sla:
            print_with_flush("\n📈 SLA:")
            print_with_flush(f"  Target Availability: {sla.get('availability', 'N/A')}%")
            print_with_flush(f"  Max Response Time: {sla.get('responseTime', 'N/A')}ms")
            print_with_flush(f"  Max Error Rate: {sla.get('errorRate', 'N/A')}%")
        
        # Ownership
        owner = data.get('ownership', {})
        if owner:
            print_with_flush("\n👥 OWNERSHIP:")
            print_with_flush(f"  Team: {owner.get('team', 'N/A')}")
            print_with_flush(f"  Lead: {owner.get('leadEngineer', 'N/A')}")
            print_with_flush(f"  On-call: {owner.get('oncallRotation', 'N/A')}")
            print_with_flush(f"  Slack: {owner.get('slackChannel', 'N/A')}")
        
        print_with_flush("\n" + "="*80)
    
    def display_components_table(self, components: List[Dict[str, Any]]):
        """Display components in a table format"""
        if not components:
            print_with_flush("No components found")
            return
        
        print_with_flush("\n" + "="*100)
        print_with_flush(f"{'ID':<20} {'Name':<25} {'Type':<15} {'Status':<10} {'Health':<10} {'Version':<10}")
        print_with_flush("="*100)
        
        for comp in components:
            data = comp.get('Data', {})
            health = data.get('health', {})
            print_with_flush(
                f"{data.get('componentId', 'N/A')[:19]:<20} "
                f"{data.get('name', 'Unknown')[:24]:<25} "
                f"{data.get('componentType', 'N/A'):<15} "
                f"{data.get('status', 'N/A'):<10} "
                f"{health.get('status', 'unknown'):<10} "
                f"{data.get('version', 'N/A'):<10}"
            )
        
        print_with_flush("="*100)
        print_with_flush(f"Total components: {len(components)}")
    
    def display_dependency_graph(self, dependencies: List[Dict[str, Any]]):
        """Display dependencies as a graph"""
        if not dependencies:
            print_with_flush("No dependencies found")
            return
        
        print_with_flush("\n🔗 DEPENDENCY GRAPH:")
        print_with_flush("="*60)
        
        for dep in dependencies:
            data = dep.get('Data', {})
            arrow = "→" if data.get('dependencyType') == 'runtime' else "⇢"
            criticality_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(data.get('criticality', 'medium'), '⚪')
            
            print_with_flush(
                f"{criticality_icon} {data.get('sourceComponentName', 'Unknown')} "
                f"{arrow} {data.get('targetComponentName', 'Unknown')} "
                f"({data.get('dependencyType', 'unknown')})"
            )
        
        print_with_flush("="*60)


class InteractiveComponentWizard:
    """Interactive wizard for creating components"""
    
    def __init__(self, manager: ComponentManager = None):
        """Initialize wizard with optional manager (for unit test compatibility)"""
        self.manager = manager if manager is not None else ComponentManager()
    
    def run(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """Run the interactive component creation wizard"""
        print_with_flush("\n🧙 COMPONENT CREATION WIZARD")
        print_with_flush("="*60)
        
        component_data = {}
        
        # Basic Information
        print_with_flush("\n📝 BASIC INFORMATION:")
        component_data['name'] = input("Component name: ").strip()
        if not component_data['name']:
            print_with_flush("❌ Name is required")
            return None
        
        component_data['description'] = input("Description: ").strip()
        
        # Component Type selection
        print_with_flush("\n🔧 Select Component Type:")
        for idx, comp_type in enumerate(self.manager.component_types, 1):
            print_with_flush(f"  {idx}. {comp_type}")
        
        try:
            type_choice = input("Select type (number): ").strip()
            type_idx = int(type_choice) - 1
            if 0 <= type_idx < len(self.manager.component_types):
                component_data['componentType'] = self.manager.component_types[type_idx]
            else:
                component_data['componentType'] = 'api-server'
        except (ValueError, IndexError):
            component_data['componentType'] = 'api-server'
        
        # Layer selection
        print_with_flush("\n📚 Select Layer:")
        for idx, layer in enumerate(self.manager.layers, 1):
            print_with_flush(f"  {idx}. {layer}")
        
        try:
            layer_choice = input("Select layer (number): ").strip()
            layer_idx = int(layer_choice) - 1
            if 0 <= layer_idx < len(self.manager.layers):
                component_data['layer'] = self.manager.layers[layer_idx]
            else:
                component_data['layer'] = 'business'
        except (ValueError, IndexError):
            component_data['layer'] = 'business'
        
        # Order/Priority
        try:
            order = input("\nOrder/Priority (1-99, lower = higher priority) [50]: ").strip()
            component_data['order'] = int(order) if order else 50
        except ValueError:
            component_data['order'] = 50
        
        # Technology Stack
        print_with_flush("\n💻 TECHNOLOGY STACK:")
        stack = input("  Stack (e.g., nodejs, python, java): ").strip()
        framework = input("  Framework (e.g., express, fastapi, spring): ").strip()
        language = input("  Language: ").strip()
        
        if stack or framework or language:
            component_data['technology'] = {
                'stack': stack or 'unknown',
                'framework': framework or 'unknown',
                'language': language or 'unknown',
                'runtime': 'unknown',
                'dependencies': []
            }
        
        # Deployment
        print_with_flush("\n🚀 DEPLOYMENT:")
        print_with_flush("Deployment types: container, serverless, vm, bare-metal")
        deploy_type = input("  Deployment type [container]: ").strip() or 'container'
        
        print_with_flush("Platforms: kubernetes, ecs, lambda, ec2, on-premise")
        platform = input("  Platform [kubernetes]: ").strip() or 'kubernetes'
        
        component_data['deployment'] = {
            'type': deploy_type,
            'platform': platform
        }
        
        # Ownership
        print_with_flush("\n👥 OWNERSHIP:")
        team = input("  Team name: ").strip()
        lead = input("  Lead engineer: ").strip()
        
        if team or lead:
            component_data['ownership'] = {
                'team': team or 'unassigned',
                'leadEngineer': lead or 'unassigned'
            }
        
        # Confirmation
        print_with_flush("\n📋 SUMMARY:")
        print_with_flush(f"  Name: {component_data['name']}")
        print_with_flush(f"  Type: {component_data['componentType']}")
        print_with_flush(f"  Layer: {component_data['layer']}")
        print_with_flush(f"  Order: {component_data.get('order', 50)}")
        
        confirm = input("\n✅ Create component? (Y/n): ").strip().lower()
        if confirm != 'n':
            return self.manager.create_component(capability_id, component_data)
        else:
            print_with_flush("❌ Cancelled")
            return None


def main():
    """Main function for testing"""
    print_with_flush("\n🔧 SOFTWARE COMPONENT MANAGEMENT SYSTEM")
    print_with_flush("="*60)
    
    # Get capability ID
    capability_id = input("Enter capability ID (or 'test' for testing): ").strip()
    if not capability_id:
        capability_id = 'test'
    
    manager = ComponentManager()
    
    while True:
        print_with_flush("\n📋 MAIN MENU:")
        print_with_flush("1. List components")
        print_with_flush("2. Create component")
        print_with_flush("3. View component details")
        print_with_flush("4. Update component")
        print_with_flush("5. Delete component")
        print_with_flush("6. Create dependency")
        print_with_flush("7. List dependencies")
        print_with_flush("8. Update health metrics")
        print_with_flush("9. Interactive wizard")
        print_with_flush("0. Exit")
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            # List components
            components = manager.list_components(capability_id)
            manager.display_components_table(components)
            
        elif choice == '2':
            # Create component
            print_with_flush("\n📝 Enter component details:")
            data = {
                'name': input("Name: ").strip(),
                'componentType': input("Type (ui-dashboard/api-server/etc): ").strip(),
                'layer': input("Layer (presentation/business/data): ").strip(),
                'status': input("Status (planning/development/active): ").strip() or 'planning'
            }
            
            component = manager.create_component(capability_id, data)
            if component:
                manager.display_component(component)
                
        elif choice == '3':
            # View component
            comp_id = input("\nEnter component ID: ").strip()
            component = manager.get_component(capability_id, comp_id)
            if component:
                manager.display_component(component)
                
        elif choice == '4':
            # Update component
            comp_id = input("\nEnter component ID: ").strip()
            print_with_flush("Enter updates (JSON format):")
            updates_str = input().strip()
            try:
                updates = json.loads(updates_str) if updates_str else {}
                updated = manager.update_component(capability_id, comp_id, updates)
                if updated:
                    manager.display_component(updated)
            except json.JSONDecodeError:
                print_with_flush("❌ Invalid JSON format")
                
        elif choice == '5':
            # Delete component
            comp_id = input("\nEnter component ID: ").strip()
            if manager.delete_component(capability_id, comp_id):
                print_with_flush("✅ Component deleted")
                
        elif choice == '6':
            # Create dependency
            print_with_flush("\n🔗 Create Dependency:")
            dep_data = {
                'sourceComponentId': input("Source component ID: ").strip(),
                'targetComponentId': input("Target component ID: ").strip(),
                'dependencyType': input("Type (runtime/buildtime/data): ").strip() or 'runtime',
                'criticality': input("Criticality (low/medium/high/critical): ").strip() or 'medium'
            }
            dependency = manager.create_dependency(capability_id, dep_data)
            if dependency:
                print_with_flush("✅ Dependency created")
                
        elif choice == '7':
            # List dependencies
            dependencies = manager.list_dependencies(capability_id)
            manager.display_dependency_graph(dependencies)
            
        elif choice == '8':
            # Update health
            comp_id = input("\nEnter component ID: ").strip()
            health_data = {
                'status': input("Health status (healthy/degraded/unhealthy): ").strip(),
                'availability': float(input("Availability % (0-100): ").strip() or "0"),
                'responseTime': int(input("Response time (ms): ").strip() or "0"),
                'errorRate': float(input("Error rate % (0-100): ").strip() or "0"),
                'activeAlerts': int(input("Active alerts count: ").strip() or "0")
            }
            manager.update_component_health(capability_id, comp_id, health_data)
            
        elif choice == '9':
            # Interactive wizard
            wizard = InteractiveComponentWizard(manager)
            component = wizard.run(capability_id)
            if component:
                manager.display_component(component)
                
        elif choice == '0':
            print_with_flush("\n👋 Goodbye!")
            break
        else:
            print_with_flush("❌ Invalid choice")


if __name__ == "__main__":
    main()
