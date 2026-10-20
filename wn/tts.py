"""VibeVoice 1.5B, one line per generation. Runs in a subprocess with its own pinned libraries (/tmp/wn/vvlib).

A job = {"text", "voice" (wav path), "seed", "path" (output wav)}. Jobs whose output exists are skipped.
"""
import json, os, subprocess, sys, time

MODEL = "/tmp/wn/models/VibeVoice-1.5B"

WORKER = r'''
import sys, json, os
sys.path.insert(0, "/tmp/wn/vvlib"); sys.path.insert(1, "/tmp/wn/VibeVoice")
import torch
from vibevoice.modular.modeling_vibevoice_inference import VibeVoiceForConditionalGenerationInference
from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
cfg = json.load(open(sys.argv[1]))
processor = VibeVoiceProcessor.from_pretrained(cfg["model"])
DT = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[cfg.get("dtype", "bf16")]
model = VibeVoiceForConditionalGenerationInference.from_pretrained(cfg["model"], torch_dtype=DT, device_map="cuda", attn_implementation="sdpa")
model.eval(); model.set_ddpm_inference_steps(num_steps=cfg["steps"])
for job in cfg["jobs"]:
    if os.path.exists(job["path"]): continue
    os.makedirs(os.path.dirname(job["path"]), exist_ok=True)
    torch.manual_seed(job["seed"]); torch.cuda.manual_seed_all(job["seed"])
    inputs = processor(text=["Speaker 1: " + job["text"]], voice_samples=[[job["voice"]]], padding=True, return_tensors="pt", return_attention_mask=True)
    inputs = {k: (v.to("cuda") if torch.is_tensor(v) else v) for k, v in inputs.items()}
    out = model.generate(**inputs, max_new_tokens=None, cfg_scale=cfg["cfg_scale"], tokenizer=processor.tokenizer,
                         generation_config={"do_sample": False}, verbose=False)
    processor.save_audio(out.speech_outputs[0], output_path=job["path"])
    print("saved", job["path"], flush=True)
'''


def generate(jobs, cfg_scale=1.3, steps=10, dtype="bf16", log="/tmp/wn"):
    jobs = [j for j in jobs if not os.path.exists(j["path"])]
    if not jobs: return 0
    os.makedirs(log, exist_ok=True); open(f"{log}/vv_worker.py", "w").write(WORKER)
    out = subprocess.run("nvidia-smi -L | wc -l", shell=True, capture_output=True, text=True).stdout.strip()
    ngpu = max(1, int(out or 1))
    load, buckets = [0] * ngpu, [[] for _ in range(ngpu)]
    for j in sorted(jobs, key=lambda j: -len(j["text"])):               # balance work across GPUs
        g = load.index(min(load)); buckets[g].append(j); load[g] += len(j["text"])
    t0, procs = time.time(), []
    for g, bj in enumerate(buckets):
        if not bj: continue
        json.dump({"model": MODEL, "steps": steps, "cfg_scale": cfg_scale, "dtype": dtype, "jobs": bj}, open(f"{log}/jobs{g}.json", "w"))
        procs.append(subprocess.Popen([sys.executable, f"{log}/vv_worker.py", f"{log}/jobs{g}.json"],
                                      env={**os.environ, "CUDA_VISIBLE_DEVICES": str(g)},
                                      stdout=open(f"{log}/worker{g}.log", "w"), stderr=subprocess.STDOUT))
    while any(p.poll() is None for p in procs):
        time.sleep(30)
        print(f"  {(time.time() - t0) / 60:.0f} min: {sum(os.path.exists(j['path']) for j in jobs)}/{len(jobs)} takes", flush=True)
    done = sum(os.path.exists(j["path"]) for j in jobs)
    if done < len(jobs):
        for g in range(len(procs)): print(open(f"{log}/worker{g}.log").read()[-2000:])
    print(f"  generated {done}/{len(jobs)} takes in {(time.time() - t0) / 60:.1f} min")
    return done
