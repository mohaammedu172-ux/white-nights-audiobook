"""Retrain the voice's text reader (Chatterbox T3) with LoRA so it pronounces vowelled classical Arabic properly.

Only small add-on weights are trained (LoRA on the transformer + the text embedding table), saved as one
adapter file of a few dozen MB. The speech decoder and voice encoder are untouched, so the voice stays the same.

    python -m ar.train.finetune --data /kaggle/working/data/dataset.pt --out /kaggle/working/adapter \
        --steps 3000 --batch 8 [--husary-weight 0.5]
"""
import argparse, math, os, random, time
import torch, torch.nn.functional as F

LORA_TARGETS = ['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']


def load_base(device):
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    m = ChatterboxMultilingualTTS.from_pretrained(device)
    return m


def add_lora(t3, r=32, alpha=64, dropout=0.05):
    from peft import LoraConfig, get_peft_model
    t3.tfmr = get_peft_model(t3.tfmr, LoraConfig(r=r, lora_alpha=alpha, lora_dropout=dropout, target_modules=LORA_TARGETS))
    t3.text_emb.weight.requires_grad_(True)
    return t3


def adapter_state(t3):
    from peft import get_peft_model_state_dict
    return {'lora': {k: v.detach().half().cpu() for k, v in get_peft_model_state_dict(t3.tfmr).items()},
            'text_emb': t3.text_emb.weight.detach().half().cpu()}


def load_adapter(t3, path):
    """Apply a saved adapter to a base T3 (used by the torch voice backend)."""
    from peft import set_peft_model_state_dict
    sd = torch.load(path, map_location='cpu')
    cfg = sd.get('config', {})
    add_lora(t3, r=cfg.get('r', 32), alpha=cfg.get('alpha', 64), dropout=0.0)
    set_peft_model_state_dict(t3.tfmr, {k: v.float() for k, v in sd['lora'].items()})
    with torch.no_grad():
        t3.text_emb.weight.copy_(sd['text_emb'].float())
    return t3


def make_batch(items, data, hp, device):
    from chatterbox.models.t3.modules.cond_enc import T3Cond
    sot, eot, sos, eos = hp.start_text_token, hp.stop_text_token, hp.start_speech_token, hp.stop_speech_token
    tt = [[sot] + x['tt'] + [eot] for x in items]
    st = [[sos] + x['st'] + [eos] for x in items]
    tl, sl = [len(t) for t in tt], [len(s) for s in st]
    T, S = max(tl), max(sl)
    text = torch.tensor([t + [eot] * (T - len(t)) for t in tt], device=device)
    speech = torch.tensor([s + [eos] * (S - len(s)) for s in st], device=device)
    spk = torch.tensor([data['spk_emb'][x['spk']] for x in items], device=device)
    plen = hp.speech_cond_prompt_len
    pr = []
    for x in items:
        p = random.choice(data['prompts'][x['spk']])
        pr.append((p + p * plen)[:plen])
    cond = T3Cond(speaker_emb=spk, cond_prompt_speech_tokens=torch.tensor(pr, device=device),
                  emotion_adv=0.5 * torch.ones(len(items), 1, 1, device=device))
    return cond, text, torch.tensor(tl, device=device), speech, torch.tensor(sl, device=device)


def step_loss(t3, batch, text_weight=0.1):
    cond, text, tl, speech, sl = batch
    out = t3.forward(t3_cond=cond, text_tokens=text, text_token_lens=tl, speech_tokens=speech,
                     speech_token_lens=sl, training=True)
    # next-token targets; positions past each clip's length are ignored
    ts = speech[:, 1:].clone()
    ts[torch.arange(ts.size(1), device=ts.device)[None] >= (sl - 1)[:, None]] = -100
    tt = text[:, 1:].clone()
    tt[torch.arange(tt.size(1), device=tt.device)[None] >= (tl - 1)[:, None]] = -100
    ls = F.cross_entropy(out.speech_logits[:, :-1].transpose(1, 2).float(), ts, ignore_index=-100)
    lt = F.cross_entropy(out.text_logits[:, :-1].transpose(1, 2).float(), tt, ignore_index=-100)
    return ls, lt, ls + text_weight * lt


