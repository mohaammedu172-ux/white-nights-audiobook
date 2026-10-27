"""Everything the Kaggle notebook does, kept in the repo so the notebook cell never has to change.

    python -m ar.train.kaggle_run

Run 2: a fair test of one thing only, how much Quran recitation to mix in. Same settings as run 1 (rank 32, lr 1e-4),
2000 steps (run 1 stopped improving there).
1) training set: ClArTTS + 6 h al-Husary (skipped if it exists)
2) adapter "clartts": al-Husary weight 0 (never drawn)   adapter "mix": al-Husary weight 0.15 (a small share)
3) blind listening test (ar/train/abtest.py): 12 hard lines, original voice vs the two adapters, 3 seeds each
4) if GITHUB_TOKEN is set (Kaggle Secrets), save adapters + test to the branch voice-adapter
"""
import argparse, datetime, os, shutil, subprocess, sys

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
    ap.add_argument('--steps', type=int, default=2000)
    ap.add_argument('--repo', default='github.com/mohaammedu172-ux/white-nights-audiobook.git')
    a = ap.parse_args()
    py = sys.executable
    data = f'{W}/data'
    if not os.path.exists(f'{data}/dataset.pt'):
        run(f'{py} -m ar.train.prep --out {data} --husary-hours 6 --husary-index ar/train/tarteel_index.json')
    arms = {'clartts': 0.0, 'mix': 0.15}
    for name, w in arms.items():
        out = f'{W}/adapter_{name}'
        if not os.path.exists(f'{out}/adapter_{a.steps}.pt'):
            run(f'{py} -m ar.train.finetune --data {data}/dataset.pt --out {out} --steps {a.steps} --batch 8 '
                f'--rank 32 --husary-weight {w} --save-every 1000')
    var = ' '.join(['--variant base=none'] + [f'--variant {n}={W}/adapter_{n}/adapter_{a.steps}.pt' for n in arms])
    run(f'{py} -m ar.train.abtest {var} --out {W}/abtest')
    os.makedirs(f'{W}/samples', exist_ok=True)  # the notebook cell plays samples/before_after.mp3 at the end
    shutil.copy(f'{W}/abtest/blind_test.mp3', f'{W}/samples/before_after.mp3')
    tok = os.environ.get('GITHUB_TOKEN', '')
    for n in arms:  # keep the two training logs apart
        p = f'{W}/adapter_{n}/train_log.txt'
        if os.path.exists(p):
            shutil.copy(p, f'{W}/adapter_{n}/train_log_{n}.txt')
    files = [f'{W}/adapter_{n}/adapter_{a.steps}.pt' for n in arms] + [f'{W}/adapter_{n}/train_log_{n}.txt' for n in arms]
    files += [f'{W}/abtest/blind_test.mp3', f'{W}/abtest/key.json']
    if tok:
        push(files, f'https://x-access-token:{tok}@{a.repo}', 'run2')
    else:
        print('No GITHUB_TOKEN secret: download blind_test.mp3 and key.json from the Output tab.', flush=True)
    print('ALL DONE', flush=True)


if __name__ == '__main__':
    main()
