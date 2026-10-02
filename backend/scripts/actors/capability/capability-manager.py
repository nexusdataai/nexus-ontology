#!/usr/bin/env python3
"""
TMF ODA Business Capability Manager CLI
Interactive portal for complete capability lifecycle management
Enhanced version integrating all capability-scripts functionality
"""

import sys
import os
import json
import uuid
import time
import importlib.util
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

# TEST MODE - Set to True to run without AWS authentication
TEST_MODE = True

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    if not TEST_MODE:
        print("boto3 not installed. Please install boto3 or run in TEST_MODE")
        sys.exit(1)
    ClientError = Exception  # Mock for test mode

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Conditionally import AWS utilities
if not TEST_MODE:
    try:
        from src.utils.aws_client_utils import create_aws_resource, create_aws_client
    except ImportError:
        print("Warning: AWS utilities not available. Running in TEST_MODE.")
        TEST_MODE = True

# Import capability-scripts modules
capability_scripts_path = os.path.join(project_root, 'scripts', 'capability-scripts')
sys.path.insert(0, capability_scripts_path)

# Import the capability manager
spec = importlib.util.spec_from_file_location(
    "manage_capability", 
    os.path.join(capability_scripts_path, "manage_capability.py")
)
manage_capability_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage_capability_module)

# Import component manager
spec = importlib.util.spec_from_file_location(
    "manage_components",
    os.path.join(capability_scripts_path, "manage_components.py")
)
components_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(components_module)

# Import implementation jobs manager
spec = importlib.util.spec_from_file_location(
    "manage_implementation_jobs",
    os.path.join(capability_scripts_path, "manage_implementation_jobs.py")
)
jobs_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs_module)

# Import performance metrics manager
spec = importlib.util.spec_from_file_location(
    "manage_performance_metrics",
    os.path.join(capability_scripts_path, "manage_performance_metrics.py")
)
metrics_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics_module)


class MenuContext:
    """Manages menu navigation state and breadcrumbs"""
    def __init__(self):
        self.breadcrumbs = ["Main Menu"]
        self.current_menu = "main"
        self.capability_context = None
        self.component_context = None
        self.job_context = None
    
    def push(self, menu_name: str):
        """Add menu to navigation stack"""
        self.breadcrumbs.append(menu_name)
        self.current_menu = menu_name
    
    def pop(self):
        """Remove menu from navigation stack"""
        if len(self.breadcrumbs) > 1:
            self.breadcrumbs.pop()
            self.current_menu = self.breadcrumbs[-1]
    
    def get_breadcrumb_string(self):
        """Get formatted breadcrumb string"""
        return " > ".join(self.breadcrumbs)
    
    def clear(self):
        """Clear navigation stack"""
        self.breadcrumbs = ["Main Menu"]
        self.current_menu = "main"


