# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

lib-learn is an LLM-powered interactive CLI for learning Python libraries. It uses agents to explore libraries, identify important components, and generate interactive questions that test understanding through code execution.

## Commands

### LLM-Powered Interactive Learning (New)
```bash
python main.py learn pandas.DataFrame              # Start learning session
python main.py learn collections.Counter -n 5     # Generate 5 questions
python main.py learn pandas.DataFrame --provider anthropic --model claude-sonnet-4-20250514
```

### Classic Flashcard Mode (Legacy)
```bash
python main.py flashcards pandas.DataFrame        # Basic flashcard mode
python main.py flashcards pandas.DataFrame -f -c -s  # Full docs, cycle, shuffle
```

### Configuration
```bash
python main.py config --init    # Create ~/.lib-learn/config.toml
python main.py config --show    # Show current configuration
```

### Session Commands
During a learning session:
- `/hint` - Get a hint for the current question
- `/skip` - Skip the current question
- `/repl` - Enter REPL mode to experiment
- `/quit` - End the session

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Package Structure
```
lib-learn/
├── main.py              # CLI entry point with subcommands
├── config.py            # Configuration management (TOML, env vars)
├── introspection/       # Library analysis
│   ├── analyzer.py      # LibraryAnalyzer for discovering components
│   └── component.py     # LibraryComponent and RankedComponent dataclasses
├── agents/              # LLM-powered agents
│   ├── base.py          # BaseAgent with litellm integration
│   ├── explorer.py      # ExplorerAgent for ranking components
│   └── prompts.py       # Prompt templates
├── questions/           # Question generation
│   ├── base.py          # Question dataclass, QuestionGenerator ABC
│   ├── generator.py     # QuestionOrchestrator
│   └── types/           # 4 question type generators
├── execution/           # Code execution
│   ├── sandbox.py       # Sandboxed subprocess execution
│   └── validator.py     # Answer validation
├── session/             # Session management
│   ├── state.py         # SessionState dataclass
│   ├── manager.py       # SessionManager
│   └── repl.py          # Interactive REPL
└── flashcards.py        # Legacy flashcard mode
```

### Data Flow
1. **LibraryAnalyzer** introspects the target library using `inspect.getmembers()`
2. **ExplorerAgent** ranks components by importance (heuristics + LLM)
3. **QuestionOrchestrator** generates varied question types
4. **SessionManager** runs the interactive loop
5. **AnswerValidator** executes user code in sandbox and validates

### Question Types
- `write_syntax` - Write code from scratch
- `fill_blank` - Complete partial code
- `predict_output` - Predict what code returns
- `fix_buggy` - Fix buggy code

### Configuration
Config sources (priority order): CLI args > env vars > ~/.lib-learn/config.toml > defaults

Key environment variables:
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - LLM API keys
- `LIBLEARN_LLM_PROVIDER` - Provider name
- `LIBLEARN_LLM_MODEL` - Model name

## Key Design Decisions

- **litellm for multi-provider support**: Works with OpenAI, Anthropic, Ollama, etc.
- **Subprocess sandbox**: User code executes in isolated subprocess with import restrictions
- **Heuristic + LLM ranking**: Components scored by both automated heuristics and LLM analysis
- **Backward compatible**: `flashcards` subcommand preserves legacy behavior

## Known Limitations

- Cannot obtain signatures for some routines where `inspect.signature()` fails
- Does not work on `itertools` module (apparent functions are actually classes)
- Sandbox restrictions prevent some library features from working
