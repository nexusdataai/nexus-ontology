"""
Raw Analysis Stage Implementation

This stage handles the initial analysis of raw input data:
1. Schema File Parsing
2. Relationship Discovery
3. Data Type Analysis
4. Business Rules Extraction
5. Complexity Assessment
"""

import json
import re
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..base_stage import BaseStage


class RawAnalysisStage(BaseStage):
    """
    Raw Input Analysis Stage
    
    This stage analyzes the raw customer database schema by:
    - Reading real SQL schema files from S3
    - Parsing SQL schema files and extracting table definitions
    - Identifying foreign key relationships and table dependencies
    - Analyzing column data types and constraints
    - Extracting business rules from stored procedures and constraints
    - Assessing schema complexity and identifying potential challenges
    """
    
    def __init__(self, journey_id: str, stage_id: str, job_id: str, region_name: str = None, role_arn: Optional[str] = None, enable_logging: bool = True):
        """
        Initialize the Raw Analysis Stage
        
        Args:
            journey_id: The journey ID
            stage_id: The stage ID
            job_id: The job ID
            region_name: AWS region name (optional)
            role_arn: AWS role ARN to assume (optional)
            enable_logging: Whether to enable file logging (default: True)
        """
        super().__init__(journey_id, stage_id, job_id, region_name, role_arn)
        
        # S3 configuration for input files
        self.input_bucket = 'mtn-totolcore-ui-1751374633-4498-1fc9a47e'  # Update if different
        self.input_prefix = 'customer-input/MTN-SA/'
        
        # File paths
        self.schema_file = 'Eppix_Schema_202050317.sql'
        self.procedure_file = 'Eppix_Procedure_20250317.sql'
        self.guide_file = 'SecondBrain.md'
        
        # Analysis results storage
        self.parsed_data = {}
        
        # Initialize logging attributes
        self.local_logger = None
        self.local_log_file = None
        
        # Only setup local logging if enabled (not for temporary instances)
        if enable_logging:
            self._setup_local_logging()
    
    def _setup_local_logging(self):
        """Setup local file logging for debugging and testing"""
        try:
            # Determine the project root and logs directory
            # Look for the project root by going up until we find the scripts directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = current_dir
            
            # Go up the directory tree to find the project root
            while not os.path.exists(os.path.join(project_root, 'scripts')):
                parent = os.path.dirname(project_root)
                if parent == project_root:
                    # We've reached the root of the filesystem without finding 'scripts'
                    # Fall back to a relative approach
                    project_root = os.path.join(current_dir, '..', '..', '..')
                    break
                project_root = parent
            
            # Create logs directory at project root
            logs_dir = os.path.join(project_root, 'logs')
            
            # Create logs directory if it doesn't exist
            os.makedirs(logs_dir, exist_ok=True)
            
            # Create job-specific log file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f'raw_analysis_{self.job_id}_{timestamp}.log'
            self.local_log_file = os.path.join(logs_dir, log_filename)
            
            # Setup logger
            self.local_logger = logging.getLogger(f'raw_analysis_{self.job_id}')
            self.local_logger.setLevel(logging.INFO)
            
            # Remove existing handlers to avoid duplicates
            for handler in self.local_logger.handlers[:]:
                self.local_logger.removeHandler(handler)
            
            # Create file handler
            file_handler = logging.FileHandler(self.local_log_file)
            file_handler.setLevel(logging.INFO)
            
            # Create console handler for immediate feedback (use stderr to avoid interfering with JSON-RPC)
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers to logger
            self.local_logger.addHandler(file_handler)
            self.local_logger.addHandler(console_handler)
            
            # Log initialization
            self.local_logger.info("=" * 80)
            self.local_logger.info(f"🚀 RAW ANALYSIS STAGE STARTED")
            self.local_logger.info(f"Journey ID: {self.journey_id}")
            self.local_logger.info(f"Job ID: {self.job_id}")
            self.local_logger.info(f"Stage ID: {self.stage_id}")
            # Show relative path from project root
            log_relative_path = os.path.relpath(self.local_log_file, project_root)
            self.local_logger.info(f"Local Log File: logs/{os.path.basename(self.local_log_file)}")
            self.local_logger.info("=" * 80)
            
        except Exception as e:
            # Log to stderr to avoid interfering with JSON-RPC protocol
            import sys
            sys.stderr.write(f"⚠️ Failed to setup local logging: {str(e)}\n")
            # Create a dummy logger that doesn't break the execution
            self.local_logger = logging.getLogger('dummy')
            self.local_logger.addHandler(logging.NullHandler())
    
    def _log_local(self, level: str, message: str, step_id: str = None):
        """Enhanced logging that writes to both local file and base logger"""
        # Create formatted message
        step_prefix = f"[{step_id}] " if step_id else ""
        formatted_message = f"{step_prefix}{message}"
        
        # Log to local file
        if hasattr(self, 'local_logger'):
            if level.upper() == 'ERROR':
                self.local_logger.error(f"❌ {formatted_message}")
            elif level.upper() == 'WARNING':
                self.local_logger.warning(f"⚠️ {formatted_message}")
            else:
                self.local_logger.info(f"ℹ️ {formatted_message}")
        
        # Also log using base class method for S3 upload
        if level.upper() == 'ERROR':
            self.log_error(message, step_id)
        elif level.upper() == 'WARNING':
            self.log_warning(message, step_id)
        else:
            self.log_info(message, step_id)
    
    @property
    def stage_name(self) -> str:
        return "Raw Input Analysis"
    
    @property
    def stage_description(self) -> str:
        return "Analyze the raw customer database schema to understand structure and relationships"
    
    @property
    def steps(self) -> List[Dict[str, Any]]:
        return [
            {
                'id': 'schema_parsing',
                'name': 'Schema File Parsing',
                'description': 'Parse SQL schema files and extract table definitions',
                'order': 0,
                'estimatedDuration': '3m',
            },
            {
                'id': 'relationship_discovery',
                'name': 'Relationship Discovery',
                'description': 'Identify foreign key relationships and table dependencies',
                'order': 1,
                'estimatedDuration': '3m',
            },
            {
                'id': 'data_type_analysis',
                'name': 'Data Type Analysis',
                'description': 'Analyze column data types and constraints',
                'order': 2,
                'estimatedDuration': '3m',
            },
            {
                'id': 'business_rules_extraction',
                'name': 'Business Rules Extraction',
                'description': 'Extract business rules from stored procedures and constraints',
                'order': 3,
                'estimatedDuration': '3m',
            },
            {
                'id': 'complexity_assessment',
                'name': 'Complexity Assessment',
                'description': 'Assess schema complexity and identify potential challenges',
                'order': 4,
                'estimatedDuration': '3m',
            },
        ]
    
    def execute_step(self, step_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific step of the raw analysis stage"""
        
        self._log_local('INFO', f"🔄 Starting execution of step: {step_id}", step_id)
        
        try:
            if step_id == 'schema_parsing':
                return self._execute_schema_parsing(step_data)
            elif step_id == 'relationship_discovery':
                return self._execute_relationship_discovery(step_data)
            elif step_id == 'data_type_analysis':
                return self._execute_data_type_analysis(step_data)
            elif step_id == 'business_rules_extraction':
                return self._execute_business_rules_extraction(step_data)
            elif step_id == 'complexity_assessment':
                return self._execute_complexity_assessment(step_data)
            else:
                raise ValueError(f"Unknown step_id: {step_id}")
        except Exception as e:
            self._log_local('ERROR', f"Step {step_id} failed: {str(e)}", step_id)
            raise
    
    def _download_file_from_s3(self, file_name: str) -> str:
        """Download a file from S3 and return its content"""
        try:
            key = f"{self.input_prefix}{file_name}"
            self._log_local('INFO', f"Downloading {file_name} from s3://{self.input_bucket}/{key}")
            
            response = self.s3.get_object(Bucket=self.input_bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            self._log_local('INFO', f"Successfully downloaded {file_name} ({len(content):,} characters)")
            return content
            
        except Exception as e:
            self._log_local('ERROR', f"Failed to download {file_name}: {str(e)}")
            raise
    
    def _parse_sql_schema(self, sql_content: str) -> Dict[str, Any]:
        """Parse SQL schema content to extract table definitions"""
        self._log_local('INFO', "🔍 Starting SQL schema parsing")
        
        tables = {}
        
        # Regex patterns for SQL parsing
        create_table_pattern = r'CREATE\s+TABLE\s+(\w+)\s*\((.*?)\);'
        column_pattern = r'(\w+)\s+([A-Z]+(?:\([^)]+\))?)\s*([^,\n]*)'
        
        self._log_local('INFO', f"Scanning SQL content ({len(sql_content):,} characters) for CREATE TABLE statements")
        
        # Find all CREATE TABLE statements
        table_matches = re.finditer(create_table_pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        for match in table_matches:
            table_name = match.group(1)
            columns_section = match.group(2)
            
            self._log_local('INFO', f"📋 Processing table: {table_name}")
            
            columns = []
            
            # Parse columns
            for line in columns_section.split('\n'):
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                # Remove trailing comma
                line = line.rstrip(',')
                
                # Check for constraints
                if 'PRIMARY KEY' in line.upper():
                    continue
                if 'FOREIGN KEY' in line.upper():
                    continue
                if 'CONSTRAINT' in line.upper():
                    continue
                
                # Parse column definition
                col_match = re.match(column_pattern, line, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1)
                    col_type = col_match.group(2)
                    col_constraints = col_match.group(3).strip()
                    
                    column_def = {
                        'name': col_name,
                        'type': col_type,
                        'nullable': 'NOT NULL' not in col_constraints.upper(),
                        'primary_key': 'PRIMARY KEY' in col_constraints.upper(),
                        'unique': 'UNIQUE' in col_constraints.upper(),
                        'default': None
                    }
                    
                    # Extract default value
                    default_match = re.search(r'DEFAULT\s+([^,\s]+)', col_constraints, re.IGNORECASE)
                    if default_match:
                        column_def['default'] = default_match.group(1)
                    
                    columns.append(column_def)
            
            tables[table_name] = {
                'name': table_name,
                'columns': columns
            }
            
            self._log_local('INFO', f"✅ Parsed table {table_name} with {len(columns)} columns")
        
        self._log_local('INFO', f"🎯 Schema parsing completed: {len(tables)} tables found")
        return tables
    
    def _extract_foreign_keys(self, sql_content: str) -> List[Dict[str, Any]]:
        """Extract foreign key relationships from SQL content"""
        self._log_local('INFO', "🔗 Extracting foreign key relationships")
        
        relationships = []
        
        # Regex pattern for foreign key constraints
        fk_pattern = r'FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)'
        
        fk_matches = re.finditer(fk_pattern, sql_content, re.IGNORECASE)
        
        for match in fk_matches:
            from_column = match.group(1).strip()
            to_table = match.group(2).strip()
            to_column = match.group(3).strip()
            
            relationship = {
                'from_column': from_column,
                'to_table': to_table,
                'to_column': to_column,
                'relationship_type': 'many_to_one'
            }
            
            relationships.append(relationship)
            self._log_local('INFO', f"🔗 Found relationship: {from_column} → {to_table}.{to_column}")
        
        self._log_local('INFO', f"✅ Relationship extraction completed: {len(relationships)} relationships found")
        return relationships
    
    def _parse_stored_procedures(self, sql_content: str) -> List[Dict[str, Any]]:
        """Parse stored procedures from SQL content"""
        self._log_local('INFO', "⚙️ Parsing stored procedures")
        
        procedures = []
        
        # Regex pattern for stored procedure definitions
        proc_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)\s*\((.*?)\)\s+AS\s+(.*?)(?=CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE|\Z)'
        
        proc_matches = re.finditer(proc_pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        for match in proc_matches:
            proc_name = match.group(1)
            parameters = match.group(2).strip()
            body = match.group(3).strip()
            
            procedure = {
                'name': proc_name,
                'parameters': parameters,
                'body': body[:500] + '...' if len(body) > 500 else body,  # Truncate for brevity
                'purpose': self._extract_procedure_purpose(body)
            }
            
            procedures.append(procedure)
            self._log_local('INFO', f"⚙️ Found procedure: {proc_name} - {procedure['purpose']}")
        
        self._log_local('INFO', f"✅ Procedure parsing completed: {len(procedures)} procedures found")
        return procedures
    
    def _extract_procedure_purpose(self, procedure_body: str) -> str:
        """Extract the purpose/description from procedure body"""
        # Look for comments that might describe the procedure
        comment_patterns = [
            r'--\s*(.+)',
            r'/\*\s*(.*?)\s*\*/',
        ]
        
        for pattern in comment_patterns:
            match = re.search(pattern, procedure_body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Purpose not explicitly documented"
    
    def _execute_schema_parsing(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse SQL schema files from S3"""
        step_id = 'schema_parsing'
        
        self._log_local('INFO', '🚀 Starting real schema file parsing from S3', step_id)
        
        try:
            # Download schema file
            self._log_local('INFO', f"📥 Downloading main schema file: {self.schema_file}", step_id)
            schema_content = self._download_file_from_s3(self.schema_file)
            
            # Download SecondBrain guide
            self._log_local('INFO', f"📥 Downloading analysis guide: {self.guide_file}", step_id)
            guide_content = self._download_file_from_s3(self.guide_file)
            
            # Parse SQL schema
            self._log_local('INFO', '🔍 Parsing SQL schema content', step_id)
            parsed_tables = self._parse_sql_schema(schema_content)
            
            # Store parsed data for use in other steps
            self.parsed_data['schema_content'] = schema_content
            self.parsed_data['guide_content'] = guide_content
            self.parsed_data['tables'] = parsed_tables
            
            # Set metrics
            self.set_metric('tables_parsed', len(parsed_tables), step_id)
            self.set_metric('total_columns', sum(len(table['columns']) for table in parsed_tables.values()), step_id)
            self.set_metric('schema_file_size', len(schema_content), step_id)
            self.set_metric('guide_file_size', len(guide_content), step_id)
            
            # Add artifacts
            self.add_artifact('parsed_schema', parsed_tables, step_id)
            self.add_artifact('source_files', {
                'schema_file': self.schema_file,
                'guide_file': self.guide_file
            }, step_id)
            
            total_columns = sum(len(table['columns']) for table in parsed_tables.values())
            self._log_local('INFO', f'✅ Successfully parsed {len(parsed_tables)} tables with {total_columns:,} total columns', step_id)
            
            # Log sample tables for verification
            if parsed_tables:
                sample_tables = list(parsed_tables.keys())[:5]
                self._log_local('INFO', f"📋 Sample tables: {', '.join(sample_tables)}", step_id)
            
            # Create step report
            report = {
                'step_id': step_id,
                'status': 'completed',
                'summary': f'Parsed {len(parsed_tables)} tables with {total_columns:,} total columns from real SQL schema files',
                'tables_found': list(parsed_tables.keys()),
                'source_files': [self.schema_file, self.guide_file],
                'metrics': self.metrics.get(step_id, {}),
                'artifacts': self.artifacts.get(step_id, {})
            }
            
            self._log_local('INFO', f"📊 Step completed successfully: {report['summary']}", step_id)
            
        except Exception as e:
            self._log_local('ERROR', f'Schema parsing failed: {str(e)}', step_id)
            report = {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
                'summary': 'Failed to parse schema files from S3'
            }
        
        # Upload to S3
        self.upload_logs_to_s3(step_id)
        self.upload_report_to_s3(step_id, report)
        
        return report
    
    def _execute_relationship_discovery(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify table relationships from parsed schema"""
        step_id = 'relationship_discovery'
        
        self._log_local('INFO', '🔗 Starting relationship discovery from parsed schema', step_id)
        
        try:
            schema_content = self.parsed_data.get('schema_content', '')
            
            if not schema_content:
                raise Exception("No schema content available from previous step")
            
            # Extract foreign key relationships
            self._log_local('INFO', "🔍 Analyzing SQL content for foreign key relationships", step_id)
            relationships = self._extract_foreign_keys(schema_content)
            
            # Store relationships for later use
            self.parsed_data['relationships'] = relationships
            
            # Set metrics
            self.set_metric('relationships_discovered', len(relationships), step_id)
            self.set_metric('foreign_keys_found', len([r for r in relationships if r['relationship_type'] == 'many_to_one']), step_id)
            
            # Add artifacts
            self.add_artifact('relationships', relationships, step_id)
            
            self._log_local('INFO', f'✅ Discovered {len(relationships)} relationships', step_id)
            
            # Log sample relationships
            if relationships:
                sample_rels = relationships[:3]
                for rel in sample_rels:
                    self._log_local('INFO', f"🔗 {rel['from_column']} → {rel['to_table']}.{rel['to_column']}", step_id)
            
            # Create step report
            report = {
                'step_id': step_id,
                'status': 'completed',
                'summary': f'Discovered {len(relationships)} table relationships from real schema analysis',
                'relationships_found': relationships,
                'metrics': self.metrics.get(step_id, {}),
                'artifacts': self.artifacts.get(step_id, {})
            }
            
            self._log_local('INFO', f"📊 Step completed successfully: {report['summary']}", step_id)
            
        except Exception as e:
            self._log_local('ERROR', f'Relationship discovery failed: {str(e)}', step_id)
            report = {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
                'summary': 'Failed to discover relationships from schema'
            }
        
        # Upload to S3
        self.upload_logs_to_s3(step_id)
        self.upload_report_to_s3(step_id, report)
        
        return report
    
    def _execute_data_type_analysis(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze column data types from parsed schema"""
        step_id = 'data_type_analysis'
        
        self._log_local('INFO', '📊 Starting data type analysis from parsed schema', step_id)
        
        try:
            tables = self.parsed_data.get('tables', {})
            
            if not tables:
                raise Exception("No tables available from schema parsing step")
            
            # Analyze data types
            self._log_local('INFO', f"🔍 Analyzing data types across {len(tables)} tables", step_id)
            
            type_distribution = {}
            data_types = {
                'string_types': [],
                'numeric_types': [],
                'date_types': [],
                'boolean_types': [],
                'other_types': []
            }
            
            for table_name, table in tables.items():
                for column in table['columns']:
                    col_type = column['type'].upper()
                    
                    # Count occurrences
                    base_type = col_type.split('(')[0]  # Remove size specifications
                    type_distribution[base_type] = type_distribution.get(base_type, 0) + 1
                    
                    # Categorize types
                    if any(t in col_type for t in ['VARCHAR', 'TEXT', 'CHAR', 'STRING']):
                        if col_type not in data_types['string_types']:
                            data_types['string_types'].append(col_type)
                    elif any(t in col_type for t in ['INT', 'DECIMAL', 'FLOAT', 'NUMERIC', 'NUMBER']):
                        if col_type not in data_types['numeric_types']:
                            data_types['numeric_types'].append(col_type)
                    elif any(t in col_type for t in ['DATE', 'TIME', 'TIMESTAMP']):
                        if col_type not in data_types['date_types']:
                            data_types['date_types'].append(col_type)
                    elif any(t in col_type for t in ['BOOL']):
                        if col_type not in data_types['boolean_types']:
                            data_types['boolean_types'].append(col_type)
                    else:
                        if col_type not in data_types['other_types']:
                            data_types['other_types'].append(col_type)
            
            # Store analysis results
            self.parsed_data['data_types'] = data_types
            self.parsed_data['type_distribution'] = type_distribution
            
            # Log data type summary
            total_columns = sum(type_distribution.values())
            self._log_local('INFO', f"📊 Type analysis summary:", step_id)
            self._log_local('INFO', f"  • String types: {len(data_types['string_types'])} unique, {sum(1 for k, v in type_distribution.items() if any(t in k for t in ['VARCHAR', 'TEXT', 'CHAR', 'STRING']))} columns", step_id)
            self._log_local('INFO', f"  • Numeric types: {len(data_types['numeric_types'])} unique, {sum(v for k, v in type_distribution.items() if any(t in k for t in ['INT', 'DECIMAL', 'FLOAT', 'NUMERIC', 'NUMBER']))} columns", step_id)
            self._log_local('INFO', f"  • Date/Time types: {len(data_types['date_types'])} unique", step_id)
            
            # Set metrics
            self.set_metric('data_types_analyzed', len(data_types), step_id)
            self.set_metric('type_distribution', type_distribution, step_id)
            self.set_metric('unique_types_found', len(type_distribution), step_id)
            
            # Add artifacts
            self.add_artifact('data_types', data_types, step_id)
            self.add_artifact('type_distribution', type_distribution, step_id)
            
            self._log_local('INFO', f'✅ Analyzed {total_columns:,} columns across {len(type_distribution)} unique data types', step_id)
            
            # Create step report
            report = {
                'step_id': step_id,
                'status': 'completed',
                'summary': f'Analyzed {total_columns:,} columns across {len(type_distribution)} unique data types from real schema',
                'data_types_found': data_types,
                'distribution': type_distribution,
                'metrics': self.metrics.get(step_id, {}),
                'artifacts': self.artifacts.get(step_id, {})
            }
            
            self._log_local('INFO', f"📊 Step completed successfully: {report['summary']}", step_id)
            
        except Exception as e:
            self._log_local('ERROR', f'Data type analysis failed: {str(e)}', step_id)
            report = {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
                'summary': 'Failed to analyze data types from schema'
            }
        
        # Upload to S3
        self.upload_logs_to_s3(step_id)
        self.upload_report_to_s3(step_id, report)
        
        return report
    
    def _execute_business_rules_extraction(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract business rules from stored procedures and constraints"""
        step_id = 'business_rules_extraction'
        
        self._log_local('INFO', '⚙️ Starting business rules extraction from procedures', step_id)
        
        try:
            # Download and parse procedure file
            self._log_local('INFO', f"📥 Downloading procedures file: {self.procedure_file}", step_id)
            procedure_content = self._download_file_from_s3(self.procedure_file)
            stored_procedures = self._parse_stored_procedures(procedure_content)
            
            # Extract constraints from schema
            schema_content = self.parsed_data.get('schema_content', '')
            if not schema_content:
                raise Exception("No schema content available from previous step")
                
            self._log_local('INFO', "🔍 Extracting constraints from schema", step_id)
            constraints = self._extract_constraints(schema_content)
            
            # Extract triggers if any
            self._log_local('INFO', "🔍 Extracting triggers from schema", step_id)
            triggers = self._extract_triggers(schema_content)
            
            business_rules = {
                'constraints': constraints,
                'stored_procedures': stored_procedures,
                'triggers': triggers
            }
            
            # Store business rules
            self.parsed_data['business_rules'] = business_rules
            
            # Log summary
            self._log_local('INFO', f"📊 Business rules summary:", step_id)
            self._log_local('INFO', f"  • Constraints: {len(constraints)}", step_id)
            self._log_local('INFO', f"  • Stored Procedures: {len(stored_procedures)}", step_id)
            self._log_local('INFO', f"  • Triggers: {len(triggers)}", step_id)
            
            # Set metrics
            self.set_metric('constraints_found', len(constraints), step_id)
            self.set_metric('stored_procedures_found', len(stored_procedures), step_id)
            self.set_metric('triggers_found', len(triggers), step_id)
            self.set_metric('procedure_file_size', len(procedure_content), step_id)
            
            # Add artifacts
            self.add_artifact('business_rules', business_rules, step_id)
            
            self._log_local('INFO', f'✅ Extracted {len(constraints)} constraints, {len(stored_procedures)} stored procedures, {len(triggers)} triggers', step_id)
            
            # Create step report
            report = {
                'step_id': step_id,
                'status': 'completed',
                'summary': f'Extracted {len(constraints)} constraints, {len(stored_procedures)} stored procedures, {len(triggers)} triggers from real SQL files',
                'business_rules_found': business_rules,
                'source_files': [self.procedure_file, self.schema_file],
                'metrics': self.metrics.get(step_id, {}),
                'artifacts': self.artifacts.get(step_id, {})
            }
            
            self._log_local('INFO', f"📊 Step completed successfully: {report['summary']}", step_id)
            
        except Exception as e:
            self._log_local('ERROR', f'Business rules extraction failed: {str(e)}', step_id)
            report = {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
                'summary': 'Failed to extract business rules from SQL files'
            }
        
        # Upload to S3
        self.upload_logs_to_s3(step_id)
        self.upload_report_to_s3(step_id, report)
        
        return report
    
    def _extract_constraints(self, sql_content: str) -> List[Dict[str, Any]]:
        """Extract constraints from SQL content"""
        self._log_local('INFO', "🔍 Scanning for database constraints")
        
        constraints = []
        
        # Patterns for different constraint types
        patterns = {
            'unique': r'UNIQUE\s*\(([^)]+)\)',
            'check': r'CHECK\s*\(([^)]+)\)',
            'not_null': r'(\w+)\s+[^,\n]*NOT\s+NULL'
        }
        
        for constraint_type, pattern in patterns.items():
            matches = re.finditer(pattern, sql_content, re.IGNORECASE)
            for match in matches:
                constraint = {
                    'type': constraint_type,
                    'definition': match.group(1).strip(),
                    'rule': f'{constraint_type.replace("_", " ").title()} constraint'
                }
                constraints.append(constraint)
                self._log_local('INFO', f"  Found {constraint_type} constraint: {constraint['definition'][:50]}...")
        
        return constraints
    
    def _extract_triggers(self, sql_content: str) -> List[Dict[str, Any]]:
        """Extract triggers from SQL content"""
        self._log_local('INFO', "🔍 Scanning for database triggers")
        
        triggers = []
        
        # Pattern for trigger definitions
        trigger_pattern = r'CREATE\s+TRIGGER\s+(\w+)\s+(\w+)\s+(\w+)\s+ON\s+(\w+)'
        
        matches = re.finditer(trigger_pattern, sql_content, re.IGNORECASE)
        for match in matches:
            trigger = {
                'name': match.group(1),
                'timing': match.group(2),  # BEFORE/AFTER
                'event': match.group(3),   # INSERT/UPDATE/DELETE
                'table': match.group(4),
                'action': 'Execute trigger logic'
            }
            triggers.append(trigger)
            self._log_local('INFO', f"  Found trigger: {trigger['name']} on {trigger['table']}")
        
        return triggers
    
    def _execute_complexity_assessment(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess schema complexity and generate comprehensive report"""
        step_id = 'complexity_assessment'
        
        self._log_local('INFO', '🎯 Starting complexity assessment and report generation', step_id)
        
        try:
            # Gather all analysis results
            tables = self.parsed_data.get('tables', {})
            relationships = self.parsed_data.get('relationships', [])
            business_rules = self.parsed_data.get('business_rules', {})
            type_distribution = self.parsed_data.get('type_distribution', {})
            
            if not tables:
                raise Exception("No analysis data available from previous steps")
            
            # Calculate complexity metrics
            total_tables = len(tables)
            total_columns = sum(len(table['columns']) for table in tables.values())
            total_relationships = len(relationships)
            total_constraints = len(business_rules.get('constraints', []))
            total_procedures = len(business_rules.get('stored_procedures', []))
            
            self._log_local('INFO', f"📊 Calculating complexity metrics:", step_id)
            self._log_local('INFO', f"  • Tables: {total_tables}", step_id)
            self._log_local('INFO', f"  • Columns: {total_columns:,}", step_id)
            self._log_local('INFO', f"  • Relationships: {total_relationships}", step_id)
            self._log_local('INFO', f"  • Constraints: {total_constraints}", step_id)
            self._log_local('INFO', f"  • Procedures: {total_procedures}", step_id)
            
            # Calculate complexity score (1-10 scale)
            complexity_score = min(10, max(1, 
                (total_tables * 0.1) + 
                (total_relationships * 0.2) + 
                (total_procedures * 0.3) + 
                (len(type_distribution) * 0.1)
            ))
            
            complexity_analysis = {
                'schema_metrics': {
                    'total_tables': total_tables,
                    'total_columns': total_columns,
                    'total_relationships': total_relationships,
                    'total_constraints': total_constraints,
                    'total_procedures': total_procedures,
                    'unique_data_types': len(type_distribution)
                },
                'complexity_score': round(complexity_score, 1),
                'complexity_factors': [
                    {
                        'factor': 'Table Count',
                        'score': min(10, total_tables / 5),
                        'description': f'{total_tables} tables in schema'
                    },
                    {
                        'factor': 'Relationship Complexity', 
                        'score': min(10, total_relationships / 3),
                        'description': f'{total_relationships} relationships detected'
                    },
                    {
                        'factor': 'Business Logic Complexity',
                        'score': min(10, total_procedures / 2),
                        'description': f'{total_procedures} stored procedures found'
                    }
                ]
            }
            
            self._log_local('INFO', f"🎯 Complexity score calculated: {complexity_analysis['complexity_score']}/10", step_id)
            
            # Generate comprehensive markdown report
            self._log_local('INFO', "📝 Generating comprehensive markdown report", step_id)
            report_md = self._generate_comprehensive_report(
                tables, relationships, business_rules, type_distribution, complexity_analysis
            )
            
            # Upload report to S3
            report_key = f'journeys/{self.journey_id}/stages/{self.stage_id}/executions/{self.job_id}/reports/step1-report.md'
            self._log_local('INFO', f"📤 Uploading report to S3: {report_key}", step_id)
            
            self.s3.put_object(
                Bucket=self._config.s3_journey_reports_bucket,
                Key=report_key,
                Body=report_md,
                ContentType='text/markdown'
            )
            
            # Also save report locally
            local_report_path = os.path.join(os.path.dirname(self.local_log_file), f'step1-report_{self.job_id}.md')
            with open(local_report_path, 'w', encoding='utf-8') as f:
                f.write(report_md)
            
            self._log_local('INFO', f"💾 Report also saved locally: {local_report_path}", step_id)
            
            # Store final results
            self.parsed_data['complexity_analysis'] = complexity_analysis
            
            # Set metrics
            self.set_metric('complexity_score', complexity_analysis['complexity_score'], step_id)
            self.set_metric('report_generated', True, step_id)
            self.set_metric('report_size', len(report_md), step_id)
            
            # Add artifacts
            self.add_artifact('complexity_analysis', complexity_analysis, step_id)
            self.add_artifact('final_report', {'s3_key': report_key, 'local_path': local_report_path, 'size': len(report_md)}, step_id)
            
            self._log_local('INFO', f'✅ Complexity assessment completed with score {complexity_analysis["complexity_score"]}/10', step_id)
            self._log_local('INFO', f'📄 Generated comprehensive report ({len(report_md):,} characters)', step_id)
            
            # Create step report
            report = {
                'step_id': step_id,
                'status': 'completed',
                'summary': f'Schema complexity assessed with score {complexity_analysis["complexity_score"]}/10, comprehensive report generated',
                'complexity_analysis': complexity_analysis,
                'report_location': f's3://{self._config.s3_journey_reports_bucket}/{report_key}',
                'local_report_path': local_report_path,
                'metrics': self.metrics.get(step_id, {}),
                'artifacts': self.artifacts.get(step_id, {})
            }
            
            self._log_local('INFO', f"📊 Step completed successfully: {report['summary']}", step_id)
            
        except Exception as e:
            self._log_local('ERROR', f'Complexity assessment failed: {str(e)}', step_id)
            report = {
                'step_id': step_id,
                'status': 'failed',
                'error': str(e),
                'summary': 'Failed to complete complexity assessment and report generation'
            }
        
        # Upload to S3
        self.upload_logs_to_s3(step_id)
        self.upload_report_to_s3(step_id, report)
        
        # Final summary log
        if hasattr(self, 'local_logger'):
            self.local_logger.info("=" * 80)
            self.local_logger.info("🏁 RAW ANALYSIS STAGE COMPLETED")
            if report.get('status') == 'completed':
                self.local_logger.info("✅ All steps completed successfully")
                self.local_logger.info(f"📊 Final complexity score: {complexity_analysis.get('complexity_score', 'N/A')}/10")
            else:
                self.local_logger.error("❌ Stage completed with errors")
            # Show relative path in logs
            if self.local_log_file:
                self.local_logger.info(f"📁 Local log file: logs/{os.path.basename(self.local_log_file)}")
            self.local_logger.info("=" * 80)
        
        return report
    
    def _generate_comprehensive_report(self, tables: Dict, relationships: List, business_rules: Dict, 
                                     type_distribution: Dict, complexity_analysis: Dict) -> str:
        """Generate comprehensive markdown report"""
        
        self._log_local('INFO', "📝 Building comprehensive report sections")
        
        report_lines = [
            "# MTN Telco Schema - Comprehensive Analysis",
            "",
            "## Summary",
            "",
            f"Based on the analysis of the SQL schema files, here's a comprehensive overview of the table structure and relationships for the MTN Customer Database.",
            "",
            "### Customer Schema Overview",
            "",
            f"I found **{len(tables)} tables** in the MTN Customer database schema. The analysis includes table definitions, relationships, data types, and business rules.",
            "",
            "### Main Tables Identified",
            ""
        ]
        
        # List all tables
        if tables:
            table_names = sorted(tables.keys())
            for i, table_name in enumerate(table_names[:20], 1):  # Show first 20 tables
                report_lines.append(f"{i}. **{table_name}** ({len(tables[table_name]['columns'])} columns)")
            
            if len(table_names) > 20:
                report_lines.append(f"... and {len(table_names) - 20} more tables")
        
        report_lines.extend([
            "",
            "### Key Table Details",
            ""
        ])
        
        # Show details for first few tables
        for table_name in sorted(tables.keys())[:5]:
            table = tables[table_name]
            report_lines.extend([
                f"#### {table_name}",
                f"- **Columns**: {len(table['columns'])}",
                "- **Column Details**:"
            ])
            
            for col in table['columns'][:10]:  # Show first 10 columns
                constraints = []
                if col.get('primary_key'):
                    constraints.append('PRIMARY KEY')
                if col.get('unique'):
                    constraints.append('UNIQUE')
                if not col.get('nullable'):
                    constraints.append('NOT NULL')
                
                constraint_str = f" ({', '.join(constraints)})" if constraints else ""
                report_lines.append(f"  - `{col['name']}` {col['type']}{constraint_str}")
            
            if len(table['columns']) > 10:
                report_lines.append(f"  - ... and {len(table['columns']) - 10} more columns")
            report_lines.append("")
        
        # Relationships section
        if relationships:
            report_lines.extend([
                "### Key Foreign Key Relationships",
                "",
                f"Found **{len(relationships)} relationships** between tables:",
                ""
            ])
            
            for rel in relationships[:10]:  # Show first 10 relationships
                report_lines.append(f"- {rel['from_column']} → {rel['to_table']}.{rel['to_column']} ({rel['relationship_type']})")
            
            if len(relationships) > 10:
                report_lines.append(f"- ... and {len(relationships) - 10} more relationships")
        
        # Data types section
        if type_distribution:
            report_lines.extend([
                "",
                "### Data Type Distribution",
                ""
            ])
            
            sorted_types = sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)
            for data_type, count in sorted_types[:15]:  # Show top 15 data types
                report_lines.append(f"- **{data_type}**: {count} columns")
        
        # Business rules section
        if business_rules:
            constraints = business_rules.get('constraints', [])
            procedures = business_rules.get('stored_procedures', [])
            
            if procedures:
                report_lines.extend([
                    "",
                    "### Stored Procedures Identified",
                    "",
                    f"Found **{len(procedures)} stored procedures**:",
                    ""
                ])
                
                for proc in procedures[:10]:  # Show first 10 procedures
                    report_lines.append(f"- **{proc['name']}**: {proc.get('purpose', 'Purpose not documented')}")
            
            if constraints:
                report_lines.extend([
                    "",
                    "### Database Constraints",
                    "",
                    f"Found **{len(constraints)} constraints**:",
                    ""
                ])
                
                constraint_counts = {}
                for constraint in constraints:
                    c_type = constraint['type']
                    constraint_counts[c_type] = constraint_counts.get(c_type, 0) + 1
                
                for c_type, count in constraint_counts.items():
                    report_lines.append(f"- **{c_type.replace('_', ' ').title()}**: {count} constraints")
        
        # Complexity assessment
        metrics = complexity_analysis['schema_metrics']
        report_lines.extend([
            "",
            "### Complexity Assessment",
            "",
            f"**Overall Complexity Score**: {complexity_analysis['complexity_score']}/10",
            "",
            "**Complexity Factors**:",
            ""
        ])
        
        for factor in complexity_analysis['complexity_factors']:
            report_lines.append(f"- **{factor['factor']}**: {factor['score']:.1f}/10 - {factor['description']}")
        
        # Database statistics
        report_lines.extend([
            "",
            "## Database Statistics",
            "",
            f"- **Total Tables**: {metrics['total_tables']:,}",
            f"- **Total Columns**: {metrics['total_columns']:,}",
            f"- **Total Relationships**: {metrics['total_relationships']:,}",
            f"- **Total Constraints**: {metrics['total_constraints']:,}",
            f"- **Stored Procedures**: {metrics['total_procedures']:,}",
            f"- **Unique Data Types**: {metrics['unique_data_types']:,}",
            "",
            "## Files Analyzed",
            "",
            f"- `{self.schema_file}` - Main database schema",
            f"- `{self.procedure_file}` - Stored procedures",
            f"- `{self.guide_file}` - Analysis guide and documentation",
            "",
            "## Files Generated",
            "",
            "- `step1-report.md` - This comprehensive analysis report",
            "",
            f"*Analysis completed on {self._get_current_timestamp()}*"
        ])
        
        return "\n".join(report_lines)
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for report"""
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC") 