class EnhancedCapabilityManager:
    """Enhanced Capability Manager with comprehensive functionality"""
    
    def __init__(self):
        """Initialize Enhanced Capability Manager"""
        # Color codes for terminal output (initialize first)
        self.colors = {
            'header': '\033[95m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'green': '\033[92m',
            'warning': '\033[93m',
            'error': '\033[91m',
            'bold': '\033[1m',
            'underline': '\033[4m',
            'end': '\033[0m'
        }
        
        self.test_mode = TEST_MODE
        self.dynamodb = None
        self.s3_client = None
        self.cloudwatch_client = None
        self.current_user = None
        self.current_capability = None
        self.current_component = None
        self.menu_context = MenuContext()
        
        # Initialize managers from capability-scripts
        self.capability_manager = manage_capability_module.CapabilityManager()
        self.component_manager = components_module.ComponentManager()
        self.job_manager = jobs_module.ImplementationJobManager()
        self.metrics_manager = metrics_module.PerformanceMetricsManager()
        
        # Initialize AWS clients (only if not in test mode)
        if not self.test_mode:
            self.init_aws_clients()
        else:
            print(f"{self.colors['warning']}⚠ Running in TEST MODE - No AWS authentication required{self.colors['end']}")
            print(f"{self.colors['blue']}ℹ All operations will use mock data{self.colors['end']}")
    
    def init_aws_clients(self):
        """Initialize AWS service clients"""
        try:
            self.dynamodb = create_aws_resource('dynamodb')
            self.s3_client = create_aws_client('s3')
            self.cloudwatch_client = create_aws_client('cloudwatch')
            print(f"{self.colors['green']}✓ AWS clients initialized successfully{self.colors['end']}")
        except Exception as e:
            print(f"{self.colors['warning']}⚠ Failed to initialize AWS clients: {str(e)}{self.colors['end']}")
            print(f"{self.colors['blue']}ℹ Switching to TEST MODE{self.colors['end']}")
            self.test_mode = True
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self, title: str):
        """Print formatted header"""
        self.clear_screen()
        print(f"\n{self.colors['header']}{'='*80}{self.colors['end']}")
        print(f"{self.colors['bold']}{self.colors['cyan']}{title.center(80)}{self.colors['end']}")
        print(f"{self.colors['header']}{'='*80}{self.colors['end']}")
        
        # Show breadcrumbs
        breadcrumb = self.menu_context.get_breadcrumb_string()
        print(f"{self.colors['blue']}📍 {breadcrumb}{self.colors['end']}")
        
        # Show current context
        if self.current_capability:
            print(f"{self.colors['green']}📦 Current Capability: {self.current_capability.get('name', 'N/A')} ({self.current_capability.get('capabilityId', 'N/A')}){self.colors['end']}")
        if self.current_component:
            print(f"{self.colors['green']}🔧 Current Component: {self.current_component.get('name', 'N/A')}{self.colors['end']}")
        print()
    
    def print_menu_options(self, options: List[Tuple[str, str]]):
        """Print formatted menu options"""
        print(f"\n{self.colors['bold']}Available Options:{self.colors['end']}")
        print("-" * 40)
        for key, description in options:
            if key == '0':
                print(f"{self.colors['warning']}[{key}] {description}{self.colors['end']}")
            else:
                print(f"[{key}] {description}")
    
    def get_user_choice(self, prompt: str = "Select option") -> str:
        """Get user input with formatted prompt"""
        print()
        return input(f"{self.colors['cyan']}{prompt}: {self.colors['end']}").strip()
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"\n{self.colors['green']}✓ {message}{self.colors['end']}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"\n{self.colors['error']}✗ {message}{self.colors['end']}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"\n{self.colors['warning']}⚠ {message}{self.colors['end']}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"\n{self.colors['blue']}ℹ {message}{self.colors['end']}")
    
    def confirm_action(self, message: str) -> bool:
        """Get confirmation for an action"""
        response = input(f"\n{self.colors['warning']}{message} (y/n): {self.colors['end']}").strip().lower()
        return response == 'y'
    
    def pause(self):
        """Pause for user to read output"""
        input(f"\n{self.colors['cyan']}Press Enter to continue...{self.colors['end']}")
    
    # Main Menu Functions
    def main_menu(self):
        """Display main menu"""
        while True:
            self.print_header("🚀 TMF ODA CAPABILITY MANAGER")
            
            options = [
                ('1', '📦 Capability Management'),
                ('2', '🔧 Component Management'),
                ('3', '🚀 Implementation Jobs'),
                ('4', '📊 Performance Metrics'),
                ('5', '📈 Analytics & Reports'),
                ('6', '⚡ Batch Operations'),
                ('7', '🔄 Sync with Journeys'),
                ('8', '⚙️ System Settings'),
                ('0', 'Exit')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.menu_context.push("Capability Management")
                self.capability_menu()
                self.menu_context.pop()
            elif choice == '2':
                self.menu_context.push("Component Management")
                self.component_menu()
                self.menu_context.pop()
            elif choice == '3':
                self.menu_context.push("Implementation Jobs")
                self.jobs_menu()
                self.menu_context.pop()
            elif choice == '4':
                self.menu_context.push("Performance Metrics")
                self.metrics_menu()
                self.menu_context.pop()
            elif choice == '5':
                self.menu_context.push("Analytics & Reports")
                self.analytics_menu()
                self.menu_context.pop()
            elif choice == '6':
                self.menu_context.push("Batch Operations")
                self.batch_operations_menu()
                self.menu_context.pop()
            elif choice == '7':
                self.menu_context.push("Journey Sync")
                self.journey_sync_menu()
                self.menu_context.pop()
            elif choice == '8':
                self.menu_context.push("Settings")
                self.settings_menu()
                self.menu_context.pop()
            elif choice == '0':
                if self.confirm_action("Are you sure you want to exit?"):
                    self.print_info("Thank you for using Capability Manager!")
                    break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Capability Management Menu
    def capability_menu(self):
        """Capability management submenu"""
        while True:
            self.print_header("📦 CAPABILITY MANAGEMENT")
            
            if self.test_mode:
                print(f"{self.colors['warning']}[TEST MODE] Using mock data{self.colors['end']}\n")
            
            options = [
                ('1', '📋 List All Capabilities'),
                ('2', '➕ Create New Capability'),
                ('3', '🔍 View Capability Details'),
                ('4', '✏️ Update Capability'),
                ('5', '🗑️ Delete Capability'),
                ('6', '🏢 List by Business Domain'),
                ('7', '🎯 Set Current Capability'),
                ('8', '🔮 Interactive Creation Wizard'),
                ('9', '📤 Export Capabilities'),
                ('10', '📥 Import Capabilities'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.list_capabilities()
            elif choice == '2':
                self.create_capability()
            elif choice == '3':
                self.view_capability_details()
            elif choice == '4':
                self.update_capability()
            elif choice == '5':
                self.delete_capability()
            elif choice == '6':
                self.list_capabilities_by_domain()
            elif choice == '7':
                self.set_current_capability()
            elif choice == '8':
                self.capability_creation_wizard()
            elif choice == '9':
                self.export_capabilities()
            elif choice == '10':
                self.import_capabilities()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Component Management Menu
    def component_menu(self):
        """Component management submenu"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.set_current_capability()
            if not self.current_capability:
                return
        
        while True:
            self.print_header("🔧 COMPONENT MANAGEMENT")
            
            options = [
                ('1', '📋 List Components'),
                ('2', '➕ Create Component'),
                ('3', '🔍 View Component Details'),
                ('4', '✏️ Update Component'),
                ('5', '🗑️ Delete Component'),
                ('6', '🔗 Manage Dependencies'),
                ('7', '🎯 Set Current Component'),
                ('8', '🔮 Interactive Component Wizard'),
                ('9', '📊 Component Health Check'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.list_components()
            elif choice == '2':
                self.create_component()
            elif choice == '3':
                self.view_component_details()
            elif choice == '4':
                self.update_component()
            elif choice == '5':
                self.delete_component()
            elif choice == '6':
                self.manage_dependencies()
            elif choice == '7':
                self.set_current_component()
            elif choice == '8':
                self.component_creation_wizard()
            elif choice == '9':
                self.component_health_check()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Implementation Jobs Menu
    def jobs_menu(self):
        """Implementation jobs management submenu"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.set_current_capability()
            if not self.current_capability:
                return
        
        while True:
            self.print_header("🚀 IMPLEMENTATION JOBS")
            
            options = [
                ('1', '📋 List Jobs'),
                ('2', '➕ Create New Job'),
                ('3', '🔍 View Job Details'),
                ('4', '▶️ Start Job'),
                ('5', '⏸️ Pause Job'),
                ('6', '✅ Complete Job'),
                ('7', '❌ Cancel Job'),
                ('8', '↩️ Create Rollback'),
                ('9', '📊 Job Timeline'),
                ('10', '📜 View Job Logs'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.list_jobs()
            elif choice == '2':
                self.create_job()
            elif choice == '3':
                self.view_job_details()
            elif choice == '4':
                self.start_job()
            elif choice == '5':
                self.pause_job()
            elif choice == '6':
                self.complete_job()
            elif choice == '7':
                self.cancel_job()
            elif choice == '8':
                self.create_rollback()
            elif choice == '9':
                self.view_job_timeline()
            elif choice == '10':
                self.view_job_logs()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Performance Metrics Menu
    def metrics_menu(self):
        """Performance metrics management submenu"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.set_current_capability()
            if not self.current_capability:
                return
        
        while True:
            self.print_header("📊 PERFORMANCE METRICS")
            
            options = [
                ('1', '📝 Record Metric'),
                ('2', '📊 View Latest Metrics'),
                ('3', '📈 View Metric History'),
                ('4', '🔄 Aggregate Metrics'),
                ('5', '🔔 Create Alert'),
                ('6', '❤️ Health Status'),
                ('7', '📑 Metrics Summary'),
                ('8', '📤 Export Metrics'),
                ('9', '📉 Performance Trends'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.record_metric()
            elif choice == '2':
                self.view_latest_metrics()
            elif choice == '3':
                self.view_metric_history()
            elif choice == '4':
                self.aggregate_metrics()
            elif choice == '5':
                self.create_metric_alert()
            elif choice == '6':
                self.check_health_status()
            elif choice == '7':
                self.metrics_summary()
            elif choice == '8':
                self.export_metrics()
            elif choice == '9':
                self.performance_trends()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Analytics Menu
    def analytics_menu(self):
        """Analytics and reports submenu"""
        while True:
            self.print_header("📈 ANALYTICS & REPORTS")
            
            options = [
                ('1', '📊 Capability Utilization'),
                ('2', '📈 Performance Analysis'),
                ('3', '🔗 Dependency Visualization'),
                ('4', '💼 Business Value Metrics'),
                ('5', '🚀 Job Success Rates'),
                ('6', '💾 Resource Usage'),
                ('7', '📑 Generate Executive Report'),
                ('8', '📤 Export All Reports'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.capability_utilization_report()
            elif choice == '2':
                self.performance_analysis()
            elif choice == '3':
                self.dependency_visualization()
            elif choice == '4':
                self.business_value_metrics()
            elif choice == '5':
                self.job_success_rates()
            elif choice == '6':
                self.resource_usage_report()
            elif choice == '7':
                self.generate_executive_report()
            elif choice == '8':
                self.export_all_reports()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Batch Operations Menu
    def batch_operations_menu(self):
        """Batch operations submenu"""
        while True:
            self.print_header("⚡ BATCH OPERATIONS")
            
            options = [
                ('1', '📥 Batch Import from CSV'),
                ('2', '📤 Batch Export to CSV'),
                ('3', '🔄 Bulk Update Capabilities'),
                ('4', '🚀 Batch Deploy Components'),
                ('5', '📊 Batch Collect Metrics'),
                ('6', '⚙️ Batch Job Execution'),
                ('7', '🧹 Cleanup Operations'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.batch_import_csv()
            elif choice == '2':
                self.batch_export_csv()
            elif choice == '3':
                self.bulk_update_capabilities()
            elif choice == '4':
                self.batch_deploy_components()
            elif choice == '5':
                self.batch_collect_metrics()
            elif choice == '6':
                self.batch_job_execution()
            elif choice == '7':
                self.cleanup_operations()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Journey Sync Menu
    def journey_sync_menu(self):
        """Journey synchronization submenu"""
        while True:
            self.print_header("🔄 JOURNEY SYNCHRONIZATION")
            
            options = [
                ('1', '🔗 Link Capability to Journey'),
                ('2', '📋 List Journey-Linked Capabilities'),
                ('3', '🔄 Sync Status with Journey'),
                ('4', '📊 Journey-Capability Matrix'),
                ('5', '⚠️ Unlink from Journey'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.link_to_journey()
            elif choice == '2':
                self.list_journey_linked()
            elif choice == '3':
                self.sync_with_journey()
            elif choice == '4':
                self.journey_capability_matrix()
            elif choice == '5':
                self.unlink_from_journey()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Settings Menu
    def settings_menu(self):
        """System settings submenu"""
        while True:
            self.print_header("⚙️ SYSTEM SETTINGS")
            
            options = [
                ('1', '👤 User Profile'),
                ('2', '🔑 API Configuration'),
                ('3', '📊 Default Settings'),
                ('4', '🎨 Display Preferences'),
                ('5', '📝 Export Configuration'),
                ('6', '📥 Import Configuration'),
                ('0', 'Back to Main Menu')
            ]
            
            self.print_menu_options(options)
            choice = self.get_user_choice()
            
            if choice == '1':
                self.user_profile()
            elif choice == '2':
                self.api_configuration()
            elif choice == '3':
                self.default_settings()
            elif choice == '4':
                self.display_preferences()
            elif choice == '5':
                self.export_configuration()
            elif choice == '6':
                self.import_configuration()
            elif choice == '0':
                break
            else:
                self.print_error("Invalid option. Please try again.")
                self.pause()
    
    # Capability Management Functions
    def list_capabilities(self):
        """List all capabilities with filtering"""
        self.print_header("📋 LIST CAPABILITIES")
        
        # Get filter options
        print("Filter Options (press Enter to skip):")
        status_filter = input("Status (pending/active/deprecated): ").strip() or None
        domain_filter = input("Business Domain: ").strip() or None
        priority_filter = input("Priority (low/medium/high/critical): ").strip() or None
        
        try:
            if self.test_mode:
                # Use mock data in test mode
                capabilities = self._get_mock_capabilities()
                if status_filter:
                    capabilities = [c for c in capabilities if c.get('status') == status_filter]
                if domain_filter:
                    capabilities = [c for c in capabilities if c.get('businessDomain') == domain_filter]
                if priority_filter:
                    capabilities = [c for c in capabilities if c.get('priority') == priority_filter]
            else:
                capabilities = self.capability_manager.list_capabilities(
                    status_filter=status_filter,
                    domain_filter=domain_filter,
                    priority_filter=priority_filter
                )
            
            if capabilities:
                self.capability_manager.display_capabilities_table(capabilities)
                self.print_success(f"Found {len(capabilities)} capabilities")
            else:
                self.print_warning("No capabilities found matching criteria")
        except Exception as e:
            self.print_error(f"Error listing capabilities: {str(e)}")
        
        self.pause()
    
    def create_capability(self):
        """Create a new capability"""
        self.print_header("➕ CREATE NEW CAPABILITY")
        
        print("Enter capability details:")
        data = {}
        
        # Basic information
        data['name'] = input("Name: ").strip()
        data['description'] = input("Description: ").strip()
        
        # Business Domain selection with numbered options
        print(f"\n{self.colors['cyan']}📦 Select Business Domain:{self.colors['end']}")
        for idx, domain in enumerate(self.capability_manager.valid_business_domains, 1):
            print(f"  [{idx}] {domain}")
        
        try:
            domain_choice = input(f"\n{self.colors['cyan']}Select domain (1-{len(self.capability_manager.valid_business_domains)}): {self.colors['end']}").strip()
            domain_idx = int(domain_choice) - 1
            if 0 <= domain_idx < len(self.capability_manager.valid_business_domains):
                data['businessDomain'] = self.capability_manager.valid_business_domains[domain_idx]
                print(f"{self.colors['green']}✓ Selected: {data['businessDomain']}{self.colors['end']}")
            else:
                self.print_warning("Invalid selection, using default: operations")
                data['businessDomain'] = 'operations'
        except (ValueError, IndexError):
            self.print_warning("Invalid input, using default: operations")
            data['businessDomain'] = 'operations'
        
        # Priority selection with numbered options
        print(f"\n{self.colors['cyan']}⚡ Select Priority:{self.colors['end']}")
        for idx, priority in enumerate(self.capability_manager.valid_priorities, 1):
            print(f"  [{idx}] {priority}")
        
        try:
            priority_choice = input(f"\n{self.colors['cyan']}Select priority (1-{len(self.capability_manager.valid_priorities)}): {self.colors['end']}").strip()
            priority_idx = int(priority_choice) - 1
            if 0 <= priority_idx < len(self.capability_manager.valid_priorities):
                data['priority'] = self.capability_manager.valid_priorities[priority_idx]
                print(f"{self.colors['green']}✓ Selected: {data['priority']}{self.colors['end']}")
            else:
                self.print_warning("Invalid selection, using default: medium")
                data['priority'] = 'medium'
        except (ValueError, IndexError):
            self.print_warning("Invalid input, using default: medium")
            data['priority'] = 'medium'
        
        # Owner and creator information
        print()  # Add spacing
        data['owner'] = input("Owner: ").strip()
        data['createdBy'] = self.current_user or input("Created by: ").strip()
        
        # Validate
        errors = self.capability_manager.validate_capability_data(data)
        if errors:
            self.print_error("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            self.pause()
            return
        
        if self.confirm_action("Create this capability?"):
            try:
                if self.test_mode:
                    # Mock creation in test mode
                    capability_id = f"CAP-{uuid.uuid4().hex[:8].upper()}"
                    self.print_success(f"[TEST MODE] Capability created successfully with ID: {capability_id}")
                else:
                    capability_id = self.capability_manager.create_capability(data)
                    self.print_success(f"Capability created successfully with ID: {capability_id}")
            except Exception as e:
                self.print_error(f"Error creating capability: {str(e)}")
        
        self.pause()
    
    def view_capability_details(self):
        """View detailed information about a capability"""
        self.print_header("🔍 VIEW CAPABILITY DETAILS")
        
        capability_id = input("Enter Capability ID: ").strip()
        if not capability_id:
            self.print_warning("Capability ID is required")
            self.pause()
            return
        
        try:
            if self.test_mode:
                # Use mock data in test mode
                capabilities = self._get_mock_capabilities()
                capability = next((c for c in capabilities if c['capabilityId'] == capability_id), None)
                if capability:
                    print("\nCapability Details:")
                    print("="*60)
                    for key, value in capability.items():
                        print(f"{key}: {value}")
                else:
                    self.print_warning(f"Capability {capability_id} not found")
            else:
                capability = self.capability_manager.get_capability(capability_id)
                if capability:
                    self.capability_manager.display_capability_details(capability)
                else:
                    self.print_warning(f"Capability {capability_id} not found")
        except Exception as e:
            self.print_error(f"Error retrieving capability: {str(e)}")
        
        self.pause()
    
    def update_capability(self):
        """Update capability information"""
        self.print_header("✏️ UPDATE CAPABILITY")
        
        capability_id = input("Enter Capability ID: ").strip()
        if not capability_id:
            self.print_warning("Capability ID is required")
            self.pause()
            return
        
        # Get current capability
        try:
            capability = self.capability_manager.get_capability(capability_id)
            if not capability:
                self.print_warning(f"Capability {capability_id} not found")
                self.pause()
                return
            
            print("\nCurrent values (press Enter to keep current):")
            updates = {}
            
            # Name
            current = capability.get('name', '')
            new_value = input(f"Name [{current}]: ").strip()
            if new_value:
                updates['name'] = new_value
            
            # Description
            current = capability.get('description', '')
            new_value = input(f"Description [{current}]: ").strip()
            if new_value:
                updates['description'] = new_value
            
            # Status selection with numbered options
            current = capability.get('status', '')
            print(f"\n{self.colors['cyan']}📊 Update Status (current: {current}):{self.colors['end']}")
            print("  [Enter] Keep current")
            for idx, status in enumerate(self.capability_manager.valid_statuses, 1):
                print(f"  [{idx}] {status}")
            
            status_choice = input(f"\n{self.colors['cyan']}Select status or press Enter to skip: {self.colors['end']}").strip()
            if status_choice:
                try:
                    status_idx = int(status_choice) - 1
                    if 0 <= status_idx < len(self.capability_manager.valid_statuses):
                        updates['status'] = self.capability_manager.valid_statuses[status_idx]
                        print(f"{self.colors['green']}✓ Updated to: {updates['status']}{self.colors['end']}")
                except (ValueError, IndexError):
                    self.print_warning("Invalid input, keeping current value")
            
            # Priority selection with numbered options
            current = capability.get('priority', '')
            print(f"\n{self.colors['cyan']}⚡ Update Priority (current: {current}):{self.colors['end']}")
            print("  [Enter] Keep current")
            for idx, priority in enumerate(self.capability_manager.valid_priorities, 1):
                print(f"  [{idx}] {priority}")
            
            priority_choice = input(f"\n{self.colors['cyan']}Select priority or press Enter to skip: {self.colors['end']}").strip()
            if priority_choice:
                try:
                    priority_idx = int(priority_choice) - 1
                    if 0 <= priority_idx < len(self.capability_manager.valid_priorities):
                        updates['priority'] = self.capability_manager.valid_priorities[priority_idx]
                        print(f"{self.colors['green']}✓ Updated to: {updates['priority']}{self.colors['end']}")
                except (ValueError, IndexError):
                    self.print_warning("Invalid input, keeping current value")
            
            if updates:
                if self.confirm_action("Update capability?"):
                    result = self.capability_manager.update_capability(capability_id, updates)
                    if result:
                        self.print_success("Capability updated successfully")
                    else:
                        self.print_error("Failed to update capability")
            else:
                self.print_warning("No changes specified")
        except Exception as e:
            self.print_error(f"Error updating capability: {str(e)}")
        
        self.pause()
    
    def delete_capability(self):
        """Delete a capability"""
        self.print_header("🗑️ DELETE CAPABILITY")
        
        capability_id = input("Enter Capability ID: ").strip()
        if not capability_id:
            self.print_warning("Capability ID is required")
            self.pause()
            return
        
        # Check if capability exists
        try:
            capability = self.capability_manager.get_capability(capability_id)
            if not capability:
                self.print_warning(f"Capability {capability_id} not found")
                self.pause()
                return
            
            self.print_warning(f"This will delete capability: {capability.get('name', 'Unknown')}")
            if self.confirm_action("Are you sure you want to delete this capability?"):
                result = self.capability_manager.delete_capability(capability_id)
                if result:
                    self.print_success("Capability deleted successfully")
                    if self.current_capability and self.current_capability.get('capabilityId') == capability_id:
                        self.current_capability = None
                else:
                    self.print_error("Failed to delete capability")
        except Exception as e:
            self.print_error(f"Error deleting capability: {str(e)}")
        
        self.pause()
    
    def list_capabilities_by_domain(self):
        """List capabilities grouped by business domain"""
        self.print_header("🏢 CAPABILITIES BY BUSINESS DOMAIN")
        
        try:
            capabilities = self.capability_manager.list_capabilities()
            
            # Group by domain
            by_domain = {}
            for cap in capabilities:
                domain = cap.get('businessDomain', 'Unknown')
                if domain not in by_domain:
                    by_domain[domain] = []
                by_domain[domain].append(cap)
            
            # Display grouped
            for domain in sorted(by_domain.keys()):
                print(f"\n{self.colors['bold']}{domain}:{self.colors['end']}")
                print("-" * 40)
                for cap in by_domain[domain]:
                    status_color = self.colors['green'] if cap.get('status') == 'active' else self.colors['warning']
                    print(f"  • {cap.get('capabilityId')} - {cap.get('name')} [{status_color}{cap.get('status')}{self.colors['end']}]")
            
            self.print_success(f"Total: {len(capabilities)} capabilities across {len(by_domain)} domains")
        except Exception as e:
            self.print_error(f"Error listing capabilities by domain: {str(e)}")
        
        self.pause()
    
    def set_current_capability(self):
        """Set the current working capability"""
        self.print_header("🎯 SET CURRENT CAPABILITY")
        
        capability_id = input("Enter Capability ID (or 'list' to see available): ").strip()
        
        if capability_id.lower() == 'list':
            if self.test_mode:
                capabilities = self._get_mock_capabilities()
                print("\nAvailable Capabilities:")
                print("="*60)
                for cap in capabilities:
                    print(f"  {cap['capabilityId']}: {cap['name']} [{cap['status']}]")
            else:
                capabilities = self.capability_manager.list_capabilities()
                self.capability_manager.display_capabilities_table(capabilities)
            capability_id = input("\nEnter Capability ID: ").strip()
        
        if not capability_id:
            self.print_warning("Capability ID is required")
            self.pause()
            return
        
        try:
            if self.test_mode:
                capabilities = self._get_mock_capabilities()
                capability = next((c for c in capabilities if c['capabilityId'] == capability_id), None)
            else:
                capability = self.capability_manager.get_capability(capability_id)
            
            if capability:
                self.current_capability = capability
                self.print_success(f"Current capability set to: {capability.get('name')}")
            else:
                self.print_warning(f"Capability {capability_id} not found")
        except Exception as e:
            self.print_error(f"Error setting current capability: {str(e)}")
        
        self.pause()
    
    def capability_creation_wizard(self):
        """Interactive wizard for creating a capability"""
        self.print_header("🔮 CAPABILITY CREATION WIZARD")
        
        try:
            wizard = manage_capability_module.InteractiveCapabilityWizard(self.capability_manager)
            capability_id = wizard.run()
            if capability_id:
                self.print_success(f"Capability created successfully with ID: {capability_id}")
            else:
                self.print_warning("Capability creation cancelled")
        except Exception as e:
            self.print_error(f"Error in creation wizard: {str(e)}")
        
        self.pause()
    
    def export_capabilities(self):
        """Export capabilities to file"""
        self.print_header("📤 EXPORT CAPABILITIES")
        
        format_type = input("Export format (json/csv) [json]: ").strip().lower() or 'json'
        filename = input(f"Output filename [capabilities.{format_type}]: ").strip() or f"capabilities.{format_type}"
        
        try:
            capabilities = self.capability_manager.list_capabilities()
            
            if format_type == 'json':
                import json
                with open(filename, 'w') as f:
                    json.dump(capabilities, f, indent=2, default=str)
            elif format_type == 'csv':
                import csv
                if capabilities:
                    with open(filename, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=capabilities[0].keys())
                        writer.writeheader()
                        writer.writerows(capabilities)
            else:
                self.print_error("Unsupported format")
                self.pause()
                return
            
            self.print_success(f"Exported {len(capabilities)} capabilities to {filename}")
        except Exception as e:
            self.print_error(f"Error exporting capabilities: {str(e)}")
        
        self.pause()
    
    def import_capabilities(self):
        """Import capabilities from file"""
        self.print_header("📥 IMPORT CAPABILITIES")
        
        filename = input("Input filename: ").strip()
        if not filename or not os.path.exists(filename):
            self.print_warning("File not found")
            self.pause()
            return
        
        try:
            if filename.endswith('.json'):
                import json
                with open(filename, 'r') as f:
                    capabilities = json.load(f)
            elif filename.endswith('.csv'):
                import csv
                capabilities = []
                with open(filename, 'r') as f:
                    reader = csv.DictReader(f)
                    capabilities = list(reader)
            else:
                self.print_error("Unsupported file format")
                self.pause()
                return
            
            self.print_info(f"Found {len(capabilities)} capabilities to import")
            if self.confirm_action("Proceed with import?"):
                success_count = 0
                for cap in capabilities:
                    try:
                        # Remove ID if present (will generate new)
                        cap.pop('capabilityId', None)
                        self.capability_manager.create_capability(cap)
                        success_count += 1
                    except Exception as e:
                        self.print_warning(f"Failed to import {cap.get('name', 'Unknown')}: {str(e)}")
                
                self.print_success(f"Successfully imported {success_count}/{len(capabilities)} capabilities")
        except Exception as e:
            self.print_error(f"Error importing capabilities: {str(e)}")
        
        self.pause()
    
    # Component Management Functions
    def list_components(self):
        """List components for current capability"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📋 LIST COMPONENTS")
        
        try:
            if self.test_mode:
                # Use mock data in test mode
                components = [c for c in self._get_mock_components() 
                            if c['capabilityId'] == self.current_capability['capabilityId']]
                if components:
                    print("\nComponents:")
                    print("="*60)
                    for comp in components:
                        print(f"\n{comp['componentId']}: {comp['name']}")
                        print(f"  Type: {comp['type']}")
                        print(f"  Version: {comp['version']}")
                        print(f"  Status: {comp['status']}")
                    self.print_success(f"Found {len(components)} components")
                else:
                    self.print_warning("No components found")
            else:
                components = self.component_manager.list_components(
                    self.current_capability['capabilityId']
                )
                
                if components:
                    self.component_manager.display_components_table(components)
                    self.print_success(f"Found {len(components)} components")
                else:
                    self.print_warning("No components found")
        except Exception as e:
            self.print_error(f"Error listing components: {str(e)}")
        
        self.pause()
    
    def create_component(self):
        """Create a new component"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("➕ CREATE NEW COMPONENT")
        
        print("Enter component details:")
        data = {}
        
        # Basic information
        data['name'] = input("Name: ").strip()
        
        # Component Type selection with numbered options
        print(f"\n{self.colors['cyan']}🔧 Select Component Type:{self.colors['end']}")
        for idx, comp_type in enumerate(self.component_manager.valid_component_types, 1):
            print(f"  [{idx}] {comp_type}")
        
        try:
            type_choice = input(f"\n{self.colors['cyan']}Select type (1-{len(self.component_manager.valid_component_types)}): {self.colors['end']}").strip()
            type_idx = int(type_choice) - 1
            if 0 <= type_idx < len(self.component_manager.valid_component_types):
                data['type'] = self.component_manager.valid_component_types[type_idx]
                print(f"{self.colors['green']}✓ Selected: {data['type']}{self.colors['end']}")
            else:
                self.print_warning("Invalid selection, using default: api-server")
                data['type'] = 'api-server'
        except (ValueError, IndexError):
            self.print_warning("Invalid input, using default: api-server")
            data['type'] = 'api-server'
        
        # Other component details
        print()  # Add spacing
        data['version'] = input("Version: ").strip()
        data['repository'] = input("Repository URL: ").strip()
        data['description'] = input("Description: ").strip()
        data['owner'] = input("Owner: ").strip()
        
        # Validate
        errors = self.component_manager.validate_component_data(data)
        if errors:
            self.print_error("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            self.pause()
            return
        
        if self.confirm_action("Create this component?"):
            try:
                component_id = self.component_manager.create_component(
                    self.current_capability['capabilityId'],
                    data
                )
                self.print_success(f"Component created successfully with ID: {component_id}")
            except Exception as e:
                self.print_error(f"Error creating component: {str(e)}")
        
        self.pause()
    
    def view_component_details(self):
        """View detailed information about a component"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔍 VIEW COMPONENT DETAILS")
        
        component_id = input("Enter Component ID: ").strip()
        if not component_id:
            self.print_warning("Component ID is required")
            self.pause()
            return
        
        try:
            component = self.component_manager.get_component(
                self.current_capability['capabilityId'],
                component_id
            )
            if component:
                self.component_manager.display_component_details(component)
            else:
                self.print_warning(f"Component {component_id} not found")
        except Exception as e:
            self.print_error(f"Error retrieving component: {str(e)}")
        
        self.pause()
    
    def update_component(self):
        """Update component information"""
        # Implementation similar to update_capability
        self.print_info("Component update functionality")
        self.pause()
    
    def delete_component(self):
        """Delete a component"""
        # Implementation similar to delete_capability
        self.print_info("Component deletion functionality")
        self.pause()
    
    def manage_dependencies(self):
        """Manage component dependencies"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔗 MANAGE DEPENDENCIES")
        
        options = [
            ('1', 'Add Dependency'),
            ('2', 'Remove Dependency'),
            ('3', 'View Dependencies'),
            ('0', 'Back')
        ]
        
        self.print_menu_options(options)
        choice = self.get_user_choice()
        
        if choice == '1':
            # Add dependency
            component_id = input("Component ID: ").strip()
            depends_on = input("Depends on Component ID: ").strip()
            if component_id and depends_on:
                try:
                    self.component_manager.add_dependency(
                        self.current_capability['capabilityId'],
                        component_id,
                        depends_on
                    )
                    self.print_success("Dependency added successfully")
                except Exception as e:
                    self.print_error(f"Error adding dependency: {str(e)}")
        elif choice == '3':
            # View dependencies
            component_id = input("Component ID: ").strip()
            if component_id:
                try:
                    deps = self.component_manager.get_dependencies(
                        self.current_capability['capabilityId'],
                        component_id
                    )
                    if deps:
                        print("\nDependencies:")
                        for dep in deps:
                            print(f"  • {dep}")
                    else:
                        self.print_warning("No dependencies found")
                except Exception as e:
                    self.print_error(f"Error getting dependencies: {str(e)}")
        
        self.pause()
    
    def set_current_component(self):
        """Set the current working component"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🎯 SET CURRENT COMPONENT")
        
        component_id = input("Enter Component ID: ").strip()
        if not component_id:
            self.print_warning("Component ID is required")
            self.pause()
            return
        
        try:
            component = self.component_manager.get_component(
                self.current_capability['capabilityId'],
                component_id
            )
            if component:
                self.current_component = component
                self.print_success(f"Current component set to: {component.get('name')}")
            else:
                self.print_warning(f"Component {component_id} not found")
        except Exception as e:
            self.print_error(f"Error setting current component: {str(e)}")
        
        self.pause()
    
    def component_creation_wizard(self):
        """Interactive wizard for creating a component"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔮 COMPONENT CREATION WIZARD")
        
        try:
            wizard = components_module.InteractiveComponentWizard(
                self.component_manager,
                self.current_capability['capabilityId']
            )
            component_id = wizard.run()
            if component_id:
                self.print_success(f"Component created successfully with ID: {component_id}")
            else:
                self.print_warning("Component creation cancelled")
        except Exception as e:
            self.print_error(f"Error in creation wizard: {str(e)}")
        
        self.pause()
    
    def component_health_check(self):
        """Check health status of components"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📊 COMPONENT HEALTH CHECK")
        
        try:
            components = self.component_manager.list_components(
                self.current_capability['capabilityId']
            )
            
            print("\nComponent Health Status:")
            print("-" * 60)
            for comp in components:
                status = comp.get('status', 'unknown')
                if status == 'active':
                    status_icon = "✅"
                    color = self.colors['green']
                elif status == 'inactive':
                    status_icon = "⚠️"
                    color = self.colors['warning']
                else:
                    status_icon = "❌"
                    color = self.colors['error']
                
                print(f"{status_icon} {comp.get('name')} - {color}{status}{self.colors['end']}")
        except Exception as e:
            self.print_error(f"Error checking component health: {str(e)}")
        
        self.pause()
    
    # Implementation Jobs Functions
    def list_jobs(self):
        """List implementation jobs"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📋 LIST JOBS")
        
        status_filter = input("Filter by status (optional): ").strip() or None
        
        try:
            if self.test_mode:
                # Use mock data in test mode
                jobs = [j for j in self._get_mock_jobs() 
                       if j['capabilityId'] == self.current_capability['capabilityId']]
                if status_filter:
                    jobs = [j for j in jobs if j.get('status') == status_filter]
                
                if jobs:
                    print("\nJobs:")
                    print("="*60)
                    for job in jobs:
                        print(f"\n{job['jobId']}: {job['name']}")
                        print(f"  Type: {job['type']}")
                        print(f"  Status: {job['status']}")
                        print(f"  Assigned To: {job['assignedTo']}")
                    self.print_success(f"Found {len(jobs)} jobs")
                else:
                    self.print_warning("No jobs found")
            else:
                jobs = self.job_manager.list_jobs(
                    self.current_capability['capabilityId'],
                    status_filter=status_filter
                )
                
                if jobs:
                    self.job_manager.display_jobs_table(jobs)
                    self.print_success(f"Found {len(jobs)} jobs")
                else:
                    self.print_warning("No jobs found")
        except Exception as e:
            self.print_error(f"Error listing jobs: {str(e)}")
        
        self.pause()
    
    def create_job(self):
        """Create a new implementation job"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("➕ CREATE NEW JOB")
        
        print("Enter job details:")
        data = {}
        
        # Basic information
        data['name'] = input("Job name: ").strip()
        
        # Job Type selection with numbered options
        print(f"\n{self.colors['cyan']}🚀 Select Job Type:{self.colors['end']}")
        for idx, job_type in enumerate(self.job_manager.valid_job_types, 1):
            print(f"  [{idx}] {job_type}")
        
        try:
            type_choice = input(f"\n{self.colors['cyan']}Select type (1-{len(self.job_manager.valid_job_types)}): {self.colors['end']}").strip()
            type_idx = int(type_choice) - 1
            if 0 <= type_idx < len(self.job_manager.valid_job_types):
                data['type'] = self.job_manager.valid_job_types[type_idx]
                print(f"{self.colors['green']}✓ Selected: {data['type']}{self.colors['end']}")
            else:
                self.print_warning("Invalid selection, using default: deployment")
                data['type'] = 'deployment'
        except (ValueError, IndexError):
            self.print_warning("Invalid input, using default: deployment")
            data['type'] = 'deployment'
        
        # Job details
        print()  # Add spacing
        data['description'] = input("Description: ").strip()
        data['assignedTo'] = input("Assigned to: ").strip()
        
        # Priority selection with numbered options
        print(f"\n{self.colors['cyan']}⚡ Select Priority:{self.colors['end']}")
        priorities = ['low', 'medium', 'high', 'critical']
        for idx, priority in enumerate(priorities, 1):
            print(f"  [{idx}] {priority}")
        
        try:
            priority_choice = input(f"\n{self.colors['cyan']}Select priority (1-{len(priorities)}): {self.colors['end']}").strip()
            priority_idx = int(priority_choice) - 1
            if 0 <= priority_idx < len(priorities):
                data['priority'] = priorities[priority_idx]
                print(f"{self.colors['green']}✓ Selected: {data['priority']}{self.colors['end']}")
            else:
                self.print_warning("Invalid selection, using default: medium")
                data['priority'] = 'medium'
        except (ValueError, IndexError):
            self.print_warning("Invalid input, using default: medium")
            data['priority'] = 'medium'
        
        # Validate
        errors = self.job_manager.validate_job_data(data)
        if errors:
            self.print_error("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            self.pause()
            return
        
        if self.confirm_action("Create this job?"):
            try:
                job_id = self.job_manager.create_job(
                    self.current_capability['capabilityId'],
                    data
                )
                self.print_success(f"Job created successfully with ID: {job_id}")
            except Exception as e:
                self.print_error(f"Error creating job: {str(e)}")
        
        self.pause()
    
    def view_job_details(self):
        """View detailed information about a job"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔍 VIEW JOB DETAILS")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            self.print_warning("Job ID is required")
            self.pause()
            return
        
        try:
            job = self.job_manager.get_job(
                self.current_capability['capabilityId'],
                job_id
            )
            if job:
                self.job_manager.display_job_details(job)
            else:
                self.print_warning(f"Job {job_id} not found")
        except Exception as e:
            self.print_error(f"Error retrieving job: {str(e)}")
        
        self.pause()
    
    def start_job(self):
        """Start a job"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("▶️ START JOB")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            self.print_warning("Job ID is required")
            self.pause()
            return
        
        if self.confirm_action("Start this job?"):
            try:
                result = self.job_manager.start_job(
                    self.current_capability['capabilityId'],
                    job_id
                )
                if result:
                    self.print_success("Job started successfully")
                else:
                    self.print_error("Failed to start job")
            except Exception as e:
                self.print_error(f"Error starting job: {str(e)}")
        
        self.pause()
    
    def pause_job(self):
        """Pause a running job"""
        self.print_info("Job pause functionality")
        self.pause()
    
    def complete_job(self):
        """Mark a job as complete"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("✅ COMPLETE JOB")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            self.print_warning("Job ID is required")
            self.pause()
            return
        
        result_notes = input("Result notes (optional): ").strip()
        
        if self.confirm_action("Mark this job as complete?"):
            try:
                result = self.job_manager.complete_job(
                    self.current_capability['capabilityId'],
                    job_id,
                    result_notes
                )
                if result:
                    self.print_success("Job completed successfully")
                else:
                    self.print_error("Failed to complete job")
            except Exception as e:
                self.print_error(f"Error completing job: {str(e)}")
        
        self.pause()
    
    def cancel_job(self):
        """Cancel a job"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("❌ CANCEL JOB")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            self.print_warning("Job ID is required")
            self.pause()
            return
        
        reason = input("Cancellation reason: ").strip()
        
        if self.confirm_action("Cancel this job?"):
            try:
                result = self.job_manager.cancel_job(
                    self.current_capability['capabilityId'],
                    job_id,
                    reason
                )
                if result:
                    self.print_success("Job cancelled successfully")
                else:
                    self.print_error("Failed to cancel job")
            except Exception as e:
                self.print_error(f"Error cancelling job: {str(e)}")
        
        self.pause()
    
    def create_rollback(self):
        """Create a rollback job"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("↩️ CREATE ROLLBACK")
        
        original_job_id = input("Original Job ID to rollback: ").strip()
        if not original_job_id:
            self.print_warning("Original Job ID is required")
            self.pause()
            return
        
        reason = input("Rollback reason: ").strip()
        
        if self.confirm_action("Create rollback job?"):
            try:
                rollback_id = self.job_manager.create_rollback(
                    self.current_capability['capabilityId'],
                    original_job_id,
                    reason
                )
                if rollback_id:
                    self.print_success(f"Rollback job created with ID: {rollback_id}")
                else:
                    self.print_error("Failed to create rollback")
            except Exception as e:
                self.print_error(f"Error creating rollback: {str(e)}")
        
        self.pause()
    
    def view_job_timeline(self):
        """View timeline of job events"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📊 JOB TIMELINE")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            # Show timeline for all jobs
            try:
                jobs = self.job_manager.list_jobs(self.current_capability['capabilityId'])
                print("\nJob Timeline:")
                print("-" * 60)
                for job in sorted(jobs, key=lambda x: x.get('createdAt', '')):
                    created = job.get('createdAt', 'Unknown')
                    status = job.get('status', 'unknown')
                    print(f"{created}: {job.get('jobId')} - {job.get('name')} [{status}]")
            except Exception as e:
                self.print_error(f"Error getting job timeline: {str(e)}")
        else:
            # Show detailed timeline for specific job
            try:
                timeline = self.job_manager.get_job_timeline(
                    self.current_capability['capabilityId'],
                    job_id
                )
                if timeline:
                    print("\nJob Timeline:")
                    print("-" * 60)
                    for event in timeline:
                        print(f"{event.get('timestamp')}: {event.get('event')} - {event.get('details', '')}")
                else:
                    self.print_warning("No timeline data found")
            except Exception as e:
                self.print_error(f"Error getting job timeline: {str(e)}")
        
        self.pause()
    
    def view_job_logs(self):
        """View job execution logs"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📜 JOB LOGS")
        
        job_id = input("Enter Job ID: ").strip()
        if not job_id:
            self.print_warning("Job ID is required")
            self.pause()
            return
        
        try:
            logs = self.job_manager.get_job_logs(
                self.current_capability['capabilityId'],
                job_id
            )
            if logs:
                print("\nJob Logs:")
                print("-" * 60)
                for log in logs:
                    level = log.get('level', 'INFO')
                    if level == 'ERROR':
                        color = self.colors['error']
                    elif level == 'WARNING':
                        color = self.colors['warning']
                    else:
                        color = self.colors['blue']
                    
                    print(f"{log.get('timestamp')} [{color}{level}{self.colors['end']}] {log.get('message')}")
            else:
                self.print_warning("No logs found")
        except Exception as e:
            self.print_error(f"Error getting job logs: {str(e)}")
        
        self.pause()
    
    # Performance Metrics Functions
    def record_metric(self):
        """Record a new performance metric"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        if not self.current_component:
            self.print_warning("Please set a current component first")
            self.set_current_component()
            if not self.current_component:
                return
        
        self.print_header("📝 RECORD METRIC")
        
        print("Enter metric details:")
        metric_name = input("Metric name: ").strip()
        metric_value = input("Metric value: ").strip()
        unit = input("Unit (e.g., ms, %, count): ").strip()
        
        try:
            metric_value = float(metric_value)
            result = self.metrics_manager.record_metric(
                self.current_capability['capabilityId'],
                self.current_component['componentId'],
                metric_name,
                metric_value,
                unit
            )
            if result:
                self.print_success("Metric recorded successfully")
            else:
                self.print_error("Failed to record metric")
        except ValueError:
            self.print_error("Invalid metric value")
        except Exception as e:
            self.print_error(f"Error recording metric: {str(e)}")
        
        self.pause()
    
    def view_latest_metrics(self):
        """View latest performance metrics"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📊 LATEST METRICS")
        
        component_id = None
        if self.current_component:
            component_id = self.current_component['componentId']
        else:
            component_id = input("Component ID (or Enter for all): ").strip() or None
        
        try:
            if self.test_mode:
                # Use mock data in test mode
                metrics = self._get_mock_metrics()
                metrics = [m for m in metrics if m['capabilityId'] == self.current_capability['capabilityId']]
                if component_id:
                    metrics = [m for m in metrics if m['componentId'] == component_id]
                
                if metrics:
                    print("\nMetrics:")
                    print("="*60)
                    for metric in metrics:
                        print(f"\n{metric['name']}: {metric['value']} {metric['unit']}")
                        print(f"  Component: {metric['componentId']}")
                        print(f"  Timestamp: {metric['timestamp']}")
                    self.print_success(f"Found {len(metrics)} metrics")
                else:
                    self.print_warning("No metrics found")
            else:
                metrics = self.metrics_manager.get_latest_metrics(
                    self.current_capability['capabilityId'],
                    component_id
                )
                
                if metrics:
                    self.metrics_manager.display_metrics_table(metrics)
                else:
                    self.print_warning("No metrics found")
        except Exception as e:
            self.print_error(f"Error getting metrics: {str(e)}")
        
        self.pause()
    
    def view_metric_history(self):
        """View historical metrics data"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📈 METRIC HISTORY")
        
        component_id = self.current_component['componentId'] if self.current_component else input("Component ID: ").strip()
        metric_name = input("Metric name: ").strip()
        days = input("Days of history (default 7): ").strip() or '7'
        
        try:
            history = self.metrics_manager.get_metric_history(
                self.current_capability['capabilityId'],
                component_id,
                metric_name,
                int(days)
            )
            
            if history:
                print("\nMetric History:")
                print("-" * 60)
                for entry in history:
                    print(f"{entry.get('timestamp')}: {entry.get('value')} {entry.get('unit')}")
            else:
                self.print_warning("No historical data found")
        except Exception as e:
            self.print_error(f"Error getting metric history: {str(e)}")
        
        self.pause()
    
    def aggregate_metrics(self):
        """Aggregate metrics over time period"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔄 AGGREGATE METRICS")
        
        component_id = self.current_component['componentId'] if self.current_component else input("Component ID: ").strip()
        metric_name = input("Metric name: ").strip()
        aggregation_type = input("Aggregation (avg/sum/min/max): ").strip()
        
        try:
            result = self.metrics_manager.aggregate_metrics(
                self.current_capability['capabilityId'],
                component_id,
                metric_name,
                aggregation_type
            )
            
            if result:
                print(f"\n{aggregation_type.upper()}: {result.get('value')} {result.get('unit')}")
                print(f"Sample count: {result.get('count')}")
                print(f"Time period: {result.get('period')}")
            else:
                self.print_warning("No data to aggregate")
        except Exception as e:
            self.print_error(f"Error aggregating metrics: {str(e)}")
        
        self.pause()
    
    def create_metric_alert(self):
        """Create alert for metric thresholds"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("🔔 CREATE METRIC ALERT")
        
        print("Enter alert details:")
        metric_name = input("Metric name: ").strip()
        threshold_type = input("Threshold type (min/max): ").strip()
        threshold_value = input("Threshold value: ").strip()
        
        try:
            threshold_value = float(threshold_value)
            result = self.metrics_manager.create_alert(
                self.current_capability['capabilityId'],
                metric_name,
                threshold_type,
                threshold_value
            )
            if result:
                self.print_success("Alert created successfully")
            else:
                self.print_error("Failed to create alert")
        except ValueError:
            self.print_error("Invalid threshold value")
        except Exception as e:
            self.print_error(f"Error creating alert: {str(e)}")
        
        self.pause()
    
    def check_health_status(self):
        """Check overall health status"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("❤️ HEALTH STATUS")
        
        try:
            health = self.metrics_manager.check_health_status(
                self.current_capability['capabilityId']
            )
            
            if health:
                overall = health.get('overall', 'unknown')
                if overall == 'healthy':
                    color = self.colors['green']
                    icon = "✅"
                elif overall == 'warning':
                    color = self.colors['warning']
                    icon = "⚠️"
                else:
                    color = self.colors['error']
                    icon = "❌"
                
                print(f"\n{icon} Overall Status: {color}{overall.upper()}{self.colors['end']}")
                print("\nComponent Status:")
                print("-" * 40)
                
                for comp_id, status in health.get('components', {}).items():
                    print(f"  {comp_id}: {status}")
                
                if health.get('alerts'):
                    print("\nActive Alerts:")
                    for alert in health.get('alerts'):
                        print(f"  ⚠️ {alert}")
            else:
                self.print_warning("Unable to determine health status")
        except Exception as e:
            self.print_error(f"Error checking health status: {str(e)}")
        
        self.pause()
    
    def metrics_summary(self):
        """Display metrics summary"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📑 METRICS SUMMARY")
        
        try:
            summary = self.metrics_manager.get_metrics_summary(
                self.current_capability['capabilityId']
            )
            
            if summary:
                print("\nMetrics Summary:")
                print("=" * 60)
                print(f"Total Metrics: {summary.get('total_metrics', 0)}")
                print(f"Active Components: {summary.get('active_components', 0)}")
                print(f"Average Response Time: {summary.get('avg_response_time', 'N/A')} ms")
                print(f"Success Rate: {summary.get('success_rate', 'N/A')}%")
                print(f"Error Rate: {summary.get('error_rate', 'N/A')}%")
                print("\nTop Metrics:")
                for metric in summary.get('top_metrics', []):
                    print(f"  • {metric['name']}: {metric['value']} {metric['unit']}")
            else:
                self.print_warning("No metrics data available")
        except Exception as e:
            self.print_error(f"Error getting metrics summary: {str(e)}")
        
        self.pause()
    
    def export_metrics(self):
        """Export metrics data"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📤 EXPORT METRICS")
        
        format_type = input("Export format (json/csv) [json]: ").strip().lower() or 'json'
        filename = input(f"Output filename [metrics.{format_type}]: ").strip() or f"metrics.{format_type}"
        
        try:
            metrics = self.metrics_manager.get_all_metrics(
                self.current_capability['capabilityId']
            )
            
            if format_type == 'json':
                import json
                with open(filename, 'w') as f:
                    json.dump(metrics, f, indent=2, default=str)
            elif format_type == 'csv':
                import csv
                if metrics:
                    with open(filename, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
                        writer.writeheader()
                        writer.writerows(metrics)
            
            self.print_success(f"Exported {len(metrics)} metrics to {filename}")
        except Exception as e:
            self.print_error(f"Error exporting metrics: {str(e)}")
        
        self.pause()
    
    def performance_trends(self):
        """Analyze performance trends"""
        if not self.current_capability:
            self.print_warning("Please set a current capability first")
            self.pause()
            return
        
        self.print_header("📉 PERFORMANCE TRENDS")
        
        try:
            trends = self.metrics_manager.analyze_trends(
                self.current_capability['capabilityId']
            )
            
            if trends:
                print("\nPerformance Trends:")
                print("=" * 60)
                
                for metric_name, trend in trends.items():
                    direction = trend.get('direction', 'stable')
                    if direction == 'improving':
                        icon = "📈"
                        color = self.colors['green']
                    elif direction == 'declining':
                        icon = "📉"
                        color = self.colors['error']
                    else:
                        icon = "➡️"
                        color = self.colors['blue']
                    
                    print(f"\n{icon} {metric_name}: {color}{direction}{self.colors['end']}")
                    print(f"  Current: {trend.get('current')}")
                    print(f"  Previous: {trend.get('previous')}")
                    print(f"  Change: {trend.get('change')}%")
            else:
                self.print_warning("Insufficient data for trend analysis")
        except Exception as e:
            self.print_error(f"Error analyzing trends: {str(e)}")
        
        self.pause()
    
    # Analytics Functions
    def capability_utilization_report(self):
        """Generate capability utilization report"""
        self.print_header("📊 CAPABILITY UTILIZATION")
        
        try:
            # Get all capabilities
            capabilities = self.capability_manager.list_capabilities()
            
            print("\nCapability Utilization Report:")
            print("=" * 70)
            print(f"{'Capability':<30} {'Status':<15} {'Components':<10} {'Jobs':<10}")
            print("-" * 70)
            
            for cap in capabilities:
                cap_id = cap.get('capabilityId')
                # Get component count
                components = self.component_manager.list_components(cap_id)
                # Get job count
                jobs = self.job_manager.list_jobs(cap_id)
                
                print(f"{cap.get('name', 'N/A')[:30]:<30} {cap.get('status', 'N/A'):<15} {len(components):<10} {len(jobs):<10}")
            
            print("-" * 70)
            print(f"Total Capabilities: {len(capabilities)}")
        except Exception as e:
            self.print_error(f"Error generating utilization report: {str(e)}")
        
        self.pause()
    
    def performance_analysis(self):
        """Analyze overall performance"""
        self.print_info("Performance analysis functionality - comprehensive metrics analysis")
        self.pause()
    
    def dependency_visualization(self):
        """Visualize component dependencies"""
        self.print_info("Dependency visualization - shows component dependency graph")
        self.pause()
    
    def business_value_metrics(self):
        """Calculate business value metrics"""
        self.print_info("Business value metrics - ROI and value calculations")
        self.pause()
    
    def job_success_rates(self):
        """Calculate job success rates"""
        self.print_header("🚀 JOB SUCCESS RATES")
        
        try:
            capabilities = self.capability_manager.list_capabilities()
            
            print("\nJob Success Rate Analysis:")
            print("=" * 60)
            
            total_jobs = 0
            successful_jobs = 0
            
            for cap in capabilities:
                cap_id = cap.get('capabilityId')
                jobs = self.job_manager.list_jobs(cap_id)
                
                cap_total = len(jobs)
                cap_success = len([j for j in jobs if j.get('status') == 'completed'])
                
                total_jobs += cap_total
                successful_jobs += cap_success
                
                if cap_total > 0:
                    rate = (cap_success / cap_total) * 100
                    print(f"{cap.get('name', 'N/A')}: {rate:.1f}% ({cap_success}/{cap_total})")
            
            if total_jobs > 0:
                overall_rate = (successful_jobs / total_jobs) * 100
                print("-" * 60)
                print(f"Overall Success Rate: {overall_rate:.1f}% ({successful_jobs}/{total_jobs})")
            else:
                self.print_warning("No jobs found for analysis")
        except Exception as e:
            self.print_error(f"Error calculating success rates: {str(e)}")
        
        self.pause()
    
    def resource_usage_report(self):
        """Generate resource usage report"""
        self.print_info("Resource usage report - AWS resource utilization")
        self.pause()
    
    def generate_executive_report(self):
        """Generate comprehensive executive report"""
        self.print_info("Executive report generation - comprehensive PDF report")
        self.pause()
    
    def export_all_reports(self):
        """Export all analytics reports"""
        self.print_info("Export all reports - batch export functionality")
        self.pause()
    
    # Batch Operations Functions
    def batch_import_csv(self):
        """Batch import from CSV file"""
        self.print_info("Batch CSV import functionality")
        self.pause()
    
    def batch_export_csv(self):
        """Batch export to CSV file"""
        self.print_info("Batch CSV export functionality")
        self.pause()
    
    def bulk_update_capabilities(self):
        """Bulk update multiple capabilities"""
        self.print_info("Bulk capability update functionality")
        self.pause()
    
    def batch_deploy_components(self):
        """Batch deploy multiple components"""
        self.print_info("Batch component deployment functionality")
        self.pause()
    
    def batch_collect_metrics(self):
        """Batch collect metrics from multiple sources"""
        self.print_info("Batch metrics collection functionality")
        self.pause()
    
    def batch_job_execution(self):
        """Execute multiple jobs in batch"""
        self.print_info("Batch job execution functionality")
        self.pause()
    
    def cleanup_operations(self):
        """Cleanup and maintenance operations"""
        self.print_info("Cleanup operations - data maintenance functionality")
        self.pause()
    
    # Journey Sync Functions
    def link_to_journey(self):
        """Link capability to a journey"""
        self.print_info("Link capability to journey functionality")
        self.pause()
    
    def list_journey_linked(self):
        """List capabilities linked to journeys"""
        self.print_info("List journey-linked capabilities")
        self.pause()
    
    def sync_with_journey(self):
        """Sync capability status with journey"""
        self.print_info("Sync with journey status")
        self.pause()
    
    def journey_capability_matrix(self):
        """Display journey-capability relationship matrix"""
        self.print_info("Journey-capability matrix visualization")
        self.pause()
    
    def unlink_from_journey(self):
        """Unlink capability from journey"""
        self.print_info("Unlink from journey functionality")
        self.pause()
    
    # Settings Functions
    def user_profile(self):
        """Manage user profile settings"""
        self.print_header("👤 USER PROFILE")
        
        print(f"Current User: {self.current_user or 'Not set'}")
        
        new_user = input("\nEnter username (or press Enter to keep current): ").strip()
        if new_user:
            self.current_user = new_user
            self.print_success(f"User set to: {self.current_user}")
        
        self.pause()
    
    def api_configuration(self):
        """Configure API settings"""
        self.print_info("API configuration settings")
        self.pause()
    
    def default_settings(self):
        """Manage default settings"""
        self.print_info("Default settings management")
        self.pause()
    
    def display_preferences(self):
        """Configure display preferences"""
        self.print_info("Display preferences configuration")
        self.pause()
    
    def export_configuration(self):
        """Export configuration to file"""
        self.print_info("Export configuration functionality")
        self.pause()
    
    def import_configuration(self):
        """Import configuration from file"""
        self.print_info("Import configuration functionality")
        self.pause()
    
    def _get_mock_capabilities(self):
        """Get mock capabilities for test mode"""
        return [
            {
                'capabilityId': 'CAP-001',
                'name': 'Customer Management',
                'description': 'Manages customer data and relationships',
                'businessDomain': 'Customer',
                'status': 'active',
                'priority': 'high',
                'owner': 'John Doe',
                'createdAt': '2024-01-01T10:00:00Z',
                'updatedAt': '2024-01-15T14:30:00Z'
            },
            {
                'capabilityId': 'CAP-002',
                'name': 'Product Catalog',
                'description': 'Product information and catalog management',
                'businessDomain': 'Product',
                'status': 'active',
                'priority': 'medium',
                'owner': 'Jane Smith',
                'createdAt': '2024-01-05T09:00:00Z',
                'updatedAt': '2024-01-20T11:00:00Z'
            },
            {
                'capabilityId': 'CAP-003',
                'name': 'Order Processing',
                'description': 'Handles order lifecycle and fulfillment',
                'businessDomain': 'Sales',
                'status': 'pending',
                'priority': 'critical',
                'owner': 'Bob Johnson',
                'createdAt': '2024-01-10T08:00:00Z',
                'updatedAt': '2024-01-25T16:00:00Z'
            }
        ]
    
    def _get_mock_components(self):
        """Get mock components for test mode"""
        return [
            {
                'componentId': 'COMP-001',
                'capabilityId': 'CAP-001',
                'name': 'Customer API',
                'type': 'api',
                'version': '1.2.0',
                'status': 'active',
                'repository': 'https://github.com/example/customer-api'
            },
            {
                'componentId': 'COMP-002',
                'capabilityId': 'CAP-001',
                'name': 'Customer Database',
                'type': 'database',
                'version': '2.0.0',
                'status': 'active',
                'repository': 'N/A'
            }
        ]
    
    def _get_mock_jobs(self):
        """Get mock jobs for test mode"""
        return [
            {
                'jobId': 'JOB-001',
                'capabilityId': 'CAP-001',
                'name': 'Deploy Customer API v1.2',
                'type': 'deployment',
                'status': 'completed',
                'assignedTo': 'DevOps Team',
                'createdAt': '2024-01-15T10:00:00Z'
            },
            {
                'jobId': 'JOB-002',
                'capabilityId': 'CAP-001',
                'name': 'Database Migration',
                'type': 'migration',
                'status': 'running',
                'assignedTo': 'DB Team',
                'createdAt': '2024-01-20T14:00:00Z'
            }
        ]
    
    def _get_mock_metrics(self):
        """Get mock metrics for test mode"""
        return [
            {
                'metricId': 'MET-001',
                'capabilityId': 'CAP-001',
                'componentId': 'COMP-001',
                'name': 'Response Time',
                'value': 125.5,
                'unit': 'ms',
                'timestamp': '2024-01-25T10:30:00Z'
            },
            {
                'metricId': 'MET-002',
                'capabilityId': 'CAP-001',
                'componentId': 'COMP-001',
                'name': 'Success Rate',
                'value': 99.8,
                'unit': '%',
                'timestamp': '2024-01-25T10:30:00Z'
            }
        ]
    
    def run(self):
        """Main entry point for the CLI"""
        self.print_header("🚀 TMF ODA CAPABILITY MANAGER")
        
        if self.test_mode:
            print(f"{self.colors['warning']}{'='*80}{self.colors['end']}")
            print(f"{self.colors['warning']}⚠  RUNNING IN TEST MODE - NO AUTHENTICATION REQUIRED  ⚠{self.colors['end']}")
            print(f"{self.colors['blue']}All data operations will use mock data and won't persist{self.colors['end']}")
            print(f"{self.colors['warning']}{'='*80}{self.colors['end']}\n")
        
        print(f"{self.colors['cyan']}Welcome to the Enhanced Capability Management System!{self.colors['end']}")
        print(f"{self.colors['blue']}This portal provides comprehensive capability lifecycle management.{self.colors['end']}")
        
        # Set username (optional in test mode)
        if not self.test_mode:
            self.current_user = input(f"\n{self.colors['cyan']}Enter your username: {self.colors['end']}").strip()
            if not self.current_user:
                self.current_user = "admin"
        else:
            self.current_user = "testuser"
            print(f"\n{self.colors['blue']}Auto-logged in as: {self.current_user} (TEST MODE){self.colors['end']}")
        
        self.print_success(f"Welcome, {self.current_user}!")
        self.pause()
        
        # Start main menu
        self.main_menu()
        
        # Cleanup
        self.print_info("\nGoodbye! Thank you for using Capability Manager.")


def main():
    """Main entry point"""
    try:
        manager = EnhancedCapabilityManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
