# League Coach macro rules and evidence

Reviewed for patch 26.19 (October 2026). This file records why the coach proposes each route and what the current data feed can actually verify.

## Current objective rules

- On standard Summoner's Rift, Grubs are one early three-monster window, beginning at 8:00, and do not respawn. Their value is primarily in structure pressure. Riot reduced the pressure to send a whole team to Grubs and concentrated their direct gold on the killer. A Grub play should usually use top, mid, and jungle while bot continues getting its wave or plates. [Patch 25.09](https://www.leagueoflegends.com/en-us/news/game-updates/patch-25-09-notes/), [Patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/).
- Dragon gives a lasting stack and brings a team toward soul. Dragon is a real trade against the one-time Grub window, especially if bot and mid can move first. The coach counts observed dragon kills by team; it does not assume a particular dragon type is alive. [Patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/).
- After a team claims four elemental drakes, the route changes to Elder rather than recommending another ordinary drake. The code tracks observed dragon kills and the six-minute Elder window. [Riot's Elder timing notes](https://www.leagueoflegends.com/en-au/news/game-updates/patch-9-23-notes/).
- Atakhan is removed in 2026 and Baron is back at 20:00. Herald occupies the top pit before Baron. Swiftplay has different objective rules: no Grubs or Herald, Baron at 12:00, and only two elemental dragons. Queue identification is not yet reliable in the Riot local feed, so use a standard Summoner's Rift match for objective comparisons. [2026 season preview](https://www.leagueoflegends.com/en-us/news/dev/dev-2026-season-one-gameplay-preview/), [Patch 26.1](https://www.leagueoflegends.com/en-us/news/game-updates/patch-26-1-notes/).

## Decision sequence encoded in the bot

The ranking now weighs three horizons: immediate numbers and wave setup, the next objective window, and later structure or soul conversion. It also reads each player's listed summoner spells. A listed Teleport does not reveal whether it is ready.

1. Check the question and the game clock. When asked “Grubs or Dragon?”, compare those two routes; after the Grub window, replace it with Herald or Baron rather than suggesting an obsolete camp.
2. Use observed deaths, role assignments, champion identities, item lists, and lane level/CS differences. A lane score lead is a clue about power, not proof that its wave is pushed or its player can move first.
   - Grub plans call out a small curated set of structure-pressure champions (Yorick, Fiora, Tryndamere, Ziggs, Caitlyn). Riot names these as split-push or siege examples in its [2026 season preview](https://www.leagueoflegends.com/en-us/news/dev/dev-2026-season-one-gameplay-preview/). This is a specific conversion cue, not a full champion matchup model.
3. Give each option an executable sequence: which lanes shove, which players move into which river, who starts the objective, and what to convert it into. Each route includes a fallback if the pit is empty.
4. Rank the two plans with Jev using the full snapshot and team question. The players choose between them. No unseen positions, wave state, or vision are invented.

## Position and jungle data boundary

Riot's documented local Live Client Data API supplies players, scores, items, spells, and events, but the coach does not receive each visible player's map coordinates, every minion's position, or the current state of each jungle camp. It therefore cannot calculate exact lane priority, wave arrival, jungle paths, or a travel-time bound from a last-seen position. [Riot Live Client Data API](https://developer.riotgames.com/docs/lol).

Overwolf documents jungle camp alive and vision flags, including Grubs and Dragon. This would be a useful next adapter for objective availability, but camp states alone still would not provide a trustworthy last-seen enemy position. Any future travel estimate would need a timestamped observation from normal player-visible information and must account for Teleport and global movement before being used. The coach must never treat an unseen player's location as known. [Overwolf League events](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/league-of-legends/), [Riot League game integrity policy](https://developer.riotgames.com/docs/lol).

## Data still needed for stronger calls

- Riot's [Live Client Data API](https://developer.riotgames.com/docs/lol) supplies player status, items, scores, active-player gold, and events such as dragon and Baron kills. Its published [event sample](https://static.developer.riotgames.com/docs/lol/liveclientdata_events.json) does not include Grub kills. It does not expose full live wave positions, map vision, or every teammate's unspent gold.
- Overwolf's [League GEP](https://dev.overwolf.com/ow-native/live-game-data-gep/supported-games/league-of-legends/) exposes `jungle_camps` entries including Dragon and VoidGrubs with alive and vision flags. This project does not yet have an Overwolf extension feeding those events to the bot. Overwolf requires a whitelisted development account to load an unpacked app. Until that bridge exists, the bot can check a pit as part of a plan but cannot promise the camp is alive.
- Riot's current [Data Dragon champion file](https://ddragon.leagueoflegends.com/cdn/16.19.1/data/en_US/champion.json) is cached as `champions-16.19.1.json`. It provides broad archetype tags; these are not matchup, lane priority, or power-spike models. Champion-specific calls beyond these tags need a curated matchup and item-spike knowledge base plus match review.
