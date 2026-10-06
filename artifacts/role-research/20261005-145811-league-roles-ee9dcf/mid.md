**Mid’s job in a five-stack is to turn wave control into useful arrival windows while preserving enough resources to act when arriving.** A pushed wave alone does not establish usable priority: health, mana, cooldowns, route safety, and the receiving lane determine whether the move works.

Research date: **October 5, 2026**. Scope: standard Summoner’s Rift with role quests. I inspected public patch notes, API documentation, and interview text; I did not watch or inspect a match replay.

**Evidence status and 2026 mechanics**

- **Observed in published sources:** Riot’s latest released patch notes located are 26.19. The mid-quest reward progression is **boot upgrade plus empowered recall in 26.1 → recall replaced by 6% bonus AD/AP in 26.9 → increased to 8% in 26.11**. The latest mid reward change I located is therefore **tier-three boots plus 8% bonus AD/AP**, not a four-second quest recall. [26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/), [26.9](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-9-notes/), [26.11](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-11-notes/)
- **Scheduled:** Riot lists 26.20 for October 7, 2026. Preview changes must not be treated as live on October 5. [Official schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- **Inferred:** The decision patterns below are coaching synthesis. They are conditional strategic principles, not Riot rules or claims that a professional prescribed every sequence.
- **Unknown:** The stack’s champions, skill level, queue, actual client build, and current game state. No local endpoint was queried.

The launch rules specify 1,350 mid-quest points, progress from champion damage, and a tier-two-to-tier-three boot upgrade, including when tier-two boots are purchased after completion. Melee and ranged damage contribute differently. Quest assignment follows the assigned role; arrange role swaps in champion select. Early off-lane farming also has a penalty. These details make both lane participation and correct lobby assignment relevant. [Riot 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/)

Patch 26.9 changed progression substantially: in-lane passive progress became 1.5 points/second versus roughly 0.333 outside; after level three, lane time banks roaming allowance, reaching 60 seconds after 120 seconds in lane. Banked time preserves the higher **passive** rate outside lane. Recalling disables passive progress for 12 seconds. The off-lane penalty to CS/turret/plate quest points starts at 75% and diminishes with quest progress. Thus, banking roam time does **not** make missed waves or every off-lane action free. [Riot 26.9](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-9-notes/)

Other relevant launch changes: waves spawn every 25 seconds from minute 14 and every 20 seconds from minute 30; non-Nexus towers have permanent plates; Cassiopeia’s passive was reworked to permit boots. Old wave schedules, “plates disappear at 14,” and “Cassio cannot buy boots” are obsolete starting assumptions. [Riot 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/)

Later changes affect teammates and purchases:

- **26.16:** Spellslinger’s Shoes increased to 20 flat plus 8% magic penetration; Chainlaced Crushers fell to 25 MR. Support’s off-bot minion XP/gold penalty became 33% until level five. Do not demand repeated early support visits without pricing their bot-lane cost. [Riot 26.16](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-16-notes/)
- **26.19:** Top’s quest Teleport cooldown improved; non-top Unleashed Teleport did not receive that change. Mid and top should report their own readiness rather than share an assumed timer. [Riot 26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/)

**What professional testimony supports**

Poby describes mid priority as enabling side-lane movement, pressure, and access to enemy raptors. Treat this as an explanation of priority’s value, not permission to invade regardless of the surrounding state. [Direct Poby interview](https://rft.gg/news/laning-phase-makes-everything-poby-after-navi-s-win-over-gx)

Chovy describes adjusting wave control and pressure to Peanut’s decisions and distinguishes proactively creating situations from simply fighting whatever appears. That supports planning a wave before requesting jungle action. [Direct Chovy interview, 2022](https://www.invenglobal.com/articles/18156/chovy-when-you-see-the-great-mid-laners-play-theres-kind-of-a-formula)

ShowMaker emphasized team strength, tracking summoner spells, and initial push into roaming in a **2020 meta-specific** interview. The transferable principle is converting personal advantage into coordinated action; its draft conclusions are historical. [ShowMaker and DWG coaching staff interview](https://www.invenglobal.com/articles/12493/worlds-2020-dwg-showmaker-doinb-and-caps-inspired-me-to-the-point-of-being-detailed-in-keeping-summoner-spells)

Vitality coach Pad gives a useful counterweight: losing Flash on two immobile lanes before Nocturne’s level six removed their freedom to play despite an item advantage. He also describes Humanoid directing mid/late map movement. Resources and threat interactions can outweigh nominal lane leads. [Direct Pad interview, 2026](https://rft.gg/news/we-lost-to-ourselves-pad-on-vitality-s-defeat-against-kc-humanoid-s-role-and-why-he-s-betting-on-spring)

**Live Client Data API: verification legend**

These labels keep each decision’s verification limits explicit:

| Label | Available evidence |
|---|---|
| **P — Player snapshot** | Champions, levels, items, CS/KDA, alive/dead state, respawn timers, and equipped summoner identities. Role `position` is a role label, not coordinates, and can be empty. |
| **A — Active player** | Local player’s current gold, health/resource and other stats, ability ranks. Another teammate’s client does not provide this same detailed active-player view of mid. |
| **E — Events/clock** | Game time and emitted kill, structure, and epic-monster events. Historical events establish outcomes, not current spatial control. |
| **H — Human confirmation required** | Waves, coordinates, ward coverage, enemy sightings/routes, recall channels, spell readiness, and quest progress/banked time are not established by the documented payload. |

Sources: [Riot API documentation](https://developer.riotgames.com/docs/lol#game-client-api), [player-data sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [event sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json).

Neither CS nor ward score proves priority or a safe route. Equipped Flash does not prove Flash ready. An upgraded boot is evidence of an item state, not a direct quest-progress field. Any derived cooldown or spawn estimate must remain labeled **inferred**. The following API assessments concern the public documented interface; current runtime additions remain untested.

**Decision patterns**

**1. Choose the first wave plan from the matchup and jungle plan**

- **Trigger:** Lane begins, or a purchase/level changes who can contest the wave.
- **Information required:** Relative range and waveclear, trade pattern, level-up proximity, jungle path, enemy support availability, and the next intended team action.
- **Action sequence:** Agree whether mid must move first. Seek an early minion advantage only if the trades are affordable. Against threatening engage, preserve health and thin rather than contest every last hit. Announce the consequence: “I can move after this crash” or “No river help until next wave.”
- **Counterexample:** A ranged champion repeatedly hitting a melee champion can damage the wave, lose control of its position, and become vulnerable. “Ranged wins early” is insufficient.
- **API:** **P/A** establish matchup inputs and local resources; **H** establishes wave control and jungle positioning.

**2. Build a slow push, then fully crash for a chosen action**

- **Trigger:** Mid needs a purchase, warding trip, or coordinated roam and can control the next waves.
- **Information required:** Minion numbers/health, reinforcement timing, enemy thinning ability, mana, and the opponent’s ability to hold the wave.
- **Action sequence:** Preserve a modest allied wave advantage; protect it while last-hitting. Accelerate the final wave with spells. Confirm the wave actually reaches turret before leaving. Choose one use of the window and set a return deadline.
- **Counterexample:** An opponent with superior waveclear can erase the stack. A half-crash can leave the wave frozen outside their turret and make the roam expensive.
- **API:** **A** helps assess resource affordability; **H** must verify the stack, crash, and return deadline.

**3. Hold or thin a wave when behind—or when denying is better than moving**

- **Trigger:** Enemy pressure makes pushing unsafe, or an advantageous wave can deny an opponent without sacrificing a more valuable team action.
- **Information required:** Incoming wave size, dive threat, allied jungle availability, enemy reset/roam, and whether teammates require immediate help.
- **Action sequence:** Thin enough to prevent an overwhelming crash; hold outside turret only while survivable. Give up individual CS before losing the health needed for XP access. If a dive is forming, request early cover or retreat before being trapped.
- **Counterexample:** Holding a wave while the opponent creates a decisive numbers advantage elsewhere can lose more than it denies. A large wave plus enemy jungle is not a safe freeze.
- **API:** **P/A** support deficit/resource assessment; **H** verifies wave size, dive setup, and the competing play.

**4. Spend priority through jungle–support coordination**

- **Trigger:** Mid has a usable first move and jungle/support can act in the same area.
- **Information required:** Both adjacent lanes’ movement, teammate resources, last enemy jungle/support sightings, camp/objective availability, and return path.
- **Action sequence:** Name the exact play—escort a ward, defend raptors, contest an entrance, or invade a specific camp. Move together through the confirmed route. Mid protects an approach or supplies follow-up; support supplies vision/engage; jungle chooses the camp or objective commitment. Exit when enemy reinforcements erase the advantage.
- **Counterexample:** Mid priority cannot rescue an invade where enemy bot moves first and allied support is pinned under turret.
- **API:** **P/A** provide partial readiness evidence; **H** verifies arrival order, routes, vision, and camp availability.

**5. Roam to a side lane with an arrival test and an abort condition**

- **Trigger:** A crash creates a window and top or bot has a concrete setup.
- **Information required:** Target wave direction, allied crowd control, health/mana, escape spells, enemy countergank, travel time, and mid’s expected losses.
- **Action sequence:** Ask the receiving lane to hold engagement until arrival or prepare the crash for a dive. Choose a route that does not reveal the play unnecessarily. Recheck halfway. If the target retreats or setup disappears, take a safe warding action or return immediately.
- **Counterexample:** Arriving at bot after the enemy wave has bounced toward safety produces no target and loses mid’s next wave. A successful-looking roam can still be a bad trade.
- **API:** **P** supports matchup/death checks; **H** verifies the setup, travel window, and escape cooldowns.

**6. Respond to an enemy roam without blindly following**

- **Trigger:** Enemy mid leaves vision.
- **Information required:** Last observed direction/time, current wave, route safety, side-lane exposure, and whether mid can arrive before the fight is decided.
- **Action sequence:** Call the observation precisely. Warn the exposed lane immediately. Follow only through a safe route with meaningful arrival timing; otherwise crash, pressure a structure, defend the opposite entrance, or reset. Update teammates if the enemy reappears.
- **Counterexample:** Following an assassin through an unwarded choke can add a second victim. Conversely, taking CS while a nearby, winnable countergank develops can waste the strongest response.
- **API:** **E** can confirm subsequent kills; **H** is required for disappearance, direction, and interception.

**7. Reset to finish a purchase and arrive for the next action**

- **Trigger:** A useful purchase is available, resources are insufficient, or the team needs synchronized arrival.
- **Information required:** Actual wave state, purchase value, travel time, enemy reset, Teleport readiness, and which teammate covers the gap.
- **Action sequence:** Work backward from the required arrival. Crash if feasible; request help breaking a freeze if necessary. Recall from safety, buy promptly, and announce destination. If crashing risks death, accept a controlled wave loss and reset.
- **Counterexample:** Staying for one more plate while jungle/support reset can leave mid isolated and make the team arrive in separate groups.
- **API:** **A/P** support purchasing checks; **H** verifies recall, coverage, wave loss, and movement readiness.

**8. Transition into side lanes with top and ADC**

- **Trigger:** Tower changes or ADC’s movement mid requires a new farm assignment.
- **Information required:** Which solo laner can survive each matchup, Teleport/global readiness, escape tools, vision, and the next fight’s location.
- **Action sequence:** Give every wave an owner. Usually let ADC access the shorter central lane when appropriate; allocate sides by survivability and joining speed. Without a reliable global, mid generally takes the side nearer the next contest. Catch, push only to the agreed safety boundary, then move before teammates become exposed.
- **Counterexample:** Automatically sending an immobile mage into a long lane against a fed duelist can lose both the mage and the objective. Mid may need escorted collection or a different assignment.
- **API:** **P/E** support roster and destroyed-tower checks; **H** verifies assignments, safe depth, and joining time.

**9. Use a lead to force responses, then rotate**

- **Trigger:** Mid wins a side matchup, clears faster, or threatens significant tower damage.
- **Information required:** Enemy response locations, escape route, allied pressure timing, shutdown risk, and what the rest of the team can actually take.
- **Action sequence:** Push while teammates prepare their pressure. When an enemy answers, decide whether to keep them pinned or leave first. If multiple enemies respond, retreat early and call exactly what teammates can take. Reset before the lead becomes unspent gold and low resources.
- **Counterexample:** A side push creates little value if four allies are shopping. Continuing to hit a tower after defenders disappear can surrender the lead.
- **API:** **P/E** support item and outcome checks; **H** verifies pressure synchronization and enemy responses.

**10. Recover from behind through protected collection and narrow fights**

- **Trigger:** Mid cannot contest open space or loses the side-lane duel.
- **Information required:** Safe incoming waves, friendly defensive positions, the strongest allied carry, enemy dive tools, and available defensive cooldowns.
- **Action sequence:** Assign protected farm instead of having three players share one wave. Preserve waveclear and crowd control. Move with the strongest allied unit when entering contested space. Prefer a specific local advantage—an isolated overextension, numbers advantage, or spent enemy engage—over a full formation fight.
- **Counterexample:** Abandoning every contest gives the enemy uncontested conversion. Being behind does not invalidate a visibly favorable three-versus-two.
- **API:** **P/A** identify some deficits; **H** verifies isolation, safe farm, and enemy cooldown expenditure.

**11. Prepare a fight by controlling the wave and one usable entrance**

- **Trigger:** The team intends to contest a spawning objective, defend a tower, or punish an enemy rotation.
- **Information required:** Mid and nearby side waves, purchase/reset status, entry routes, enemy flank threats, and each player’s combat readiness.
- **Action sequence:** Arrange resets early enough to return together. Push the relevant wave while teammates cover entrances. Escort support into one chosen corridor. Establish mid’s casting position before the enemy arrives. Assign who watches flank, who starts the objective, and who turns. If the entrance is lost, reassess before walking in.
- **Counterexample:** A “warding mission” after the enemy has established control can become a staggered series of deaths. Starting the objective without controlling the approach can trap your own mage.
- **API:** **E/P** provide timing and roster context; **H** verifies entrances, formation, vision, and readiness.

**12. Siege through synchronized waves and threat preservation**

- **Trigger:** A wave can reach a defended tower and the team has an advantage worth converting.
- **Information required:** Adjacent wave timing, enemy engage reach, waveclear, flank access, allied escape tools, and who should hit the tower.
- **Action sequence:** Make the side wave demand attention near the same time. Let the appropriate damage dealer hit the tower while mid threatens defenders or clears their wave. Retain the spell that prevents the enemy engage. Take incremental damage, then leave as the wave dies or defenders converge.
- **Counterexample:** Throwing every control spell at poke can create the enemy’s engage window. Five players staring at a tower against superior waveclear may accomplish less than a coordinated second lane.
- **API:** **E** confirms destruction; **H** verifies tower health, waves, flank safety, and spell availability.

**13. Anti-siege: protect the waveclearer and avoid simultaneous collapse**

- **Trigger:** Enemies approach a tower with a wave, especially with pressure in another lane.
- **Information required:** Whether the wave can be cleared safely, enemy dive range, friendly mana/cooldowns, side-wave arrival, and escape routes.
- **Action sequence:** Assign one safe clearer and protect their cast window. Conserve spells for the wave or the actual dive. Allocate another defender before the second wave arrives. If holding requires stepping into guaranteed engage, concede the structure and defend the next line together.
- **Counterexample:** Trading half of mid’s health for harmless poke before the wave arrives can remove the team’s only defense. Splitting defenders against a committed five-player dive can also fail.
- **API:** **A/E** support local resource and structure checks; **H** verifies dive range, waveclear safety, and parallel pressure.

**14. Teamfight according to the champion’s job and available threats**

- **Trigger:** Teams enter engagement range.
- **Information required:** Which enemy can reach mid, major engage cooldowns, allied engage/peel, target durability, and escape path.
- **Action sequence:** Decide the job before committing: control mage holds an approach and damages reachable threats; assassin seeks a protected entry after key defenses are used; battle mage requires sustained access. Avoid sharing an easy area-of-effect hit with ADC. Coordinate top/jungle entry and support follow-up. Reposition between casts.
- **Counterexample:** “Always hit backline” makes mages walk through frontline threat. “Always stand behind ADC” prevents useful zoning and can expose both carries to the same flank.
- **API:** **P/A** support composition/resource context; **H** verifies spacing, targeting, and the cooldown sequence.

**Communication with all four roles**

Use **observation → consequence → request → expiry**. For example: “Enemy mid last seen moving bot; I cannot follow through river; bot back off; I can move after this wave.” Do not convert “last seen bot side” into “enemy is definitely bot.”

| Teammate | Mid should communicate | Teammate must supply |
|---|---|---|
| **Top** | Roam arrival, side assignment, pressure timing, whether mid can join | Wave/dive setup, matchup safety, actual Teleport readiness |
| **Jungle** | Earliest usable move, health/mana cost, which entrance mid can cover | Intended path, contest commitment, enemy jungle evidence |
| **ADC** | Missing threats, lane handoff, mid-wave ownership, fight damage plan | Whether support can leave, bot-wave state, defensive resources |
| **Support** | Safe movement window, CC follow-up, warding escort destination | Bot cost, enemy support sightings, route and vision confirmation |

A coach should let the player with direct evidence correct the plan. Issue one immediate action and its cancellation condition; save explanations for after the sequence.

**Six approximately ten-second voice calls**

These are conditional examples for a human-confirmed situation, not claims the API can generate reliably.

1. “Mid, build this wave, then crash the next. Jungle, cover lower river. We leave together once the wave reaches tower.”
2. “Enemy mid missing toward bot; river is dark. Bot, back off now. Mid, shove and reset—we cannot follow safely.”
3. “Their mid just spent the clear spell. Jungle and support, enter together now. Mid follows; leave if their bot moves first.”
4. “ADC takes mid. Mid catches bot only to our ward line. Top holds the opposite side; call Teleport readiness.”
5. “Our wave is arriving. ADC hits tower; mid saves control for their engage. Back out when the wave dies.”
6. “Mid, stay offset from ADC. Hold your stun for the diver. Jungle starts; damage whoever enters range, then step back.”

**Six failure cases and misleading heuristics**

1. **“I pushed, so I have priority.”** Mid spent all mana, cannot cross the enemy’s threat range, or has no safe route. Priority must include the ability to arrive and contribute.
2. **“Roam every cannon wave.”** Cannon presence does not prove a crash, sufficient travel time, or a target. The return window depends on the actual wave and clear speed.
3. **“Enemy mid roamed; follow immediately.”** The opponent may be baiting a dark choke. Warn, assess arrival, then follow safely or take a specific alternative.
4. **“Support should permanently unlock mid.”** This can sacrifice ADC’s lane and support progression; 2026 changes explicitly increased early off-lane costs. Use agreed windows.
5. **“After lane phase, mid always goes bot and never groups without pushing.”** Matchup, global availability, and an immediate fight can override the default. Sometimes conceding a wave is correct.
6. **“Quest completed: use the four-second recall,” or “quest bonus means 8% more final damage.”** The recall reward was removed; the replacement modifies stats. Damage still depends on ratios, defenses, penetration, and access.

**Source list**

- [Riot patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) — role-quest launch, waves, towers, Cassiopeia.
- [Riot patch 26.9](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-9-notes/) — roaming allowance, progression changes, recall replacement.
- [Riot patch 26.11](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-11-notes/) — mid reward increased to 8%.
- [Riot patch 26.16](https://www.leagueoflegends.com/en-gb/news/game-updates/league-of-legends-patch-26-16-notes/) — boots and support roaming changes.
- [Riot patch 26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/) — current published patch context and top Teleport.
- [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends) — scheduled dates.
- [Live Client Data documentation](https://developer.riotgames.com/docs/lol#game-client-api), [data sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json), [event sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json) — verification boundaries.
- [Poby interview](https://rft.gg/news/laning-phase-makes-everything-poby-after-navi-s-win-over-gx) — priority and lane importance.
- [Chovy interview](https://www.invenglobal.com/articles/18156/chovy-when-you-see-the-great-mid-laners-play-theres-kind-of-a-formula) — proactive wave/pressure coordination.
- [ShowMaker and coaches interview](https://www.invenglobal.com/articles/12493/worlds-2020-dwg-showmaker-doinb-and-caps-inspired-me-to-the-point-of-being-detailed-in-keeping-summoner-spells) — teamplay and composition intent.
- [Pad interview](https://rft.gg/news/we-lost-to-ourselves-pad-on-vitality-s-defeat-against-kc-humanoid-s-role-and-why-he-s-betting-on-spring) — Flash constraints, overextension, and mid/late leadership.

**Research gaps**

No replay-based validation, matchup-specific damage tests, or current local API schema inspection was performed. The documented samples may lag the client, particularly for quest state and newer events. Exact quest interpolation and special interactions need runtime verification before numerical automation. Later patch searches located the changes above but do not constitute an exhaustive audit of every champion, boot, or hotfix. To make reliable live calls, this coach still needs timely player reports—or separately authorized visual observation—for waves, locations, wards, and cooldowns.