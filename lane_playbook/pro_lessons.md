# Pro lessons

Where this comes from: a CC0 Kaggle dataset of machine-transcribed English broadcasts of Worlds 2025 (speech-to-text of the commentary, 84 games, kept in transcripts\).
Each lesson is a principle paraphrased in our own words and checked against the passage named in its Source line. No commentary is copied here, and no player or team is named in the lesson text. The Source lines are the exception: they give transcript file names, which contain team abbreviations, and a video offset; they are reader notes and are not sent to the ranker.
These are background for ranking the coach's options. They are not observations of the current match, they are never spoken as a play, and five-player coordination often does not carry over to solo queue.

Format: a title line, then Roles (top, jungle, mid, bot, support, or all), Phase (early, lane, mid, late, or any), When (situation tags the coach can observe, or any), Situation, Our side, Their side, Player check and Seen in.
Only those lines are sent to the ranker. The Principle, Feed signal and Source lines sit below a blank line as notes for the reader; keep that blank line, or they fold into the line above.
Source is game_file@seconds: a file in transcripts\games\ without .csv, and the video offset of the passage, which is not the game clock.
To make one of these a plan you can pick, copy it into lessons.md with an Offer at line.

## Gank when your camps are down
Roles: jungle
Phase: early, lane
When: any
Situation: Your clear is finished and nothing on your side has respawned yet.
Our side: A gank now costs no camps; a kill can become the objective beside that lane before camps return.
Their side: A jungler with nothing to farm is the likeliest visitor, so the fragile lane steps back.
Player check: Are your camps really all down, and can that lane's target be reached?
Seen in: 2 games

Principle: The cheapest time to leave the jungle is when nothing is left in it to farm.
Feed signal: Game time against the first-clear and respawn rhythm; your level and CS showing a finished clear.
Source: cfo_vs_al_worlds_2025_swiss_game_01_ctbc_61@866; gen_vs_t1_worlds_2025_swiss_game_01_gen__57@1122

## An early gank is paid for in camps
Roles: jungle
Phase: early
When: any
Situation: You cut the first clear short to gank a side lane.
Our side: You may get a kill or a Flash, but the untouched half of your jungle and the far river are open.
Their side: Their jungler takes the far crab, your far camps or a re-clear, more so if their mid has push.
Player check: Which camps did you skip, is your mid pushed in, and is that laner worth it?
Seen in: 2 games

Principle: A short-clear gank is an investment; decide beforehand what happens to the camps you skipped.
Feed signal: An early kill or assist on the jungler while their CS is below the enemy jungler's.
Source: kt_vs_t1_worlds_2025_grand_final_game_5__0@556; al_vs_t1_worlds_2025_quarterfinals_game__15@585

## Time in their jungle is time given away
Roles: jungle
Phase: early, lane
When: any
Situation: You invade or hover one half of the map for a long stretch in the first clears.
Our side: A stolen buff or camp is possible, but a failed steal leaves you late to your own camps.
Their side: Their jungler knows where you are and has free time on the far side and its lane.
Player check: Which of your camps are up, and was your far-side laner warned?
Seen in: 2 games

Principle: An invade trades time, not only risk; the opposite half is uncovered while you are there.
Feed signal: Jungle CS falling behind the enemy jungler's with no kill or assist to explain it.
Source: hle_vs_psg_worlds_2025_swiss_stage_game__64@703; t1_vs_tes_worlds_2025_semifinals_game_1__7@665

## An invade ends when the nearest lane arrives
Roles: jungle, support
Phase: early, lane
When: ahead, after_kill
Situation: You won the first exchange in their jungle and want to stay for more.
Our side: Leave with the camp and the health lead; the second exchange goes to whoever gets help first.
Their side: A laner who shoved first arrives before yours and takes the kill for a few minions.
Player check: Is their nearest laner missing or shoved in, and can yours follow?
Seen in: 2 games

Principle: Invades are decided by which adjacent lane can move, not by the two junglers.
Feed signal: An early level, item or kill lead over the enemy jungler.
Source: psg_vs_vks_worlds_2025_swiss_game_02_psg_50@597; psg_vs_vks_worlds_2025_swiss_game_03_psg_49@752

## The jungle beside a losing lane is theirs
Roles: jungle
Phase: early, lane
When: any
Situation: A side lane of yours is pushed in and their jungler duels better early.
Our side: Path away and take the half where your laners can move; you give camps but keep your life.
Their side: Their laners arrive first, so they hold that quadrant.
Player check: Is that wave under your tower now, and where was their jungler last seen?
Seen in: 2 games

Principle: Lane priority decides which half of the jungle is safe; do not mirror a stronger early jungler.
Feed signal: A lane ally trailing in CS early; the enemy jungler ahead on level or kills.
Source: t1_vs_tes_worlds_2025_semifinals_game_3__5@1027; cfo_vs_fly_worlds_2025_swiss_game_2_ctbc_33@620

