"""Prompt templates for question generation."""

SYSTEM_PROMPT_QUESTION_GEN = """You are creating practice questions to help someone learn the {library} library.
Generate questions that:
- Are solvable with the specific function/method being taught
- Have clear, unambiguous expected answers
- Include realistic use cases
- Are appropriate for the specified difficulty level

Respond only with valid JSON."""


USER_PROMPT_WRITE_SYNTAX = """Create a "write code from scratch" question for:
Function: {qualified_path}
Signature: {signature}
Purpose: {synopsis}
Full docstring: {docstring}

The question should:
1. Describe a concrete task the user should accomplish
2. Provide any necessary input data as part of setup_code
3. Have a clear expected output

Respond in JSON:
{{
  "prompt": "Write code to...",
  "setup_code": "import library\\ndata = ...",
  "expected_code": "result = data.method(...)",
  "expected_output": "the expected result as a string",
  "hints": ["Hint 1", "Hint 2", "Hint 3"],
  "difficulty": 3,
  "explanation": "This works because..."
}}"""


USER_PROMPT_FILL_BLANK = """Create a fill-in-the-blank question for:
Function: {qualified_path}
Signature: {signature}
Purpose: {synopsis}

The blank should replace the function/method name.
Provide enough context that the correct function is obvious to someone who knows it.

Respond in JSON:
{{
  "prompt": "Complete the code to {task}:\\n```python\\n{code_with_blank}\\n```",
  "setup_code": "import statements and data setup",
  "code_with_blank": "code with ___ for the blank",
  "answer": "the_function_name",
  "full_code": "complete working code",
  "hints": ["Hint 1", "Hint 2"],
  "difficulty": 2,
  "explanation": "This works because..."
}}"""


USER_PROMPT_PREDICT_OUTPUT = """Create a "predict the output" question for:
Function: {qualified_path}
Signature: {signature}
Purpose: {synopsis}

The code should demonstrate the function's behavior clearly.
The output should be deterministic and educational.

Respond in JSON:
{{
  "prompt": "What does this code output?",
  "setup_code": "import statements",
  "code": "the code to show the user",
  "expected_output": "the exact output as a string",
  "hints": ["Think about...", "Remember that..."],
  "difficulty": 2,
  "explanation": "This outputs X because..."
}}"""


USER_PROMPT_FIX_BUGGY = """Create a bug-fixing question for:
Function: {qualified_path}
Signature: {signature}
Purpose: {synopsis}

Create code with exactly ONE bug related to this function:
- Misspelled function name, OR
- Wrong parameter name, OR
- Incorrect parameter value, OR
- Type error in argument

The bug should be subtle but fixable by someone who knows the function.

Respond in JSON:
{{
  "prompt": "Fix the bug in this code:",
  "setup_code": "import statements and data",
  "buggy_code": "code with the bug",
  "correct_code": "the fixed code",
  "bug_description": "The bug is...",
  "hints": ["Check the...", "The correct method is..."],
  "difficulty": 3,
  "explanation": "The bug was X, fixed by Y"
}}"""
