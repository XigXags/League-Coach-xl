**Jungle research memo — five-stack Discord coach, 5 October 2026**

The jungler should coordinate **where the team can act before the enemy can respond**. Camp efficiency supplies the resources; wave states, movement windows, and information determine where those resources can be spent.

This is public-document and interview research. I did not inspect a match, run code, access a local client, or edit files.

**Evidence status and 2026 mechanics**

- **Observed in published sources:** the rules and interview statements below. “Observed” does not mean tested in a live game.
- **Scheduled:** Riot lists 26.20 for October 7; its proposed changes should not drive October 5 calls.
- **Inferred:** 26.19 is the expected live patch on the research date, based on Riot’s September 23 release schedule and published notes. The user’s actual client version is unknown. [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- **Unknown:** champion pool, skill level, actual match state, deployed API behavior, and any unexamined hotfixes.

For conventional Summoner’s Rift, these are **verified 26.1 changes**, not a claim that every subsequent patch has been exhaustively audited:

| Mechanic | Published change |
|---|---|
| Opening camps | Buffs, wolves, raptors: **0:55**; gromp, krugs: **1:07** |
| First Scuttle | **2:55** |
| Baron | **20:00** |
| Removed | Atakhan, Blood Roses, Feats of Strength |
| Jungle progression | First evolution requirement: **15**; completion: **35** pet counters |
| Smite monster damage | **600 / 1,000 / 1,400**, by evolution |
| Completed quest | Jungle/river movement speed **4%, 8% out of combat**; **+10 gold/+10 XP** per large monster |
| Clearing | Monster damage amplification **10%**; junglers take **50% damage from non-epic monsters** |
| Buff sharing | Global late-game buffs removed; second pickup remains after elemental transformation |
| Objectives | Durability increased; taking one exposes the team for longer |
| Mode distinction | Swiftplay’s **120-second small camps/270-second buffs** are separate rules |

Source: [Riot 26.1 notes](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/).

Later verified changes materially affect coaching:

- **26.3:** river pixel-brush Faelight coverage stops before the Scuttle pad and epic-pit entrance. Yellow-trinket cooldown changed to 210–90 seconds by level. A pixel ward therefore does not establish pit-entry control. [Riot 26.3](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-3-notes/)
- **26.16:** pet damage scaling increased to 16% AP, 25% bonus armor, 25% bonus MR, and 4% bonus health; the 10% bonus-AD ratio remained. Reassess clear estimates after purchases rather than assuming only offensive AD accelerates camps. [Riot 26.16](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-16-notes/)
- **26.19:** top’s free quest Teleport cooldown became 390 seconds; upgraded top-lane Unleashed Teleport became 300–210 seconds. Elise, Poppy, Vi, and other junglers also received changes. Old clear benchmarks and Teleport estimates can be wrong. [Riot 26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/)

For ordinary camp cycles, the longstanding **2:15 small-camp/5:00 buff** intervals have secondary corroboration, but I did not obtain a current official consolidated timer specification. Treat them as a provisional baseline requiring in-client confirmation, especially camp-completion edge cases. [Community wiki’s jungling reference](https://leagueoflegends.fandom.com/wiki/Jungling)

**Enduring principles supported by professional interviews**

Jankos explains that unsuccessful repeated ganks would have left him far behind a farming opponent; he also describes punishing excessive mid grouping through side-lane pressure. These support evaluating both opportunity cost and conversion, rather than counting ganks. They are historical strategic evidence, not 2026 balance evidence. [Direct Jankos interview](https://www.esportsheaven.com/features/g2-jankos-on-lack-of-na-side-laning-just-because-people-in-solo-queue-arent-playing-well-at-side-laning-doesnt-mean-pro-players-have-to-play-like-shit-as-well)

Bwipo describes Broxah covering the lane the opponent wanted to attack, and criticizes a jungle advantage that failed to become river control. He also explains that switching the team’s favored side changes responsibilities for mid and the opposite side lane. That supports coordinated coverage and team-wide adjustment. [Direct Bwipo interview, February 2019](https://www.invenglobal.com/articles/7688/interview-bwipo-talks-fnatics-game-against-team-vitality-the-pressure-of-conceding-lanes-fnatics-identity-and-more)

The decision patterns below are **my coaching synthesis**, not quotations or claims of professional consensus.

**What the local API supports**

Use these capability codes throughout:

- **S:** player champions, levels, items, scores, death/respawn state, summoner identities.
- **A:** active player’s health, resources, gold, ability ranks.
- **T:** game clock, map/mode.
- **E:** emitted kill/objective/structure events.

Undocumented inputs are **U**: coordinates, waves, camp state, wards/vision, cooldowns/Smite charges, pet progress, monster health. `position` means role, not coordinates. Active-player detail concerns the local player. API coverage follows Riot’s documentation; runtime behavior remains untested. [Live Client Data API](https://developer.riotgames.com/docs/lol#game-client-api)

Riot’s event examples include dragon, Herald, Baron, champion, turret, and inhibitor kills. Events establish completed outcomes, not current pit safety. Future timers calculated from events remain derived estimates; the sample does not establish modern Voidgrub coverage. [Riot event schema examples](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json)

**Decision patterns**

For each pattern, “API: supports …; missing U” means the named fields can corroborate background state, but the tactical trigger still requires player reports or visual observation.

1. **Choose a first-clear destination, then a route**

   **Trigger:** loading into a game or recovering from a disrupted opening.  
   **Information required:** champion clear constraints, likely first wave crashes, allied setup spells, enemy invade strength, and which lane needs protection.  
   **Action sequence:** identify the useful arrival lane; choose a safe starting quadrant; state the planned endpoint and alternative; reassess after each camp. A candidate red-start full clear is red–krugs–raptors–wolves–blue–gromp; reverse the destination when the other side offers greater value. Treat this as a route candidate, not a universal optimum.  
   **Counterexample:** a guaranteed imminent dive requires early coverage; finishing six camps would sacrifice several waves and a teammate.  
   **API:** supports S/A/T; missing U.

2. **Cycle camps without allowing the route to dictate every decision**

   **Trigger:** finishing a quadrant or returning from a purchase.  
   **Information required:** actual camp completion times, surviving camps, travel time, purchase threshold, next useful lane window.  
   **Action sequence:** record completed camps; estimate their return windows; clear a connected sequence toward the next play; use downtime for a short gank, vision, or recall. Compare one extra camp against arriving before a wave crashes.  
   **Counterexample:** crossing the map for one freshly spawned camp loses both travel time and the chance to defend the nearby lane. Delaying a camp is justified when a temporary opportunity is more valuable.  
   **API:** supports A/T; missing U.

3. **Gank according to the wave’s future position**

   **Trigger:** an enemy must advance to farm, has spent an escape, or an allied freeze creates a long retreat path.  
   **Information required:** wave direction and size, health/mana, crowd control, escape spells, vision, reinforcement timing.  
   **Action sequence:** obtain the laner’s commitment; approach outside known vision; let the enemy commit; sequence crowd control; reassess after a summoner is forced. Afterward, explicitly choose crash, freeze, or leave.  
   **Counterexample:** the enemy is extended behind a large minion wave while your laner is low and about to lose a level advantage. The apparent positional opening is a losing fight.  
   **API:** supports S/A; missing U.

4. **Repair a lane without requiring a kill**

   **Trigger:** an ally cannot break an enemy freeze, cannot safely crash before recalling, or risks losing a large returning wave.  
   **Information required:** exact wave balance, enemy threat, allied recall timing, and whether assistance exposes the other quadrant.  
   **Action sequence:** announce “wave help”; threaten the defender; help complete the crash or escort the laner; leave once the reset is secured. Agree on last hits instead of automatically taxing the lane.  
   **Counterexample:** touching a safely maintained allied freeze removes the denial and pushes the ally into danger.  
   **API:** supports S/A; missing U.

5. **Countergank the opponent’s best window**

   **Trigger:** a vulnerable ally must push, a stacked wave approaches their tower, or enemy behavior changes after a jungle sighting.  
   **Information required:** sighting age, likely approach routes, allied survival time, enemy engage cooldowns, and matchup strength.  
   **Action sequence:** shorten the clear toward the threatened lane; remain hidden nearby; warn the laner against premature commitment; counter after the enemy spends mobility, or reveal early to prevent the dive. Set a departure condition.  
   **Counterexample:** waiting indefinitely for an inferred gank surrenders camps while the opponent resets. If the ally cannot survive first contact, baiting is inappropriate.  
   **API:** supports S/A/T; missing U.

6. **Track the enemy as several possibilities**

   **Trigger:** any fresh sighting, objective kill, revealed camp, or unexpected lane appearance.  
   **Information required:** timestamp, location, movement direction, visible buffs, level, CS changes, and plausible travel routes.  
   **Action sequence:** record the observation; generate two or more plausible continuations; identify which lanes each threatens; seek another observation at a route junction. Downgrade confidence as time passes. Treat “not seen crossing” as useful only if coverage was continuous.  
   **Counterexample:** one CS total rarely identifies an exact route; lane farm, partial clears, steals, and unusual pathing can fit the same evidence. A late laner is not proof of a leash.  
   **API:** supports S/T/E; missing U.

7. **Invade with a return route and a deadline**

   **Trigger:** enemy jungler is committed elsewhere, or your nearby teammates can genuinely move first.  
   **Information required:** camp availability, both neighboring lanes’ movement times, support location, matchup strength, exits, and enemy global abilities.  
   **Action sequence:** obtain explicit movement commitments; enter together or under reliable coverage; ward the collapse route; take the nearest valuable resource; leave when the movement advantage expires.  
   **Counterexample:** a pushed allied lane has no mana and needs to recall. Its wave position creates apparent priority, but no usable reinforcement. Your duel advantage does not survive a three-player collapse.  
   **API:** supports S/A; missing U.

8. **Cross-map immediately when arriving would be too late**

   **Trigger:** the opponent commits multiple players to an objective or dive you cannot reach in time.  
   **Information required:** commitment certainty, opposite-side waves and defenders, objective importance, travel time, and escape routes.  
   **Action sequence:** tell the endangered side what to concede; select a named return—tower damage, a safe camp sequence, Herald, or a different objective; execute promptly; exit before the enemy rotates.  
   **Counterexample:** conceding a game-ending push or decisive Soul/Elder for a minor camp is not an acceptable exchange. Seeing one enemy near dragon does not prove the entire team committed.  
   **API:** supports S/T/E; missing U.

9. **Reset backward from the required arrival**

   **Trigger:** a purchase breakpoint, depleted resources, or a coming contest.  
   **Information required:** recall and shopping time, travel time, wave preparation, ward refresh needs, Smite readiness, and who must remain on the map.  
   **Action sequence:** determine when the team must control the entrance; subtract preparation and travel; recall before that deadline; finish only camps that fit. Coordinate jungle/support purchases with lane crashes.  
   **Counterexample:** “one more camp” causes a late river entry through darkness. Conversely, recalling while a teammate faces an immediate dive abandons the more urgent task.  
   **API:** supports A/T/S; missing U.

10. **Establish an entrance before starting an objective**

   **Trigger:** the team intends to contest or take a specific epic monster.  
   **Information required:** adjacent wave states, enemy entry routes, available sweepers/wards, flank threats, and time until opponents can move.  
   **Action sequence:** push the relevant waves; jungle and support enter together; scout from a safe boundary; secure one approach and a retreat path; maintain the next layer with mid/top pressure. Start only after assigning damage, zoning, and turn responsibilities.  
   **Counterexample:** clearing the pit ward while both river entrances remain dark creates concealment without control. A swept corridor can be re-entered immediately.  
   **API:** supports S/T; missing U.

11. **Choose finish, turn, or disengage before Smite range**

   **Trigger:** enemies approach while an epic monster is being damaged.  
   **Information required:** current monster health, actual burst damage, both junglers’ access, own Smite value/readiness, crowd control, and escape tools.  
   **Action sequence:** assign one caller; keep the jungler healthy and in range; assign a teammate to exclude the enemy jungler; call “finish,” “turn,” or “out.” For a finish, synchronize a named burst spell with Smite. For a turn, stop damage early enough to avoid gifting a low-health objective.  
   **Counterexample:** the enemy is excluded, but the whole team abandons a secure finish to chase. Alternatively, everybody keeps hitting while the jungler is displaced.  
   **API:** supports S/E; missing U.

12. **Convert an advantage into repeatable access**

   **Trigger:** a successful gank, enemy jungle death, or strong purchase advantage.  
   **Information required:** return timers, nearby waves, accessible structures, remaining health, and the next enemy resource window.  
   **Action sequence:** repair the wave; choose one immediate conversion; spend gold; return with allies to defend or deny the next resource cycle. Establish vision that makes the next action easier.  
   **Counterexample:** chasing a second kill with unspent gold loses the original lead and gives away a shutdown. A distant objective can be inferior to the tower already exposed beside you.  
   **API:** supports S/A/E; missing U.

13. **When behind, secure one usable portion of the map**

   **Trigger:** repeated camp losses, losing neighboring lanes, or inability to enter either river safely.  
   **Information required:** enemy commitments, safe waves/camps, allied defensive tools, a reachable power spike, and whether an objective is optional or decisive.  
   **Action sequence:** group information-gathering with support; scout before entering; farm the defensible quadrant; request help for one specific camp cycle or level breakpoint; trade optional contests; seek isolated attackers instead of equal-number fights.  
   **Counterexample:** defending every camp causes repeated deaths. But surrendering all camps while a safe regroup could protect one quadrant makes recovery unnecessarily impossible.  
   **API:** supports S/A/E; missing U.

14. **Coordinate side pressure and the jungler’s fight job**

   **Trigger:** outer towers fall, carries rotate, or an approaching late-game contest demands allocation.  
   **Information required:** side-wave arrival times, Teleports, enemy engage range, who can survive alone, objective damage, and the team’s strongest damage source.  
   **Action sequence:** assign side-wave collection; move jungle through the quadrant connecting those lanes to the next contest; protect the carry’s approach. Before contact, choose the jungler’s job: primary engage, follow-up, peel, flank, or objective secure. After winning, select end, structure, or epic monster using wave position and enemy returns.  
   **Counterexample:** the jungler dives the backline while their only sustained damage dealer is killed, or farms a distant quadrant while the team cannot safely approach Baron.  
   **API:** supports S/T/E; missing U.

**Interactions with all four other roles**

These are proposed communication responsibilities:

| Role | Information the jungler needs | Joint decision |
|---|---|---|
| **Top** | “Wave crashes after this wave”; freeze status; dive risk; Teleport readiness; enemy top’s escape | Cover the crash, break the freeze, arrange a dive, or explicitly concede weak-side farm. Later, agree whether top pressures side or joins before starting Baron. |
| **Mid** | Earliest movement time; mana; wave-clear cooldown; missing opponent; safe river side | Decide which river entrance is usable. Mid may help by holding the opponent in lane rather than physically joining the monster. |
| **ADC** | Crash/reset plan; combat summoners; item purchase; whether support can leave | Schedule bot ganks and dragon access around the wave. Later, protect the ADC’s route into range and distinguish objective damage from chasing. |
| **Support** | Roam window; ward/sweeper availability; enemy support position; engage tools | Enter fog together, establish entrances, and name who zones while the jungler secures. Support movement must account for the ADC’s next wave. |

Define priority as **“can arrive by a stated time and still contribute”**, not simply “has pushed the wave.” Useful laner reports are “I can move in eight seconds after these casters” and “I cannot leave this crash.”

For fog information, preserve four separate statements:

- **Observed:** “Enemy jungle crossed the bot river ward at 6:12.”
- **Scheduled/derived:** “Our recorded camp timer reaches zero at 6:35.”
- **Inferred:** “Their next likely options are bot gank or recall.”
- **Unknown:** “Their support position and Smite readiness are unconfirmed.”

The coach should never silently promote the third statement into the first.

**Six concrete voice calls, each roughly ten seconds**

These assume the stated facts have been confirmed.

1. “Top, your wave’s coming back. I finish wolves and cover your crash. Save stun; leave the freeze until I arrive.”
2. “Enemy jungle showed bot five seconds ago. Mid, push then move. We take their raptors together and leave when mid disappears.”
3. “Bot, back off the stacked wave; their jungler can dive. I’m behind tower. Save exhaust until they commit.”
4. “Dragon in seventy. Crash mid, then jungle and support reset. Skip krugs; enter together through our bot jungle.”
5. “Stop dragon damage. Their jungler is in river. Support zone the entrance; turn together on my call.”
6. “We can’t reach their dragon. Top, take the tower; I take their top camps. Mid hold safely, then everyone reset.”

**Six failure cases and misleading heuristics**

1. **“Always full clear.”** A farm plan becomes harmful when a preventable dive or high-certainty short gank has a closing window. Evaluate arrival time and expected loss.
2. **“Never gank a losing lane.”** A losing lane may need a safe crash to remain playable. Distinguish rescue of its wave from committing to a losing duel.
3. **“Pushed lanes mean we can invade.”** Health, mana, recalls, movement distance, and willingness determine whether priority is usable.
4. **“Enemy jungle showed top, so dragon is free.”** The sighting may be old; mid/support can still collapse; Teleport or a fast return can invalidate the window.
5. **“We warded river, so this is safe.”** Coverage has edges and expiry times. Faelight coverage, pit visibility, and control of enemy entrances are different facts.
6. **“An objective steal proves a jungle mistake.”** Access denial, synchronized damage, displacement, and conflicting turn calls can decide the outcome before Smite. Review the setup and final seconds separately.

**Source list**

- [Riot 2026 patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends) — scheduled versus live dates.
- [Riot patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) — opening times, jungle progression, Smite, objectives, mode differences.
- [Riot patch 26.3](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-3-notes/) — Faelight and trinket corrections.
- [Riot patch 26.16](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-16-notes/) — pet scaling.
- [Riot patch 26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/) — current patch reference and top Teleport changes.
- [Riot Live Client Data documentation](https://developer.riotgames.com/docs/lol#game-client-api) and [event examples](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json) — documented capabilities.
- [Jankos direct interview](https://www.esportsheaven.com/features/g2-jankos-on-lack-of-na-side-laning-just-because-people-in-solo-queue-arent-playing-well-at-side-laning-doesnt-mean-pro-players-have-to-play-like-shit-as-well) — farming opportunity cost and side pressure.
- [Bwipo direct interview](https://www.invenglobal.com/articles/7688/interview-bwipo-talks-fnatics-game-against-team-vitality-the-pressure-of-conceding-lanes-fnatics-identity-and-more) — countergank coverage, river control, team coordination.
- [Community jungling reference](https://leagueoflegends.fandom.com/wiki/Jungling) — secondary camp-cycle corroboration only.

**Research gaps**

This is not an exhaustive 26.1–26.19 mechanics diff. Exact current camp-reset edge cases, catch-up XP, lane-farm penalties, pet-counter accrual, full epic spawn/despawn schedules, and champion-specific secure combinations need further verification before hardcoding advice.

No current professional VOD was inspected; the professional evidence is historical interview testimony. Champion-specific first-clear benchmarks need current-patch measurement. The installed API’s event completeness, visibility/update behavior, and quest representation also remain untested. Until those gaps are closed, exact tactical calls should require fresh player confirmation.