## A jungler who is behind has few places to go
Roles: jungle
Phase: early, lane
When: ahead, behind, enemy_jungler_dead, after_kill
Situation: One jungler lost camps or died early and is short of safe farm.
Our side: Ahead, stand at the one camp or crab he can still reach before returning to your own.
Their side: Behind, the obvious enemy camp is the expected one; own camps or lane cover are safer.
Player check: Which camps and crab can the trailing jungler still reach, and who has push there?
Seen in: 2 games

Principle: A trailing jungler's next move is predictable, and that cuts both ways.
Feed signal: A clear level and CS gap between the junglers; an early kill involving a jungler.
Source: cfo_vs_hle_worlds_2025_swiss_game_2_ctbc_47@813; psg_vs_vks_worlds_2025_swiss_game_02_psg_50@718

## End the clear beside the lane that matters
Roles: jungle
Phase: early, lane
When: any
Situation: Your team needs one lane ahead and you are about to clear and recall.
Our side: After a recall you return to the camps cleared first, so plan to come back beside that lane.
Their side: A jungler who clears that side and recalls is pulled away from it.
Player check: Which camps are up, and does the next clear lead toward that lane?
Seen in: 1 game

Principle: Where your next camps are decides which lane you can help for the following minute.
Feed signal: A jungler item change after a recall around the second clear; a CS gap growing in the lane to play for.
Source: t1_vs_tes_worlds_2025_semifinals_game_3__5@573

## Hovering a play that never starts costs the next clear
Roles: jungle
Phase: early, lane
When: any
Situation: You wait near a lane for a dive or gank and their cover arrives first.
Our side: Leave early, recall and restart at the camp that returns first.
Their side: The jungler already on his camps as they return is also first to the next river fight.
Player check: Has their cover arrived, is the wave still right, and which camp is back?
Seen in: 1 game

Principle: Set a short limit on waiting for a play; seconds spent hovering come out of camp respawns.
Feed signal: Jungle CS falling behind between clears with no kill or assist to show for it.
Source: cfo_vs_fly_worlds_2025_swiss_game_1_ctbc_34@758

## Stop repeating a gank that keeps failing
Roles: jungle
Phase: lane, mid
When: after_death, behind
Situation: You ganked one lane more than once and the target reached his tower each time.
Our side: Another lane or your camps is the better use of time, unless the last try burned his Flash.
Their side: A safe champion near his tower turns each attempt into lost tempo or a kill for him.
Player check: Did the last gank force Flash or an ultimate, and where is the wave?
Seen in: 1 game

Principle: Sound reasoning for a gank does not make it work on a champion that is safe near his tower.
Feed signal: Kill events showing you dying to the same champion; deaths rising while CS falls behind.
Source: tes_vs_blg_worlds_2025_swiss_game_2_tope_31@1078

## Without Flash, a farming jungler clears it back
Roles: jungle
Phase: early
When: any
Situation: A jungler lost Flash in the first minutes.
Our side: If it is you, about two full clears cover most of the cooldown; ganks and invades wait.
Their side: If it is theirs, those minutes are the turn to invade or gank; farming too hands it back.
Player check: Was Flash really used and when, and does your champion need it to gank?
Seen in: 1 game

Principle: An early lost Flash removes play-making for a few minutes; farming junglers lose the least.
Feed signal: Game time since an early skirmish; champion types from the champion list.
Source: kt_vs_t1_worlds_2025_grand_final_game_4__1@486

## Take the crab on the side where your lanes can move
Roles: jungle, mid, support
Phase: early
When: any
Situation: Both junglers are heading to river as the first clears end.
Our side: Contest where your nearest lanes have push; otherwise cross and take the other crab.
Their side: The side with push brings a second and third body and wins the crab or a kill.
Player check: Which mid and side waves are pushed, and who is already walking to river?
Seen in: 2 games

Principle: Early river fights are decided by which lanes arrive, so an even swap of crabs is a fine result.
Feed signal: Game time near the first crab spawn; lane CS and level hint at who is winning, not at wave position.
Source: fly_vs_t1_worlds_2025_swiss_stage_game_0_75@669; kt_vs_t1_worlds_2025_grand_final_game_1__4@731

## A fast clear and recall brings an item to the river
Roles: jungle
Phase: early
When: any
Situation: One jungler finishes the first clear early and recalls before heading to river.
Our side: Back with an item, he can trade crabs safely or look for the duel at the crab.
Their side: The slower jungler can decline, leave that side and take the other crab or camps.
Player check: Is your clear done, which side is their jungler on, and is a crab alive?
Seen in: 2 games

Principle: An item component at the first river meeting is an edge, and the other jungler need not accept the duel.
Feed signal: The enemy jungler showing an extra item component and higher CS at the same game time.
Source: kt_vs_tes_worlds_2025_swiss_game_02_kt_r_62@504; kt_vs_t1_worlds_2025_grand_final_game_3__2@576

## A crab can be the level that wins the skirmish
Roles: jungle, mid, top
Phase: early, lane
When: any
Situation: A skirmish forms around a river crab with players a step from level 6.
Our side: Keep hitting the crab if its experience would finish your level; an ultimate can decide it.
Their side: They zone your jungler off it, at the cost of abilities spent away from the fight.
Player check: Is the crab alive, would it level you, and who has an ultimate?
Seen in: 1 game

