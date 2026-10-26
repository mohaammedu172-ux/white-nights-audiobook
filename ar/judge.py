"""Speech-recognition 'judges' that listen to each clip and write down what they heard.

- cohere: NAMAA-Space/Cohere-Speech-Tashkeel-2B (Apache-2.0) - transcribes with vowel marks. Used for everything.
- clartts: rufaelfekadu/diactc-wav2vec2-clartts (MIT) - trained on classical recitation. Used for the original verses.
Each judge is loaded, run over the whole batch, then freed, so they never sit in memory together.
"""
import gc, torch, librosa


def _device():
    return "cuda" if torch.cuda.is_available() else "cpu"


def run_cohere(wavs):
    from transformers import AutoProcessor, CohereAsrForConditionalGeneration
    repo = "NAMAA-Space/Cohere-Speech-Tashkeel-2B"
    dev = _device()
    dt = torch.float16 if dev == "cuda" else torch.bfloat16
    proc = AutoProcessor.from_pretrained(repo)
    model = CohereAsrForConditionalGeneration.from_pretrained(repo, dtype=dt).to(dev).eval()
    prompt = torch.tensor([proc.get_decoder_prompt_ids(language="ar", punctuation=True)], dtype=torch.long)
    out = []
    for w in wavs:
        a, _ = librosa.load(w, sr=16000)
        f = proc.feature_extractor([a], sampling_rate=16000, return_tensors="pt", padding="longest", return_attention_mask=True)
        idx = f.pop("audio_chunk_index")
        with torch.no_grad():
            g = model.generate(input_features=f["input_features"].to(dev, dt), attention_mask=f["attention_mask"].to(dev),
                               decoder_input_ids=prompt.to(dev), max_new_tokens=200)
        h = proc.decode(g.cpu(), skip_special_tokens=True, audio_chunk_index=idx, language="ar")
        out.append(h[0] if isinstance(h, list) else h)
    del model; gc.collect()
    if dev == "cuda": torch.cuda.empty_cache()
    return out


def run_clartts(wavs):
    from transformers import AutoProcessor, Wav2Vec2ForCTC
    repo = "rufaelfekadu/diactc-wav2vec2-clartts"
    dev = _device()
    proc = AutoProcessor.from_pretrained(repo)
    model = Wav2Vec2ForCTC.from_pretrained(repo).to(dev).eval()
    out = []
    for w in wavs:
        a, _ = librosa.load(w, sr=16000)
        x = proc.feature_extractor(a, sampling_rate=16000, return_tensors="pt").input_values.to(dev)
        with torch.no_grad():
            ids = model(x).logits.argmax(-1)[0].tolist()
        out.append(proc.tokenizer.decode(ids))
    del model; gc.collect()
    if dev == "cuda": torch.cuda.empty_cache()
    return out


JUDGES = {"cohere": run_cohere, "clartts": run_clartts}
