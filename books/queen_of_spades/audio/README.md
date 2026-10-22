# Audio assets — The Queen of Spades

Staged ambience beds and sound effects for the mix stage. The mix code does not exist yet.
Do not reference these files in any pipeline until the mix step is built.

## Scenes and their sounds

### Opening card table (lines 1–36)
- Base ambience: `ambience/amb_city_cold.flac` (distant snowy street outside the window)
- Action SFX: `sfx/sfx_cards.aif` (shuffle, deal, cut at card moments)
- Optional background: `sfx/sfx_men_murmur.wav` (only if clean and license is clear)

### Confrontation — Herman and the living Countess (lines 73–86)
- Base ambience: `ambience/amb_winter_quiet.flac` (cold room, wind, light snow outside)
- Backup: `ambience/amb_snow_city.wav`, `ambience/amb_pirita_night.flac`
- Action SFX: `sfx/sfx_pistol_cock.wav` at the start of line 83

### Ghost — Countess appears in Herman's room (lines 122–125)
- Base ambience: `ambience/amb_horror_cellar.flac` (unnatural, cellar-like, wrongness)
- Action SFX: `sfx/sfx_door_open.wav` at the start of line 123 (verify it is a single slow creak, no reverb, no theatrical spookiness)

### Street scene — Herman watches Lisaveta at the window
- Base ambience: `ambience/amb_pirita_night.flac` (distant dogs, traffic, quiet residential)
- No action SFX

## Not used in this book

- `ambience/amb_berlin_wind.wav` — contains a distant alarm klaxon, wrong mood. Parked for future projects.

## No music

Music is deliberately omitted. The story's silences are part of its tension.

## Cue sheet (generated from `events.json` — edit the JSON, not this table)

Times are in the current full test MP3 and will move when the script changes; the line + phrase anchors do not. ↳ = supporting layer, 2–4 LU under the event's main sound.

| Bed | Lines (time) | Scene | File | LU under | Status |
|---|---|---|---|---|---|
| B01 | 1–37 (0:02) | Card party at Naroumov's (dawn) | `ambience/amb_city_cold.flac` | 18 | proposed |
| B02 | 1–4 (0:02) | Card party chatter | `sfx/sfx_men_murmur.wav` | 22 | listen-check |
| B03 | 50–61 (4:40) | Lisaveta at the window / street (day) | `ambience/amb_street_havana.flac` | 22 | listen-check |
| B04 | 66–86 (7:52) | Night visit and Confrontation, Countess's house | `ambience/amb_winter_quiet.flac` | 15 | approved |
| B05 | 87–113 (10:47) | Lisaveta's room, same night | `ambience/amb_winter_quiet.flac` | 18 | proposed |
| B06 | 114–117 (13:32) | Funeral | `ambience/amb_hall_crowd.wav` | 20 | proposed |
| B07 | 119–126 (14:42) | Ghost in Herman's room | `ambience/amb_horror_cellar.flac` | 14 | approved |
| B08 | 127–129 (16:16) | Herman's obsession, night streets | `ambience/amb_pirita_night.flac` | 22 | proposed |
| B09 | 130–166 (16:52) | Tchekalinsky's club | `ambience/amb_hall_crowd.wav` | 18 | proposed |
| B10 | 167–168 (21:39) | Ending: Herman in the hospital | — (silence) | — | proposed |