Principle: A neutral monster in the middle of a fight is also experience, and the level it gives can be the fight.
Feed signal: Junglers and solo laners at level 5; a level change to 6 during a cluster of kill events.
Source: gen_vs_psg_worlds_2025_swiss_stage_game__72@765

## Skipping the recall keeps camp pace but not power
Roles: jungle
Phase: early, lane
When: gold_ready, ahead
Situation: You stay out after a clear or a kill while their jungler has recalled and bought.
Our side: You keep pace on camps by taking the first one to respawn, but fight on old items.
Their side: The jungler who bought picks the next gank or skirmish while your gold is unspent.
Player check: How much unspent gold do you hold, and is a camp about to return?
Seen in: 2 games

Principle: Staying out trades item power for camp tempo; a lead only counts once it is spent.
Feed signal: The active player's gold high with an unchanged item list; the enemy jungler's items changing.
Source: mkoi_vs_tsw_worlds_2025_swiss_game_2_mov_42@665; fly_vs_g2_worlds_2025_swiss_game_1_flyqu_46@711

## A jungler missing from where he should be is information
Roles: top, mid, bot, support
Phase: early, lane
When: any
Situation: Their jungler has not shown at the camp or crab where his path should put him.
Our side: Treat him as unseen and pull an extended lane back; it costs a few minions.
Their side: He gains surprise by breaking his route, and loses tempo if nobody is there.
Player check: Is there a ward where he should be, and when and where was he last seen?
Seen in: 2 games

Principle: Your own jungler's position says nothing about theirs; an absence on a ward is a warning.
Feed signal: Game time against the usual first-clear route; enemy jungler CS low for the time.
Source: t1_vs_tes_worlds_2025_semifinals_game_2__6@576; gen_vs_kt_worlds_2025_semifinals_game_2__10@666

## A jungler seen on the far side opens yours
Roles: jungle, top, mid, bot
Phase: early, lane
When: any
Situation: Their jungler has just been seen committing to the other half of the map.
Our side: The lane he left can trade or push, and a gank there has no counter-gank behind it.
Their side: He takes the crab or camp he went for and gives up pressure on the side he left.
Player check: Was he actually seen, how long ago, and can your wave still be left safely?
Seen in: 2 games

Principle: A confirmed sighting is a short window; it expires as fast as he can walk back.
Feed signal: Game time in the first clear window; junglers at similar level and CS suggest similar clear speed.
Source: al_vs_t1_worlds_2025_quarterfinals_game__12@576; fly_vs_g2_worlds_2025_swiss_game_2_flyqu_45@836

## A lane that fights early without a ward invites a short clear
Roles: jungle, bot, support
Phase: early
When: any
Situation: A duo lane traded hard at levels 1 and 2, spent summoners and kept pushing.
Our side: As jungler, a two-camp clear into that lane finds a long lane with no escapes.
Their side: The aggressive lane keeps its lead only by warding the gank path after.
Player check: Were summoners used, are they past the middle, and did a ward go down?
Seen in: 1 game

Principle: Early aggression has to be paid for with vision, or one visit takes everything back.
Feed signal: Game time in the first minutes; bot laners still level 1 or 2.
Source: blg_vs_fnc_worlds_2025_swiss_stage_game__65@521

## The lane without help gives nothing
Roles: top, bot, support
Phase: early, lane, mid
When: any
Situation: Your jungler and mid are making a play or taking an objective on the far side.
Our side: Hold the wave near your tower; skip the even trade and the last plate.
Their side: Their jungler's only useful move is your lane; if nobody contests far away, expect a dive.
Player check: Where are your jungler and mid, and is their jungler missing?
Seen in: 4 games

Principle: When the team plays the other side, the weak-side lane's job is to give nothing back.
Feed signal: An objective or kill event on the far side followed by an ally death in the opposite lane.
Source: mkoi_vs_tsw_worlds_2025_swiss_game_3_mov_41@826; gen_vs_kt_worlds_2025_semifinals_game_3__9@873; psg_vs_vks_worlds_2025_swiss_game_01_psg_51@971; gen_vs_kt_worlds_2025_semifinals_game_1__11@1211

## A dive runs on minions and one defensive button
Roles: top, bot, support, jungle
Phase: early, lane
When: any
Situation: Several players are set to dive a laner under his tower.
Our side: Diving, wait out the block or dodge, and go only when other enemies are accounted for.
Their side: Defending, clear the minions so the tower turns on the divers, then hold one in range.
Player check: Is the defensive ability down, how many minions tank the tower, and who is missing?
Seen in: 3 games

Principle: Divers have the time; the defender wins by removing the wave or holding his key ability.
Feed signal: Not in the feed beyond champion names, which hint at who has a block or dodge.
Source: gen_vs_tes_worlds_2025_swiss_game_1_gen__40@1069; tes_vs_blg_worlds_2025_swiss_game_3_tope_30@1017; hle_vs_100t_worlds_2025_swiss_game_01_ha_55@657

