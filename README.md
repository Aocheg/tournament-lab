# TOURNAMENTLAB: Esports League Manager.

> **A robust, mathematically fair, and tamper-proof esports league manager built with Python.**

---

## 1. Project Overview & Mission.

TournamentLab is a professional command-line Esports League Manager designed to guarantee competitive fairness, data integrity, and deterministic ranking.

TournamentLab enforces strict tournament rules:
- **Fair Scheduling:** Generates a deterministic single round-robin schedule where every pair meets once ($N(N-1)/2$ matches).
- **Dynamic Derivation:** League standings are always computed on-demand from canonical played match records—never from a driftable parallel scoreboard.
- **Strict Validation:** Scores must be non-negative integers. Booleans (`True`/`False`), floats, and negative numbers are strictly rejected.
- **Atomic Match Updates:** Fixture status and scores are updated simultaneously or not at all. Duplicate submissions are rejected.
- **Rigorous Multi-Key Tie-Break:** Teams are sorted by Points descending, Goal Difference descending, Goals For descending, and Normalized Name ascending.
- **Referential Integrity & Persistence:** Saves and loads JSON (`schema_version=1`) with complete validate-before-mutate guarantees.
- **Crowned Champion:** A champion is crowned only when 100% of fixtures are completed; otherwise, standings remain labeled *in progress*.

---

## 2. Architecture & File Structure.

TournamentLab follows clean modular architecture, strictly adhering to standard library Python without external dependencies:

```
tournament-lab/
├── .gitignore
├── README.md
├── main.py                       # CLI entry point & argument handler
├── tournament/
│   ├── __init__.py               # Package metadata
│   ├── models.py                 # Domain constants, types, strict int checks
│   ├── exceptions.py             # Custom exception hierarchy
│   ├── teams.py                  # Team registration, validation & TM-ID generation
│   ├── fixtures.py               # Round-robin pairing & atomic result recording
│   ├── standings.py              # Pure standings computation, tie-breaks & invariants
│   ├── simulation.py             # Seeded reproducible demo fixtures
│   ├── storage.py                # JSON schema & referential integrity validation
│   └── cli.py                    # Interactive terminal user interface
├── tests/
│   ├── __init__.py
│   ├── test_teams.py             # Unit tests for team rules (Scenarios 1-2)
│   ├── test_fixtures.py          # Unit tests for scheduling & combinatorics (Scenarios 3-7)
│   ├── test_standings.py         # Unit tests for scoring, tie-breaks & champion (Scenarios 8-13, 16)
│   ├── test_storage.py           # Unit tests for JSON persistence & schema (Scenarios 14-15)
│   ├── test_simulation.py        # Unit tests for reproducible simulation
│   └── test_integration.py      # End-to-end controlled demonstration dataset
└── docs/
    ├── design-decisions.md       # Architecture trade-offs & audit defence
    └── ai-learning-log.md        # 6 evidence-based AI learning cycles & reflections
```

---

## 3. Installation & Quick Start.

TournamentLab requires **Python 3.10+** (tested on Python 3.12). No third-party dependencies are needed.

### Running the CLI
```bash
# Run the interactive manager
python3 main.py

# Or pre-load a saved tournament file
python3 main.py season.json
```

---

## 4. CLI Menu & Navigation.

When launched, TournamentLab displays an interactive menu with real-time status banners:

```
-----------------------------------------------------------------
 TOURNAMENTLAB | Teams: 4/8 | Status: [IN PROGRESS]
-----------------------------------------------------------------
  1. Register Team
  2. List Registered Teams
  3. Generate Round-Robin Schedule
  4. List Fixtures & Results
  5. Record Match Result
  6. View League Standings
  7. Simulate Remaining Demo Fixtures (Seeded)
  8. Season Report & Crown Champion
  9. Save Tournament to JSON
 10. Load Tournament from JSON
 11. Reset Tournament / New Season
  0. Exit
-----------------------------------------------------------------
```