| Event | Line (time) | At | Sounds (overlapping) | Status |
|---|---|---|---|---|
| E01 Card party | 1 (0:02) | line start | `sfx/sfx_cards.aif` 16 LU, -1.5 s<br>`sfx/sfx_chips.wav` 20 LU, -1.0 s | proposed |
| E02 Breakfast | 2 (0:14) | "pushed back their plates" | `sfx/sfx_cutlery.wav` 16 LU<br>`sfx/sfx_plates.wav` 16 LU, +0.3 s<br>`sfx/sfx_chair_scrape.wav` 16 LU, +1.0 s | proposed |
| E03 Party breaks up | 37 (3:34) | "draining his glass" | `sfx/sfx_glass_set.wav` 14 LU, +0.5 s<br>`sfx/sfx_chair_scrape.wav` 16 LU at "taking his leave"<br>`sfx/sfx_people_leaving.ogg` 14 LU, +0.6 s at "taking his leave" | proposed |
| E04 Countess at her mirror | 38 (3:41) | "Three women were assisting" | `sfx/sfx_clothes_rustle.wav` 18 LU<br>↳ `sfx/sfx_chair_creak.wav` 21 LU at "seated before her mirror" | proposed |
| E05 Carriage, note thrust into her hand | 57 (5:56) | "about to enter the carriage" | `sfx/sfx_horse_snort.wav` 14 LU<br>`sfx/sfx_paper_flutter.wav` 16 LU, +0.3 s at "a note was thrust" | proposed |
| E06 Reads the note | 58 (6:11) | "to read the missive" | `sfx/sfx_paper_unfold.mp3` 14 LU<br>↳ `sfx/sfx_paper_flutter.wav` 17 LU, +0.8 s | proposed |
| E07 Writes her reply | 60 (6:36) | "She therefore wrote a few lines" | `sfx/sfx_quill_writing.wav` 16 LU<br>↳ `sfx/sfx_paper_unfold.mp3` 19 LU, -0.8 s<br>backup: `sfx/sfx_pen_writing.wav` | proposed |
| E08 Letter dropped from the window | 60 (6:36) | "dropped it" | `sfx/sfx_paper_flutter.wav` 14 LU, +0.4 s | proposed |
| E09 He enters a shop | 61 (6:50) | "entered a shop" | `sfx/sfx_shop_door_bell.wav` 14 LU | proposed |
| E10 Climbs to the bedchamber | 66 (7:52) | "he reached the old lady" | `sfx/sfx_stairs_boots.wav` 14 LU, -5.0 s<br>↳ `sfx/sfx_floorboard_creak.wav` 17 LU, +2.0 s<br>↳ `sfx/sfx_clothes_rustle.wav` 18 LU, -4.5 s | tested |
| E11 Waiting in the closet | 67 (8:05) | "he concealed himself" | `sfx/sfx_clock_tick.mp3` 18 LU | approved |
| E12 The carriage returns | 68 (8:15) | "at last he heard" | `sfx/sfx_carriage_path.wav` 10 LU, +0.4 s<br>↳ `sfx/sfx_carriage_wedding.wav` 13 LU, +0.8 s<br>↳ `sfx/sfx_horse_snort.wav` 13 LU, +3.0 s<br>backup: `sfx/sfx_carriage_wedding.wav` | approved |
| E13 Servants move about | 68 (8:15) | "servants began" | `sfx/sfx_footsteps_group.mp3` 16 LU, +0.5 s | listen-check |
| E14 The Countess sways in her chair | 71 (8:50) | "As the old lady sat swaying" | `sfx/sfx_chair_creak.wav` 16 LU<br>↳ `sfx/sfx_clothes_rustle.wav` 19 LU, +0.3 s | tested |
| E15 Herman steps out | 72 (9:08) | line start | `sfx/sfx_floorboard_creak.wav` 10 LU, -0.6 s<br>↳ `sfx/sfx_clothes_rustle.wav` 13 LU, -0.4 s | tested |
| E16 The pistol | 83 (10:19) | "drew a pistol" | `sfx/sfx_pistol_cock.wav` 10 LU, +0.8 s | listen-check |
| E17 Herman bursts into Lisaveta's room | 100 (12:01) | "the door of her apartment suddenly opened" | `sfx/sfx_door_squeaky.wav` 10 LU<br>↳ `sfx/sfx_floorboard_creak.wav` 13 LU, +1.0 s<br>↳ `sfx/sfx_clothes_rustle.wav` 14 LU at "She drew back"<br>backup: `sfx/sfx_door_sliding.wav` | proposed |
| E18 He leaves by the street door | 113 (13:22) | "then went out" | `sfx/sfx_front_door_nobeep.wav` 12 LU, +0.3 s<br>backup: `sfx/sfx_front_door_chime.wav` | proposed |
| E19 Herman falls at the funeral | 117 (14:15) | "fell to the floor" | `sfx/sfx_body_fall.mp3` 10 LU<br>`sfx/sfx_men_murmur.wav` 18 LU at "He was picked up" | proposed |
| E20 Footsteps in slippers | 121 (15:04) | "The step was" | `sfx/sfx_slippers.mp3` 12 LU<br>↳ `sfx/sfx_floorboard_creak.wav` 15 LU, +2.5 s<br>↳ `sfx/sfx_clothes_rustle.wav` 16 LU, +0.5 s | approved |
| E21 The ghost enters | 122 (15:15) | line start | `sfx/sfx_door_open.wav` 8 LU, -1.2 s<br>↳ `sfx/sfx_clothes_rustle.wav` 11 LU at "She came close to the bed"<br>↳ `sfx/sfx_floorboard_creak.wav` 12 LU, +1.0 s at "She came close to the bed" | approved |
| E22 The outside door closes | 125 (15:52) | "Herman heard the outside door" | `sfx/sfx_door_close_distant.wav` 10 LU, +1.2 s<br>↳ `sfx/sfx_slippers.mp3` 13 LU at "The fantom then turned" | approved |
| E23 The club: whist and faro | 132 (17:26) | "played whist" | `sfx/sfx_cards.aif` 20 LU<br>`sfx/sfx_glass_set.wav` 20 LU at "eating ices"<br>`sfx/sfx_chips.wav` 18 LU at "playing faro" | proposed |
| E24 The host returns to his dealing | 134 (17:59) | "returned, to his dealing" | `sfx/sfx_deal.wav` 16 LU<br>↳ `sfx/sfx_chips.wav` 19 LU, +0.5 s<br>↳ `sfx/sfx_glass_set.wav` 20 LU at "More than thirty cards" | proposed |
| E25 Cards shuffled | 136 (18:25) | "the cards were shuffled" | `sfx/sfx_cards.aif` 14 LU<br>↳ `sfx/sfx_chips.wav` 17 LU, +0.5 s | proposed |
| E26 First deal | 151 (19:32) | "He began dealing" | `sfx/sfx_deal.wav` 14 LU<br>↳ `sfx/sfx_chips.wav` 17 LU, +0.6 s | proposed |
| E27 A murmur ran through the crowd | 154 (19:44) | "A murmur ran through the crowd" | `sfx/sfx_men_murmur.wav` 14 LU<br>`sfx/sfx_paper_flutter.wav` 18 LU at "counted out the required sum" | proposed |
| E28 Second deal | 156 (20:10) | "The banker began dealing" | `sfx/sfx_deal.wav` 14 LU<br>↳ `sfx/sfx_chips.wav` 17 LU at "placed upon it his fresh stake" | proposed |
| E29 The onlookers exclaimed | 157 (20:21) | "The onlookers exclaimed" | `sfx/sfx_men_murmur.wav` 12 LU<br>↳ `sfx/sfx_paper_flutter.wav` 15 LU at "He counted out ninety-four-thousand rubles"<br>↳ `sfx/sfx_chips.wav` 16 LU, +0.3 s at "He counted out ninety-four-thousand rubles" | proposed |
| E30 Third deal (the queen) | 159 (20:51) | "The dealing began" | `sfx/sfx_deal.wav` 14 LU | proposed |
| E31 The croupier rakes in the money; the game goes on | 166 (21:27) | "The croupier raked in the money" | `sfx/sfx_chips.wav` 14 LU<br>`sfx/sfx_cards.aif` 16 LU at "the cards were shuffled, and the gambling went on" | proposed |