## Early on, a level is worth more than a little gold
Roles: all
Phase: early, lane
When: any
Situation: Before first items, one side has a level lead and the other a small gold lead.
Our side: A level is stats now and sometimes an ability rank; take early fights when you hold it.
Their side: Gold only counts once it finishes an item, so they delay until it does.
Player check: Is anyone about to level, and has their carry based since the gold?
Seen in: 2 games

Principle: Respect a level lead in early fights unless the gold has just become a completed item.
Feed signal: Level difference between matched players, supports included; a newly completed item.
Source: cfo_vs_fly_worlds_2025_swiss_game_1_ctbc_34@2266; hle_vs_al_worlds_2025_swiss_stage_game_0_74@644

## Kills are not a lead if the farm went the other way
Roles: top, mid, bot
Phase: early, lane
When: after_kill, after_death
Situation: A lane traded kills, or the killer had to recall as a wave crashed.
Our side: Judge the lane by CS and items; a kill that costs you a stacked wave can leave you behind.
Their side: The player who died stays level by collecting every wave while the killer is away.
Player check: Where is the wave, how big is it, and can you stay to collect it?
Seen in: 2 games

Principle: Count minions and items, not the kill column, before calling a lane won or lost.
Feed signal: K/D/A compared with CS for the two players in a lane; who completed an item first.
Source: gen_vs_hle_worlds_2025_quarterfinals_gam_26@865; al_vs_t1_worlds_2025_quarterfinals_game__12@627

## Their jungler or carry in base is your window
Roles: jungle, mid, support
Phase: lane, mid
When: any
Situation: Their jungler or main carry just recalled while yours stayed out.
Our side: Force the nearby fight or start the objective at once; the numbers edge lasts seconds.
Their side: The side that recalled returns with items, so its laners must back off until then.
Player check: Did you see the recall or is it a guess, and is your own jungler still near?
Seen in: 3 games

Principle: A recall is a short numbers advantage for the other team; staggered recalls before a spawn give it away.
Feed signal: An enemy item list changing, with a kill or objective event shortly after.
Source: ig_vs_t1_worlds_2025_play_ins_game_01_in_83@819; t1_vs_tes_worlds_2025_semifinals_game_1__7@1278; fly_vs_tsw_worlds_2025_swiss_game_01_fly_58@1088

## Before a spawn, arrive alive and on time
Roles: jungle, support, top
Phase: lane, mid, late
When: objective_soon
Situation: An objective spawns within a minute and a risky kill, ward or wave is on offer.
Our side: Skip the coin flip, recall early and walk in together; you give up a little gold.
Their side: One death, a late recall or a jungler low from tower shots hands it to them.
Player check: How long until the spawn, who is low or in base, and where is their jungler?
Seen in: 4 games

Principle: A death or a late base just before a spawn costs the whole objective, not only the kill.
Feed signal: Game time close to a known spawn; an ally death, especially jungler or support, in that window.
Source: mkoi_vs_fnc_worlds_2025_swiss_game_03_mo_52@1263; tes_vs_g2_worlds_2025_quarterfinals_game_19@1799; kt_vs_mkoi_worlds_2025_swiss_stage_game__77@760; gen_vs_kt_worlds_2025_semifinals_game_2__10@1083

## The lane that pushes first moves first
Roles: mid, bot, top, support
Phase: lane, mid
When: objective_soon
Situation: An objective is about to spawn and nearby lanes are still fighting over waves.
Our side: Shove before the spawn and walk over as a group; it can cost a plate behind you.
Their side: The side still under its wave loses minions or arrives late and blind, the long way round.
Player check: Is your wave pushed, who clears mid fastest, and what do you lose behind?
Seen in: 3 games

Principle: Priority at an objective is made by wave clear half a minute earlier, not by winning duels.
Feed signal: Game time before a spawn; champion names show wave-clear carries; laner CS dropping near timers.
Source: cfo_vs_al_worlds_2025_swiss_game_01_ctbc_61@959; hle_vs_psg_worlds_2025_swiss_stage_game__64@1544; mkoi_vs_t1_worlds_2025_swiss_game_2_movi_28@1567

## A low or dead enemy mid makes the river yours
Roles: jungle, mid, support
Phase: lane
When: after_kill, numbers_up, enemy_death_window, objective_soon
Situation: Their mid laner was just killed or chunked out of lane while an objective is up.
Our side: Start it now; nobody on their side can rotate first, even if they see it.
Their side: They concede it rather than walk in at half health, and look to the other side.
Player check: Is the objective up, where was their jungler last seen, and what spawns next?
Seen in: 2 games

Principle: A health gap or a death in mid is priority without a wave; convert it straight into the objective.
Feed signal: A kill event on the enemy mid with a dragon or grubs available; time to the next objective.
Source: fly_vs_g2_worlds_2025_swiss_game_1_flyqu_46@965; mkoi_vs_fnc_worlds_2025_swiss_game_01_mo_54@732

