We are in the process of building the project described in @doc/prd.md
We are doing this by going through the phases described in @doc/phaseplan.md
We are currently in Phase1 and not yet implemented the changes in @doc/checklist.md

Please create a new plan for implementing the missing elements of phase 1/2/3.
Look around the repo and past checklists to understand the current project.
Then create a .md checklist with ~20 items that will allow us to make the most progress towards finishing the current phase. Keep the items simple and use max 2 layers of hierarchy. Do not put in any code snippets.



========================================

For each unchecked item in the checklist:

1. Read the item.
2. Gather context (PRD, checklists, relevant files).
3. Plan the edits.
4. Execute.
5. If backend-related, run a quick terminal test.
6. Mark the item complete & note decisions/bugs.
7. Repeat until checklist is done.

======================================

We are currently in stage X and have recently implemented the changes in @ChecklistX.md

I want to make sure everything works properly.

Please conduct a simple set of tests, either by creating a testing script or simply by testing API routes and backend features via your terminal.

I am looking for the simplest, most straightforward confirmation that everything works. We are building an MVP here, not Google core infrastructure.

Execute the tests right away, and report back to me with any issues.

------------------
Test Prompts
Here is an insanely useful Claude 4 prompt for engineers.

Use it to automatically generate unit tests for your code:

---
<prompt_explanation>
You are an expert software tester tasked with thoroughly testing a given piece of code. Your goal is to generate a comprehensive set of test cases that will exercise the code and uncover any potential bugs or issues.

First, carefully analyze the provided code. Understand its purpose, inputs, outputs, and any key logic or calculations it performs. Spend significant time considering all the different scenarios and edge cases that need to be tested.

Next, brainstorm a list of test cases you think will be necessary to fully validate the correctness of the code. For each test case, specify the following in a table:
- Objective: The goal of the test case 
- Inputs: The specific inputs that should be provided 
- Expected Output: The expected result the code should produce for the given inputs
- Test Type: The category of the test (e.g. positive test, negative test, edge case, etc.)

After defining all the test cases in tabular format, write out the actual test code for each case. Ensure the test code follows these steps:
1. Arrange: Set up any necessary preconditions and inputs 
2. Act: Execute the code being tested
3. Assert: Verify the actual output matches the expected output

For each test, provide clear comments explaining what is being tested and why it's important. 

Once all the individual test cases have been written, review them to ensure they cover the full range of scenarios. Consider if any additional tests are needed for completeness.

Finally, provide a summary of the test coverage and any insights gained from this test planning exercise. 
</prompt_explanation>

<response_format>
<code_analysis_section>
<header>Code Analysis:</header>
<analysis>$code_analysis</analysis>
</code_analysis_section>

<test_cases_section>
<header>Test Cases:</header>
<table>
<header_row>
<column1>Objective</column1>
<column2>Inputs</column2>
<column3>Expected Output</column3>
<column4>Test Type</column4>
</header_row>
$test_case_table
</table>
</test_cases_section>

<test_code_section>
<header>Test Code:</header>
$test_code
</test_code_section>

<test_review_section>
<header>Test Review:</header>
<review>$test_review</review>
</test_review_section>

<coverage_summary_section>
<header>Test Coverage Summary:</header>
<summary>$coverage_summary</summary>
<insights>$insights</insights>
</coverage_summary_section>
</response_format>

Here is the code that you must generate test cases for:
<code>
{{PASTE_YOUR_CODE_HERE{{
</code>
---