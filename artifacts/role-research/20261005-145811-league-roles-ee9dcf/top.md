**Top-lane research for a five-stack Discord coach — assessed October 5, 2026.**

Top’s central decision is how to convert the next wave into an advantage the team can actually use: a safe purchase, denied experience, a protected jungle entrance, turret damage, or timely fight participation. A coach should call the wave’s purpose, the required help, and the condition that ends the play.

This report uses public Riot documentation and written professional-player interviews. I did not inspect match footage, run code, access a local client, or edit files. Strategic recommendations below are my synthesis; they are not presented as tested outcomes or direct professional quotations.

**Evidence status and 2026 mechanics**

- **Observed in published sources:** Riot’s patch notes and API documentation, plus the interview statements cited below. “Observed” here does not mean independently tested in a live game.
- **Scheduled:** Riot lists 26.19 for September 23 and 26.20 for October 7. Thus 26.19 is the working baseline for October 5; 26.20 previews should not govern live calls. Regional deployment and hotfix state still require confirmation. [Riot patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- **Inferred:** The decision patterns, role assignments, and voice calls below.
- **Unknown:** This stack’s champions, skill level, current match state, actual client schema, and any undocumented behavior.

The relevant official changes are:

| Mechanic | Published rule and coaching consequence |
|---|---|
| Top quest foundation | Assigned through lobby role; officially swap roles in champion select. Completion requires 1,200 points and grants 600 XP and a level cap of 20. Before level 3, top suffers a 25% minion gold/XP reduction outside top lane. [26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) |
| Progression revised in April | 26.9 changes the off-lane CS/turret/plate quest-point penalty to 75%, declining toward zero with quest progress. Passive gain becomes 0.333/s, or 1.5/s anywhere in the assigned lane outside base. Recall disables passive gain for 12 seconds. After level 3, 120 seconds in lane can bank 60 seconds of enhanced progression while roaming. [26.9](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-9-notes/) |
| XP reward revised | The original 12.5% bonus is outdated: 26.9 specifies **80 additional XP per champion takedown and 11% from other sources**. [26.9](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-9-notes/) |
| Quest Teleport | Without selected Teleport, completion grants an additional Unleashed Teleport. In 26.19 its cooldown becomes **390 seconds**. Top’s upgraded selected Unleashed Teleport becomes **300–210 seconds**; non-top Unleashed Teleport remains **330–240 seconds**. [26.19](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/) |
| Selected-Teleport shield | 26.12 changes the quest-enhanced arrival shield to **35% maximum health for 10 seconds**, replacing 30% for 30 seconds. Plan immediate useful arrival, rather than storing the shield through a long setup. [26.12](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-12-notes/) |
| Turret and vision context | 26.1 makes outer plates permanent, adds inner/inhibitor turret plates, introduces Crystalline Overgrowth, and adds Faelight ward zones. The old “plates disappear at 14” deadline is obsolete. Check current turret state and vision coverage before extending. [26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/) |

**Strategic interpretation:** quest completion is another power breakpoint, but quest efficiency does not justify dying or conceding the base. Roaming now has an explicit allowance; “never leave top before completing quest” is too rigid. Combat summoners exchange early Teleport access for lane tools, with quest Teleport arriving later. That trade depends on matchup and the team’s plan.

**What professional evidence supports**

Odoamne described team-provided aggressive vision and jungle intervention at volatile lane moments as enabling sustained top pressure. The useful principle is to schedule help around a wave that can swing the lane, rather than treating the jungler’s completed clear as the only permissible timing. This is historical testimony, not evidence about current regional strength. [Odoamne, Inven Global, 2021](https://www.invenglobal.com/articles/15502/the-top-lane-gap-at-worlds-2021)

He later described playing weak side while still exploiting specific opportunities with his jungler. Weak side therefore need not mean permanent abandonment. [Odoamne interview, 2022](https://www.invenglobal.com/articles/16313/odoamne-now-we-have-the-tools-to-not-go-0-3-in-playoffs-like-the-meme-is)

Bwipo’s discussion of carry tops emphasizes turning invested resources into control of the game. A lane lead that never creates usable pressure is an incomplete return on the team’s investment. [Bwipo interview, Team Liquid, 2022](https://teamliquid.com/news/2022/01/28/bwipo-creativity-consistency)

UmTi’s assessment of Morgan also identifies a useful failure mode: waiting for a perfect teamfight angle can itself become a weakness. [UmTi interview, Team Liquid](https://teamliquid.com/articles/team-liquid-morgan-umti)

**Live Client Data API: evidence boundary**

Use these codes in the patterns:

- **P:** Player data: champions, levels, items, scores, death state, respawn timer and summoner identities.
- **A:** Active player only: current gold, health/resources, combat stats and learned ability ranks.
- **E:** Available event records and game time.

The documented schema does **not** provide a wave map, champion coordinates, ward coverage, enemy jungle routes, live spell cooldowns, or a dedicated role-quest progress/readiness interface. `position` denotes role, not map coordinates. Ability rank is not cooldown readiness. [Riot API documentation](https://developer.riotgames.com/docs/lol)

The public sample is illustrative, not a verified 2026 payload. One local client’s active-player detail is not all five players’ detail. Treat quest Teleport representation, freshness and field availability as untested. [Riot sample response](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json)

Operationally, keep player reports separate from API facts: “Lee was seen bot twelve seconds ago” is a dated observation; “Lee may path top next” is an inference.

**Decision patterns**

Each pattern specifies a trigger, required information, sequence, exception, and API boundary. Matchup examples describe situations to evaluate, not current matchup win-rate claims.

**1. Contest a level or ability breakpoint**

- **Trigger:** Either laner is about to gain a meaningful level, ability rank, or quest-completion spike.
- **Information:** XP proximity, missed/shared experience, health, resources, combat summoners, key cooldowns, minion damage, and escape distance.
- **Sequence:** Identify who levels first → position before the relevant minion dies → learn the intended ability → take a short trade or zone immediately → stop before the opponent catches up unless the all-in remains favorable.
- **Counterexample:** Being level 2 against level 1 does not justify fighting through a large enemy wave at low health. A champion’s level-6 spike may be utility rather than immediate duel strength.
- **API:** P/A confirm levels and own ranks; not XP proximity or readiness.

For the stack’s champion pool, prepare matchup cards with three questions: who controls the opening wave, which enemy ability creates the trading window, and which item/level reverses the duel. Do not substitute “melee beats ranged later” for champion-specific analysis.

**2. Build a slow push into a real crash**

- **Trigger:** Top can control the wave and wants a recall, warding trip, dive setup, or first move.
- **Information:** Relative minion health/count, next reinforcement, enemy waveclear, jungle danger, purchase target, and defender’s return options.
- **Sequence:** Create a modest friendly surplus → preserve it through selective last hits → escort the accumulated wave → accelerate clearance before reinforcements prevent the crash → confirm the wave reaches turret → spend the resulting window.
- **Counterexample:** An opponent can trim freely or hold the wave outside turret. Leaving then creates an enemy freeze instead of a safe reset.
- **API:** P/A support purchase assessment; crash remains unverified.

A “third-wave recall” is an outcome of control, not a command to recall regardless of the wave.

**3. Freeze for denial or recovery**

- **Trigger:** An incoming wave can be held outside your turret without losing excessive health or map access.
- **Information:** Minion damage and reinforcements, opponent’s ability to break the hold, your sustain, jungle proximity, and teammates’ need for first move.
- **Sequence:** Thin the excess → retain enough enemy strength to keep the wave coming toward you → last-hit selectively → position to deny access if stronger → release and push when the team needs movement.
- **Counterexample:** Holding a large wave while vulnerable to a dive compounds the loss. Freezing while your jungler contests an entrance may surrender the only useful support.
- **API:** P shows CS/level consequences; wave stability is unknown.

Avoid a universal “four casters” prescription: health, location, reinforcement timing, and champion interference matter.

**4. Break a hostile freeze**

- **Trigger:** The opponent holds your wave outside their turret and can punish every approach.
- **Information:** Whether top can survive a trade, enemy jungle/mid location, allied help timing, and how many waves are at risk.
- **Sequence:** Call “help crash,” explicitly distinguishing it from a kill request → jungle or mid escorts top → clear together → ensure the crash → recall or withdraw together.
- **Counterexample:** Both helpers arrive too late or lose the resulting skirmish. Conceding some farm and preserving XP access can be cheaper than donating multiple kills.
- **API:** P detects resource deficit; freeze and safe intervention remain unknown.

**5. Survive weak side before the dive forms**

- **Trigger:** Allied resources are committed elsewhere while the enemy stacks a wave, disappears into top-side fog, or gains a dangerous health advantage.
- **Information:** Latest enemy sightings, mid/support absences, incoming wave size, escape route, defensive cooldowns, and whether help can arrive before contact.
- **Sequence:** Preserve health early → thin only when safe → request cover with a specific deadline → if cover is unavailable, retreat before exits close → identify what the other four can safely gain.
- **Counterexample:** Retreating solely because jungle is unseen can concede freely in a defendable state. Weak side does not prohibit punishing a confirmed enemy mistake.
- **API:** A/P show own condition; dive formation is unverified.

“Give the wave” must happen while retreat remains possible, not after the enemy surrounds the turret.

**6. Convert strong-side investment**

- **Trigger:** Top has a controllable wave and allied jungle/support can arrive during a favorable window.
- **Information:** Defender’s health and summoners, countergank risk, mid priority, turret aggro plan, and post-play wave.
- **Sequence:** Announce crash timing → establish approach vision → decide whether the value is denial, damage, or a dive → assign first turret aggro and exit → secure the crash → reset or take safe structure damage.
- **Counterexample:** A mechanically difficult dive is unnecessary when the defender is already forced off a large wave. Staying for another plate can lose the purchased advantage.
- **API:** P/E record outcomes; aggro and conversion safety are unknown.

Judge the investment by subsequent lane control and map access, not merely whether the gank produced a kill.

**7. Track jungle as an expiring estimate**

- **Trigger:** Jungle appears, a ward loses coverage, mid/support disappears, or top is about to cross a dangerous line.
- **Information:** Sighting location/time, movement direction, plausible exits, allied vision, and opponent behavior.
- **Sequence:** State the observation → list plausible next routes → choose a retreat boundary → place vision before extending → update immediately when new evidence contradicts the route.
- **Counterexample:** “Jungle showed bot” does not make top safe indefinitely; recall, mobility and elapsed travel time change the situation.
- **API:** P/E provide context; sightings and paths are unavailable.

Ward for warning time. A nearby ward that reveals a gank only after escape is impossible may add little protection. Use available Faelight coverage where it actually watches the relevant approach.

**8. Reset after a kill, recall, or item threshold**

- **Trigger:** Opponent dies/leaves, top reaches a meaningful purchase, or health/resources make the next wave unsafe.
- **Information:** Current wave, ability to finish a crash, enemy return timing, available Teleport, and the next team deadline.
- **Sequence:** Choose among immediate recall, crash then recall, or hold → spend promptly → announce return method → re-evaluate the wave on arrival.
- **Counterexample:** A kill at low health does not authorize pushing through another full wave while enemy jungle is missing. Sometimes an imperfect recall loses less.
- **API:** A/P/E establish gold/death context; recall safety is unknown.

For coordinated resets, name who temporarily catches each lane. Avoid all five recalling while a large wave reaches an exposed structure.

**9. Leave lane for a specific river action**

- **Trigger:** Jungle requests help, or a nearby contest is likely to start.
- **Information:** Whether top can leave first, mid’s movement, enemy top’s route, fight odds, wave loss, and quest state.
- **Sequence:** Agree on the actual job—guard entrance, zone enemy top, threaten turn, or hit monster → prepare/crash the wave if time permits → move through controlled space → set an exit deadline → return when the job ends.
- **Counterexample:** Following an enemy through fog while your wave crashes can lose both the fight and lane. An announced concession can be better.
- **API:** E establishes recorded events/time; priority and quest bank are unknown.

Do not bring top merely to stand beside a monster when controlling the opponent’s entry would be more valuable.

**10. Assign side lanes and Teleport responsibility**

- **Trigger:** Outer turrets fall, a major contest approaches, or either solo laner resets.
- **Information:** Top/mid matchup safety, actual Teleport readiness, target availability, who must engage, and the four-player group’s ability to disengage.
- **Sequence:** Assign each wave by name → give the distant lane to a suitable responder with verified access → set a maximum push boundary → establish a usable arrival target → require “top available” before committing.
- **Counterexample:** A tank who supplies the team’s only engage may need to arrive on foot even with Teleport ready. A mid laner may be the safer distant-lane holder.
- **API:** P shows identity/items; Teleport availability and target safety are unknown.

Budget channel, travel, and movement after arrival. Summoner Teleport was changed to include visible travel in 2025; it is not an instantaneous rescue. [Riot Teleport redesign](https://www.leagueoflegends.com/en-au/news/game-updates/patch-25-s1-1-notes/)

**11. Split push with a synchronized four-player group**

- **Trigger:** Top can pressure a side defender while teammates can threaten elsewhere at the same time.
- **Information:** Duel outcome, enemy catch tools, collapse routes, wave arrival timing, structure state, and whether the four can survive without top.
- **Sequence:** Synchronize pressure → expose only as far as vision and escape allow → force a response → report who responds → have the four advance or take a concrete opportunity → retreat before the collapse closes.
- **Counterexample:** Pushing while the other four are shopping creates an isolated target. Drawing two enemies is not valuable if top dies before teammates can act.
- **API:** P/E confirm resulting losses/gains; pressure synchronization is unknown.

When ahead, keep the defender occupied without gambling the shutdown. When behind, collect safe waves and threaten only where the opponent’s response is genuinely costly. Neither state automatically dictates grouping.

**12. Group and choose the fight job**

- **Trigger:** Side pressure no longer creates leverage, a decisive fight is imminent, or top’s utility is essential.
- **Information:** Carry positions, engage range, flank route, enemy disengage, allied follow-up, and whether top is needed for peel.
- **Sequence:** Prepare side wave → reset early enough to arrive → choose front line, flank, secondary engage, or peel → name the target/trigger → act when allies can follow → reassess after the first cooldown exchange.
- **Counterexample:** Diving the enemy carry can abandon your fed ADC to an assassin. Waiting indefinitely for a perfect flank can let the fight finish without you.
- **API:** P/A establish broad strength; positioning and follow-up are unknown.

A behind top can still decide the fight by stopping one diver or zoning one entrance. A fed top should not assume every fight requires a solo backline dive.

**13. Defend a siege or an enemy split push**

- **Trigger:** Multiple waves approach structures, Baron pressure develops, or a side opponent threatens an inhibitor.
- **Information:** Wave arrival order, defender waveclear, enemy dive tools, safe movement between lanes, and who can hold the split pusher.
- **Sequence:** Assign defenders before waves arrive → put safe waveclear against the main siege → let top screen divers or match the side threat as appropriate → clear safely → concede an indefensible outer structure early → reassess after the wave dies.
- **Counterexample:** Sending the losing duelist alone to “match top” can donate both a kill and inhibitor. Sending everyone after the splitter can expose the other lane.
- **API:** P/E establish deaths/structure events; current siege geometry is unknown.

Top may need help clearing one wave, rather than permanent company. State that distinction so mid and support can leave again promptly.

**Interactions with all four teammates**

| Partner | Top supplies | Partner supplies | Useful agreement |
|---|---|---|---|
| Jungle | Crash/bounce forecast, trade conditions, danger deadline | Route intention, cover availability, contest choice | “Cover this crash, then leave”; distinguish cover, freeze-break, gank and dive. |
| Mid | Top opponent’s movement and side-lane needs | Enemy-mid movement, river access, alternative side assignment | Name which solo laner catches each wave and which reaches the fight first. |
| ADC | Space to damage, peel commitment, side pressure timing | Purchase/reset timing, ability to hold the central lane | ADC does not step forward while top’s pressure is still preparing. |
| Support | Flank requirements and dangerous collapse routes | Vision escort, arrival target, disengage readiness | Support and top establish the route before top commits to it. |

Keep communications to **state → action → limit**. For example: “Wave coming into me; holding until your reset; leaving if support disappears.” Use “confirmed,” “likely,” and “unknown” explicitly when the distinction changes risk.

**Six concrete voice calls, approximately ten seconds each**

These assume the stated situation has been reported or seen.

1. “You hit two first. Take the short trade after that melee dies; stop before their level-up. Keep your escape.”
2. “Wave’s frozen against you. Jungle, escort the crash only. Top, save health; both leave as soon as it reaches tower.”
3. “They’re stacking for a dive. Give the tower now, retreat toward second. Bot, take the free wave; don’t force.”
4. “Top, crash and buy. Mid holds center. Jungle waits for your return before entering their upper jungle.”
5. “Top pressures bot on our next mid wave. Four hold distance. If two show bot, advance; top exits immediately.”
6. “No safe flank target. Top, walk in and peel our ADC. Support holds engage until their diver commits.”

**Six failure cases and misleading heuristics**

1. **“Always freeze when ahead.”** You may deny one opponent while surrendering river access, a reset, and useful pressure elsewhere.
2. **“Always crash wave three and recall.”** Without control and a completed crash, this can hand the opponent a freeze.
3. **“Weak side means never ask for help.”** A brief escort or anti-dive appearance can prevent a much larger loss.
4. **“Teleport up means the four can fight.”** The target, departure safety, arrival delay and resulting position can all fail.
5. **“Two enemies came for me, so the split worked.”** Their time matters only if teammates can exploit it and the total exchange is favorable.
6. **“Use January’s 2026 quest guide.”** It misses April’s progression/XP changes, June’s shorter shield, and September’s Teleport cooldown buffs.

**Source list**

Official mechanics and documentation:

- [Riot 2026 patch schedule](https://support.riotgames.com/en-us/league-of-legends/gameplay/patch-schedule-league-of-legends)
- [Patch 26.1: quests, turrets, vision](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/)
- [Patch 26.9: progression and XP revision](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-9-notes/)
- [Patch 26.12: Teleport shield revision](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-12-notes/)
- [Patch 26.19: top Teleport cooldowns](https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-26-19-notes/)
- [Patch 25.S1.1: Teleport travel redesign](https://www.leagueoflegends.com/en-au/news/game-updates/patch-25-s1-1-notes/)
- [Riot Live Client Data documentation](https://developer.riotgames.com/docs/lol)
- [Riot example payload](https://static.developer.riotgames.com/docs/lol/liveclientdata_sample.json)

Professional testimony:

- [Odoamne on vision and top–jungle coordination, 2021](https://www.invenglobal.com/articles/15502/the-top-lane-gap-at-worlds-2021)
- [Odoamne on weak-side opportunities, 2022](https://www.invenglobal.com/articles/16313/odoamne-now-we-have-the-tools-to-not-go-0-3-in-playoffs-like-the-meme-is)
- [Bwipo on converting carry resources, 2022](https://teamliquid.com/news/2022/01/28/bwipo-creativity-consistency)
- [UmTi on Morgan’s defense and fight selection](https://teamliquid.com/articles/team-liquid-morgan-umti)

**Research gaps**

- No match footage was inspected; this is not a VOD review or measurement of professional execution.
- Current champion-specific trading sequences, damage thresholds and exact wave/level counts need validation for the stack’s actual pool.
- The cited changes establish a patch-note baseline, not an exhaustive audit of every intervening hotfix.
- Live-client representation of the extra quest Teleport, quest completion, and cooldown modifiers remains untested.
- Exact Faelight coverage, turret thresholds and travel times should be confirmed for the current map state before turning them into automatic calls.
- Professional testimony supports coordination principles, but much of it predates 2026. It should not be treated as proof of today’s best champion picks or lane assignments.