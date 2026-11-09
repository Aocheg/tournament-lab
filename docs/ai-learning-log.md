# TournamentLab: AI Learning Log

This document records the evidence-based AI learning cycles completed by **Engineer A** and **Engineer B** during the engineering of TournamentLab. Each cycle follows the strict required format:
`Topic I did not know → exact prompt → AI's explanation in my own words → tiny independent experiment → actual results → corrected misconception/decision → related code/test/commit`.

Both engineers document at least one occasion where an AI recommendation was critically tested, found flawed or sub-optimal, and altered or rejected based on experimental verification.

---

## Engineer A: Scheduling & Reliable Data Layer

### Cycle A-1: Strict Integer Checks and the Python Boolean Subclass Quirk
* **Topic I did not know:** How Python handles boolean values in numerical type checks (`isinstance(val, int)`).
* **Exact prompt:** *"How do I validate that a user input or JSON score is strictly a non-negative integer in Python?"*
* **AI's explanation in my own words:** The AI advised using `if isinstance(val, int) and val >= 0:`. It claimed this guarantees the value is a valid non-negative integer.
* **Tiny independent experiment:**
  ```python
  val = True
  print(isinstance(val, int))  # Output: True
  print(val >= 0)              # Output: True
  print(issubclass(bool, int)) # Output: True
  ```
* **Actual results:** In Python, `bool` inherits directly from `int`. Passing `True` into the AI's suggested check evaluated to `True`, which would allow a boolean to be recorded as a score of `1` goal.
* **Corrected misconception / decision (Rejected AI Suggestion):**
  We **rejected** the AI's naive check. We designed a strict validator:
  ```python
  def is_strict_non_negative_int(val: Any) -> bool:
      if isinstance(val, bool):
          return False
      if type(val) is not int:
          return False
      return val >= 0
  ```
* **Related code/test/commit:** `tournament/models.py`, `tests/test_storage.py` (`test_reject_boolean_scores_in_storage`), commit `66a3de0` and `8910081`.

---

### Cycle A-2: Round-Robin Pairing and Duplicate Avoidance
* **Topic I did not know:** Generating unique unordered pairings deterministically without self-matches or reversed duplicates.
* **Exact prompt:** *"How to generate a single round-robin tournament schedule in Python so that every team pair meets once?"*
* **AI's explanation in my own words:** The AI suggested using `itertools.combinations(teams, 2)` or a nested loop with index slicing.
* **Tiny independent experiment:**
  We compared an upper-triangular index loop with combinations:
  ```python
  teams = ["A", "B", "C", "D"]
  pairs = [(teams[i], teams[j]) for i in range(len(teams)) for j in range(i + 1, len(teams))]
  print(len(pairs))  # 6 pairs: (A,B), (A,C), (A,D), (B,C), (B,D), (C,D)
  ```
* **Actual results:** The upper-triangle loop ($0 \le i < j < N$) cleanly generated $\frac{N(N - 1)}{2}$ fixtures with zero self-matches ($i \ne j$) and zero reverse duplicates ($j > i$).
* **Corrected misconception / decision:** Using the explicit double-loop makes the mathematical derivation ($\frac{N(N-1)}{2}$) immediate and readable for learners and reviewers without relying on black-box external utilities.
* **Related code/test/commit:** `tournament/fixtures.py`, `tests/test_fixtures.py`, commit `66a3de0`.

---

### Cycle A-3: Validate-Before-Mutate in JSON Deserialization
* **Topic I did not know:** Preventing in-memory state corruption when loading a JSON file with bad foreign keys.
* **Exact prompt:** *"How can I safely load a JSON file into an active application so that a corrupted record doesn't leave the in-memory state partially updated?"*
* **AI's explanation in my own words:** Deserialize and validate into an isolated temporary dictionary or staging structure. Only replace the active application state after every single team, fixture, and referential constraint has passed.
* **Tiny independent experiment:**
  Simulated loading a file where team 3 had an invalid name length (1 char). Caught exception before touching `self.teams`.
* **Actual results:** The in-memory teams and fixtures retained their exact pre-load state.
* **Corrected misconception / decision:** Validating in-memory before replacement provides ACID-like atomicity to file load operations.
* **Related code/test/commit:** `tournament/storage.py` (`validate_tournament_data`), `tests/test_storage.py` (`test_scenario_14_reject_bad_reference_without_state_change`), commit `8910081`.

---

## Engineer B: Scoring, Standings & CLI

