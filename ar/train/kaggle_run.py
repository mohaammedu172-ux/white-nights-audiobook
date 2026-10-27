"""Everything the Kaggle notebook does, kept in the repo so the notebook cell never has to change.

    python -m ar.train.kaggle_run

Run 2 ("recipe B"):
1) training set: ClArTTS only, no Quran recitation (skipped if it exists)
2) train a bigger add-on (rank 64) for 2000 steps (run 1 stopped improving around 2000)
3) bake-off on 40 half-verses: original voice without / with tajweed spellings, run-1 adapter (if attached as input),
   recipe B at 1000 and 2000 steps, and every "best take per line" combination (ar/train/bakeoff.py)
4) if GITHUB_TOKEN is set (Kaggle Secrets), save adapters + report + mp3s to the branch voice-adapter
"""
import argparse, datetime, glob, os, shutil, subprocess, sys

W = '/kaggle/working'


def run(cmd):
    print('>>', cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def push(files, repo_url, label):
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M') + '-' + label
    d = f'{W}/push'
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(f'{d}/adapters/{stamp}')
    for f in files:
        if os.path.exists(f):
            shutil.copy(f, f'{d}/adapters/{stamp}/')
    cmds = (f'cd {d} && git init -q -b voice-adapter && git remote add origin {repo_url} && '
            f'(git fetch -q --depth 1 origin voice-adapter && git reset -q --soft FETCH_HEAD || true) && '
            f'git add adapters && git -c user.name=kaggle -c user.email=kaggle@users.noreply.github.com '
            f'commit -qm "Voice adapter {stamp}" && git push -q origin voice-adapter')
    r = subprocess.run(cmds, shell=True, capture_output=True, text=True)
    print(r.stderr[-800:].replace(repo_url, '<repo>') or f'saved to GitHub: voice-adapter/adapters/{stamp}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--husary-hours', type=float, default=0)
    ap.add_argument('--steps', type=int, default=2000)
    ap.add_argument('--rank', type=int, default=64)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--keep', default='1000,2000')
    ap.add_argument('--repo', default='github.com/mohaammedu172-ux/white-nights-audiobook.git')
    a = ap.parse_args()
    py = sys.executable
    data, ad = f'{W}/data_b', f'{W}/adapter_b'
    if not os.path.exists(f'{data}/dataset.pt'):
        run(f'{py} -m ar.train.prep --out {data} --husary-hours {a.husary_hours} --husary-index ar/train/tarteel_index.json')
    if not os.path.exists(f'{ad}/adapter_{a.steps}.pt'):
        run(f'{py} -m ar.train.finetune --data {data}/dataset.pt --out {ad} --steps {a.steps} --batch {a.batch} '
            f'--rank {a.rank} --husary-weight 0 --save-every 500')
    keep = [int(x) for x in a.keep.split(',') if x]
    var = ['--variant base=none']
    old = sorted(glob.glob('/kaggle/input/**/adapter_3000.pt', recursive=True))  # run 1, if its output is attached
    if old:
        var.append(f'--variant run1_step3000={old[0]}')
    var += [f'--variant b{k}={ad}/adapter_{k}.pt' for k in keep]
    run(f'{py} -m ar.train.bakeoff --plain {" ".join(var)} --out {W}/bakeoff --verses 1-20')
    # the notebook cell plays samples/before_after.mp3 at the end
    os.makedirs(f'{W}/samples', exist_ok=True)
    best = f'{W}/bakeoff/best_takes_5_verses.mp3'
    if os.path.exists(best):
        shutil.copy(best, f'{W}/samples/before_after.mp3')
    tok = os.environ.get('GITHUB_TOKEN', '')
    files = [f'{ad}/adapter_{k}.pt' for k in keep] + [f'{ad}/train_log.txt'] + \
        [f'{W}/bakeoff/{f}' for f in ('report.md', 'takes.json', 'best_takes_5_verses.mp3', 'original_voice_5_verses.mp3')]
    if tok:
        push(files, f'https://x-access-token:{tok}@{a.repo}', 'recipeB')
    else:
        print('No GITHUB_TOKEN secret: download the files from the Output tab instead.', flush=True)
    print('ALL DONE', flush=True)


if __name__ == '__main__':
    main()
