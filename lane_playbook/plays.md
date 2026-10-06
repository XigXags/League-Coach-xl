# Recognized plays

Each play is a pattern that pro analysts discuss repeatedly. The `Trigger` line names a check in `coach.py` (`recognized_plays`). A play is offered only when that check passes on the observed feed. Every play states both sides, because the same pattern is a plan for one team and a problem for the other.

## Punished split: turret for dragon

Trigger: punished_split
Summary: the enemy isolates one laner, dives him, and takes the objective the diving team was not contesting.

The diving team keeps one ADC in bot, keeps the top laner pushing the top wave, and keeps the mid laner pushing mid. Everyone is farming plates, so nobody looks like they are moving. The mid laner leaves mid, the support joins top, and the team dives the one player under his turret wall. The result is a kill plus a turret, while the other team's dragon is taken elsewhere. The trade is a turret and a kill for a dragon. Whether it is good depends on the dragon's value (stacks, soul timing) against the turret and the respawn time the diving team gains.

Diving team: start the dive only when the isolated player cannot retreat and the nearby lanes are pushed. Leave the wave in a state that keeps the turret pressure after the kill. Trade the turret for the objective only if the objective spawns in the next minute.
Isolated team: a lone player under a turret with no ally in range should not wait for a dive. Recall or walk to the wave where an ally can see the approach. If the dive is already on, give up the turret and save the player. Losing one player to a 3v1 is worse than losing a plate.
Observed on the feed: an ally death, a turret kill, and a dragon kill within about 90 seconds. Not observed: where the divers stood before the dive, or whether the wave was pushed.

## Lone laner under the turret wall

Trigger: punished_split
Summary: a single player is left alone under a turret while the rest of the team is elsewhere. This is the defending side of the punished split.

The lone player's options are to trade into the wave, back toward a teammate, or recall. Each choice changes what the enemy can take next. A player who can see three enemies arriving should stop the trade and retreat. A player who has a jungler or support walking in should hold the wave. The strongest version is to make the dive cost the diving team its objective: if the enemy dives you, the enemy's dragon or lane is free.

Observed on the feed: the ally's death and respawn timer, plus the enemy objective that followed it. Not observed: who is in the approaching group, or whether they are coming.

## Freeze-and-dive

Trigger: dive_setup
Summary: a team holds a wave near its own tower, so the enemy must walk into it. Then the team dives the enemy who came forward.

The freezing team keeps the wave close to its tower. The enemy laner who came forward to deny the wave is isolated when the freezing team arrives from the jungle or river. The dive wins a kill and then pushes the wave into a tower. Two conditions decide it: the diving team has more living players nearby, and the isolated enemy has no retreat path.

Observed on the feed: alive-count advantage and an objective due soon. Not observed: wave position, the isolated player's location.

## Bait then rotate

Trigger: dive_setup
Summary: one lane is made to look weak so the enemy commits there, then the team rotates to a different lane or objective.

A team shows a single laner pushing hard, or drops a dive stance on one side. The other team sends players to defend that lane. The rotating team then moves through the river to the side the enemy left open. The trade works only if the bait holds long enough for the rotation to arrive.

Observed on the feed: deaths and objective events after the fact. Not observed: the bait, the rotation, or what the enemy saw.

## Mid crash into side dive

Trigger: punished_split
Summary: the mid wave is crashed into the enemy mid tower, the mid laner walks to a side lane, and the team dives the isolated laner.

Mid has the most flexible move. A crashed wave forces the enemy mid to respond to the tower, and the mid laner can leave for a side lane while the response is slow. The team then concentrates on the side lane where the enemy is isolated. The crash must be cleared before the mid laner leaves, or the enemy takes the wave for free.

Observed on the feed: an ally death on the side, a tower taken by the diving team. Not observed: the crash itself.

## Dragon-for-tower swap

Trigger: objective_swap
Summary: both teams take objectives in the same minute, so the net value depends on what each objective is worth.