### Options Breakdown:
1. **Register Team:** Prompts for team display name (2–30 characters). Strips surrounding whitespace and rejects case-insensitive duplicates.
2. **List Registered Teams:** Displays all registered teams with their stable `TMxxx` IDs.
3. **Generate Round-Robin Schedule:** Creates $N(N-1)/2$ pairings for 4–8 registered teams. Enforces single generation per season.
4. **List Fixtures & Results:** Displays all scheduled matches, opponents, current scores, and pending/played status.
5. **Record Match Result:** Safely records scores for a pending match ID. Rejects invalid scores or duplicate entries without mutating state.
6. **View League Standings:** Dynamically computes and displays the formatted standings table, sorted by tie-breaker rules, along with invariant verification.
7. **Simulate Remaining Demo Fixtures:** Explicit choice to simulate remaining pending matches using a deterministic seed (default `42`).
8. **Season Report & Crown Champion:** Displays season winner if all matches have been played; otherwise announces remaining games.
9. **Save Tournament to JSON:** Serializes validated tournament data to JSON with `schema_version: 1`.
10. **Load Tournament from JSON:** Loads and strictly validates JSON with validate-before-mutate guarantees.
11. **Reset Tournament:** Clears all memory state after explicit confirmation.

---

## 5. Tournament Rules & Mathematical Invariants.

### 1. Scoring System
- **Win:** 3 points
- **Draw:** 1 point to each team
- **Loss:** 0 points

### 2. League Mathematical Invariants
Every computed table is audited against strict invariants:
1. **Total Points Invariant:**
   $$\text{Total Points} = 3 \times (\text{Non-Draw Played Matches}) + 2 \times (\text{Draw Played Matches})$$
2. **Goal Conservation Invariant:**
   $$\sum \text{Goals For (GF)} = \sum \text{Goals Against (GA)}$$
3. **Team Balance Invariants:**
   - $\text{Played} = \text{Won} + \text{Drawn} + \text{Lost}$
   - $\text{Goal Difference} = \text{Goals For} - \text{Goals Against}$
   - $\text{Points} = 3 \times \text{Won} + 1 \times \text{Drawn}$

### 3. Multi-Key Tie-Break Hierarchy
When two or more teams have identical points, TournamentLab breaks ties predictably using:
1. **Points descending** (`-points`)
2. **Goal Difference descending** (`-goal_difference`)
3. **Goals For descending** (`-goals_for`)
4. **Normalized Team Name ascending** (`name.casefold()`)

---

## 6. Controlled Demonstration Dataset Walkthrough.

TournamentLab includes a verified walkthrough replicating the Stage 4 benchmark:

1. **Register 4 Teams:**
   - `TM001`: Thunder
   - `TM002`: Comets
   - `TM003`: Phoenix
   - `TM004`: Rockets
2. **Generate Schedule:**
   - Produces exactly $4 \times 3 / 2 = 6$ fixtures (`M001` to `M006`).
3. **Enter Two Match Results:**
   - `M001`: Thunder 2 - 0 Comets (Win for Thunder)
   - `M002`: Thunder 1 - 1 Phoenix (Draw)
4. **Verified In-Progress Standings:**
   ```
   Pos  | Team                   |   P |   W |   D |   L |  GF |  GA |   GD |  PTS
   ------------------------------------------------------------------------------
   1    | Thunder                |   2 |   1 |   1 |   0 |   3 |   1 |   +2 |    4
   2    | Phoenix                |   1 |   0 |   1 |   0 |   1 |   1 |    0 |    1
   3    | Rockets                |   0 |   0 |   0 |   0 |   0 |   0 |    0 |    0
   4    | Comets                 |   1 |   0 |   0 |   1 |   0 |   2 |   -2 |    0
   ------------------------------------------------------------------------------
   ```
   *(Note: Rockets with GD 0 ranks above Comets with GD -2; Champion status is `IN PROGRESS`).*
5. **Intentionally Invalid Inputs Rejected:**
   - Submitting `home_score = -1`, `home_score = True`, or `away_score = 1.5` raises `ValidationError` and leaves `M003` in `pending` status with zero state drift.
6. **Save & Reload Round-Trip:**
   - Saved to JSON and reloaded; standings and match states match 100%.
7. **Complete Remaining 4 Fixtures:**
   - `M003`: Thunder 3 - 0 Rockets
   - `M004`: Comets 1 - 2 Phoenix
   - `M005`: Comets 2 - 1 Rockets
   - `M006`: Phoenix 0 - 0 Rockets
