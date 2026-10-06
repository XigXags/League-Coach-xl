# What League Coach can reason about

This is the coaching model for the current Riot Live Client Data feed. It is a decision framework, not a claim that Jev has watched or learned every professional game. Jev ranks the candidate plays generated in `coach.py`; it does not invent new plays or receive video frames.

## Decision order

1. **Immediate safety (seconds):** count living players, recent kills, and active-player health. After a lost fight, clear safely and regroup. After a pick, use the short numbers window for a nearby wave, tower, or guarded jungle entrance. Avoid a blind chase.
2. **Lane and jungle tempo (roughly the next wave):** before 14 minutes, look for a wave to finish, a safe reset, and a jungle path that covers a lane. A CS or level lead can suggest which lane to play through but cannot prove the wave is pushed, that the enemy is visible, or that a gank is safe.
3. **Conversion (next minute):** once a wave reaches a tower, choose between tower damage, a rotation toward the defender, or a grouped entrance into nearby jungle. A neutral objective is one possible conversion. Its spawn timer alone is not a reason to call everyone to its pit.
4. **Longer plan:** after lanes open, use side pressure, mid siege, and resets to create a favorable numbers or vision window. Dragon stacks, Baron, and structures then matter according to the actual position and team composition. The bot currently lacks much of that position data, so it must keep these as conditional plans.
5. **No forced call:** with equal numbers and no recent event, farming the next safe wave or camp and waiting for a clearer opening can be the right answer. The bot responds when asked; it should not pretend an objective fight is urgent merely to fill silence.

## Source and confidence of each fact

| Fact | Current source | Confidence for a call |
| --- | --- | --- |
| Game time, champion identity, role, listed spells, items, deaths, respawn status, event history | Riot Live Client Data API | Observed, subject to feed delay |
| Active player's unspent gold and health | Riot Live Client Data API | Observed for that player only |
| Lane CS and level difference | Derived from observed player data | Clue about strength, not wave priority or location |
| Next Dragon or Baron timing | Published rules plus last event | Scheduled estimate; verify mode and live pit |
| Wave position, ward coverage, jungle camp status, enemy last-seen position, spell cooldown | Not in this adapter | Unknown; never state as observed |
| Opponent jungle path, gank route, side lane safety | Requires vision, wave, and camp observations | Unknown; ask players to verify |

## Why the strategy scope is wider than objectives

Riot's [2026 gameplay preview](https://www.leagueoflegends.com/en-us/news/dev/dev-2026-season-one-gameplay-preview/) explicitly describes a shift toward more viable split pushing and sieging. [Patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) changed minion waves, role quests, and vision to support those routes. The [Live Client Data API](https://developer.riotgames.com/docs/lol) still returns only a subset of the live map. This means objective-centric coaching is both strategically narrow and easy to overstate from the available data.

## Next evidence needed for genuinely deeper calls

- A legal, player-visible adapter for wave state, visible enemy positions with timestamps, jungle camps, and wards. Its records need `observed`, `scheduled`, `inferred`, or `unknown` provenance.
- A curated champion and matchup knowledge base with patch and role context. Data Dragon archetype tags are too coarse to tell whether a lane can move first or whether a composition wins a specific fight.
- Reviewed match scenarios from multiple teams and eras, with questions, game snapshots, coach choices, and outcomes. A sampled set of Worlds writeups exists in `WORLDS_RESEARCH.md`; it is not a claim that all Worlds games were watched.
- Replay evaluation: score whether a suggestion was actionable and accurate, whether it appeared too late, and whether silence would have been better. Win rates alone do not establish causation for a specific live call.
