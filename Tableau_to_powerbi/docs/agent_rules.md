# Agent Rules

## Code Standards
1. Python 3.11+ with type hints on all function signatures
2. Pydantic models for all data structures
3. Structured logging via `logging` module
4. No global mutable state
5. Functions should be pure where possible
6. Maximum function length: 50 lines

## Naming Conventions
- Modules: snake_case (e.g., `twb_parser.py`)
- Classes: PascalCase (e.g., `WorkbookIR`)
- Functions: snake_case (e.g., `parse_datasource`)
- Constants: UPPER_SNAKE_CASE (e.g., `MARK_TYPE_MAP`)

## Error Handling
- Raise `ValueError` for invalid input data
- Raise `FileNotFoundError` for missing files
- Log warnings for non-critical parsing failures (skip unknown elements)
- Never silently swallow exceptions

## Module Boundaries
- Parser modules only produce IR models (no generation logic)
- Translation modules take IR as input and produce enriched IR
- Generator modules take IR as input and produce file content (strings/bytes)
- The pipeline orchestrator is the only module that chains all stages

## Testing
- Unit tests for each module
- Integration test for full pipeline
- Test with the provided Shopping (1).twb file

## Dependencies
- Only use: streamlit, lxml, pydantic, python standard library
- No external PBI SDK or proprietary libraries