## Arrive together or do not arrive
Roles: jungle, support, bot
Phase: lane, mid
When: objective_soon, after_objective, numbers_down
Situation: The enemy is on an objective, or has just taken it, and your team is spread out.
Our side: Go as a group with a wave pushed, or give it; a lone jungler in first is locked down.
Their side: The grouped team can let the monster reset, wait for Smite and collapse on stragglers.
Player check: Can your laners leave their waves now, and is anything left to fight for there?
Seen in: 2 games

Principle: A late, piecemeal contest costs more than conceding: the jungler, a wave and often more kills.
Feed signal: An enemy objective event near a death of your jungler; several ally deaths right after it.
Source: kt_vs_cfo_worlds_2025_quarterfinals_game_22@814; 100t_vs_t1_worlds_2025_swiss_game_2_100__35@1846

## Count who can actually arrive before contesting
Roles: all
Phase: lane, mid
When: objective_soon
Situation: Your team is deciding whether to fight for a dragon or grubs.
Our side: Contest with waves pushed, equal arrival and your side laner able to come; otherwise give it.
Their side: A Teleport, a long-range ultimate or a wave pinning your laner flips the numbers.
Player check: Which lanes are pushing, who got to river first, and whose Teleport is up?
Seen in: 3 games

Principle: Health bars near the pit matter less than how many bodies each side can bring.
Feed signal: Summoner spell names show Teleport; champion names show global ultimates; item completions.
Source: kt_vs_cfo_worlds_2025_quarterfinals_game_23@624; fly_vs_g2_worlds_2025_swiss_game_2_flyqu_45@1042; hle_vs_al_worlds_2025_swiss_stage_game_0_74@917

## Do not fight an objective one spike behind
Roles: jungle, mid, bot
Phase: lane, mid
When: objective_soon, behind
Situation: An objective is starting and one side is a level 6 or an item short.
Our side: Behind the spike, give a dragon that is not soul point and take camps or waves instead.
Their side: Ahead of it, they start at once; delay closes the gap.
Player check: How far is each carry from the item, who is level 6, and is this their third dragon?
Seen in: 4 games

Principle: Fight objectives on finished items and ultimates; a conceded early dragon is cheaper than a lost fight.
Feed signal: Completed items and levels on each side, level 6 against 5; dragon kill counts.
Source: fly_vs_g2_worlds_2025_swiss_game_2_flyqu_45@1245; gen_vs_hle_worlds_2025_quarterfinals_gam_25@1296; gen_vs_tes_worlds_2025_swiss_game_1_gen__40@787; gen_vs_tes_worlds_2025_swiss_game_2_gen__39@1320

## Cooldowns spent before the objective decide it
Roles: all
Phase: lane, mid, late
When: objective_soon
Situation: An objective is a minute away and key Flashes or ultimates are being traded.
Our side: Make their engager or carry spend Flash, then start at once; with yours down, delay.
Their side: They keep the key player out of sight until it starts, giving up the area and vision.
Player check: Which Flashes and ultimates did you see used, and who is missing?
Seen in: 4 games

Principle: Use strength in the minute before the fight; an ultimate held too long or thrown for nothing both lose it.
Feed signal: Game time before a spawn; summoner spell names; item lists showing a dash item.
Source: cfo_vs_al_worlds_2025_swiss_game_01_ctbc_61@1765; blg_vs_vks_worlds_2025_swiss_game_1_bili_38@1561; t1_vs_tes_worlds_2025_semifinals_game_1__7@1632; gen_vs_hle_worlds_2025_quarterfinals_gam_24@1430

## A pushed side wave pulls a carry away from the pit
Roles: bot, mid, jungle, support
Phase: lane, mid
When: objective_soon
Situation: A dragon is near, your team lacks a key ultimate, but a far side wave can be pushed.
Our side: One player keeps shoving while the rest start; their fight is short a carry for a while.
Their side: They choose between losing the wave and tower damage or arriving late.
Player check: Which enemy went to the wave, how far is he, and is Smite ready?
Seen in: 1 game

Principle: A missing ultimate does not force a concession if a wave can split their damage away.
Feed signal: Game time near a dragon spawn; the rest is on the minimap, not in the feed.
Source: gen_vs_kt_worlds_2025_semifinals_game_1__11@1109

## If you cannot contest, take something elsewhere at once
Roles: all
Phase: lane, mid, late
When: objective_soon, after_objective, objective_swap, team_behind
Situation: The enemy has numbers and push at an objective or stacks one side.
Our side: Trade at once: a tower, plates, their camps or the other objective; give the stacked side.
Their side: They get what they came for; hovering nearby or arriving late hands them both.
Player check: How many enemies show, and what can you finish before they rotate?
Seen in: 8 games

Principle: Giving an objective is fine only if you are paid for it; start the trade when they start theirs.
Feed signal: An enemy objective event with no tower or objective event for your team in the next minute.
Source: al_vs_t1_worlds_2025_quarterfinals_game__16@883; 100t_vs_t1_worlds_2025_swiss_game_2_100__35@1328; blg_vs_fnc_worlds_2025_swiss_stage_game__65@1699; blg_vs_vks_worlds_2025_swiss_game_1_bili_38@1354; mkoi_vs_tsw_worlds_2025_swiss_game_1_mov_43@1154; gen_vs_al_worlds_2025_swiss_stage_game_0_66@1375; tes_vs_g2_worlds_2025_quarterfinals_game_19@1178; al_vs_t1_worlds_2025_quarterfinals_game__12@1280

