"""
BDD Endurance Testing Framework
Continuous testing for stability and performance validation
"""

__version__ = "1.0.0"
__author__ = "AI Job Engine Team"

from .bdd_endurance_runner import BDDEnduranceRunner
from .server_health_monitor import ServerHealthMonitor
from .result_aggregator import ResultAggregator
from .endurance_report import EnduranceReportGenerator

__all__ = [
    'BDDEnduranceRunner',
    'ServerHealthMonitor',
    'ResultAggregator',
    'EnduranceReportGenerator',
]
