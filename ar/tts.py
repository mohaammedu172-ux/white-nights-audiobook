"""Chatterbox Multilingual (ONNX) voice, loaded once and reused for every half-verse.

Adapted from the example script on the model card of onnx-community/chatterbox-multilingual-ONNX (MIT).
Greedy decoding with repetition penalty 1.2, so the same text + settings always give the same audio;
retries therefore change the text or the settings, not the random seed.
"""
import numpy as np, librosa, soundfile as sf, onnxruntime
from huggingface_hub import hf_hub_download
from transformers import AutoTokenizer

MODEL_ID = "onnx-community/chatterbox-multilingual-ONNX"
SR = 24000
START, STOP = 6561, 6562
LAYERS, KV_HEADS, HEAD_DIM = 30, 16, 64


def _providers():
    av = onnxruntime.get_available_providers()
    if 'CUDAExecutionProvider' in av:
        try:  # use the CUDA/cuDNN libraries that come with PyTorch on Kaggle
            import torch  # noqa: F401
            onnxruntime.preload_dlls()
        except Exception as e:
            print("preload_dlls:", e)
    return [p for p in ('CUDAExecutionProvider', 'CPUExecutionProvider') if p in av]


class Voice:
    def __init__(self, ref_wav, model_dir="/tmp/ar/chatterbox"):
        paths = {}
        for name in ("speech_encoder", "embed_tokens", "conditional_decoder", "language_model"):
            paths[name] = hf_hub_download(MODEL_ID, f"{name}.onnx", subfolder="onnx", local_dir=model_dir)
            hf_hub_download(MODEL_ID, f"{name}.onnx_data", subfolder="onnx", local_dir=model_dir)
        prov = _providers()
        print("onnx providers:", prov, flush=True)
        mk = lambda p: onnxruntime.InferenceSession(p, providers=prov)
        self.enc = mk(paths["speech_encoder"])
        self.emb = mk(paths["embed_tokens"])
        self.lm = mk(paths["language_model"])
        self.dec = mk(paths["conditional_decoder"])
        self.tok = AutoTokenizer.from_pretrained(MODEL_ID)
        self._refs = {}
        self.use(ref_wav)

    def use(self, ref_wav):
        """Switch the reference voice (cached). The voice copies the delivery style of the reference."""
        if ref_wav not in self._refs:
            ref, _ = librosa.load(ref_wav, sr=SR)
            self._refs[ref_wav] = self.enc.run(None, {"audio_values": ref[None, :].astype(np.float32)})
        self.cond = self._refs[ref_wav]

    def say(self, text, out_wav, exaggeration=0.35, max_new_tokens=300, penalty=1.2, **_):
        ids = self.tok(f"[ar]{text}", return_tensors="np")["input_ids"].astype(np.int64)
        pos = np.where(ids >= START, 0, np.arange(ids.shape[1])[None, :] - 1).astype(np.int64)
        feed = {"input_ids": ids, "position_ids": pos, "exaggeration": np.array([exaggeration], np.float32)}
        cond_emb, prompt_tok, xvec, pfeat = self.cond
        gen = np.array([[START]], dtype=np.int64)
        hit_stop = False
        for i in range(max_new_tokens):
            x = self.emb.run(None, feed)[0]
            if i == 0:
                x = np.concatenate((cond_emb, x), axis=1)
                past = {f"past_key_values.{l}.{kv}": np.zeros([1, KV_HEADS, 0, HEAD_DIM], np.float32)
                        for l in range(LAYERS) for kv in ("key", "value")}
                mask = np.ones((1, x.shape[1]), np.int64)
            logits, *present = self.lm.run(None, dict(inputs_embeds=x, attention_mask=mask, **past))
            logits = logits[:, -1, :]
            sc = np.take_along_axis(logits, gen, axis=1)
            sc = np.where(sc < 0, sc * penalty, sc / penalty)
            np.put_along_axis(logits, gen, sc, axis=1)
            nxt = np.argmax(logits, axis=-1, keepdims=True).astype(np.int64)
            gen = np.concatenate((gen, nxt), axis=-1)
            if nxt[0, 0] == STOP:
                hit_stop = True
                break
            feed["input_ids"] = nxt
            feed["position_ids"] = np.full((1, 1), i + 1, np.int64)
            mask = np.concatenate([mask, np.ones((1, 1), np.int64)], axis=1)
            for j, k in enumerate(past):
                past[k] = present[j]
        toks = gen[:, 1:-1] if hit_stop else gen[:, 1:]
        toks = np.concatenate([prompt_tok, toks], axis=1)
        wav = self.dec.run(None, {"speech_tokens": toks, "speaker_embeddings": xvec, "speaker_features": pfeat})[0]
        wav = np.squeeze(wav, 0)
        sf.write(out_wav, wav, SR)
        return {"seconds": round(len(wav) / SR, 2), "hit_stop": hit_stop}
