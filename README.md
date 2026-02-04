# databricks_mcq_copilot_agent
Test simulation platform for Databricks certification examinations

# Databricks Data Engineer – MCQ Assessment Agent

Interactive MCQ practice platform for:

- Databricks Certified Data Engineer **Associate**
- Databricks Certified Data Engineer **Professional**

## Features

- Exam selector (Associate / Professional)
- Separate question pools per exam (difficulty-based)
- Separate saved sessions per user & exam
- Next / Previous navigation
- Mark-for-review per question
- Jump to any question by number
- Sidebar navigator with status icons
- Real-time feedback + explanations
- Running summary (attempted, correct, incorrect, % score)
- Elapsed time tracking
- Final detailed summary by question

## How To Deploy (FREE)

1. Push all files to a public GitHub repo.
2. Go to https://share.streamlit.io/
3. Select your repo → choose `app.py` → Deploy.

## Extend the Question Bank

Just add new objects to `question_bank.json` with:

- `difficulty`: `"associate"` or `"professional"`
- `question_id`
- `domain`
- `question_text`
- `choices`
- `correct_answer`
- `explanation`
