# TournamentLab: Architecture & Design Decisions

This document details the critical engineering decisions, trade-offs, state invariants, and architectural choices made during the development of TournamentLab.

---

## 1. Core Architectural Decisions

### Decision 1: Stable Identifiers vs Display Names
* **Decision:** Teams are assigned immutable, sequential IDs (`TM001`, `TM002`), and fixtures are assigned immutable IDs (`M001`, `M002`). Fixtures store only team IDs (`home_id`, `away_id`), never display names.
* **Rationale:** In esports and real tournament systems, team renames, sponsorships, or typography edits occur frequently. If fixtures reference display names directly, updating a team name requires traversing and mutating every historical match record, creating risks of broken foreign references and referential corruption. With stable IDs, renaming display labels is completely decoupled from fixture history and referential integrity.

### Decision 2: Single Round-Robin Combinatorics ($N \times (N - 1) / 2$)
* **Decision:** Use a deterministic nested loop over team indices:
  ```python
  for i in range(n):
      for j in range(i + 1, n):
          create_fixture(teams[i]["id"], teams[j]["id"])
  ```
* **Derivation:** Each of the $N$ teams must play every other $N - 1$ team. Because each match involves 2 teams, the total number of unordered pairings is:
  $$\text{Total Fixtures} = \frac{N(N - 1)}{2}$$
  - For $N = 4$: $\frac{4 \times 3}{2} = 6$ fixtures.
  - For $N = 6$: $\frac{6 \times 5}{2} = 15$ fixtures.
  - For $N = 8$: $\frac{8 \times 7}{2} = 28$ fixtures.
* **Invariant:** Since $j > i$ strictly, no team plays itself ($i \ne j$), and reverse duplicates ($B$ vs $A$ when $A$ vs $B$ exists) are mathematically impossible.

### Decision 3: Single Source of Truth vs Mutable Scoreboard
* **Decision:** Never maintain an independently updated league standings dictionary during match recording. Standings are computed dynamically on-demand from the canonical list of completed fixtures.
* **Rationale:** Storing a persistent, mutable standings table alongside match results creates duplicate state. If a bug, crash, or manual edit alters one without the other, the table drifts from historical reality. Recomputing standings dynamically guarantees that the standings are always 100% faithful to the played match records.

### Decision 4: Strict Score Validation and the Python Boolean Quirk
* **Decision:** Reject any score where `isinstance(score, bool)` is `True` or `type(score) is not int` or `score < 0`.
* **Rationale:** In Python, `bool` is a direct subclass of `int` (`issubclass(bool, int) is True`). Consequently, `isinstance(True, int)` evaluates to `True`, and `True >= 0` is `True`. A standard check like `if isinstance(score, int) and score >= 0` would allow a user to submit `True` as a goal score, adding `1` goal silently. Our strict validator:
  ```python
  def is_strict_non_negative_int(val: Any) -> bool:
      if isinstance(val, bool):
          return False
      if type(val) is not int:
          return False
      return val >= 0
  ```
  guarantees that only genuine integer values ($\ge 0$) are accepted.

### Decision 5: Atomic Updates (Validate-Before-Mutate)
* **Decision:** In both memory and file operations, validate all constraints before modifying any state.
* **Rationale:** If a result submission has a valid home score but an invalid away score (e.g. `home=2, away=-1`), modifying the fixture's home score before failing leaves the fixture in a corrupt half-updated state. In TournamentLab, all validations (fixture existence, pending status, home score, away score) must pass before a single property on the fixture is updated.

### Decision 6: Lexicographic Multi-Key Tie-Break
* **Decision:** Sort standings rows using the key:
  ```python
  key=lambda r: (-r["points"], -r["goal_difference"], -r["goals_for"], r["name"].strip().casefold())
  ```
* **Rationale:** Python's `sort()` sorts ascending. Negating numeric values (`-r["points"]`, `-r["goal_difference"]`, `-r["goals_for"]`) causes higher scores to sort first (descending). Leaving the normalized string `r["name"].strip().casefold()` positive ensures alphabetical sorting ascending (A before Z) for complete, reproducible fairness without head-to-head ambiguity.

### Decision 7: JSON Persistence Schema & Referential Integrity
* **Decision:** Enforce `schema_version = 1`. During `load_tournament`, parse into a temporary structure and validate:
  1. Top-level keys (`schema_version`, `teams`, `fixtures`).
  2. Team constraints (ID formatting, length 2–30, unique casefolded names).
  3. Referential integrity: Every fixture's `home_id` and `away_id` must exist in `teams`.
  4. Fixture uniqueness: No duplicate match IDs and no duplicate unordered pairs.
  5. State consistency: Pending fixtures must have `home_score is None` and `away_score is None`. Played fixtures must have strict non-negative integers.
* **Failure Safety:** If any validation fails, a `StorageError` is raised, and the in-memory tournament state is untouched.

---

## 2. Cross-Check Technical Audit

### Q1: If a game ends 0–0, should both teams receive one point?
**Answer:** Yes. A 0–0 result is a draw. Both teams receive 1 point, 0 goals for, 0 goals against, and a goal difference change of 0. Total points awarded across the match is $1 + 1 = 2$, preserving the draw point invariant ($3 \times \text{non-draws} + 2 \times \text{draws}$).

### Q2: If a team loses 3–2, does it still get two goals for?
**Answer:** Yes. In league football and esports, Goals For (GF) tracks every goal scored regardless of match outcome. The losing team receives 0 points, +2 GF, +3 GA, and a GD delta of $-1$.

### Q3: Can two teams occupy the same points and GD, and how do you break the tie?
**Answer:** Yes. If Team A and Team B both have 7 points and $+3$ GD:
1. Compare Goals For (GF) descending: A team with 8 GF ranks above a team with 6 GF.
2. If GF is also tied (e.g. both have 8 GF), compare their casefolded display names alphabetically ascending (e.g. "Alpha" ranks above "Beta").

### Q4: Can a corrupt JSON file create a fixture with a phantom team?
**Answer:** No. TournamentLab's `load_tournament()` inspects every fixture's `home_id` and `away_id` against the validated set of registered team IDs. If an ID is missing, `StorageError` is immediately raised, and memory state is never updated.

### Q5: Why should rendering standings not modify fixtures?
**Answer:** Pure functions promote architectural stability. Displaying or computing standings is a read-only query. Modifying match records or creating duplicate scoreboard state during rendering violates separation of concerns and leads to cumulative mutation bugs.