## A trade needs something real to take
Roles: jungle, top, mid
Phase: lane, mid
When: objective_soon, split_pressure
Situation: You plan a cross-map answer or a deep split push while the enemy groups.
Our side: Check that an objective or tower of similar size is actually available to your team.
Their side: If nothing is, they lose nothing by taking theirs or sending everyone at the split pusher.
Player check: Is the far objective up, can a tower be reached, and how many enemies show?
Seen in: 2 games

Principle: A camp or two does not match a dragon; with nothing to trade, stop at a safe point.
Feed signal: Game time against objective spawn times; outer towers still standing; a solo death with no trade.
Source: kt_vs_tes_worlds_2025_swiss_game_01_kt_r_63@753; cfo_vs_hle_worlds_2025_swiss_game_2_ctbc_47@1891

## Count what the map pays for a dive or collapse
Roles: jungle, top, support
Phase: lane, mid
When: after_kill, objective_soon
Situation: Several of you commit to one target while waves, plates or a dragon are open.
Our side: You may get the kill, but you need more than a burned Flash to come out ahead.
Their side: The rest of their team takes the dragon, plates or towers and can lead in gold.
Player check: Is a dragon up, where are the other waves, and will the target die or only Flash?
Seen in: 2 games

Principle: A dive that kills its target can still lose the exchange; price the other lanes first.
Feed signal: Kill events for one team with dragon or tower events for the other in the same minute.
Source: 100t_vs_t1_worlds_2025_swiss_game_1_100__36@1095; tes_vs_blg_worlds_2025_swiss_game_2_tope_31@1547

## Price grubs against plates and waves
Roles: jungle, top, bot
Phase: lane
When: objective_soon
Situation: Grubs are up and a laner must leave a side lane to join.
Our side: Take what is free and send the carry back to the wave; grubs pay only if you reach towers.
Their side: The laner who stays takes plates and may nearly solo the tower.
Player check: Who has Teleport, where is each wave, and did their carry stay in lane?
Seen in: 4 games

Principle: A partial take is a fine result; the cost of grubs is the waves and plates bleeding elsewhere.
Feed signal: Game time near the grub spawn; Teleport in summoner spells; CS dropping for laners who left.
Source: tes_vs_g2_worlds_2025_quarterfinals_game_17@903; g2_vs_tes_worlds_2025_swiss_stage_game_0_73@871; blg_vs_vks_worlds_2025_swiss_game_2_bili_37@896; cfo_vs_fly_worlds_2025_swiss_game_2_ctbc_33@1289

## Early dragons are the clock against a scaling team
Roles: jungle, bot, support, mid
Phase: lane, mid
When: team_ahead, ahead
Situation: Your team is stronger now and theirs wants a quiet game until items arrive.
Our side: Stack dragons so they must fight before they are ready; kills alone are a thin lead.
Their side: They concede one or two and farm, then need one good objective fight.
Player check: How many dragons has each side, and are vision and wave push set before you go?
Seen in: 2 games

Principle: A kill lead counts once it becomes dragons, towers or an item gap.
Feed signal: Kill score against dragon and tower events; item counts on their scaling carries.
Source: mkoi_vs_fnc_worlds_2025_swiss_game_02_mo_53@1126; tes_vs_blg_worlds_2025_swiss_game_1_tope_32@1014

## Give early dragons, then fight the one before soul point
Roles: all
Phase: lane, mid
When: team_behind, behind, objective_soon
Situation: You are behind or scaling and the enemy has taken the first dragons.
Our side: Collect waves and items, then plan recalls and Teleports around the soul-point dragon.
Their side: They bank stacks but must keep forcing towers, or your items arrive.
Player check: Is the next dragon their soul point, and how far are your carries from an item?
Seen in: 3 games

Principle: Conceded dragons buy time only until soul point; that one fight can be worth a jungler's life for a steal.
Feed signal: Dragon kill counts; item counts on your carries; turret events.
Source: fly_vs_g2_worlds_2025_swiss_game_1_flyqu_46@1799; mkoi_vs_tsw_worlds_2025_swiss_game_2_mov_42@1565; tes_vs_blg_worlds_2025_swiss_game_3_tope_30@1505

## Herald in mid before a dragon buys the river
Roles: jungle, mid
Phase: lane, mid
When: objective_soon
Situation: Your team holds Herald and a dragon spawns soon.
Our side: Drop it mid just before the spawn; it hits the tower and makes them answer in two places.
Their side: They stop the charge and arrive second at the dragon, or keep the dragon and lose the tower.
Player check: Do you still hold it, will the mid wave carry it, and can they kill it first?
Seen in: 2 games

Principle: Herald's second use is priority: a problem in mid loosens their hold on the river.
Feed signal: A Herald kill event for your team with a dragon due in a minute or two.
Source: cfo_vs_al_worlds_2025_swiss_game_02_ctbc_60@1460; al_vs_t1_worlds_2025_quarterfinals_game__14@1472

