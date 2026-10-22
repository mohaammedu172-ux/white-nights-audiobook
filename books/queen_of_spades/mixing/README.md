# Mixing

`mix.py` renders the voice track with the ambience beds and sound effects listed in `../audio/events.json`.

```bash
python books/queen_of_spades/mixing/mix.py --voice out/queen_of_spades/white_nights_queen_of_spades.mp3 \
    --qc out/queen_of_spades/qc_report.json --out out/queen_of_spades_mixed.mp3        # whole story (about 1 min on CPU)
# add --start 470 --end 560 for one stretch, --skip E18 B03 to leave cues out
```

Rules, each proven in tests Mohammed approved by ear:
- Levels are perceived loudness (LU below the voice around the cue), never RMS.
- Cues are anchored by line id + phrase, so they follow the script when timing changes.
- Loops use a 0.2 s equal-power crossfade. Sound effects are aligned on their own onset.
- The voice is not processed; the mix is scaled once so peaks stay at or below −3 dBFS.
- Change sounds, levels or timing in `events.json`, not in the code.