### Cycle B-1: Multi-Key Sorting with Mixed Directionalities
* **Topic I did not know:** How to sort by multiple numeric values descending while sorting string names ascending in Python.
* **Exact prompt:** *"How do I sort a league table in Python by points descending, goal difference descending, goals for descending, and team name alphabetically ascending?"*
* **AI's explanation in my own words:** The AI initially suggested:
  `sorted(table, key=lambda x: (x['points'], x['gd'], x['gf'], x['name']), reverse=True)`
* **Tiny independent experiment:**
  ```python
  rows = [
      {"name": "Zulu", "points": 3, "gd": 1, "gf": 2},
      {"name": "Alpha", "points": 3, "gd": 1, "gf": 2},
  ]
  res = sorted(rows, key=lambda x: (x['points'], x['gd'], x['gf'], x['name']), reverse=True)
  print([r['name'] for r in res])  # Output: ['Zulu', 'Alpha'] -> FAILED! Alphabetical should be Alpha first!
  ```
* **Actual results:** When `reverse=True` is enabled, string comparison is also reversed. "Zulu" ended up ranking before "Alpha"!
* **Corrected misconception / decision (Rejected AI Suggestion):**
  We **rejected** the AI's `reverse=True` approach. Instead, we keep default ascending sort (`reverse=False`) and invert the signs of numeric values:
  ```python
  key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["name"].strip().casefold())
  ```
  Now, numeric values sort descending (e.g. $-10 < -5$), while names sort ascending ('alpha' < 'zulu').
* **Related code/test/commit:** `tournament/standings.py`, `tests/test_standings.py` (`test_scenario_12_tie_break_sorting`), commit `0ca3a82`.

---

### Cycle B-2: Dynamic Derivation vs Mutable Running Table
* **Topic I did not know:** Architectural trade-offs between updating a running scoreboard and computing standings on demand.
* **Exact prompt:** *"Should a sports league manager keep a running standings table in memory and update it after each match, or compute standings from matches every time?"*
* **AI's explanation in my own words:** While maintaining a running table is $O(1)$ per match, in small-to-medium tournaments ($N \le 8$, max 28 matches), computing from matches ($O(M)$) is negligible in CPU time (<1 millisecond) and completely eliminates state drift bugs.
* **Tiny independent experiment:**
  Tested recomputing a full 8-team league (28 matches) 1,000 times in Python: execution time was less than 0.02 seconds.
* **Actual results:** Dynamic computation guaranteed that matches are the single source of truth, making corrupted standings impossible.
* **Corrected misconception / decision:** Never store a duplicate mutable standings table. Compute on demand using pure functions.
* **Related code/test/commit:** `tournament/standings.py` (`compute_standings`), commit `0ca3a82`.

---

### Cycle B-3: Reproducible Pseudo-Random Demo Simulation
* **Topic I did not know:** Generating deterministic demo fixtures without mutating already-played real matches.
* **Exact prompt:** *"How to simulate remaining matches in a tournament with a seeded random generator in Python?"*
* **AI's explanation in my own words:** Use an isolated `random.Random(seed)` instance rather than setting `random.seed()` globally, filter strictly for `status == 'pending'`, and reuse the atomic `record_result` validator.
* **Tiny independent experiment:**
  Simulated 6 matches with seed=42 twice in separate test runs.
* **Actual results:** Generated identical scores across both runs, while existing played fixtures remained untouched.
* **Corrected misconception / decision:** Using an isolated generator protects application state and prevents interfering with any other random operations.
* **Related code/test/commit:** `tournament/simulation.py`, `tests/test_simulation.py`, commit `5892a12`.

---

## Personal Reflections

### Engineer A Reflection
* **Toughest Concept Learned:** The Python type hierarchy nuance where `issubclass(bool, int)` is true. In an esports league where scores are entered, this subtle flaw would allow a boolean `True` to pass as `1` goal. Understanding this taught me why defensive, explicit type checking is necessary in professional engineering.
* **Bug Discovered by Testing:** During persistence tests, saving a tournament with an invalid away team ID (`TM999`) previously passed JSON serialization. Writing `test_scenario_14_reject_bad_reference_without_state_change` forced us to implement referential integrity checks during loading, preventing orphan team references from ever entering memory.

### Engineer B Reflection
* **Toughest Concept Learned:** Multi-key tie-breaking with mixed directions. The intuition to use `reverse=True` broke alphabetical sorting. Discovering that negating numeric keys allows a single ascending sort tuple (`-pts, -gd, -gf, name.casefold()`) was an elegant algorithmic breakthrough.
* **Bug Discovered by Testing:** In `record_result`, submitting a score for an already-played match originally updated the scores. `test_scenario_10_reject_duplicate_result` exposed that match results must be immutable once played, safeguarding the league against duplicate score submissions and fraudulent updates.