8. **Final Result & Champion:**
   - Thunder finishes with 7 Points and is crowned **CHAMPION**!

---

## 7. Automated Test Suite

The test suite covers **38 comprehensive unit and integration tests** testing all 16 required rubric scenarios:

### Run All Tests
```bash
python3 -m unittest discover -s tests -v
```

### Test Suite Execution Output
```
test_deterministic_fixture_ids_and_initial_pending_state (test_fixtures.TestFixtureGeneration.test_deterministic_fixture_ids_and_initial_pending_state) ... ok
test_fixture_formula (test_fixtures.TestFixtureGeneration.test_fixture_formula) ... ok
test_reject_more_than_eight_teams (test_fixtures.TestFixtureGeneration.test_reject_more_than_eight_teams) ... ok
test_scenario_3_reject_fewer_than_four_teams (test_fixtures.TestFixtureGeneration.test_scenario_3_reject_fewer_than_four_teams) ... ok
test_scenario_4_four_teams_produce_six_fixtures (test_fixtures.TestFixtureGeneration.test_scenario_4_four_teams_produce_six_fixtures) ... ok
test_scenario_5_six_teams_produce_fifteen_fixtures (test_fixtures.TestFixtureGeneration.test_scenario_5_six_teams_produce_fifteen_fixtures) ... ok
test_scenario_6_no_self_match (test_fixtures.TestFixtureGeneration.test_scenario_6_no_self_match) ... ok
test_scenario_7_no_duplicate_unordered_pair (test_fixtures.TestFixtureGeneration.test_scenario_7_no_duplicate_unordered_pair) ... ok
test_full_controlled_lifecycle (test_integration.TestControlledDemonstrationDataset.test_full_controlled_lifecycle) ... ok
test_reproducible_simulation_with_seed (test_simulation.TestSimulation.test_reproducible_simulation_with_seed) ... ok
test_simulation_does_not_overwrite_played_fixtures (test_simulation.TestSimulation.test_simulation_does_not_overwrite_played_fixtures) ... ok
test_diagnostic_stage_0_validation (test_standings.TestStandingsAndResults.test_diagnostic_stage_0_validation) ... ok
test_scenario_10_reject_duplicate_result (test_standings.TestStandingsAndResults.test_scenario_10_reject_duplicate_result) ... ok
test_scenario_11_correct_points_win_draw_loss (test_standings.TestStandingsAndResults.test_scenario_11_correct_points_win_draw_loss) ... ok
test_scenario_12_tie_break_sorting (test_standings.TestStandingsAndResults.test_scenario_12_tie_break_sorting) ... ok
test_scenario_13_standings_recomputed_from_matches (test_standings.TestStandingsAndResults.test_scenario_13_standings_recomputed_from_matches) ... ok
test_scenario_16_champion_shown_only_when_all_matches_played (test_standings.TestStandingsAndResults.test_scenario_16_champion_shown_only_when_all_matches_played) ... ok
test_scenario_8_reject_bool_goals (test_standings.TestStandingsAndResults.test_scenario_8_reject_bool_goals) ... ok
test_scenario_8_reject_float_goals (test_standings.TestStandingsAndResults.test_scenario_8_reject_float_goals) ... ok
test_scenario_8_reject_negative_goals (test_standings.TestStandingsAndResults.test_scenario_8_reject_negative_goals) ... ok
test_scenario_9_reject_unknown_fixture (test_standings.TestStandingsAndResults.test_scenario_9_reject_unknown_fixture) ... ok
test_reject_boolean_scores_in_storage (test_storage.TestStorage.test_reject_boolean_scores_in_storage) ... ok
test_reject_duplicate_fixture_id_in_file (test_storage.TestStorage.test_reject_duplicate_fixture_id_in_file) ... ok
test_reject_duplicate_team_id_in_file (test_storage.TestStorage.test_reject_duplicate_team_id_in_file) ... ok
test_reject_missing_required_keys (test_storage.TestStorage.test_reject_missing_required_keys) ... ok
test_reject_negative_scores_in_storage (test_storage.TestStorage.test_reject_negative_scores_in_storage) ... ok
test_reject_nonexistent_file (test_storage.TestStorage.test_reject_nonexistent_file) ... ok
test_reject_unsupported_schema_version (test_storage.TestStorage.test_reject_unsupported_schema_version) ... ok
test_scenario_14_reject_bad_reference_without_state_change (test_storage.TestStorage.test_scenario_14_reject_bad_reference_without_state_change) ... ok
test_scenario_15_reload_preserves_ids_and_standings (test_storage.TestStorage.test_scenario_15_reload_preserves_ids_and_standings) ... ok
test_maximum_eight_teams_enforced (test_teams.TestTeamRegistration.test_maximum_eight_teams_enforced) ... ok
test_name_trimming (test_teams.TestTeamRegistration.test_name_trimming) ... ok
test_register_single_team_success (test_teams.TestTeamRegistration.test_register_single_team_success) ... ok
test_reject_non_string_name (test_teams.TestTeamRegistration.test_reject_non_string_name) ... ok
test_scenario_1_reject_duplicate_casefolded_team_name (test_teams.TestTeamRegistration.test_scenario_1_reject_duplicate_casefolded_team_name) ... ok
test_scenario_2_reject_blank_and_too_short_name (test_teams.TestTeamRegistration.test_scenario_2_reject_blank_and_too_short_name) ... ok
test_scenario_2_reject_too_long_name (test_teams.TestTeamRegistration.test_scenario_2_reject_too_long_name) ... ok
test_stable_sequential_team_ids (test_teams.TestTeamRegistration.test_stable_sequential_team_ids) ... ok

----------------------------------------------------------------------
Ran 38 tests in 0.033s

OK
```