Still wanted: line 114 "Her funeral": one slow church bell toll; line 126 "his orderly lay asleep": snoring; line 126 "lit his candle": match strike / candle; line 139 "with a piece of chalk": chalk writing; line 151/156/159 "to the right": single card flips; line 154 "counted out the required sum": paper money counting; line 157 "The onlookers exclaimed": crowd gasp; line 163-164 "the queen of spades": slow low heartbeat; line 83 "drew a pistol": flintlock / percussion pistol cock (replace modern slide); line 113 "then went out": old front door (adrianornhagen) without alarm beeps.

## Files

Present: see the folders; every file is listed in `ambience/CREDITS.md`.

Pending upload by Mohammed: `ambience/amb_snow_city.wav`, `ambience/amb_berlin_wind.wav`.

Line numbers above refer to `script/queen_of_spades_lines.json` (v4, same numbering as v3).

## Known issues

- `ambience/amb_city_cold.flac` is 46 s; the opening card scene needs it looped (use a crossfade at each join).

- Several files still need their Freesound licenses verified. See CREDITS.md.
- `sfx/sfx_door_open.wav` needs a listen check — if it is too reverby or theatrical, replace it with a dry single creak.
- `sfx/sfx_men_murmur.wav` is a 1930s optical transfer; check for noise before using.
- `sfx/sfx_pistol_cock.wav` is a modern semi-auto slide. The story is 1830s; the sound is slightly anachronistic but probably unnoticeable to listeners.