def batches(items, batch, husary_weight, rng, max_tokens=2400):
    """Length-bucketed random batches capped by total speech tokens (25 per second), so long clips come in
    smaller batches and the GPU doesn't run out of memory. husary_weight scales how often Quran clips are drawn."""
    w = [husary_weight if x['spk'] == 'husary' else 1.0 for x in items]
    while True:
        pick = rng.choices(range(len(items)), weights=w, k=batch * 50)
        pick.sort(key=lambda i: len(items[i]['st']))
        groups, cur = [], []
        for i in pick:
            L = len(items[i]['st']) + 2
            if cur and (len(cur) >= batch or (len(cur) + 1) * max(L, max(len(items[j]['st']) + 2 for j in cur)) > max_tokens):
                groups.append(cur); cur = []
            cur.append(i)
        if cur:
            groups.append(cur)
        rng.shuffle(groups)
        for g in groups:
            yield [items[i] for i in g]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--accum', type=int, default=1)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--rank', type=int, default=32)
    ap.add_argument('--husary-weight', type=float, default=0.5)
    ap.add_argument('--eval-every', type=int, default=250)
    ap.add_argument('--save-every', type=int, default=500)
    ap.add_argument('--resume', default=None, help='adapter file to continue from')
    ap.add_argument('--max-tokens', type=int, default=2400, help='speech tokens per batch (padded); lower if out of GPU memory')
    ap.add_argument('--no-checkpointing', action='store_true')
    args = ap.parse_args()
    os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')  # read at the first GPU allocation
    os.makedirs(args.out, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    torch.manual_seed(0)
    rng = random.Random(0)

    data = torch.load(args.data)
    m = load_base(dev)
    t3 = m.t3
    del m.s3gen, m.ve
    import gc; gc.collect()
    for p in t3.parameters():
        p.requires_grad_(False)
    if args.resume:
        load_adapter(t3, args.resume)
        t3.text_emb.weight.requires_grad_(True)
    else:
        add_lora(t3, r=args.rank, alpha=2 * args.rank)
    t3.tfmr.print_trainable_parameters()
    if not args.no_checkpointing:  # recompute activations in the backward pass: far less GPU memory, ~30% slower
        t3.tfmr.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    t3.train()
    params = [p for p in t3.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    warm = max(1, min(100, args.steps // 10))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / args.steps))))
    use_amp = dev == 'cuda'
    scaler = torch.amp.GradScaler('cuda', enabled=use_amp)
    gen = batches(data['train'], args.batch, args.husary_weight, rng, args.max_tokens)
    log = open(os.path.join(args.out, 'train_log.txt'), 'a')

    def evaluate():
        t3.eval()
        tot, n = 0.0, 0
        with torch.no_grad(), torch.autocast(dev, dtype=torch.float16, enabled=use_amp):
            ev = sorted(data['eval'], key=lambda x: len(x['st']))
            eb = max(1, args.batch // 2)
            for i in range(0, len(ev), eb):
                ls, _, _ = step_loss(t3, make_batch(ev[i:i + eb], data, t3.hp, dev))
                tot += ls.item() * len(ev[i:i + eb]); n += len(ev[i:i + eb])
        t3.train()
        return tot / max(1, n)

    def save(tag):
        sd = adapter_state(t3)
        sd['config'] = {'r': args.rank, 'alpha': 2 * args.rank, 'targets': LORA_TARGETS, 'steps': tag}
        path = os.path.join(args.out, f'adapter_{tag}.pt')
        torch.save(sd, path)
        torch.save(sd, os.path.join(args.out, 'adapter_latest.pt'))
        return path

    first = evaluate()
    print(f'eval speech loss before training: {first:.4f}', flush=True); log.write(f'eval 0 {first:.4f}\n')
    t0 = time.time()
    for step in range(1, args.steps + 1):
        for _ in range(args.accum):
            b = make_batch(next(gen), data, t3.hp, dev)
            with torch.autocast(dev, dtype=torch.float16, enabled=use_amp):
                ls, lt, loss = step_loss(t3, b)
            scaler.scale(loss / args.accum).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        scaler.step(opt); scaler.update(); opt.zero_grad(set_to_none=True); sched.step()
        if step % 25 == 0:
            msg = f'step {step} speech {ls.item():.4f} text {lt.item():.4f} lr {sched.get_last_lr()[0]:.2e} {time.time() - t0:.0f}s'
            print(msg, flush=True); log.write(msg + '\n'); log.flush()
        if step % args.eval_every == 0 or step == args.steps:
            e = evaluate()
            print(f'eval {step}: {e:.4f}', flush=True); log.write(f'eval {step} {e:.4f}\n'); log.flush()
        if step % args.save_every == 0 or step == args.steps:
            print('saved', save(step), flush=True)
    print('TRAINING DONE', flush=True)


if __name__ == '__main__':
    main()
