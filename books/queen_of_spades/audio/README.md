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

## Additional sounds (added 2026-10-22, proposed placements — times in the current full MP3)

| Time | Line | Moment | Sound |
|---|---|---|---|
| 0:14 | 2 | "pushed back their plates" | `sfx/sfx_cutlery.wav`, `sfx/sfx_plates.wav`, `sfx/sfx_chair_scrape.wav` |
| 3:38 | 37 | "draining his glass and taking his leave" | `sfx/sfx_glass_set.wav`, `sfx/sfx_people_leaving.ogg` |
| 3:46 | 38 | Countess at her mirror, women dressing her | `sfx/sfx_clothes_rustle.wav` |
| 6:15 | 58 | Lisaveta reads the note | `sfx/sfx_paper_unfold.mp3` |
| 6:40 | 60 | "She therefore wrote a few lines" | `sfx/sfx_pen_writing.wav` (modern pen — listen check) |
| 6:55 | 61 | "entered a shop" | `sfx/sfx_shop_door_bell.wav` |
| 7:57 | 66 | Herman climbs to the bedchamber | `sfx/sfx_stairs_boots.wav` (first 29 s = walking) |
| 8:19 | 68 | "servants began moving about" | `sfx/sfx_footsteps_group.mp3` (outdoor concrete — listen check) |
| 8:55 | 71 | "the old lady sat swaying" | `sfx/sfx_chair_creak.wav` |
| 9:12 | 72 | "At the slight noise" | `sfx/sfx_floorboard_creak.wav` |
| 13:27 | 113 | key to the street door | `sfx/sfx_front_door_chime.wav` (cut the modern alarm beeps first) |
| 6:00 | 57 | Lisaveta enters the carriage | `ambience/amb_street_havana.flac` (listen check), `sfx/sfx_horse_snort.wav` |
| 6:40–6:55 | 60–61 | letter dropped from the window, picked up | `sfx/sfx_paper_flutter.wav` |
| 8:19 | 68 | "The hours dragged slowly by" | `sfx/sfx_clock_tick.mp3` (looped, soft) |
| 8:19 | 68 | "at last he heard the sound of wheels" | `sfx/sfx_carriage_path.wav` or `sfx/sfx_carriage_wedding.wav` |
| 12:06 | 100 | "the door of her apartment suddenly opened" | `sfx/sfx_door_squeaky.wav` or `sfx/sfx_door_sliding.wav` |
| 14:04–14:19 | 116–117 | funeral; Herman falls | `ambience/amb_hall_crowd.wav` (low), `sfx/sfx_body_fall.mp3` (one of three) |
| 15:08 | 121 | "the shuffling sound of loose slippers" | `sfx/sfx_slippers.mp3` |
| 15:21 | 122 | "The door of his room opened" | `sfx/sfx_door_open.wav` (tested and approved; moved from line 123) |
| 15:56 | 125 | "Herman heard the outside door close" | `sfx/sfx_door_close_distant.wav` |
| 18:00–21:40 | 130–166 | gambling club | `ambience/amb_hall_crowd.wav` or `sfx/sfx_men_murmur.wav`; `sfx/sfx_cards.aif`, `sfx/sfx_deal.wav`, `sfx/sfx_chips.wav` |
| 19:49 | 154 | "A murmur ran through the crowd" | `sfx/sfx_men_murmur.wav` |

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
