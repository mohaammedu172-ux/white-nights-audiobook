"""Make the audio for one poem: generate every half-verse, let the judges listen, retry the weak ones,
assemble the tracks, mix the music, and write a QA report.

    python -m ar.run books/muallaqat/imru_al_qays/job.json [--verses 1-5] [--out out/imru] [--music DIR]

Safe to re-run: finished clips and judge results are kept in <out>/state.json and skipped.
"""
import argparse, csv, glob, json, os, shutil, time
from . import text_rules as tr
from .assemble import build_voice, to_mp3, mix_music, shape

# Retry ladder. Greedy decoding is deterministic, so each attempt changes the settings or the text.
ATTEMPTS = [
    dict(exaggeration=0.35, max_new_tokens=300, problem_words=False),
    dict(exaggeration=0.35, max_new_tokens=300, problem_words=True, breath=True),
    dict(exaggeration=0.5, max_new_tokens=350, problem_words=True),
    dict(exaggeration=0.35, max_new_tokens=300, problem_words=True, breath=True, lead=True),
]


def parse_range(s, all_nums):
    if not s or s == 'all':
        return set(all_nums)
    keep = set()
    for part in s.split(','):
        a, _, b = part.partition('-')
        keep |= set(range(int(a), int(b or a) + 1))
    return keep


