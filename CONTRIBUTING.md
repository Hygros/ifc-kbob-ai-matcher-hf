# Contributing

Thank you for considering a contribution! Here are a few guidelines.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and configure `KBOB_DATABASE_PATH`.

## Development Workflow

- Create a feature branch from `main`.
- Keep commits focused and well-described.
- Run existing tests before opening a PR:
  ```bash
  python -m unittest discover -s Evaluation/tests -p "test_*.py" -v
  ```

## Code Style

- Follow existing conventions in the codebase.
- Use clear, descriptive variable names (German domain terms are fine).

## Pull Requests

- Fill out the PR template.
- Reference related issues.
- Ensure CI passes.

## Reporting Issues

- Use the issue templates (Bug Report, Feature Request).
- Include steps to reproduce for bugs.
