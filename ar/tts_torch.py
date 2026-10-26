"""Chatterbox Multilingual in PyTorch, optionally with our retrained adapter (ar/train). Same interface as ar.tts.Voice.

Uses the official text preparation (punctuation cleanup + NFKD inside the tokenizer), so the script text is passed as is.
Sampling is seeded per call, so the same text + seed gives the same audio; retries change the seed.
"""
import numpy as np, soundfile as sf, torch
import torch.nn.functional as F

SR = 24000


class VoiceTorch:
    def __init__(self, ref_wav, adapter=None, device=None, temperature=0.7, cfg_weight=0.5,
                 repetition_penalty=2.0, min_p=0.05, top_p=1.0):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        import chatterbox.models.t3.t3 as _t3mod
        _t3mod.tqdm = lambda it, *a, **k: it  # no progress bar per clip
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.m = ChatterboxMultilingualTTS.from_pretrained(self.device)
        if adapter:
            from .train.finetune import load_adapter
            load_adapter(self.m.t3, adapter)
            self.m.t3.to(self.device)
            print('voice adapter loaded:', adapter, flush=True)
        self.m.t3.eval()
        self.kw = dict(temperature=temperature, cfg_weight=cfg_weight, repetition_penalty=repetition_penalty,
                       min_p=min_p, top_p=top_p)
        self._conds = {}
        self.ref = None
        self.use(ref_wav)

    def use(self, ref_wav):
        self.ref = ref_wav

    def _cond(self, exaggeration):
        key = (self.ref, round(float(exaggeration), 3))
        if key not in self._conds:
            self.m.prepare_conditionals(self.ref, exaggeration=exaggeration)
            self._conds[key] = self.m.conds
        return self._conds[key]

    def say(self, text, out_wav, exaggeration=0.35, max_new_tokens=300, seed=0, tries=3, **_):
        """Generate; if the clip comes out far too short for its text (the model's own repetition guard sometimes
        ends a line early), try again with another seed. hit_stop=False tells the pipeline it still failed."""
        import re
        from chatterbox.mtl_tts import punc_norm
        from chatterbox.models.s3tokenizer import drop_invalid_tokens
        m, t3 = self.m, self.m.t3
        conds = self._cond(exaggeration)
        n_letters = len(re.findall('[\u0621-\u064A]', text))
        min_sec = 0.06 * n_letters
        best = None
        for k in range(tries):
            torch.manual_seed(seed + 1000 * k)
            tt = m.tokenizer.text_to_tokens(punc_norm(text), language_id='ar').to(self.device)
            tt = torch.cat([tt, tt], dim=0)  # conditional + unconditional rows for CFG
            tt = F.pad(F.pad(tt, (1, 0), value=t3.hp.start_text_token), (0, 1), value=t3.hp.stop_text_token)
            with torch.inference_mode():
                sp = t3.inference(t3_cond=conds.t3, text_tokens=tt, max_new_tokens=max_new_tokens, **self.kw)[0]
                n = sp.numel()
                sp = drop_invalid_tokens(sp).to(self.device)
                wav, _ = m.s3gen.inference(speech_tokens=sp, ref_dict=conds.gen)
            wav = wav.squeeze(0).detach().cpu().numpy()
            sec = len(wav) / SR
            ok = n < max_new_tokens and sec >= min_sec
            if best is None or (ok and not best[2]) or (ok == best[2] and sec > best[1]):
                best = (wav, sec, ok)
            if ok:
                break
        wav, sec, ok = best
        sf.write(out_wav, wav, SR)
        return {'seconds': round(sec, 2), 'hit_stop': bool(ok), 'tries': k + 1}