def score_of(res, judges):
    accs = [res['judges'][j]['word_acc'] for j in judges if j in res.get('judges', {})]
    return sum(accs) / len(accs) if accs else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('job')
    ap.add_argument('--verses', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--music', action='append', default=None, help='folder or mp3 (repeatable)')
    ap.add_argument('--no-judge', action='store_true')
    ap.add_argument('--merge', nargs='*', default=[], help='output folders of earlier runs (e.g. parallel shards) to merge in first')
    args = ap.parse_args()

    job = json.load(open(args.job, encoding='utf8'))
    base = os.path.dirname(os.path.abspath(args.job))
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    out = os.path.abspath(args.out or job.get('out', 'out/' + job['id']))
    clips_dir = os.path.join(out, 'clips'); os.makedirs(clips_dir, exist_ok=True)
    state_path = os.path.join(out, 'state.json')
    state = json.load(open(state_path, encoding='utf8')) if os.path.exists(state_path) else {}
    save = lambda: json.dump(state, open(state_path, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    wav_path = lambda name: os.path.join(clips_dir, name)  # takes store file names; old runs stored full paths
    for d in args.merge:
        sp = os.path.join(d, 'state.json')
        if not os.path.exists(sp):
            print('merge: no state in', d, flush=True); continue
        for k, v in json.load(open(sp, encoding='utf8')).items():
            for tk in v['takes']:
                src = os.path.join(d, 'clips', os.path.basename(tk['wav']))
                tk['wav'] = os.path.basename(tk['wav'])
                if os.path.exists(src) and not os.path.exists(wav_path(tk['wav'])):
                    shutil.copy(src, wav_path(tk['wav']))
            state[k] = v
        print('merged', d, flush=True)
    save()
    problem_rows = tr.load_problem_words(os.path.join(base, job.get('problem_words', '../problem_words.csv')))
    pass_acc = job.get('pass_word_acc', 0.75)
    n_takes = max(1, int(job.get('takes', 1)))  # always make this many takes (different seeds); the best is kept
    ladder = [ATTEMPTS[0]] * n_takes + ATTEMPTS[1:]

    # ---- clip list ----
    clips = []  # (key, part, verse, half, text)
    for part in job['parts']:
        verses = tr.load_script(os.path.join(base, part['script']))
        keep = parse_range(args.verses or job.get('verses'), [v[0] for v in verses])
        for n, a, b in verses:
            if n in keep:
                for h, t in (('a', a), ('b', b)):
                    clips.append((f"{part['name']}_{n:03d}{h}", part, n, h, t))
    print(f"{len(clips)} half-verse clips", flush=True)

    voice = None

    def generate(key, text, part, attempt_no):
        nonlocal voice
        if voice is None:
            if job.get('engine') == 'torch':  # PyTorch Chatterbox, optionally with our retrained adapter
                from .tts_torch import VoiceTorch
                ad = job.get('adapter')
                voice = VoiceTorch(os.path.join(repo, job['voice']), adapter=os.path.join(repo, ad) if ad else None)
            else:
                from .tts import Voice
                voice = Voice(os.path.join(repo, job['voice']))
        a = ladder[attempt_no]
        tag, t = tr.split_tag(text)
        st = job.get('styles', {}).get(tag, {}) if tag else {}
        if not isinstance(st, dict):
            st = {'exaggeration': st}
        exag = st.get('exaggeration', a['exaggeration'])
        voice.use(os.path.join(repo, st.get('ref', job['voice'])))
        t = tr.apply_problem_words(t, problem_rows, part['name']) if a['problem_words'] else t
        t = tr.tajweed(t, job.get('tajweed'))
        if a.get('breath'):
            t = tr.add_breath(t)
        if a.get('lead') and not t.startswith('،'):
            t = '، ' + t
        wav = f"{key}_try{attempt_no}.wav"
        t0 = time.time()
        model_text = t if job.get('engine') == 'torch' else tr.for_model(t, job.get('text_prep', 'hamza_split'))
        info = voice.say(model_text, wav_path(wav), exaggeration=exag, max_new_tokens=a['max_new_tokens'],
                         seed=attempt_no * 7919 + sum(map(ord, key)))
        shape(wav_path(wav), st.get('speed', 1.0), st.get('semitones', 0.0), st.get('gain_db', 0.0))
        info.update(wav=wav, text=t, style=tag, exaggeration=exag, attempt=attempt_no, gen_seconds=round(time.time() - t0, 1))
        return info

    def judge_pending():
        if args.no_judge:
            return
        from .judge import JUDGES
        names = sorted({j for p in job['parts'] for j in p.get('judges', ['cohere'])})
        for jn in names:
            todo = [(k, tk) for k, s in state.items() for tk in s['takes']
                    if jn in s['judges_wanted'] and jn not in tk.get('judges', {})]
            if not todo:
                continue
            print(f"judge {jn}: {len(todo)} clips", flush=True)
            heard = JUDGES[jn]([wav_path(tk['wav']) for _, tk in todo])
            for (k, tk), h in zip(todo, heard):
                tk.setdefault('judges', {})[jn] = {'heard': h, **tr.compare(state[k]['script'], h)}
            save()

    # ---- round 0 + retries ----
    for rnd in range(len(ladder)):
        todo = []
        for key, part, n, h, text in clips:
            s = state.setdefault(key, {'part': part['name'], 'verse': n, 'half': h, 'script': text,
                                       'judges_wanted': part.get('judges', ['cohere']), 'takes': []})
            if s['script'] != text:  # script was edited since last run: start this clip over
                s.update(script=text, takes=[])
            tried = {tk['attempt'] for tk in s['takes']}
            if rnd in tried:
                continue
            good = [score_of(tk, s['judges_wanted']) for tk in s['takes'] if tk['hit_stop']]
            best = max(good, default=-1)
            if rnd < n_takes or (not args.no_judge and best < pass_acc):
                todo.append((key, part, text))
        if not todo:
            if rnd == 0:
                judge_pending()
            continue
        print(f"--- round {rnd}: generating {len(todo)} clips ---", flush=True)
        for i, (key, part, text) in enumerate(todo):
            info = generate(key, text, part, rnd)
            state[key]['takes'].append(info)
            print(f"[{i + 1}/{len(todo)}] {key} try{rnd} {info['seconds']}s audio in {info['gen_seconds']}s"
                  + ('' if info['hit_stop'] else ' (NO STOP - runaway?)'), flush=True)
            save()
        judge_pending()

    # ---- choose best take per clip ----
    for key, s in state.items():
        ok = [tk for tk in s['takes'] if tk['hit_stop']] or s['takes']
        best = max(ok, key=lambda tk: (score_of(tk, s['judges_wanted']), -tk['attempt']))
        s['chosen'] = best['wav']
        s['score'] = round(score_of(best, s['judges_wanted']), 3)
        s['flag'] = (not args.no_judge) and (s['score'] < pass_acc or not best['hit_stop'])
    save()

    # ---- assemble ----
    P = job['pauses']
    tracks = {}
    keys_by_part = {}
    for key, part, n, h, text in clips:
        keys_by_part.setdefault(part['name'], []).append((key, h))

    def files_pads(names, section_gap=False):
        files, pads = [], []
        for pi, pn in enumerate(names):
            for i, (key, h) in enumerate(keys_by_part[pn]):
                files.append(wav_path(state[key]['chosen']))
                pads.append(P['half'] if h == 'a' else P['verse'])
            if section_gap and pi < len(names) - 1:
                pads[-1] = P['section']
        return files, pads

    names = [p['name'] for p in job['parts']]
    combos = {n: [n] for n in names}
    if len(names) > 1:
        combos['_then_'.join(names)] = names
    for tname, parts in combos.items():
        f, p = files_pads(parts, section_gap=True)
        wav = os.path.join(out, f"{job['id']}_{tname}.wav")
        build_voice(f, p, wav, tempo=job.get('tempo', 0.8), lead=job.get('lead', 0.8),
                    smooth=job.get('smooth_joins', True))
        to_mp3(wav, wav[:-4] + '.mp3')
        tracks[tname] = wav

    music = []
    for m in (args.music or job.get('music', [])):
        music += [m] if m.endswith('.mp3') else sorted(glob.glob(os.path.join(m, '**', '*.mp3'), recursive=True))
    for mp in music:
        mname = os.path.splitext(os.path.basename(mp))[0]
        for tname, wav in tracks.items():
            mix_music(wav, mp, os.path.join(out, f"{job['id']}_{tname}__{mname}.mp3"))
    for wav in tracks.values():
        os.remove(wav)

    # ---- QA report ----
    write_report(job, state, clips, out, pass_acc, music)
    print("done:", out, flush=True)


def write_report(job, state, clips, out, pass_acc, music):
    rows, flagged, words = [], [], {}
    for key, *_ in clips:
        s = state[key]
        best = next(tk for tk in s['takes'] if tk['wav'] == s['chosen'])
        line = {'clip': key, 'score': s['score'], 'tries': len(s['takes']), 'chosen_try': best['attempt'],
                'script': s['script']}
        for jn, r in best.get('judges', {}).items():
            line[jn] = r['heard']
            for mm in r['mismatch']:
                if mm['expected']:
                    k = (s['part'], mm['expected'], mm['heard'])
                    words[k] = words.get(k, 0) + 1
        rows.append(line)
        if s['flag']:
            flagged.append(line)
    json.dump(rows, open(os.path.join(out, 'qa.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    with open(os.path.join(out, 'problem_words_found.csv'), 'w', encoding='utf8', newline='') as f:
        w = csv.writer(f); w.writerow(['part', 'expected', 'heard', 'count'])
        for (p, e, h), c in sorted(words.items(), key=lambda x: -x[1]):
            w.writerow([p, e, h, c])
    avg = sum(r['score'] for r in rows) / max(1, len(rows))
    from .score import score_pair, summarize
    pron = []
    for key, *_ in clips:
        s_ = state[key]
        best = next(tk for tk in s_['takes'] if tk['wav'] == s_['chosen'])
        h = best.get('judges', {}).get('clartts', {}).get('heard')
        if h:
            f, miss = score_pair(s_['script'], h)
            pron.append({'id': key, 'features': f, 'misses': miss})
    ppct, _ = summarize(pron) if pron else ({}, None)
    md = [f"# QA report — {job['title']}", '',
          f"- Clips: {len(rows)} · average judge word accuracy: {avg:.0%} · pass mark {pass_acc:.0%}",
          f"- Flagged for your ear: {len(flagged)}",
          f"- Music beds: {', '.join(os.path.basename(m) for m in music) or 'none'}",
          ('- Pronunciation score (%d clips): ' % len(pron) + ' · '.join(
              f"{n} {'–' if ppct.get(k) is None else str(ppct[k]) + '%'}" for k, n in
              (('overall', 'overall'), ('tanwin', 'tanwin'), ('shadda', 'shadda'), ('hamza', 'hamza'), ('heavy', 'heavy letters')))) if pron
          else '- Pronunciation score: n/a',
          '',
          '## Flagged clips', '']
    for r in flagged:
        md += [f"### {r['clip']} — {r['score']:.0%} (try {r['chosen_try']} of {r['tries']})",
               f"- script: {r['script']}"] + [f"- {j} heard: {r.get(j)}" for j in ('cohere', 'clartts') if r.get(j)] + ['']
    if pron:
        md += ['## Pronunciation misses (tanwin, shadda, hamza, heavy letters)', '']
        md += [f"- {p['id']}: " + '; '.join(f"{m['word']} ({m['feature']}) heard {m['heard']}" for m in p['misses'])
               for p in pron if p['misses']] + ['']
    md += ['## All clips', '', '| clip | score | tries |', '|---|---|---|']
    md += [f"| {r['clip']} | {r['score']:.0%} | {r['tries']} |" for r in rows]
    open(os.path.join(out, 'QA_REPORT.md'), 'w', encoding='utf8').write('\n'.join(md))


if __name__ == '__main__':
    main()
