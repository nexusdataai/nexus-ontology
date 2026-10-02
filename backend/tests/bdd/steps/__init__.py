# Step definitions for BDD testing
# Behave auto-discovers step files in the steps/ directory
# We must explicitly import subdirectory step files for behave to discover them

# Import steps from journey subdirectory
from tests.bdd.steps.journey.journey_steps import *
from tests.bdd.steps.journey.stage_steps import *

# Import steps from license subdirectory (if exists)
try:
    from tests.bdd.steps.license.license_service_steps import *
except ImportError:
    pass

# Import steps from capability subdirectory (if exists)  
try:
    from tests.bdd.steps.capability.capability_steps import *
except ImportError:
    pass

# Import steps from call_process subdirectory (if exists)
try:
    from tests.bdd.steps.call_process.call_steps import *
except ImportError:
    pass
