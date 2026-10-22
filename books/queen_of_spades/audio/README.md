# Audio assets — The Queen of Spades

Staged ambience beds and sound effects for the mix stage. The mix code does not exist yet.
Do not reference these files in any pipeline until the mix step is built.

## Scenes and their sounds

### Opening card table (lines 1–36)
- Base ambience: `ambience/amb_city_cold.flac` (distant snowy street outside the window)
- Action SFX: `sfx/sfx_cards.aif` (shuffle, deal, cut at card moments)
- Optional background: `sfx/sfx_men_murmur.wav` (only if clean and license is clear)

### Confrontation — Herman and the living Countess (lines 73–86)
- Base ambience: `ambience/amb_winter_quiet.wav` (cold room, wind, light snow outside)
- Backup: `ambience/amb_snow_city.wav`, `ambience/amb_pirita_night.flac`
- Action SFX: `sfx/sfx_pistol_cock.wav` at the start of line 83

### Ghost — Countess appears in Herman's room (lines 122–125)
- Base ambience: `ambience/amb_horror_cellar.wav` (unnatural, cellar-like, wrongness)
- Action SFX: `sfx/sfx_door_open.wav` at the start of line 123 (verify it is a single slow creak, no reverb, no theatrical spookiness)

### Street scene — Herman watches Lisaveta at the window
- Base ambience: `ambience/amb_pirita_night.flac` (distant dogs, traffic, quiet residential)
- No action SFX

## Not used in this book

- `ambience/amb_berlin_wind.wav` — contains a distant alarm klaxon, wrong mood. Parked for future projects.

## No music

Music is deliberately omitted. The story's silences are part of its tension.

## Files

Present: `ambience/amb_pirita_night.flac`, `sfx/sfx_cards.aif`, `sfx/sfx_men_murmur.wav`, `sfx/sfx_door_open.wav`, `sfx/sfx_pistol_cock.wav`.

Pending upload by Mohammed: `ambience/amb_winter_quiet.wav`, `ambience/amb_snow_city.wav`, `ambience/amb_horror_cellar.wav`,
`ambience/amb_city_cold.flac`, `ambience/amb_berlin_wind.wav`.

Line numbers above refer to `script/queen_of_spades_lines.json` (v4, same numbering as v3).

## Known issues

- Several files still need their Freesound licenses verified. See CREDITS.md.
- `sfx/sfx_door_open.wav` needs a listen check — if it is too reverby or theatrical, replace it with a dry single creak.
- `sfx/sfx_men_murmur.wav` is a 1930s optical transfer; check for noise before using.
- `sfx/sfx_pistol_cock.wav` is a modern semi-auto slide. The story is 1830s; the sound is slightly anachronistic but probably unnoticeable to listeners.
