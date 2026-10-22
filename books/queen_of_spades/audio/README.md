# Audio assets — The Queen of Spades

Staged ambience beds and sound effects for the mix stage. The mix code does not exist yet.
Do not reference these files in any pipeline until the mix step is built.

## Scenes and their sounds

### Opening card table (lines 1–36)
- Base ambience: `amb_city_cold.flac` (distant snowy street outside the window)
- Action SFX: `sfx_cards.aif` (shuffle, deal, cut at card moments)
- Extra card SFX: `sfx_deal.wav` (dealing out a deck), `sfx_chips.wav` (coins / chips spinning)
- Optional background: `sfx_men_murmur.wav` (only if clean and license is clear)

### Confrontation — Herman and the living Countess (lines 73–86)
- Base ambience: `amb_winter_quiet.wav` (cold room, wind, light snow outside)
- Backup: `amb_snow_city.wav`, `amb_pirita_night.flac`
- Action SFX: `sfx_pistol_cock.wav` at the start of line 83

### Ghost — Countess appears in Herman's room (lines 122–125)
- Base ambience: `amb_horror_cellar.wav` (unnatural, cellar-like, wrongness)
- Action SFX: `sfx_door_open.wav` at the start of line 123 (verify it is a single slow creak, no reverb, no theatrical spookiness)

### Street scene — Herman watches Lisaveta at the window
- Base ambience: `amb_pirita_night.flac` (distant dogs, traffic, quiet residential)
- No action SFX

## Added, scene not assigned yet
- `amb_room_tone.wav` — quiet apartment room tone (klankbeeld), 90 s. Candidate base for indoor scenes.

## Files

| File | Length | Format |
|---|---|---|
| amb_pirita_night.flac | 5:35 | 48 kHz stereo |
| amb_room_tone.wav | 1:30 | 48 kHz stereo, 24-bit |
| sfx_cards.aif | 1:06 | 44.1 kHz mono, 24-bit |
| sfx_deal.wav | 0:23 | 44.1 kHz stereo |
| sfx_chips.wav | 1:09 | 44.1 kHz stereo, 24-bit |
| sfx_men_murmur.wav | 0:59 | 48 kHz mono, 24-bit |
| sfx_door_open.wav | 0:08.5 | 48 kHz stereo |
| sfx_pistol_cock.wav | 0:00.6 | 48 kHz stereo, 32-bit |

Not uploaded yet: `amb_winter_quiet.wav`, `amb_snow_city.wav`, `amb_horror_cellar.wav`, `amb_city_cold.flac`, `amb_berlin_wind.wav`.

## Not used in this book

- `amb_berlin_wind.wav` — contains a distant alarm klaxon, wrong mood. Parked for future projects.

## No music

Music is deliberately omitted. The story's silences are part of its tension.

## Known issues

- Several files still need their Freesound licenses verified. See CREDITS.md.
- `sfx_door_open.wav` needs a listen check — if it is too reverby or theatrical, replace it with a dry single creak.
- `sfx_men_murmur.wav` is a 1930s optical transfer; check for noise before using.
- `sfx_pistol_cock.wav` is a modern semi-auto slide. The story is 1830s; the sound is slightly anachronistic but probably unnoticeable to listeners.
