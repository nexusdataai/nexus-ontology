# Create MCP Tool
Please refer my project specific cursor rule .cursor/rules/project-rule.mdc, the rule state the structure and process for MCP tool development. Can you read that throughly and let me know what steps would you follow if i ask you to create a MCP tool for journey management say journey-tool for the script scripts/journey-scripts/manage_journey.py, dont implement , just tell me your understanding on step details. The MCP Tool requirement is written inside doc/journey-tool.md


Please refer my project specific cursor rule .cursor/rules/project-rule.mdc, the rule state the structure and process for MCP tool development. Can you read that throughly and let me know what steps would you follow if i ask you to diagnose the cursor mcp tool.Please refer diag directory


please refer the /opt/mycode/ptr/ai-job-engine/src/stages/raw-analysis and /opt/mycode/ptr/ai-job-engine/src/stages/stripped-schema stages , understand the code , i want to create some other stages with different purpose in same way. Now i want to create a stage for Code Generation and would like to create code for that inside /opt/mycode/ptr/ai-job-engine/src/stages/code-generation. The code generation process will use cusror API to call the cursor background agent and will give specifications to the background agent for code generation. Can you write that code-generation stage

I want to write a UI developer AI Agent using that will use cusror API to call the cursor background agent and will give specifications to the background agent for complete UI development.The main specification and custom specifications are all inside src/stages/ui-development. I want to create some stage implementation for ui-development.Please refer a stage raw-analysis that is already built please refer the /opt/mycode/ptr/ai-job-engine/src/stages/raw-analysis.The ui-development stage can be of four steps :

Step1 - Planning -Read main spec and custom specs and create a detailed PRD / Phasewise Plan / Implemenation Checklists and save them as reports and also save the detailed logs of the process.

Step 2 -Development - Fork or clone the git repo from boilerplate template and develop the Phase1 implementation inside Dev Branch.

Step 3 - Tests - Do all required tests and verifications as per defined cursor rules and guidlines.

Step4 -  Deploy - Provision the prerequisite AWS infrastructures and deploy the dev branch and create a report on UI access guidelines. 

Can you create the ui-development stage implementation inside src/stages/ui-development directory

Example Prompt

Now can you go ahead and implement "Users enter co-authors in a multi-select dropdown from the list of all current users" of Phase 3 in plan.md. You need to follow the TDD aproach and create the DB test, API test , and UI test verification script for the feature.So far the verification script is written inside /workspace/test-script. 
Then incrementally develop the feature in bottom up way  and progress with test and verifications.First do the database design tasks, write migration script for data layer changes and do the database changes for the feature.After changing the db , please verify the database changes with some shell script like /workspace/test-script/db-list-users-articles.sh. After that make the backend API changes and verify every change using the script like using  /workspace/test-script/curl-api-test.sh. Once we are all set with UI , then only make the UI changes for the feature and verify it with the script like /workspace/test-script/ui-coauthor-article.spec.js.       

Please mind that while restarting frontend and backend server , you may have port conflict , please kill the existing process with pkill and start them , they should be running on 3000(backend) and 3001(frontend) respectively.


please refer the journey management cli /opt/mycode/ptr/ai-job-engine/scripts/actors/journeys/journey-manager.py , now i want create some BDD testing for this CLI functionalities with python behave library. For every behaviour , it should invoke the CLI script and give inputs for any console prompt and will complete differen business use case , can you tell me what is the best way to achieve that

Pr-10 --

Now can you go ahead and implement:

Edit Locking Mechanism (PRD: "When a user opens an article for editing, the article becomes locked. The lock remains until: The user saves the article, Navigates away, or 5 minutes pass after the user is last seen 'online'.")

You need to follow the TDD aproach and create the DB test, API test , and UI test verification script for the feature.So far the verification script is written inside /workspace/test-script. 
Then incrementally develop the feature in bottom up way  and progress with test and verifications.First do the database design tasks, write migration script for data layer changes and do the database changes for the feature.After changing the db , please verify the database changes with some shell script like /workspace/test-script/db-list-users-articles.sh. After that make the backend API changes and verify every change using the script like using  /workspace/test-script/curl-api-test.sh. Once we are all set with UI , then only make the UI changes for the feature and verify it with the script like /workspace/test-script/ui-coauthor-article.spec.js.       

Please mind that while restarting frontend and backend server , you may have port conflict , please kill the existing process with pkill and start them , they should be running on 3000(backend) and 3001(frontend) respectively.