If one team takes a tower while the other takes dragon, neither side is clearly ahead. The question is the next objective. A dragon stack that makes the next soul or Elder fight easier is worth more than a turret only if the team can use it before the enemy's next objective. A turret that opens a lane gives the team a wave and vision for the next minute. Count both: stacks and timing for the dragon side, lane pressure and tower plates for the tower side.

Observed on the feed: tower and dragon events within about 90 seconds of each other, with their killer teams. Not observed: the lane state the tower opened.

## Split push with a delayed dive

Trigger: split_pressure
Summary: the team leaves one player to pressure a side lane while the other four protect the centre. The split forces a fight that the four can win.

The split player pushes a side wave into a tower. The enemy must choose between answering the split and defending the centre. If they answer, the four take the objective or a fight on their terms. If they ignore it, the split takes the tower. The split is safe only if the split player can retreat from a three-player dive and the centre team can join the fight in time.

Observed on the feed: alive count, a tower taken by your team, and game time. Not observed: where the split player is or whether the enemy is responding.

## Counter-jungle on an invade

Trigger: split_pressure
Summary: when the enemy jungler enters your jungle, the team responds by taking the objective or camp on their side.

An invade costs the jungler's clear and its tempo. If the enemy jungler is deep in your jungle, a dragon, Herald, or Baron on their side is open. The counter-jungle works when the invader is alone and its lane is not ready to fight. It fails when the invader arrives with a second player.

Observed on the feed: the enemy jungler's kills and deaths, and any objective taken since. Not observed: the invade route or camp state.

## Baron setup after a side tower

Trigger: baron_setup
Summary: the team takes a side tower and then sets up Baron with the same wave pressure.

Baron is worth more when the team already has side pressure. A side tower opens vision and a wave, and the wave gives the team a safe way to the pit. The team must hold the entrance long enough to start Baron. If the enemy team has a large numbers lead, the setup should be delayed until the lead is gone.

Observed on the feed: the game clock, a tower event, and the alive count. Not observed: the pit's occupancy, the enemy's vision.

## Elder or soul fight

Trigger: baron_setup
Summary: the late-game dragon contest where the buff's execute or damage decides the fight.

The team that holds the buff can threaten a fight the other team must answer. The team without the buff must choose between taking the objective first and fighting the buff holder. The fight is decided by the buff holders staying alive and the rest of the team staying in range.

Observed on the feed: dragon count per team and the game clock. Not observed: which players hold the buff, or their positions.

## Death-timer window

Trigger: enemy_death_window
Summary: after an enemy death, the team uses the respawn timer to take a tower or objective before the enemy returns.

The window is short. The enemy's respawn timer is observed, but the enemy's recall or teleport is not. A team that uses the window must move with the wave and leave when the enemy respawns.

Observed on the feed: the enemy death and its respawn timer, plus alive counts. Not observed: whether the enemy can teleport back.

## Shove, leave, return

Trigger: dive_setup
Summary: a wave is pushed to a tower, the team leaves for a fight or objective, then returns to take the wave back.

The wave's position is the key. If the wave is pushed into the enemy tower, the enemy must send a player to clear it, and that player can be caught. The team returns after the objective or fight to take the wave for a tower or a reset.

Observed on the feed: the objective time and alive counts. Not observed: wave position and the enemy's response.

## Poke-then-engage

Trigger: dive_setup
Summary: a team uses range or poke to damage the enemy, then an engage champion commits when the enemy is weakened.

The engage's timing is the trade. Poke that lands before the engage makes the fight favourable. The enemy must play defensively or retreat, which gives the team the next objective.

Observed on the feed: deaths and alive count. Not observed: spell readiness or health during the poke.

## Pro-level principles across plays

- Every play is a trade. Name what each team gives up before saying which team wins.
- The live feed sees outcomes (deaths, objectives, towers, gold you hold), not positions or spell readiness. Say so when a recommendation depends on them.
- A play is only as strong as its retreat path. Name the retreat for the diving team and for the isolated team.
- The respawn timer is the cost of a death. A death at 10:00 and a death at 25:00 are different trades.
