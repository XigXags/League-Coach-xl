Bot carry coaching should connect **wave access → a useful purchase → a protected damage window**. A lane lead matters only if the team preserves those links.

Research date: **October 5, 2026**. Scope: modern Summoner’s Rift. I inspected public documents and written interviews; I did not watch match footage, run code, inspect local game data, or edit files.

**Evidence status**

- **Observed:** The published Riot mechanics and interview statements cited below. “Observed” here means inspected in a source, not verified inside a running game.
- **Scheduled:** Riot lists patch **26.20 for October 7**; it is not this report’s live-mechanics baseline. Dates can change. [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- **Inferred:** The decision patterns below are coaching synthesis, not claims that Riot or a professional prescribed every sequence.
- **Unknown:** The stack’s champions, skill level, actual client build, quest progress, and game state. No claim of exhaustive verification of every intervening 2026 hotfix.

There is a relevant product constraint: Riot lists apps that dictate player decisions and products supplying previously unknown game-session information among unapproved use cases. The voice examples below are **human coaching examples**, not evidence that an automated live shotcaller is approved. [Riot developer policy](https://developer.riotgames.com/docs/lol#_developer-api-policy)

**2026 mechanics that change bot decisions**

Riot’s **26.1 launch rules** establish:

| Mechanic | Published rule |
|---|---|
| Assignment | Quest follows assigned role; swap roles in champion select. |
| Bot quest threshold | 1,350 points. |
| Minions | 1.5 points; 3 in bot. |
| Plates / turrets | 20 / 25 points; doubled in bot. |
| Champion / epic takedowns | 15 / 30 points. |
| Passive progress | From 1:05: 1 per 3 seconds; 8 per 5 seconds in bot playspace. |
| Completion | 300 gold; thereafter +2 gold per minion and +50 per champion takedown; boots occupy the quest slot. |
| Early swaps | Bot minion gold/XP reduced 25% outside bot until level 3. |
| Plates | Permanent; outer plate value and turret resistance decline starting at minute 11. |
| Wave cadence | Waves accelerate to 25 seconds at 14 minutes, 20 seconds at 30. |

These are launch specifications, not a fresh client test. [Riot 26.1 notes](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/)

Later relevant changes:

- **26.16:** Support’s outside-bot minion gold/XP penalty became 33% until level 5, and quest-stack consumption was equalized between champion/turret damage and minion CS. Riot also adjusted marksman magic resistance and mid boots while addressing mage bot strength. This undermines importing an early-season roaming or mage-matchup script unchanged. [Riot 26.16 notes](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-16-notes/)
- **26.19:** Support starters shifted health toward regeneration. Top’s free quest Teleport cooldown became 390 seconds; upgraded Unleashed Teleport became 300–210 seconds. Reassess short all-ins versus repeated trades, and obtain top’s actual Teleport availability before committing bot to an extended siege. These tactical consequences are inference. [Riot 26.19 notes](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/)

Quest consequences are conditional: protect lane access before completion; consider the completion purchase when choosing a reset; use the extra inventory capacity for components before imagining a seven-item endgame. A mage assigned bot also requires a bot-role plan—“bot carry” does not imply sustained physical damage.

**What professional evidence supports**

- In a 2026 interview, **Rekkles** described his best supports as those who created space for him. The useful principle is that support positioning must enable the carry’s farming or damage, not merely place two champions nearby. [Direct interview](https://esportsinsider.com/2026/01/los-ratones-rekkles-lec-versus-champion-pool-support-interview)
- **Ruler’s 2021 interview** explicitly connected Ezreal’s lane strength to Karma. It supports evaluating the complete duo; it does not establish a 2026 matchup tier list. [Direct interview](https://www.invenglobal.com/articles/14257/gen-ruler-without-karma-ezreals-that-much-weaker-in-lane-so-i-think-that-hes-exploitable)
- **Doublelift** described a strategic alternative in which his duo accepted a losing lane while solo lanes received pressure. Weakside is a team resource allocation, not permission to abandon the ADC without a wave plan. [Direct interview](https://www.invenglobal.com/articles/9289/worlds-2019-lcs-insights-tl-doublelift-talks-g2-esports-his-style-with-corejj-and-sona-bot-lane)
- **Ruler and coach Edgar** discussed shared summoner tracking and the importance of communicating jungle movement. Allocate information duties rather than requiring the ADC to track everything while fighting. [Direct interview](https://www.invenglobal.com/articles/3519/ssg-coach-edgar-instead-of-upgrading-your-core-items-buying-control-wards-makes-it-easier-to-win-the-game)
- Team Liquid’s organizational analysis describes mid/jungle windows creating bot pressure, with top absorbing the corresponding cost. This is a written team analysis, not my independent match review or a coach-authored prescription. [Team Liquid analysis](https://teamliquid.com/articles/tl-vs-fly-outperforming-a-superteam)

**API evidence boundary**

Use these labels in the patterns:

- **P — Player snapshot:** champions, items, levels, CS/KDA, death status and respawn timers. Summoner identities are not cooldowns.
- **A — Active player:** local player’s current gold, health/resource and combat stats. One local client does not provide five active-player perspectives.
- **E — Events/time:** game clock and recorded kills, structure destruction and epic-monster kills.

The documented data lacks a tactical map: no usable live coordinates, wave composition, ward locations, enemy visibility, spell readiness, recall channel, objective health, or explicit role-quest progress/completion. `position` is a role label, not coordinates. Ward score does not establish safe terrain. Actual 2026 quest-slot representation remains untested. [API documentation](https://developer.riotgames.com/docs/lol#live-client-data-api), [sample payload](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [sample events](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json)

Consequently, every pattern requires player reports or visual confirmation beyond API evidence. CS changes cannot prove which wave was collected; a kill event cannot prove the winning fight was repeatable.

**Decision patterns — inferred, conditional coaching**

**1. Establish the duo’s trading plan**

- **Trigger:** Loading into lane, or either duo returns with changed items.
- **Information:** Both supports’ threat ranges, engage versus disengage, sustain, waveclear, level timing, jungle approach.
- **Sequence:** Identify the spell that makes trading unsafe → agree whether to poke, shorten trades or extend them → synchronize both players’ movement → stop when support cannot follow.
- **Counterexample:** A nominal range advantage loses value when walking up exposes the ADC to an unblocked engage.
- **API:** P verifies composition/items; not spacing or cooldown windows.

**2. Contest the first level advantage**

- **Trigger:** A wave is approaching a level breakpoint.
- **Information:** Actual XP attendance, minions about to die, both players’ health, learned abilities, enemy threat.
- **Sequence:** Decide whether the breakpoint is contestable → coordinate attacks on the wave → advance together just before leveling, or retreat before the enemy levels → avoid sacrificing health solely to match push.
- **Counterexample:** Missed XP or unusual XP mechanics invalidate memorized minion counts. A low-health level advantage may still lose.
- **API:** P verifies attained levels; not exact XP or next-minion timing.

**3. Build a crash for a purchase**

- **Trigger:** A meaningful buy is approaching and the duo has wave control.
- **Information:** Gold shortfall, wave position, incoming reinforcement, enemy clear speed, jungle locations, support resources.
- **Sequence:** Preserve enough allied minions to build pressure → accelerate the chosen wave → confirm it reaches turret → recall promptly → return toward the expected receiving wave.
- **Counterexample:** An incomplete shove gives the opponent a freeze; staying to finish it can be worse than accepting a small loss.
- **API:** A/P support purchase checks; not crash or bounce confirmation.

A historical Dignitas guide also makes recall quality conditional on buying power, safe shove, enemy purchases and objective timing. Its old wave/item specifics should not be imported verbatim. [Recall guide](https://dignitas.gg/articles/going-home-how-to-time-recalls-to-create-an-advantage)

**4. Choose denial or immediate movement while ahead**

- **Trigger:** Enemy bot recalls, dies or becomes unable to contest.
- **Information:** Wave direction, enemy return time, allied jungle plan, next purchase, quest status.
- **Sequence:** If a safe hold denies meaningful farm and no teammate needs movement, trim and hold → otherwise crash → spend the window on a purchase, tower damage or supported rotation.
- **Counterexample:** Freezing while jungle commits to a necessary river fight can surrender the team’s numbers advantage.
- **API:** P/E establish deaths and gains; not denial or movement priority.

**5. Escape a freeze or threatened dive while behind**

- **Trigger:** Enemy holds the wave beyond safe reach, or stacks waves toward your turret.
- **Information:** Enemy reinforcements, allied jungle ETA, mid movement, escape route, health and defensive spells.
- **Sequence:** Ask for help before the wave becomes inaccessible → use joint pressure to crash a freeze, or thin a dive wave safely → if help cannot arrive, abandon the lethal position early → catch the next defensible wave.
- **Counterexample:** Calling jungle into an unsupported fight against stronger mid/jungle compounds the loss.
- **API:** P/A show resources and deaths; not dive geometry.

**6. Release support with a return condition**

- **Trigger:** Support wants to ward, roam or reset separately.
- **Information:** ADC’s safe farming boundary, wave direction, enemy freeze/dive tools, support route and return time.
- **Sequence:** Fix the wave together → state what ADC can concede → name support’s return trigger → ADC avoids trades requiring absent peel → cancel the roam if opponents can deny the whole receiving wave.
- **Counterexample:** “We crashed” is insufficient when opponents can rapidly push and dive before support returns.
- **API:** P shows resource context; not separation, safety or return timing.

**7. Coordinate jungle and mid pressure**

- **Trigger:** Jungler paths bot or mid earns a movement window.
- **Information:** Arrival time, enemy jungle uncertainty, opposing mid’s response, wave size, target escapes.
- **Sequence:** Specify “hold,” “build” or “crash” → align the wave with arrival → let mid’s movement restrict enemy options → choose gank, dive or protected reset → assign who catches the aftermath.
- **Counterexample:** Diving because four allies are nearby still fails if the wave dies before entry or enemy Teleport changes numbers.
- **API:** P/E show outcomes; not arrivals, aggro or coverage.

**8. Take a plate without losing the next turn**

- **Trigger:** A crash creates tower access.
- **Information:** Remaining damage to the next payout, returning enemies, missing threats, turret resistance effects, purchase and travel deadline.
- **Sequence:** Set a departure condition before hitting → take the reachable payout → leave when the threat or reset deadline arrives → use jungle/support cover only while their opportunity cost is justified.
- **Counterexample:** One extra plate can cost the next wave, a death and the purchase window.
- **API:** E confirms destruction; not current plate health or safety.

Permanent plates remove the old “take it before 14:00 or lose it forever” rule; they do not make staying safe.

**9. Swap lanes only with a receiving plan**

- **Trigger:** Bot tower falls, the matchup becomes untenable, or another lane offers a concrete conversion.
- **Information:** Both carries’ quest status, destination waves, who receives bot, enemy matching options, top’s matchup and Teleport.
- **Sequence:** Compare continued bot access against the proposed gain → agree destination and displaced farmer → synchronize resets → establish vision before occupying the new lane.
- **Counterexample:** An automatic swap delays an unfinished quest and strands a teammate in an unplayable long lane.
- **API:** P/E verify levels/towers; not quest state or swap execution.

**10. Assign mid-game farm without starving teammates**

- **Trigger:** Laning ends or teams begin grouping.
- **Information:** Each player’s next purchase, side-lane survival, Teleport, wave locations, upcoming required attendance.
- **Sequence:** Usually place vulnerable sustained damage in the shorter central lane → send a suitable solo laner to each side → specify the next two waves’ owners → rotate only after confirming coverage → take camps only with jungle agreement.
- **Counterexample:** A mage mid with irreplaceable central waveclear may need mid while a mobile bot carry safely catches a side wave.
- **API:** P/A support economy checks; not wave ownership or route safety.

**11. Reset backward from a required arrival**

- **Trigger:** The team intends to establish control for an upcoming fight or siege.
- **Information:** Clear time, recall and shopping time, travel, warding time, ally purchases and enemy pressure.
- **Sequence:** Choose the required arrival time → work backward to the last collectible wave → communicate the reset → buy together where practical → travel behind the players establishing vision.
- **Counterexample:** Recalling “30 seconds before dragon” fails if travel plus safe entry takes longer; recalling while a critical structure falls may also be wrong.
- **API:** A/P/E support timing and purchases; not route or recall readiness.

**12. Enter dark terrain through protection**

- **Trigger:** A wave ends and the next useful position lies beyond vision.
- **Information:** Last confirmed sightings and their age, missing engage threats, allies able to check, safe exit.
- **Sequence:** Stop at the known boundary → have support/jungle establish the next safe space → follow within protection range → refresh information before advancing again.
- **Counterexample:** All five enemies shown elsewhere can justify immediate movement; a stale sighting cannot.
- **API:** No direct verification of vision, sightings or entry safety.

**13. Establish a teamfight damage position**

- **Trigger:** Contact is likely within seconds.
- **Information:** Two most dangerous engage tools, flank access, peel owner, escape spell, reachable targets, carry damage profile.
- **Sequence:** Choose a protected side of the fight → remain within peel reach → attack the safest valuable reachable target → reposition between attacks → move forward only after a relevant threat is spent or controlled.
- **Counterexample:** Standing maximally far back may produce no damage and lose a winnable fight. A clean backline opening can supersede front-to-back play.
- **API:** P/A show build/resources; not threat ranges or spell expenditure.

For a burst mage, preserve the key spell for its intended target or choke; for sustained damage, preserve uninterrupted attack time. Do not assign both the same fight script.

**14. Separate objective damage from secure and zoning**

- **Trigger:** Team considers starting or finishing dragon/Baron.
- **Information:** Damage rate, objective health, jungle secure availability, enemy entry routes, flank/Teleport, health cost and escape path.
- **Sequence:** Name damage dealers, zoners and secure caller → position ADC with an exit → preserve required combat resources → agree “finish” versus “turn” before enemy entry → coordinate any burst with jungle.
- **Counterexample:** Continuing damage while the team turns creates two losing groups; turning unnecessarily can also abandon a guaranteed finish.
- **API:** E verifies completed objectives; not health, DPS or Smite readiness.

A bot mage or utility marksman may require another role to provide sustained objective damage. Test that assumption before choosing a rush.

**15. Convert a won fight, or trade when contesting is impossible**

- **Trigger:** Enemy deaths create a window, or the enemy controls an objective your team cannot safely approach.
- **Information:** Respawns, surviving resources, nearest usable wave, travel, structure health and consequence of concession.
- **Sequence:** After a win, choose the best reachable conversion and a departure deadline → send only necessary players → reset before opponents re-establish control. When behind, secure defensible farm or a safe opposite-side gain and prepare the next contest.
- **Counterexample:** “Always trade” fails when conceding allows an immediate game-ending push; chasing after a win can erase the conversion.
- **API:** P/E establish deaths/time/outcomes; not feasibility or lethal pressure.

**Communication with all four other roles**

| Partner | Bot provides | Bot needs |
|---|---|---|
| Support | Intended wave action, follow-up range, purchase timing | Space, threat tracking, explicit roam return condition, named peel |
| Jungle | Wave arrival and whether bot can leave | Path/cover ETA, enemy-jungle confidence, objective finish/turn decision |
| Mid | Time bot can move and central farm needs | Missing calls, earliest movement, agreed side-lane exchange |
| Top | Expected fight duration and damage position | Teleport readiness, target/arrival plan, whether top will flank or protect |

Use **fact → uncertainty → action → expiry**: “Their jungle showed top; that sighting is old now; finish this crash, then leave.” Do not convert “last seen top” into “cannot be bot.”

**Six approximately ten-second human voice calls**

1. “They level first on this wave. Back together now; give those minions, then collect when it reaches us.”
2. “Jungle, cover this crash. Support, help clear. Bot has the purchase—recall immediately, skip the extra tower hits.”
3. “Support can move after the crash. Bot, no trades alone. Return before they stack the next wave into our tower.”
4. “Bot takes mid after this reset. Mid catches bottom; top keeps top. Jungle, cover the river entrance before bot steps up.”
5. “Their engage is still available. Bot, hold beside support; hit the front target. Advance only when that engage is spent.”
6. “Bot stays on dragon; top blocks the entrance. Jungle calls finish or turn. Support saves peel for the carry.”

**Six failure cases and misleading heuristics**

1. **“Winning ADC matchup means winning lane.”** Support range, cooldowns, jungle cover and actual purchases can reverse the expected trade.
2. **“Always shove before recalling.”** A lethal or incomplete shove can lose more than an immediate imperfect reset.
3. **“Always freeze when ahead.”** Denial can cost a necessary rotation, purchase or tower conversion.
4. **“Support roaming gives ADC free solo XP.”** A freeze or dive can deny both XP and quest access.
5. **“Plates expire at 14, then ADC automatically goes mid.”** The plate premise is obsolete; the rotation still requires farm coverage and quest consideration.
6. **“Hit the closest target / never hit tanks.”** Both fail as absolutes. Choose damage that is valuable and safely deliverable given current threats.

**Source list**

- [Riot 26.1: quests, plates and waves](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/)
- [Riot 26.16: roaming and bot systems](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-16-notes/)
- [Riot 26.19: support items and Teleport](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/)
- [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- [Riot API documentation and policy](https://developer.riotgames.com/docs/lol), [payload](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [events](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json)
- [Rekkles interview, 2026](https://esportsinsider.com/2026/01/los-ratones-rekkles-lec-versus-champion-pool-support-interview)
- [Ruler matchup interview, 2021](https://www.invenglobal.com/articles/14257/gen-ruler-without-karma-ezreals-that-much-weaker-in-lane-so-i-think-that-hes-exploitable)
- [Doublelift strategic-style interview, 2019](https://www.invenglobal.com/articles/9289/worlds-2019-lcs-insights-tl-doublelift-talks-g2-esports-his-style-with-corejj-and-sona-bot-lane)
- [Ruler/CoreJJ/Edgar interview, 2017](https://www.invenglobal.com/articles/3519/ssg-coach-edgar-instead-of-upgrading-your-core-items-buying-control-wards-makes-it-easier-to-win-the-game)
- [Team Liquid written analysis](https://teamliquid.com/articles/tl-vs-fly-outperforming-a-superteam)
- [Dignitas recall guide, 2020](https://dignitas.gg/articles/going-home-how-to-time-recalls-to-create-an-advantage)

**Research gaps**

- Full 26.1–26.19 hotfix reconciliation, particularly exact quest boundaries and turret details.
- Actual 2026 Live Client payloads, quest-slot serialization and field freshness.
- Champion-specific matchup breakpoints, objective damage rates and build-dependent fight plans.
- Timestamped contemporary professional VOD review; none was inspected here.
- Riot’s determination for the proposed automated Discord coaching behavior; API availability alone does not establish approval.