# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Analysis utility functions for TMF ODA Transformer."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

from ..models import (
    TMFODAComponentType,
    SchemaFormat,
    DatabaseType,
    SchemaAnalysisResult,
    SchemaFile,
    DatabaseAnalysisResult,
    DatabaseSchema,
    DatabaseTable,
    DatabaseColumn,
    ComplianceLevel,
    TransformationRecommendation,
)
from ..consts import SCHEMA_FILE_EXTENSIONS, MAX_FILE_SIZE_MB


async def discover_schema_files(workspace_dir: str, schema_format: Optional[SchemaFormat]) -> List[str]:
    """Discover schema files in the workspace directory."""
    discovered_files = []
    
    # Simulate discovering schema files
    for root, dirs, files in os.walk(workspace_dir):
        for file in files:
            if any(file.endswith(ext) for ext in SCHEMA_FILE_EXTENSIONS):
                file_path = os.path.join(root, file)
                # Check file size
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                        logger.warning(f'Skipping large file: {file_path} ({file_size} bytes)')
                        continue
                    discovered_files.append(file_path)
                except Exception as e:
                    logger.warning(f'Error accessing file {file_path}: {e}')
                    continue
    
    return discovered_files[:10]  # Limit for pseudo implementation


async def analyze_schema_file(schema_file: str, oda_component_type: TMFODAComponentType):
    """Analyze a single schema file for TMF ODA compliance (pseudo implementation)."""
    # Simulate analysis delay
    await asyncio.sleep(0.1)
    
    # Create pseudo schema file info
    file_path = Path(schema_file)
    schema_file_info = SchemaFile(
        file_path=str(file_path.absolute()),
        file_name=file_path.name,
        file_size=file_path.stat().st_size if file_path.exists() else 1000,
        format=SchemaFormat.JSON_SCHEMA,  # Pseudo detection
        last_modified=datetime.now()
    )
    
    # Simulate compliance analysis
    compliance_level = ComplianceLevel.PARTIALLY_COMPLIANT
    compliance_score = 75.5
    
    # Create pseudo recommendations
    recommendations = [
        TransformationRecommendation(
            category='Data Model',
            priority='HIGH',
            title='Implement TMF Entity Base Structure',
            description='Add standard TMF entity fields (id, href, @type, @baseType)',
            impact='Improves API consistency and TMF compliance',
            effort='MINIMAL'
        ),
        TransformationRecommendation(
            category='Validation',
            priority='MEDIUM',
            title='Add TMF Standard Patterns',
            description='Implement TMF standard validation patterns for common fields',
            impact='Ensures data consistency across TMF components',
            effort='MODERATE'
        )
    ]
    
    return SchemaAnalysisResult(
        schema_file=schema_file_info,
        compliance_level=compliance_level,
        compliance_score=compliance_score,
        issues=[],  # Simplified for now
        recommendations=recommendations,
        analysis_duration=0.5
    )


async def test_database_connection(connection_string: str, database_type: DatabaseType) -> bool:
    """Test database connection (pseudo implementation)."""
    # Simulate connection test delay
    await asyncio.sleep(0.2)
    
    # Pseudo implementation - always return True for demo
    logger.info(f'Testing {database_type} connection...')
    return True


async def discover_database_tables(connection_string: str, database_type: DatabaseType, tables_filter: Optional[str]) -> List[str]:
    """Discover database tables or collections (pseudo implementation)."""
    # Simulate database query delay
    await asyncio.sleep(0.3)
    
    # Pseudo implementation - return sample table names
    if database_type == DatabaseType.MONGODB:
        tables = ['users', 'products', 'orders', 'customers']
    else:
        tables = ['user_accounts', 'product_catalog', 'order_history', 'customer_profiles']
    
    # Apply filter if specified
    if tables_filter:
        # Simple filter implementation
        filter_terms = [term.strip() for term in tables_filter.split(',')]
        filtered_tables = []
        for table in tables:
            for term in filter_terms:
                if term.replace('*', '') in table:
                    filtered_tables.append(table)
                    break
        return filtered_tables
    
    return tables


async def analyze_database_table(connection_string: str, database_type: DatabaseType, table: str, oda_component_type: TMFODAComponentType):
    """Analyze a database table for TMF ODA compliance (pseudo implementation)."""
    # Simulate analysis delay
    await asyncio.sleep(0.2)
    
    # Create pseudo table info
    table_info = DatabaseTable(
        name=table,
        schema_name='public' if database_type in [DatabaseType.POSTGRESQL, DatabaseType.MYSQL] else None,
        type='table',
        row_count=1000,
        size_mb=5.2
    )
    
    # Create pseudo column info
    columns = [
        DatabaseColumn(
            name='id',
            data_type='VARCHAR(255)',
            is_nullable=False,
            is_primary_key=True,
            default_value=None,
            constraints=['PRIMARY KEY', 'NOT NULL']
        ),
        DatabaseColumn(
            name='name',
            data_type='VARCHAR(255)',
            is_nullable=False,
            is_primary_key=False,
            default_value=None,
            constraints=['NOT NULL']
        ),
        DatabaseColumn(
            name='created_at',
            data_type='TIMESTAMP',
            is_nullable=False,
            is_primary_key=False,
            default_value='CURRENT_TIMESTAMP',
            constraints=['NOT NULL']
        )
    ]
    
    schema = DatabaseSchema(table=table_info, columns=columns)
    
    # Simulate compliance analysis
    compliance_level = ComplianceLevel.NON_COMPLIANT
    compliance_score = 45.0
    
    # Create pseudo recommendations
    recommendations = [
        TransformationRecommendation(
            category='Schema Structure',
            priority='HIGH',
            title='Add TMF Standard Fields',
            description=f'Add href, @type, @baseType fields to {table} table for TMF compliance',
            impact='Enables TMF API resource representation',
            effort='MODERATE'
        ),
        TransformationRecommendation(
            category='Data Types',
            priority='MEDIUM',
            title='Standardize ID Format',
            description='Convert ID field to use TMF standard UUID format',
            impact='Improves data consistency and TMF compliance',
            effort='SIGNIFICANT'
        )
    ]
    
    return DatabaseAnalysisResult(
        database_schema=schema,
        compliance_level=compliance_level,
        compliance_score=compliance_score,
        recommendations=recommendations,
        analysis_duration=0.8
    ) 