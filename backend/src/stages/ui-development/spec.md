You will be working on a new react based Web UI project development with some custom features 

Use the existing boilerplate located at:
https://github.com/trilogy-group/alert-engine-ui.git

Fork it or clone it into the new repo:
https://github.com/trilogy-group/swarm-ui

The existing boilerplate will have the following cursor rules 

1.Thumb rules inside .cursor/rules/senior-engineer-task-execution.md

2.UI development rule inside .cursor/rules/ui-development-rules.mdc

3. Intgeration rule with API/MCP server inside /opt/mycode/trilogy/alert-engine-ui/.cursor/rules/integration-rule.mdc

You need to make any changes as per those rules. Please be strict on those rules while developing the complete UI.


Here follows all the custom specifications for the application. Apply the following specification to customize the base code:

1. Generic Application Specification Like it's Name and key purpose inside src/stages/ui-development/Application-Generic-spec.md

2. Authentication (login/MFA) / RBAC Rules , inside src/stages/ui-development/Auth-RBAC.md

3. Solution Specific Pages / Dashboards inside src/stages/ui-development/Solution-pages-dashboards.md

4. Solution Specific Chat Requests / Voice Commands - /opt/mycode/ptr/ai-job-engine/src/stages/ui-development/chat-integration.md

5. Solution Specific Tools Specification -/opt/mycode/ptr/ai-job-engine/src/stages/ui-development/tools-specification.md

5. Solution specfic Deployment choices (AWS accounts/ domain/certificates) -
/opt/mycode/ptr/ai-job-engine/src/stages/ui-development/deployment-specification.md

6. Any solution specific environment choices (dev/stage/prod)

/opt/mycode/ptr/ai-job-engine/src/stages/ui-development/environment-choice.md

7. Application Configuration 
    - API endppoint
    - MCP Server Endpoint
    - Langflow endpoint

inside src/stages/ui-development/Application-configuration.md

Do a proper planning first and then create PRD documentation , Phasewise Plan and Implementation Checklist.

Then proceed with UI development as per Phasewise Plan and Implementation Checklist and create the complete report of phase1 development at the end 
of developement.The development should be done on dev branch first.

Finally deploy the application and create a consolidated report of deployment , access guide , and user guide.