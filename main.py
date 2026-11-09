#!/usr/bin/env python3
"""TournamentLab: Ultimate Esports League Manager.

Main entry point for running the CLI application.
"""

import sys
from tournament.cli import TournamentCLI
from tournament.storage import load_tournament


def main() -> None:
    cli = TournamentCLI()
    if len(sys.argv) > 1:
        initial_file = sys.argv[1]
        try:
            loaded = load_tournament(initial_file)
            cli.teams = loaded["teams"]
            cli.fixtures = loaded["fixtures"]
            cli.active_file = initial_file
            print(f"Pre-loaded tournament file: '{initial_file}' ({len(cli.teams)} teams, {len(cli.fixtures)} fixtures).")
        except Exception as err:
            print(f"Warning: Could not pre-load file '{initial_file}': {err}")

    cli.run()


if __name__ == "__main__":
    main()
