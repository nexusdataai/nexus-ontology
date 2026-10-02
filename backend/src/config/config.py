from typing import Dict
import os
import yaml
from pathlib import Path

def _load_env_local():
    """Load environment variables from .env.local for local development."""
    # Skip if running on ECS
    if os.getenv('ECS_CONTAINER_METADATA_URI') or os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return
    
    project_root = Path(__file__).parent.parent.parent
    env_files = [project_root / ".env.local", project_root / ".env"]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key, value = key.strip(), value.strip().strip('"').strip("'")
                            if key not in os.environ:
                                os.environ[key] = value
            except Exception:
                pass
            break

# Load environment at module import
_load_env_local()

class Config:
    def __init__(self, config_path: str = None):
        # Environment already loaded by _load_env_local()
        
        self.config = {
            'data_sources': {
                'log_files': {
                    'path': os.getenv('LOG_FILES_PATH', './data/logs'),
                    'format': 'json'
                },
                'metrics': {
                    'host': os.getenv('METRICS_DB_HOST', 'localhost'),
                    'port': int(os.getenv('METRICS_DB_PORT', 5432)),
                }
            },
            'model': {
                'max_time_window': 3600,  # 1 hour in seconds
                'similarity_threshold': 0.7,
                'min_cluster_size': 3
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/app.log'
            }
        }
        
        # Override with config file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                self._deep_update(self.config, file_config)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def update(self, updates: Dict):
        """Update configuration"""
        self._deep_update(self.config, updates)
    
    def _deep_update(self, d: Dict, u: Dict):
        """Recursively update dictionary d with values from dictionary u"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
