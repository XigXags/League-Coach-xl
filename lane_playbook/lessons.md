# Lessons: my own long-term plans

The coach reads this file each time it answers. Edit it freely; no restart is needed.
Problems with an edit are printed in the bot log as "Lesson file: ..." on the next answer.

Each lesson starts with a line "## name", then one "Field: text" per line. Copy this
block, remove the four leading spaces, and fill it in:

    ## Name of the lesson
    Applies to: jungle, Champion Name
    Trigger: six_race
    Goal: the headline shown in chat
    Timeline: your own benchmark, in a few sentences (about 300 characters shown)
    Player check: what you must look at yourself (about 200 characters shown)
    Breaks it: what ruins the plan (about 200 characters shown)
    Say it like: the spoken line, 14 words at most
    Source: where the numbers come from

Applies to: a role, champion names, or both, separated by commas. The most specific
lesson wins: one champion beats a champion list, and a list beats the whole role.
Trigger: one of first_clear, second_clear, six_race, six_behind, six_first, scaling. It rewords a built-in call.
Offer at: a stage name instead of Trigger (first_clear, second_clear, six_race, six_behind, six_first, post_six, mid_game, or lane for laners) makes the lesson a plan of its own. Use one or the other.
Kind: farm, gank, invade, cover, trade or recover. Name: what the coach calls the plan aloud, 5 words at most.
Pick it with: what you say to choose it, separated by commas.
On track: marks the coach can check, separated by semicolons: level 4 by 3:30; enemy under 6 until 6:10; no deaths.
A lesson with neither Trigger nor Offer at is background for the ranker and is never spoken.
Plan: farm or gank, with Until: 25:00 for when a farm plan stops being offered.
Say it like can use {level}, {champion}, {enemy}, {enemy_level} and {clock}.
The coach can see only game time, levels, CS, items, deaths and objective kills.
Anything else (camps, crab, stacks, cooldowns, waves) goes under "Player check".

## Scuttle for six
Applies to: jungle
Trigger: six_race
Name: six on crab
Pick it with: six on crab, second crab, crab, scuttle, level six, six
Goal: If a river crab is up, reach it first for level 6
Timeline: Full clear all six camps and reach a first crab by about 3:00 to 3:15, recall, then clear again: buffs take 5:00 to return, so that is usually the four other camps. Be level 5 and about a camp short of 6 when the single crab comes: not before 5:25, more often 5:50 to 6:10, on a random river side.
Feed check: You are level 5 and the enemy jungler is not 6 yet. The coach compares your level and the clock with the On track marks.
Player check: Is the crab up, which side, and are you about one camp from 6? Can you get there first, even by a longer route through fog? The coach cannot see any of this.
Breaks it: A skipped camp, a slow clear, a death, a gank on you mid-clear, or an early invade of your camps, for example by their mid laner. Then give the crab and take a camp.
On track: level 4 by 3:30; level 5 by 5:50
Say it like: Level {level}. If crab's up and you're a camp from six, get it first
Source: my own benchmark for junglers who full clear fast; one third-party guide agrees; XP maths not confirmed for this patch. I guessed the second crab at 4:00 to 5:00 and asked whether 4:30 works: it does not. Both first crabs spawn at 2:55, a crab takes 2:30 to return, and the single crab exists only after both first crabs die, so 5:25 is the earliest. The two On track marks are the coach's reading of my benchmark and I can edit them. Published fastest-clear times are best cases. Stack counts for scaling champions are on the HUD passive icon, not in the feed. My two-second call: this champ can hit six on crab, or go blue into an invade, back out and full clear, to deny their six on crab.

## Blue into an invade
Applies to: jungle
Offer at: first_clear
Until: 1:30
Kind: invade
Name: blue into an invade
Pick it with: invade, blue into, raptors, counter jungle, enemy camp
Goal: Start blue, take one enemy camp, back out, then full clear
Timeline: Start on blue buff, take one camp on their side (their raptors are often unwarded, by experience, not verified), leave, then full clear. The aim is their jungler a camp short of 6 when the single crab comes, which is no earlier than 5:25. Whether one camp is enough is a guess.
Feed check: Game time is inside the first clear and before 1:30. Afterwards the coach compares your level with their jungler's.
Player check: Can your champion fight theirs this early, can a teammate help, is that camp up and unwarded, and where did their jungler start? The coach cannot see camps, wards or positions.
Breaks it: Being seen going in, their laners arriving first, a death, or losing more of your own clear than you take. Then leave at once and full clear your own side.
On track: level 4 by 3:45; enemy under 6 until 6:10; no deaths
Say it like: blue into one enemy camp, back out, then full clear
Source: my own line, untested; that one stolen camp denies level 6 is not verified. Camp spawns are patch 26.x: 0:55, Gromp and Krugs 1:07. The 1:30 cutoff and the On track marks were set by the coach and I can edit them.

## Bel'Veth farms to 80 stacks
Applies to: jungle, Bel'Veth
Plan: farm
Trigger: scaling
Until: 25:00
Goal: Keep full clearing toward 40, then 80 Lavender stacks
Timeline: About 20 minutes of mostly farming without helping lanes. 40 stacks is a 90 second True Form and 80 makes it permanent.
Feed check: You are on Bel'Veth and it is before 25:00.
Player check: Are you at 40 or 80 stacks yet (the passive icon left of your abilities shows the number), and is a gank free on your path? The coach cannot see stacks.
Breaks it: Dying, detours for low-odds ganks, or losing camps to an invade.
Say it like: Stay on camps toward eighty stacks
Source: 40 and 80 are patch 26.15 True Form breakpoints; 20 minutes is my own benchmark.

## Farm-first junglers
Applies to: jungle, Master Yi, Karthus, Graves, Shyvana, Lillia, Diana, Kayn, Kindred
Plan: farm
Source: community consensus, patch-dependent; edit this list.

## Gank-first junglers
Applies to: jungle, Lee Sin, Elise, Jarvan IV, Rek'Sai, Xin Zhao, Vi, Nunu & Willump, Warwick
Plan: gank
Source: community consensus, patch-dependent; edit this list.
