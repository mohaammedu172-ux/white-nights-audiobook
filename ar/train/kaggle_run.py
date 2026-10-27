"""Everything the Kaggle notebook does, kept in the repo so the notebook cell never has to change.

    python -m ar.train.kaggle_run [--husary-hours 6] [--steps 3000] [--batch 8] [--keep 1500,3000]

1) build the training set (skipped if it exists)  2) train (skipped if the final adapter exists)
3) listening test: original voice / step 1500 / step 3000 / step 3000 with more careful sound choices
4) if GITHUB_TOKEN is set (from Kaggle Secrets), save adapters + log + mp3 to the branch voice-adapter
"""
import argparse, datetime, os, shutil, subprocess, sys

W = '/kaggle/working'


def run(cmd):
    print('>>', cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


def push(files, repo_url):
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M')
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
    ap.add_argument('--husary-hours', type=float, default=6)
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--keep', default='1500,3000', help='checkpoints to test and save')
    ap.add_argument('--repo', default='github.com/mohaammedu172-ux/white-nights-audiobook.git')
    a = ap.parse_args()
    py = sys.executable
    if not os.path.exists(f'{W}/data/dataset.pt'):
        run(f'{py} -m ar.train.prep --out {W}/data --husary-hours {a.husary_hours} --husary-index ar/train/tarteel_index.json')
    if not os.path.exists(f'{W}/adapter/adapter_{a.steps}.pt'):
        run(f'{py} -m ar.train.finetune --data {W}/data/dataset.pt --out {W}/adapter --steps {a.steps} --batch {a.batch}')
    keep = [int(x) for x in a.keep.split(',') if x]
    var = ['--variant base=none@0.7'] + [f'--variant step{k}={W}/adapter/adapter_{k}.pt@0.7' for k in keep]
    var.append(f'--variant step{keep[-1]}_careful={W}/adapter/adapter_{keep[-1]}.pt@0.5')
    run(f'{py} -m ar.train.samples {" ".join(var)} --out {W}/samples')
    tok = os.environ.get('GITHUB_TOKEN', '')
    files = [f'{W}/adapter/adapter_{k}.pt' for k in keep] + [f'{W}/adapter/train_log.txt',
             f'{W}/samples/before_after.mp3', f'{W}/samples/samples.json']
    if tok:
        push(files, f'https://x-access-token:{tok}@{a.repo}')
    else:
        print('No GITHUB_TOKEN secret: download the files from the Output tab instead.', flush=True)
    print('ALL DONE', flush=True)


if __name__ == '__main__':
    main()
