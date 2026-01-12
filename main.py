#!/usr/bin/env python3
"""
lib-learn: Interactive CLI for learning Python libraries.

Usage:
    python main.py learn pandas.DataFrame          # LLM-powered interactive learning
    python main.py flashcards pandas.DataFrame     # Classic flashcard mode
    python main.py config --init                   # Create config file
"""

import os
import sys
import logging
import argparse
import warnings

from dotenv import load_dotenv

import util

# Suppress noisy pydantic serialization warnings from litellm
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Load environment variables from .env file
load_dotenv()

# Suppress litellm verbose output
os.environ.setdefault("LITELLM_LOG", "ERROR")

# Handle Windows unicode console (optional)
try:
    import win_unicode_console

    win_unicode_console.streams.enable()
except ImportError:
    pass

# Setup logging
util.setup_root_logger()
util.silence_loggers("httpcore", "httpx", "openai", "LiteLLM", "litellm")
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="LLM-powered interactive library learning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py learn pandas.DataFrame
    python main.py learn collections.Counter --questions 5
    python main.py flashcards pandas.DataFrame -f -c -s
    python main.py config --show
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Learn command (new LLM-powered mode)
    learn = subparsers.add_parser(
        "learn",
        help="Start interactive LLM-powered learning session",
    )
    learn.add_argument(
        "library",
        help="Library to learn (e.g., pandas.DataFrame, collections.Counter)",
    )
    learn.add_argument(
        "--model",
        help="LLM model to use (overrides config)",
    )
    learn.add_argument(
        "--provider",
        help="LLM provider (openai, anthropic, ollama, etc.)",
    )
    learn.add_argument(
        "--questions",
        "-n",
        type=int,
        help="Number of questions to generate",
    )
    learn.add_argument(
        "--no-llm",
        action="store_true",
        help="Use heuristics only (no LLM calls)",
    )

    # Flashcards command (legacy mode)
    flash = subparsers.add_parser(
        "flashcards",
        help="Classic flashcard mode (no LLM)",
    )
    flash.add_argument("path", help="Module or class path")
    flash.add_argument(
        "-f",
        "--full",
        action="store_true",
        help="Show full-length docstrings",
    )
    flash.add_argument(
        "-c",
        "--cycle",
        action="store_true",
        help="Cycle the deck indefinitely",
    )
    flash.add_argument(
        "-s",
        "--shuffle",
        action="store_true",
        help="Keep the deck shuffled",
    )
    flash.add_argument(
        "-p",
        "--private",
        action="store_true",
        help="Allow private routines",
    )
    flash.add_argument(
        "-m",
        "--special",
        action="store_true",
        help="Allow special routines",
    )

    # Config command
    config_cmd = subparsers.add_parser(
        "config",
        help="Manage configuration",
    )
    config_cmd.add_argument(
        "--init",
        action="store_true",
        help="Create default config file",
    )
    config_cmd.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration",
    )

    return parser


def cmd_learn(args):
    """Run the LLM-powered learning session."""
    from config import ConfigManager
    from session.manager import SessionManager

    # Build CLI overrides
    cli_overrides = {}
    if args.model:
        cli_overrides["llm"] = {"model": args.model}
    if args.provider:
        cli_overrides.setdefault("llm", {})["provider"] = args.provider
    if args.questions:
        cli_overrides["session"] = {"questions_per_session": args.questions}

    # Load configuration
    try:
        config = ConfigManager.load(cli_overrides)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

    # Validate configuration
    errors = ConfigManager.validate(config)
    if errors and not args.no_llm:
        for error in errors:
            print(f"Configuration error: {error}")
        print("\nRun 'python main.py config --init' to create a config file.")
        print("Or set environment variables like OPENAI_API_KEY.")
        sys.exit(1)

    # Start session
    try:
        manager = SessionManager(config)
        manager.start_session(args.library)
        manager.interact()
    except ImportError as e:
        print(f"Error: Could not import library '{args.library}'")
        print(f"Details: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSession interrupted.")
    except Exception as e:
        logger.exception("Session error")
        print(f"Error: {e}")
        sys.exit(1)


def cmd_flashcards(args):
    """Run the classic flashcard mode."""
    import flashcards

    try:
        cards, quality = flashcards.create_deck(
            args.path,
            allow_private=args.private,
            allow_special=args.special,
            short=not args.full,
        )

        if not cards:
            print(f"No documented routines found in '{args.path}'")
            sys.exit(1)

        print(f"Found {len(cards)} routines ({quality:.0f}% documented)")
        flashcards.prompt_cards(cards, cycle=args.cycle, shuffle=args.shuffle)

    except TypeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ImportError as e:
        print(f"Error: Could not import '{args.path}'")
        print(f"Details: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting.")


def cmd_config(args):
    """Handle configuration commands."""
    from config import ConfigManager

    if args.init:
        path = ConfigManager.init_config_file()
        print(f"Created config file: {path}")
        print("Edit this file to configure your LLM provider and API key.")

    elif args.show:
        config = ConfigManager.load()
        print(ConfigManager.show_config(config))

    else:
        print("Use --init to create a config file or --show to display current config.")


def main():
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "learn":
        cmd_learn(args)
    elif args.command == "flashcards":
        cmd_flashcards(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        # No command specified - show help
        parser.print_help()
        print("\nTip: Try 'python main.py learn collections.Counter' to get started!")


if __name__ == "__main__":
    main()
