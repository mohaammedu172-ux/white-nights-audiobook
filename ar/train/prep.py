"""Build the training set for retraining the voice's text reader (Chatterbox T3).

Each clip becomes: text tokens (official tokenizer, NFKD), speech tokens (S3 tokenizer, 25/s),
a speaker embedding (mean per speaker) and a pool of prompt-token snippets per speaker.

Sources
- ClArTTS (MBZUAI/ClArTTS, CC BY 4.0): ~12 h of fully vowelled classical Arabic, the reader our voice is based on.
- Husary murattal (Salama1429/tarteel-ai-everyayah-Quran, MIT): optional, verses <= MAX_SEC, private use only.

    python -m ar.train.prep --out /kaggle/working/data [--husary-hours 6] [--limit 0]
"""
import argparse, gc, json, os, random, re
import numpy as np, torch, librosa
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

MAX_SEC = 20.0
MIN_SEC = 1.0


def iter_clartts(fs, limit=0):
    base = 'datasets/MBZUAI/ClArTTS/data/'
    files = sorted(f for f in fs.ls(base, detail=False) if '/train-' in f)
    n = 0
    for f in files:
        for b in pq.ParquetFile(fs.open(f, block_size=16 * 2**20)).iter_batches(batch_size=32):
            for r in b.to_pylist():
                if not (MIN_SEC <= r['duration'] <= MAX_SEC):
                    continue
                a = np.asarray(r['audio'], dtype=np.float32)
                yield 'clartts', r['text'], a, r['sampling_rate']
                n += 1
                if limit and n >= limit:
                    return


def iter_husary(fs, hours, index_json=None):
    if hours <= 0:
        return
    base = 'datasets/Salama1429/tarteel-ai-everyayah-Quran/data/'
    files = sorted(f for f in fs.ls(base, detail=False) if f.endswith('.parquet'))
    if index_json and os.path.exists(index_json):  # optional: which files hold husary (saves scanning)
        keep = {p for p, recs, _ in json.load(open(index_json, encoding='utf8')) if 'husary' in recs}
        files = [f for f in files if f in keep] or files
    budget = hours * 3600.0
    for f in files:
        pf = pq.ParquetFile(fs.open(f, block_size=16 * 2**20))
        meta = pf.read(columns=['reciter', 'duration']).to_pylist()
        if not any(m['reciter'] == 'husary' for m in meta):
            continue
        pos = 0
        for b in pf.iter_batches(batch_size=20, columns=['audio', 'text', 'reciter', 'duration']):
            for r in b.to_pylist():
                pos += 1
                if r['reciter'] != 'husary' or not (MIN_SEC <= r['duration'] <= MAX_SEC):
                    continue
                a, sr = librosa.load(__import__('io').BytesIO(r['audio']['bytes']), sr=16000)
                yield 'husary', r['text'], a, sr
                budget -= r['duration']
                if budget <= 0:
                    return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--husary-hours', type=float, default=0.0)
    ap.add_argument('--husary-index', default=None)
    ap.add_argument('--limit', type=int, default=0, help='max ClArTTS clips (0 = all), for quick tests')
    ap.add_argument('--clartts-parquet', default=None, help='use a local ClArTTS parquet instead (tests)')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    m = ChatterboxMultilingualTTS.from_pretrained(dev)
    tok, s3, ve = m.tokenizer, m.s3gen.tokenizer, m.ve
    plen = m.t3.hp.speech_cond_prompt_len
    del m.t3
    gc.collect()

    fs = HfFileSystem()
    if args.clartts_parquet:
        def src():
            n = 0
            for b in pq.ParquetFile(args.clartts_parquet).iter_batches(batch_size=8):
                for r in b.to_pylist():
                    yield 'clartts', r['text'], np.asarray(r['audio'], dtype=np.float32), r['sampling_rate']
                    n += 1
                    if args.limit and n >= args.limit:
                        return
        sources = [src()]
    else:
        sources = [iter_clartts(fs, args.limit)]
    sources.append(iter_husary(fs, args.husary_hours, args.husary_index))

    items, spk_wavs, prompts = [], {}, {}
    for it in sources:
        for spk, text, a, sr in it:
            w = librosa.resample(a, orig_sr=sr, target_sr=16000) if sr != 16000 else a
            tt = tok.text_to_tokens(text, language_id='ar')[0].tolist()
            with torch.no_grad():
                st, sl = s3.forward([w])
            st = st[0, :sl[0]].cpu().tolist()
            if len(st) < 10:
                continue
            items.append({'spk': spk, 'text': text, 'tt': tt, 'st': st})
            if len(spk_wavs.setdefault(spk, [])) < 60:
                spk_wavs[spk].append(w)
            pr = prompts.setdefault(spk, [])
            if len(pr) < 400:
                with torch.no_grad():
                    p, _ = s3.forward([w[:16000 * 6]], max_len=plen)
                p = p[0].cpu().tolist()
                if len(p) >= plen // 2:
                    pr.append(p)
            if len(items) % 500 == 0:
                print(len(items), 'clips', {k: sum(1 for x in items if x['spk'] == k) for k in spk_wavs}, flush=True)

    spk_emb = {}
    for spk, ws in spk_wavs.items():
        e = ve.embeds_from_wavs(ws, sample_rate=16000)
        spk_emb[spk] = torch.from_numpy(e).mean(0).tolist()
    random.seed(0)
    random.shuffle(items)
    n_eval = max(2, len(items) // 50)
    torch.save({'train': items[n_eval:], 'eval': items[:n_eval], 'spk_emb': spk_emb, 'prompts': prompts},
               os.path.join(args.out, 'dataset.pt'))
    hours = {k: round(sum(len(x['st']) for x in items if x['spk'] == k) / 25 / 3600, 2) for k in spk_wavs}
    print('saved', len(items), 'clips; hours by speaker:', hours, flush=True)


if __name__ == '__main__':
    main()
