# Project Rules

The following rules apply to all code in this repository. Every contributor must follow them.

1. **Never hardcode secrets.** Use environment variables or configuration files. Never commit API keys, tokens, or passwords.

2. **Every feature must be independently testable.** Design components with clear boundaries so they can be tested in isolation.

3. **Every public function must include type hints.** All function signatures must have complete type annotations for parameters and return values.

4. **Business logic must never depend on Telegram.** The downloader framework must remain platform-agnostic at its core.

5. **Every feature requires tests.** No feature is complete without corresponding unit or integration tests.

6. **English only for code comments.** All comments, docstrings, and documentation must be written in English.

7. **Keep commits small.** Each commit should represent a single logical change. Avoid large, unrelated changes in one commit.

8. **Prefer composition over inheritance.** Use composition to build complex behavior from simple, reusable pieces.

9. **No premature optimization.** Write clear, correct code first. Optimize only when there is a measured performance need.

10. **Keep architecture simple.** Avoid unnecessary abstractions. Choose the simplest solution that meets the requirements.