## Outer towers are vision
Roles: jungle, mid, support
Phase: mid, late
When: tower_down
Situation: A mid or last outer tower has just fallen.
Our side: Breaking theirs shrinks the dark space their roamers use and opens the next objective.
Their side: The side without outer towers reaches the pit only by face-checking, or trades elsewhere.
Player check: Which brushes on the way to the pit are warded, and which tower is nearest the next objective?
Seen in: 2 games

Principle: Towers hold the approaches; take the one nearest the next objective before it spawns.
Feed signal: Tower kill events, three outer towers lost on one side; the next dragon's timing.
Source: cfo_vs_al_worlds_2025_swiss_game_03_ctbc_59@1630; cfo_vs_fly_worlds_2025_swiss_game_1_ctbc_34@2630

## Teleport decides who has the extra player
Roles: top, mid, jungle
Phase: mid, late
When: objective_soon
Situation: Side laners are split and an objective is spawning on the other side.
Our side: With the only Teleport up, fight for vision there now; without it, give ground.
Their side: A Teleport spent saving a tower that falls anyway is missing at the next dragon.
Player check: Whose Teleport is up, will yours be back by the spawn, and can the tower really be held?
Seen in: 2 games

Principle: Check the objective timer before teleporting defensively; a cooldown lead is one side's window.
Feed signal: Summoner spell names show Teleport; a tower under attack shortly before a dragon spawn.
Source: ig_vs_t1_worlds_2025_play_ins_game_01_in_83@1576; kt_vs_t1_worlds_2025_grand_final_game_1__4@1484

## Who starts the objective depends on who wants to be pinned
Roles: jungle, support, mid
Phase: mid, late
When: objective_soon
Situation: A poke team faces an engage team at dragon or Baron.
Our side: With poke, arrive first and let them start it; started in a choke, you are the clumped target.
Their side: The engage team parks on it with deep wards so the poke side must commit early.
Player check: Which team is there first, where are the flanks, and are they warded?
Seen in: 2 games

Principle: A team hitting an objective is stuck in a small space; choose which team that suits.
Feed signal: Champion picks on each team; time to the next dragon or Baron.
Source: gen_vs_hle_worlds_2025_quarterfinals_gam_26@1055; kt_vs_cfo_worlds_2025_quarterfinals_game_21@1542

## A dead jungler makes the objective free
Roles: all
Phase: lane, mid, late
When: enemy_jungler_dead
Situation: Their jungler is dead or far from the pit and an objective is up or close.
Our side: Drop the chase and start it at once; they have no reliable last hit.
Their side: Without Smite they clear waves and defend rather than walk in for a steal.
Player check: Is the objective up, does the respawn outlast the take, and can anyone else steal it?
Seen in: 4 games

Principle: The kill that matters most near an objective is the jungler; late on, the first jungler back owns it.
Feed signal: The enemy jungler dead with a respawn timer; game time near a dragon or Baron window.
Source: al_vs_t1_worlds_2025_quarterfinals_game__13@2347; al_vs_t1_worlds_2025_quarterfinals_game__14@826; fly_vs_g2_worlds_2025_swiss_game_3_flyqu_44@1813; gen_vs_kt_worlds_2025_semifinals_game_1__11@2479

## If you cannot win the Smite duel, remove their jungler
Roles: jungle, support, top
Phase: mid, late
When: objective_soon, baron_setup
Situation: You contest a major objective against a jungler who bursts monsters harder than you.
Our side: Put crowd control and zoning on him so he is out of range when it gets low.
Their side: They keep more players alive and may win the fight after losing the buff.
Player check: Which jungler has more burst on the monster, and is his Flash up?
Seen in: 1 game

Principle: Change a losing Smite contest into a zoning contest on one player.
Feed signal: Champion names of both junglers; nothing else about it is in the feed.
Source: ig_vs_t1_worlds_2025_play_ins_game_01_in_83@1758

## After a won fight, the waves decide whether you got paid
Roles: all
Phase: mid, late
When: after_kill, numbers_up, enemy_death_window
Situation: Your team just won a skirmish and the survivors are escaping.
Our side: One player leaves early for the crashing side wave; the rest take a structure.
Their side: If you all chase, they respawn onto waves pushed into your towers and have lost little.
Player check: Where are the side waves, and how long are their death timers?
Seen in: 2 games

Principle: Kills matter only when they become a tower, an objective or a clean reset.
Feed signal: Kill events for your team with no tower or objective event in the following minute.
Source: cfo_vs_hle_worlds_2025_swiss_game_1_ctbc_48@1786; cfo_vs_hle_worlds_2025_swiss_game_2_ctbc_47@1378

## A lead is not power until it is spent
Roles: all
Phase: mid, late
When: gold_ready, team_ahead, after_objective
Situation: Your team is ahead in gold but carrying it unspent or in unfinished components.
Our side: Recall, buy and line up the waves before a siege or a risky pit fight.
Their side: Against old items the defenders get a real chance to hold while the buff runs down.
Player check: How much unspent gold do you and your carries hold, and how long is left on the buff?
Seen in: 2 games