### Coverage of 16 Core Requirements
| ID | Requirement Scenario | Covered In |
|----|----------------------|------------|
| 1  | Reject duplicate casefolded team name | `test_teams.py` |
| 2  | Reject blank / too-short / too-long name | `test_teams.py` |
| 3  | Reject fixture generation with < 4 teams | `test_fixtures.py` |
| 4  | 4 teams produce exactly 6 fixtures | `test_fixtures.py` |
| 5  | 6 teams produce exactly 15 fixtures | `test_fixtures.py` |
| 6  | No self-match ($A \ne B$) | `test_fixtures.py` |
| 7  | No duplicate unordered pair ($\{A, B\}$ appears once) | `test_fixtures.py` |
| 8  | Reject negative / float / bool goals | `test_standings.py` |
| 9  | Reject unknown fixture ID | `test_standings.py` |
| 10 | Reject duplicate result on played match | `test_standings.py` |
| 11 | Correct 3 / 1 / 0 points allocation | `test_standings.py` |
| 12 | Multi-key tie-break sorting | `test_standings.py` |
| 13 | Standings dynamically re-computed from matches | `test_standings.py` |
| 14 | JSON bad references rejected without state change | `test_storage.py` |
| 15 | Reload preserves IDs and standings | `test_storage.py` |
| 16 | Champion shown only when all matches played | `test_standings.py` |

---

## 8. Professional Git Workflow & Branch History

TournamentLab was engineered following strict team practices with two distinct engineering roles:

- **Engineer A (Scheduling & Reliable Data Layer):**
  - Branch: `feat/1-team-scheduling`
  - Commits: `66a3de0`, `8910081`
  - Pull Request #1: Reviewed & Approved by Engineer B
- **Engineer B (Scoring, Standings & CLI):**
  - Branch: `feat/2-results-and-rankings`
  - Commits: `0ca3a82`, `5892a12`
  - Pull Request #2: Reviewed & Approved by Engineer A

### Git Graph Log
```text
*   3632e7c (HEAD -> main) Merge pull request #2 from feat/2-results-and-rankings
|\  
| * 5892a12 (feat/2-results-and-rankings) feat(cli): add interactive terminal interface, demo simulation, and integration tests
| * 0ca3a82 feat(scoring): implement result recording, dynamic standings, and tie-breakers
|/  
*   436b6d9 Merge pull request #1 from feat/1-team-scheduling
|\  
| * 8910081 (feat/1-team-scheduling) feat(storage): implement JSON persistence and integrity validation
| * 66a3de0 feat(scheduling): implement team registration and round-robin generator
|/  
* 688088e chore: initial repository setup with .gitignore
```

---

