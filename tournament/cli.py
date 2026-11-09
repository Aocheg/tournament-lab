"""Interactive Command-Line Interface (CLI) for TournamentLab."""

import os
import sys
from typing import Optional
from tournament.exceptions import (
    DuplicateError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from tournament.fixtures import (
    find_fixture_by_id,
    generate_schedule,
    record_result,
)
from tournament.models import (
    MAX_TEAMS,
    MIN_TEAMS,
    STATUS_PLAYED,
)
from tournament.simulation import simulate_demo_fixtures
from tournament.standings import (
    compute_standings,
    get_champion,
    get_season_status,
    verify_league_invariants,
)
from tournament.storage import load_tournament, save_tournament
from tournament.teams import find_team_by_id, register_team


class TournamentCLI:
    """Terminal user interface controller for TournamentLab."""

    def __init__(self) -> None:
        self.teams: list[dict] = []
        self.fixtures: list[dict] = []
        self.active_file: Optional[str] = None

    def print_header(self, title: str) -> None:
        print("\n" + "=" * 65)
        print(f"  {title.upper()}")
        print("=" * 65)

    def print_menu(self) -> None:
        season_status = get_season_status(self.fixtures)
        status_label = {
            "no_fixtures": "NO FIXTURES",
            "in_progress": "IN PROGRESS",
            "completed": "COMPLETED",
        }.get(season_status, "UNKNOWN")

        print("\n" + "-" * 65)
        print(f" TOURNAMENTLAB | Teams: {len(self.teams)}/8 | Status: [{status_label}]")
        print("-" * 65)
        print("  1. Register Team")
        print("  2. List Registered Teams")
        print("  3. Generate Round-Robin Schedule")
        print("  4. List Fixtures & Results")
        print("  5. Record Match Result")
        print("  6. View League Standings")
        print("  7. Simulate Remaining Demo Fixtures (Seeded)")
        print("  8. Season Report & Crown Champion")
        print("  9. Save Tournament to JSON")
        print(" 10. Load Tournament from JSON")
        print(" 11. Reset Tournament / New Season")
        print("  0. Exit")
        print("-" * 65)

    def prompt(self, message: str) -> str:
        """Prompt user with clean input handling."""
        try:
            return input(f"{message}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return ""

    def register_team_action(self) -> None:
        self.print_header("Register New Team")
        if len(self.teams) >= MAX_TEAMS:
            print(f"Error: League is at maximum capacity ({MAX_TEAMS} teams).")
            return
        if self.fixtures:
            print("Notice: Schedule has already been generated. Reset tournament to change teams.")
            return

        name = self.prompt("Enter team display name (2-30 characters)")
        if not name:
            print("Registration cancelled.")
            return

        try:
            team = register_team(self.teams, name)
            print(f"Success: Registered team '{team['name']}' with ID {team['id']}.")
            print(f"Total teams registered: {len(self.teams)} (Minimum needed: {MIN_TEAMS})")
        except (ValidationError, DuplicateError) as err:
            print(f"Registration Error: {err}")

    def list_teams_action(self) -> None:
        self.print_header("Registered Teams")
        if not self.teams:
            print("No teams registered yet. Use option 1 to register teams.")
            return

        print(f"{'Team ID':<10} | {'Display Name':<30}")
        print("-" * 45)
        for t in self.teams:
            print(f"{t['id']:<10} | {t['name']:<30}")
        print("-" * 45)
        print(f"Total: {len(self.teams)} team(s)")

    def generate_schedule_action(self) -> None:
        self.print_header("Generate Schedule")
        if self.fixtures:
            confirm = self.prompt("Schedule already exists. Overwrite and discard existing matches? (y/N)")
            if confirm.lower() != "y":
                print("Fixture generation cancelled.")
                return

        try:
            fixtures = generate_schedule(self.teams)
            self.fixtures = fixtures
            print(f"Success: Generated {len(self.fixtures)} round-robin fixtures for {len(self.teams)} teams.")
            print("Every team will play each opponent exactly once.")
        except ValidationError as err:
            print(f"Schedule Generation Error: {err}")

    def list_fixtures_action(self) -> None:
        self.print_header("League Fixtures")
        if not self.fixtures:
            print("No fixtures generated. Register 4-8 teams and use option 3 to generate.")
            return

        print(f"{'Match ID':<10} | {'Home Team':<20} | {'Score':^7} | {'Away Team':<20} | {'Status':<10}")
        print("-" * 75)
        for fix in self.fixtures:
            h_team = find_team_by_id(self.teams, fix["home_id"])
            a_team = find_team_by_id(self.teams, fix["away_id"])
            h_name = h_team["name"] if h_team else fix["home_id"]
            a_name = a_team["name"] if a_team else fix["away_id"]

            if fix["status"] == STATUS_PLAYED:
                score_str = f"{fix['home_score']} - {fix['away_score']}"
                status_str = "played"
            else:
                score_str = " - "
                status_str = "pending"

            print(f"{fix['id']:<10} | {h_name:<20} | {score_str:^7} | {a_name:<20} | {status_str:<10}")
        print("-" * 75)
        played = sum(1 for f in self.fixtures if f["status"] == STATUS_PLAYED)
        print(f"Progress: {played}/{len(self.fixtures)} fixtures completed.")

    def record_result_action(self) -> None:
        self.print_header("Record Match Result")
        if not self.fixtures:
            print("No fixtures available. Generate schedule first.")
            return

        pending = [f for f in self.fixtures if f["status"] != STATUS_PLAYED]
        if not pending:
            print("All fixtures have already been completed!")
            return

        print("Pending Match IDs:", ", ".join(f["id"] for f in pending))
        fix_id = self.prompt("Enter Match ID (e.g. M001)")
        if not fix_id:
            return

        fixture = find_fixture_by_id(self.fixtures, fix_id)
        if not fixture:
            print(f"Error: Fixture '{fix_id}' not found.")
            return
        if fixture["status"] == STATUS_PLAYED:
            print(f"Error: Fixture '{fix_id}' has already been played.")
            return

        h_team = find_team_by_id(self.teams, fixture["home_id"])
        a_team = find_team_by_id(self.teams, fixture["away_id"])
        h_name = h_team["name"] if h_team else fixture["home_id"]
        a_name = a_team["name"] if a_team else fixture["away_id"]

        print(f"Recording score for {fixture['id']}: {h_name} (Home) vs {a_name} (Away)")
        h_str = self.prompt(f"Enter goals for {h_name}")
        a_str = self.prompt(f"Enter goals for {a_name}")

        try:
            # Parse strict integer
            if not h_str.isdigit() or not a_str.isdigit():
                print("Error: Scores must be non-negative whole numbers (e.g. 0, 1, 2).")
                return
            h_score = int(h_str)
            a_score = int(a_str)

            record_result(self.fixtures, fixture["id"], h_score, a_score)
            print(f"Success: Recorded {fixture['id']} -> {h_name} {h_score} - {a_score} {a_name}")
        except (ValidationError, DuplicateError, NotFoundError) as err:
            print(f"Error recording score: {err}")

    def view_standings_action(self) -> None:
        self.print_header("League Standings")
        if not self.teams:
            print("No teams registered yet.")
            return

        try:
            standings = compute_standings(self.teams, self.fixtures)
            is_valid, msg = verify_league_invariants(standings, self.fixtures)
            if not is_valid:
                print(f"Warning: League invariants anomaly detected ({msg})")

            season_status = get_season_status(self.fixtures)
            if season_status == "completed":
                print("Status: [SEASON COMPLETED]")
            elif season_status == "in_progress":
                print("Status: [LEAGUE IN PROGRESS - STANDINGS PROVISIONAL]")
            else:
                print("Status: [PRE-SEASON]")

            print("-" * 78)
            print(
                f"{'Pos':<4} | {'Team':<22} | {'P':>3} | {'W':>3} | {'D':>3} | {'L':>3} | "
                f"{'GF':>3} | {'GA':>3} | {'GD':>4} | {'PTS':>4}"
            )
            print("-" * 78)
            for row in standings:
                print(
                    f"{row['rank']:<4} | {row['name']:<22} | {row['played']:>3} | {row['won']:>3} | "
                    f"{row['drawn']:>3} | {row['lost']:>3} | {row['goals_for']:>3} | "
                    f"{row['goals_against']:>3} | {row['goal_difference']:>+4} | {row['points']:>4}"
                )
            print("-" * 78)
            print("Tie-Break Rule: Points > Goal Difference > Goals For > Alphabetical (case-insensitive)")
        except ValidationError as err:
            print(f"Error computing standings: {err}")

    def simulate_demo_action(self) -> None:
        self.print_header("Simulate Remaining Demo Fixtures")
        if not self.fixtures:
            print("No fixtures generated. Generate schedule first.")
            return

        pending_count = sum(1 for f in self.fixtures if f["status"] != STATUS_PLAYED)
        if pending_count == 0:
            print("All fixtures have already been played. Nothing to simulate.")
            return

        print(f"There are {pending_count} pending fixture(s).")
        confirm = self.prompt("Simulate all pending fixtures now? (y/N)")
        if confirm.lower() != "y":
            print("Simulation cancelled.")
            return

        seed_str = self.prompt("Enter random seed for reproducible results (default: 42)")
        seed = 42
        if seed_str.strip():
            try:
                seed = int(seed_str)
            except ValueError:
                print("Invalid seed. Using default seed 42.")
                seed = 42

        count = simulate_demo_fixtures(self.fixtures, seed=seed)
        print(f"Success: Simulated {count} fixture(s) reproducibly using seed={seed}.")
        print("League standings have been updated.")

    def season_report_action(self) -> None:
        self.print_header("Season Report & Champion")
        champion, message = get_champion(self.teams, self.fixtures)
        status = get_season_status(self.fixtures)

        if status != "completed":
            print(f"Report: {message}")
            print("Standings remain provisional until every scheduled fixture has a recorded result.")
            return

        print("\n" + "*" * 65)
        print(f"  CONGRATULATIONS TO THE CHAMPION: {champion['name'].upper()}!")
        print("*" * 65)
        print(f"  Points:          {champion['points']}")
        print(f"  Goal Difference: {champion['goal_difference']:+d}")
        print(f"  Goals Scored:    {champion['goals_for']}")
        print(f"  Goals Conceded:  {champion['goals_against']}")
        print(f"  Record (W-D-L):  {champion['won']}-{champion['drawn']}-{champion['lost']}")
        print("*" * 65)

    def save_tournament_action(self) -> None:
        self.print_header("Save Tournament State")
        default_path = self.active_file or "tournament.json"
        path_input = self.prompt(f"Enter JSON file path to save (default: {default_path})")
        target_path = path_input if path_input else default_path

        try:
            save_tournament(target_path, self.teams, self.fixtures)
            self.active_file = target_path
            print(f"Success: Tournament saved to '{target_path}'.")
        except StorageError as err:
            print(f"Save Error: {err}")

    def load_tournament_action(self) -> None:
        self.print_header("Load Tournament State")
        default_path = self.active_file or "tournament.json"
        path_input = self.prompt(f"Enter JSON file path to load (default: {default_path})")
        target_path = path_input if path_input else default_path

        try:
            loaded = load_tournament(target_path)
            self.teams = loaded["teams"]
            self.fixtures = loaded["fixtures"]
            self.active_file = target_path
            print(f"Success: Tournament loaded from '{target_path}'.")
            print(f"Loaded {len(self.teams)} teams and {len(self.fixtures)} fixtures.")
        except StorageError as err:
            print(f"Load Error (State preserved): {err}")

    def reset_tournament_action(self) -> None:
        self.print_header("Reset Tournament")
        confirm = self.prompt("Are you sure you want to discard all teams and fixtures? (y/N)")
        if confirm.lower() == "y":
            self.teams = []
            self.fixtures = []
            self.active_file = None
            print("Tournament state has been completely reset.")
        else:
            print("Reset cancelled.")

    def run(self) -> None:
        """Main interaction loop."""
        self.print_header("Welcome to TournamentLab — Esports League Manager")
        while True:
            self.print_menu()
            choice = self.prompt("Select an option (0-11)")

            if choice == "1":
                self.register_team_action()
            elif choice == "2":
                self.list_teams_action()
            elif choice == "3":
                self.generate_schedule_action()
            elif choice == "4":
                self.list_fixtures_action()
            elif choice == "5":
                self.record_result_action()
            elif choice == "6":
                self.view_standings_action()
            elif choice == "7":
                self.simulate_demo_action()
            elif choice == "8":
                self.season_report_action()
            elif choice == "9":
                self.save_tournament_action()
            elif choice == "10":
                self.load_tournament_action()
            elif choice == "11":
                self.reset_tournament_action()
            elif choice == "0":
                print("\nThank you for using TournamentLab! Fair play to all teams.\n")
                break
            else:
                print(f"Invalid option '{choice}'. Please select a number from 0 to 11.")
