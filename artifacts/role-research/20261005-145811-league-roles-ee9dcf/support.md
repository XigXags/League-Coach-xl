Support should manage **when teammates can safely act**: help bot control the wave, turn that window into movement, establish usable vision with allies, then preserve the spell needed to win the fight.

This research covers standard Summoner’s Rift as of **October 5, 2026**. I read public Riot documentation and professional-player interviews. I did not inspect match footage or a running client; strategic sequences below are my synthesis, not claims that I observed particular plays.

**Evidence status and 2026 rules**

- **Observed in published sources:** Riot’s implemented patch notes and the interview statements cited below.
- **Scheduled:** Riot lists 26.19 for September 23 and 26.20 for October 7. Thus 26.19 is the working baseline; 26.20 previews are not live mechanics. Regional deployment or tournament versions require confirmation. [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- **Inferred:** Expected strategic consequences and all decision patterns below.
- **Unknown:** This five-stack’s champions, skill, actual match state, and the installed client’s precise API behavior.

| Verified change | Coaching consequence—an inference |
|---|---|
| Role quests follow assigned positions; handle role swaps in champion select. Swiftplay and rotating modes do not use these same quest rules. | Confirm the mode and assigned support before applying this playbook. |
| Patch 26.1 raised completed support-item income to 9 gold/10 seconds and reduced control-ward cost to 40 gold after completion. | Quest completion affects both income and recurring vision costs. |
| Patch 26.3 moved support control wards into the quest slot **from match start**. | “You must finish the quest to free the inventory slot” is outdated. |
| Patch 26.16 changed the stated off-bot minion CS gold/experience penalty to **33% until level 5**, replacing 25% until level 3. Stack consumption values became **18/21**, equalizing champion/turret damage and CS routes across the two quest stages. | Early roaming has a larger resource tradeoff; taking risky poke solely for superior quest progress is outdated. |
| Patch 26.19 changed the support-item health sequence from 30/100/200 to **0/60/200**, and regeneration from 25/50/75% to **50/75/75%**. | Reassess early burst survival; more regeneration does not replace missing health during an all-in. |

Sources: [26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/), [26.3](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-3-notes/), [26.16](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-16-notes/), [26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/). The 26.16 wording does not justify treating every off-lane experience source as penalized.

Faelights also change placement decisions: wards there gain 25% vision radius and a 45-second additional reveal region. A new allied ward replaces the existing one on that Faelight. However, 26.3 reduced river pixel-brush coverage so it stops before the scuttle pad and epic-pit entrance. Its yellow-trinket cooldown also became 210–90 seconds by level. Do not reuse January coverage diagrams uncritically. [26.1 vision rules](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/), [26.3 corrections](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-3-notes/)

Three professional perspectives anchor the strategic interpretation:

- **Mikyx, September 2019:** Bot must communicate when support is needed to push or defend a wave, and both players must coordinate follow-up. His comments about specific mage matchups are historical; the communication principle remains useful. [Direct interview](https://www.invenglobal.com/articles/9067/mikyx-on-being-the-best-support-in-the-world-if-i-dont-play-like-i-did-in-the-past-two-weeks-ill-beat-ming-and-effort-for-sure)
- **Busio, January 2026:** He describes opposing junglers prioritizing vision and wave contests before finishing camps. This challenges deterministic “their camps are up, so they cannot be here” tracking. [Direct interview](https://lcsprofiles.com/interview/kc-busio-coming-to-the-lec-was-probably-the-most-difficult-decision-ive-made-in-my-life/)
- **CoreJJ, February 2026:** He discusses keeping teammates connected and explains an objective trade through composition, spawn order, and desired fight location. That is evidence for conditional planning—not a universal Baron-for-soul rule. [Direct interview](https://www.sheepesports.com/us/all/articles/tl-corejj-it-s-going-to-take-some-time-to-show-our-final-form/en)

**What the existing local API can support**

For the patterns below, these abbreviations describe documented capabilities, not a live-client test:

| Code | Available evidence |
|---|---|
| **P** | Player champions, teams, levels, inventories, scores, death state and respawn timers. |
| **A** | Active player’s health, resources, current gold, stats and ability ranks. “Active” means the local player, not all five teammates. |
| **E** | Timestamped events, including champion, turret, inhibitor, dragon, Herald and Baron kills. |
| **G** | Game time, mode, map and terrain metadata. |
| **U** | Undocumented tactical state: coordinates, waves, ward locations/expiry, actual vision coverage, spell cooldowns, recalls, objective health and exact quest progress. |

Summoner-spell names do not establish readiness. A `position` field is not map coordinates. Ward score does not establish safe vision. Future objective timers require inference from events plus verified rules. Inventory upgrades may suggest quest milestones; the 2026 quest-slot representation remains untested.

Sources: [API documentation](https://developer.riotgames.com/docs/lol#game-client-api), [Riot payload sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [Riot event sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json).

The coach should label inputs as **API-confirmed**, **player-reported**, **estimated**, or **unknown**, with timestamps. Below, “cannot verify” refers to **U** and the documented interface.

1. **Create lane pressure without separating from bot**

   **Trigger:** An opponent approaches a last-hit, misses an important spell, or becomes temporarily separated from their partner.

   **Information required:** Both duos’ effective ranges, wave size, health, mana, cooldowns, experience proximity and jungle approach routes.

   **Action sequence:** Identify which opponent both allies can threaten → move within immediate follow-up distance of bot → pressure during the last-hit or cooldown window → use brush or retreat space to end the trade → reassess before spending another spell. Melee support can create pressure by retaining engage; ranged support should avoid poking from a position bot cannot support.

   **Counterexample:** Walking alongside bot mechanically can expose both players to the same area spell. A large hostile wave can make an apparent two-on-one trade losing.

   **API:** P/A corroborate levels and local resources; cannot verify spacing, minions or the missed spell.

2. **Choose a wave outcome before touching minions**

   **Trigger:** Bot needs a recall, a jungle visit is approaching, or a wave risks becoming stuck outside the enemy turret.

   **Information required:** Next wave arrival, minion health, available quest charges, opponent return timing and whether the duo can finish the push.

   **Action sequence:** Agree on **hold, thin, slow push or crash** → use attacks and quest executions toward that outcome → retain enough defensive resources to survive the push → confirm minions actually reach the turret before treating the wave as released. If holding, avoid casual area damage that breaks the desired state.

   **Counterexample:** Helping halfway produces an enemy freeze; executing a convenient minion may destroy bot’s intended slow push.

   **API:** P shows CS changes; cannot verify wave shape, charge availability or a completed crash.

3. **Reset before the purchase becomes irrelevant**

   **Trigger:** A crash, enemy recall or kill creates time to spend gold and restore health, mana or wards.

   **Information required:** Bot’s purchase, support’s purchase, wave return, enemy reinforcements and next team movement.

   **Action sequence:** Finish the required wave work → stop taking unnecessary turret hits or trades → recall from safety → buy for the next job → announce return route and arrival. Stagger recalls only when one player can safely hold the lane or preserve a specific window.

   **Counterexample:** Staying for one more plate delays both purchases and leaves the duo returning into a bad wave. Conversely, recalling merely because gold is available can surrender a large incoming wave.

   **API:** A/P reveal local gold and purchases; cannot verify recall safety or completion.

4. **Roam with a return condition**

   **Trigger:** Bot has a safe collection window, or support returns from base with a useful mid/river route.

   **Information required:** Whether bot can survive and collect alone; enemy dive tools; jungle positions; mid wave; target escape spells; support’s level and quest cost.

   **Action sequence:** Name one purpose—cover mid’s crash, accompany jungle, clear an entrance or threaten a gank → agree how bot handles the next wave → choose a safe route → take the first useful result → return before bot must contest an unsafe wave. A forced retreat or cleared route can complete the roam without a kill.

   **Counterexample:** A wave approaching your turret is not automatically safe: a stacked wave plus enemy jungle may enable a dive. An extended pre-level-5 expedition also incurs the current quest tradeoff.

   **API:** P/E corroborate levels and outcomes; cannot verify the roam window or return deadline.

5. **Answer enemy support movement without automatic pursuit**

   **Trigger:** Enemy support disappears, recalls earlier or appears elsewhere.

   **Information required:** Last seen time and direction, bot wave, mid/top vulnerability, likely reinforcement routes and whether following would be late.

   **Action sequence:** Report the uncertainty immediately → warn the threatened lane → choose between matching safely, intercepting with jungle, or punishing the remaining bot laner → update when new evidence arrives. If the destination remains unknown, say so.

   **Counterexample:** Following through an unwarded river arrives second and abandons a winning bot situation. Diving the isolated carry can also fail if the missing support was baiting nearby.

   **API:** E can confirm later combat; cannot establish missing status, path or destination.

6. **Make jungle and mid partners in gaining vision**

   **Trigger:** The team needs to cross river, recover an entrance or enter enemy jungle.

   **Information required:** Mid’s ability to leave, jungle’s actual arrival, enemy last sightings, available detection, damage and escape routes.

   **Action sequence:** Help mid resolve the obstructing wave if appropriate → meet jungle at a safe boundary → reveal the first contested space → enter together → place vision covering the next approach → retreat when a nearby enemy lane disappears. Support supplies information and control; jungle and mid supply the threat that makes placement defensible.

   **Counterexample:** “Our mid has priority” is meaningless if mid is low, recalling or unable to follow. Enemy jungle may abandon camps to contest, as Busio describes.

   **API:** P/A give strength proxies; cannot verify priority, proximity or a safe entrance.

7. **Convert a bot lead into a controlled transition**

   **Trigger:** Bot turret falls, the enemy lane becomes unsafe to chase, or the team proposes moving bot to mid.

   **Information required:** Remaining quests, safe farming assignments, mid’s side-lane matchup, enemy engage range and the next contested side.

   **Action sequence:** Assign the displaced laner’s wave first → escort bot through the transition → establish vision on one useful side of mid → move with jungle during bot’s safe wave-clear window → return when enemy engage can threaten bot. Track who catches each side wave.

   **Counterexample:** Three players sharing mid experience while side waves die can erase the lead. Moving bot early can also sacrifice quest progress without producing meaningful pressure.

   **API:** E confirms turret destruction; P gives levels/items; cannot verify safe lane assignments.

8. **When ahead, spend pressure on access and denied choices**

   **Trigger:** Your nearby group is stronger and opponents must approach a wave, camp entrance or structure.

   **Information required:** Actual numbers, enemy escape routes, ally follow-up, carried shutdown risk and the alternative push.

   **Action sequence:** Push the wave that forces a response → occupy the adjacent entrance with allies → deny the ward that enables that response → threaten the predictable approach → take the structure or resource when enemies yield. Preserve a safe route for your strongest damage dealer.

   **Counterexample:** Clearing every ward spends the entire pressure window. A support engage that trades away the fed carry can lose despite securing the first kill.

   **API:** P/E support strength estimates; cannot establish numbers at the location or escape coverage.

9. **When behind, rebuild access from defensible ground**

   **Trigger:** Enemy control blocks river access or repeatedly catches support entering jungle.

   **Information required:** Which wave is safely collectible, enemy visible commitments, allied protection, available ranged checking tools and the cost of conceding.

   **Action sequence:** Defend the next useful wave → place reachable wards from safety → expand one entrance when allies can accompany → use enemy appearances elsewhere to recover additional ground → concede the objective if entry remains losing, while assigning a concrete wave, turret defence or cross-map gain.

   **Counterexample:** Walking alone to “get Baron vision” dies before providing actionable information. Conversely, conceding a game-ending threat without examining a coordinated contest can be equally wrong.

   **API:** P/E show deaths and losses; cannot verify a safe warding boundary.

10. **Build objective access before deciding to start**

   **Trigger:** An upcoming objective offers a worthwhile contest and the team has enough time to prepare.

   **Information required:** Adjacent waves, purchase timings, travel time, ward supply, enemy approaches, top’s participation, damage rate and jungle’s secure tools.

   **Action sequence:** Decide the intended fight side → clear the enabling waves → reset early enough to return together → establish an entry route → cover flanks and enemy approaches → deny pit information → explicitly choose **start, threaten, turn or leave**. Keep support positioned for the enemy entrance rather than automatically adding negligible damage inside the pit.

   Work backward from arrival: recall, shopping, travel and clearing contested ground all consume time. “Ward at one minute” is only a rough planning cue.

   **Counterexample:** Excellent pit vision does not compensate for losing both adjacent waves. Starting because opponents cannot see can trap your team in an unfavourable fight.

   **API:** G/E support timer estimates; cannot verify objective health, Smite readiness or arrival routes.

11. **Choose engage or peel by the next threat**

   **Trigger:** An enemy becomes catchable, a diver disappears, or the front lines begin interacting.

   **Information required:** Which ally must remain functional, who can follow, enemy divers and defensive tools, relevant cooldowns and terrain.

   **Action sequence:** Name the protected carry and primary threat → assign who initiates → reserve the necessary interruption or disengage → engage only when follow-up can arrive → reassess after the first cooldown exchange. An engage champion may need to peel; an enchanter may enable an ally’s initiation through speed or protection.

   **Counterexample:** Landing a multi-person engage can still lose if it exposes the team’s only damage source. Holding every spell defensively can also waste a decisive catch.

   **API:** P identifies composition/items; cannot verify cooldowns, target access or follow-up range.

12. **Support top and side pressure without dragging everyone together**

   **Trigger:** Top can threaten a side structure while the remaining team holds mid or contests another area.

   **Information required:** Top’s actual Teleport availability and valid arrival options, side-wave timing, enemy catch tools and the four-player group’s survival.

   **Action sequence:** Agree whether top joins or keeps pushing → prepare the relevant flank/arrival vision → keep the central group within a safe retreat → advance only when side pressure forces a response → call off the advance if top must retreat. Support often helps top most by keeping the other four alive.

   **Counterexample:** A theoretical five-versus-four is not real if top lacks an arrival option or the central group gets engaged before Teleport completes.

   **API:** P identifies chosen spells; cannot confirm quest-granted Teleport readiness or usable targets.

13. **Siege through protected waves, then leave together**

   **Trigger:** A minion wave reaches a structure and allies can threaten damage.

   **Information required:** Wave survival, enemy flank routes, engage range, ally defensive spells and whether another lane is applying pressure.

   **Action sequence:** Ward the approach that could cut off retreat → clear vision enabling the enemy flank → stand where you can protect the hitter or punish a defender → damage the structure during the safe window → withdraw as the wave or protection expires → reset or rotate as a group. When defending, preserve wave clear and cover the ally using it.

   **Counterexample:** Five players hitting a turret leave nobody controlling its side entrance. Chasing a defender after the wave dies can turn a successful siege into a wipe.

   **API:** E confirms destruction; cannot verify turret health, wave survival or flank safety.

14. **Budget wards, experience and item completion together**

   **Trigger:** Support is buying, nearing a key level, exhausting wards or considering another map trip.

   **Information required:** Next fight location, inventory, purchase breakpoint, existing useful wards, refill opportunity and whether the next wave grants a critical level.

   **Action sequence:** Buy vision for a named purpose → preserve enough economy for consequential item completion → replenish before the intended contest → collect necessary experience when safe → replace obsolete coverage as the team moves. Ask teammates to cover secondary routes with their own tools.

   **Counterexample:** Repeatedly donating control wards in undefendable terrain delays an item without producing usable vision. Leaving just before a crucial level can weaken the very fight the roam was meant to enable.

   **API:** A/P show local gold, level and inventory; cannot certify ward coverage or exact experience-to-level.

**How the five-stack should communicate**

These are recommended operating agreements, not additional game mechanics:

| Partner | Information support needs | Commitment support returns |
|---|---|---|
| Bot | “Need help crashing,” purchase timing, solo safety, follow-up readiness | Wave plan, departure, return condition |
| Jungle | Actual path, willingness to contest, secure readiness | Meeting point, entry route, crowd-control assignment |
| Mid | Whether the wave permits movement and which side is vulnerable | Cover for the crash, intended roam, enemy-support warning |
| Top | Side-wave plan, join timing, Teleport status | Arrival vision, whether the four-player group can wait |

Use **state → action → limit**. Players should correct stale information immediately. The coach should avoid repeated calls during mechanical execution and give one owner to “turn” or “leave.” Unknown information should produce a check or conditional call, not an invented fact.

**Six calls designed to fit roughly ten seconds**

Use these only when their stated conditions have been confirmed.

1. “Their hook missed. Bot, walk up with support; short trade, then back behind our wave. Don’t chase.”
2. “Finish this crash, then both reset. Skip the extra turret hit; come back together with purchases.”
3. “Bot is safe for this wave. Support, cover mid’s crash with jungle, then return before bot pushes out.”
4. “Dragon in seventy. Push mid, reset now, then support and jungle enter together through our cleared side.”
5. “Hold engage. Their diver is missing; save peel for our carry. Turn when the diver commits.”
6. “River is lost. Don’t ward alone. Catch mid, group at our entrance, and check forward together.”

**Six failure cases or misleading heuristics**

1. **“A crashed wave means a free roam.”**  
   The crash may be incomplete, quickly cleared, or followed by a dive. Require a return deadline and a bot survival plan.

2. **“Match every support roam.”**  
   Following late through fog can lose both sides. Compare arrival time with a bot punish, interception or defensive warning.

3. **“Higher vision score means better support.”**  
   Score does not tell you whether a ward protected the next action. Review the decisions that information enabled.

4. **“Jungle is clearing, so this ward is safe.”**  
   Camps do not bind enemy movement. Use recent sightings, nearby lane freedom and an escape route.

5. **“The tank support always engages.”**  
   Spending the only reliable interruption may hand the fight to an assassin or diver. Assign peel before initiating.

6. **“Two control wards every recall; more is always better.”**  
   Cheap wards still consume gold and placement time. Repeated uncontestable replacements can delay a decisive purchase.

**Source list**

- [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends) — live-versus-scheduled baseline.
- [Riot 26.1 patch notes](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) — role quests, support rewards and Faelights.
- [Riot 26.3 patch notes](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-3-notes/) — quest-slot storage and vision corrections.
- [Riot 26.16 patch notes](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-16-notes/) — early-roaming penalties and quest consumption.
- [Riot 26.19 patch notes](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/) — current support-item health/regeneration changes.
- [Riot Live Client Data documentation](https://developer.riotgames.com/docs/lol#game-client-api), [payload sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [event sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json) — documented observability.
- [Mikyx interview, Inven Global](https://www.invenglobal.com/articles/9067/mikyx-on-being-the-best-support-in-the-world-if-i-dont-play-like-i-did-in-the-past-two-weeks-ill-beat-ming-and-effort-for-sure) — bot coordination and roam constraints.
- [Busio interview, LCS Profiles](https://lcsprofiles.com/interview/kc-busio-coming-to-the-lec-was-probably-the-most-difficult-decision-ive-made-in-my-life/) — jungle participation in vision and wave contests.
- [CoreJJ interview, Sheep Esports](https://www.sheepesports.com/us/all/articles/tl-corejj-it-s-going-to-take-some-time-to-show-our-final-form/en) — connected team movement and conditional objective trades.

**Research gaps:** No match or replay was inspected, so this report contains no observed execution examples. Champion-specific cooldowns, matchups, builds and exact quest thresholds need a separate current-patch pass. The published API samples are older than the 2026 systems; quest-slot items, field freshness and current payload differences remain unverified. I traced the consequential support and vision changes above, but did not exhaustively audit every intervening hotfix. A production coach also needs separate review of Riot’s current third-party-product rules; documented data access alone does not establish approval for every live coaching feature.