Principle: The real item gap can be far smaller than the gold gap; with soul point in hand there is no need to flip.
Feed signal: The active player's gold very high after a Baron event; item lists showing components only.
Source: kt_vs_cfo_worlds_2025_quarterfinals_game_23@1802; gen_vs_kt_worlds_2025_semifinals_game_3__9@1660

## When ahead, let them come to you
Roles: all
Phase: mid, late
When: team_ahead
Situation: You hold a clear lead and see one more kill deep in their jungle or under a tower.
Our side: Hold vision and waves; the kill is optional and the lead is not.
Their side: One death, a deep chase without ultimates or a bite on bait is their way back.
Player check: Are your main ultimates up, is Baron alive, and is the target really alone?
Seen in: 3 games

Principle: The safe play for a team far ahead is also the strong one; a greedy dive is the comeback route.
Feed signal: A large kill and item lead followed by several deaths on the leading team; Baron alive.
Source: ig_vs_t1_worlds_2025_play_ins_game_01_in_83@2204; al_vs_t1_worlds_2025_quarterfinals_game__15@1775; kt_vs_mkoi_worlds_2025_swiss_stage_game__77@1610

## With a lead, Baron is bait before it is a prize
Roles: all
Phase: late
When: team_ahead, baron_setup
Situation: You are ahead, Baron is up and their jungler is alive with Smite.
Our side: Start it to draw them through dark jungle, then drop it and fight or take what they left.
Their side: They would rather stall; a steal or a lucky face-check is their hope.
Player check: Is the pit warded, where is their jungler, and who on your team is isolated?
Seen in: 2 games

Principle: Do not turn a won game into a Smite coin flip; finish Baron after a pick.
Feed signal: Game time past Baron spawn; the enemy jungler alive; your team ahead on kills and towers.
Source: kt_vs_t1_worlds_2025_grand_final_game_5__0@1873; cfo_vs_t1_worlds_2025_swiss_stage_game_0_67@2018

## A second objective moves the fight
Roles: jungle, mid, support
Phase: mid, late
When: objective_soon, after_death, numbers_down
Situation: Dragon and Baron are both in play and one team starts the one the other was not watching.
Our side: Starting Baron stalls their dragon and spreads their vision; be ready to drop it.
Their side: They can call the bluff: if it is slow, they finish their own objective first.
Player check: Is there a ward on it, how fast can they kill it, and where are the side waves?
Seen in: 2 games

Principle: The team that can threaten two pits picks where the fight happens; do not answer on reflex.
Feed signal: Game time past Baron spawn; dragon kill counts; item lists showing sustained damage.
Source: al_vs_t1_worlds_2025_quarterfinals_game__16@1909; kt_vs_t1_worlds_2025_grand_final_game_2__3@1991; kt_vs_t1_worlds_2025_grand_final_game_2__3@2332

## Push the side waves before you posture at Baron
Roles: all
Phase: late
When: baron_setup, team_ahead, split_pressure
Situation: Baron is alive and your team wants it or already holds its buff.
Our side: Get the waves moving first, a strong duelist in a side lane; they answer waves or the pit.
Their side: Grouped, they lose towers; split, they are short at Baron or the next dragon.
Player check: Where are the three waves, how many enemies show in the side lane?
Seen in: 3 games

Principle: Waves pushing into them give control of the pit; the same push can end at the dragon as five.
Feed signal: Late game time with Baron available or a Baron kill event; tower kill events.
Source: fly_vs_g2_worlds_2025_swiss_game_1_flyqu_46@2458; gen_vs_hle_worlds_2025_quarterfinals_gam_25@2075; hle_vs_al_worlds_2025_swiss_stage_game_0_74@2179

## Time the pick against the objective clock
Roles: jungle, mid, top
Phase: late
When: objective_soon, numbers_up
Situation: A big objective spawns in about a minute and you can kill an isolated enemy.
Our side: If he cannot escape, delay the kill so his death timer runs through the spawn.
Their side: Killed too early, he is back in time, often with Teleport.
Player check: Does he truly have no Flash or escape, and how long is his death timer?
Seen in: 1 game

Principle: Line the kill up with the spawn; a numbers edge matters only at the moment of the objective.
Feed signal: Late respawn timers against the time left to the spawn.
Source: gen_vs_kt_worlds_2025_semifinals_game_4__8@2365

## One call at an objective: finish it or fight
Roles: jungle, support, top
Phase: mid, late
When: objective_soon
Situation: A fight breaks out while your jungler is partway through a dragon.
Our side: Everyone turns to fight or everyone finishes; a split dive lacks the damage to kill.
Their side: They lose the dragon but win the fight and take the larger objective that follows.
Player check: How low is the objective, where are your damage dealers, and is a bigger one up next?
Seen in: 1 game

Principle: A dragon secured while the fight is lost can cost the bigger objective after it.
Feed signal: A dragon kill event for one team followed at once by several of its deaths.
Source: kt_vs_t1_worlds_2025_grand_final_game_3__2@1834
