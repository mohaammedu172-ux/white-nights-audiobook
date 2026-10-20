"""Offline test of the audition and chapter jobs with fake voice generation + fake checks (no GPU): python tools/smoke_test.py"""
import os, sys, json, random, numpy as np, soundfile as sf
os.environ["WN_OUT"]="/tmp/wn_t/out"; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wn import run, tts, qc, voices
def fake_gen(jobs, *a, **k):
    for j in jobs:
        os.makedirs(os.path.dirname(j["path"]),exist_ok=True)
        n=len(j["text"].split()); t=np.arange(int(24000*n*0.3))/24000
        sf.write(j["path"],0.2*np.sin(2*np.pi*180*t),24000)
    return len(jobs)
random.seed(0)
def fake_check(path,text): 
    c=random.choice([0.95,0.95,0.7]); return dict(clarity=c,extra=0.0,seconds=1,rate=random.uniform(2.5,3.2),heard=text)
def fake_build(out):
    v=f"{out}/voices"; os.makedirs(v,exist_ok=True)
    for n in voices.ALL: sf.write(f"{v}/{n}.wav",np.zeros(24000)+0.01,24000)
    return v
tts.generate=fake_gen; qc.check=fake_check; voices.build=fake_build
run.audition()
run.CFG["voices"]["2"]="nastenka_A_single"; run.CFG["paragraphs"]=[15,24]; run.CFG["mix"]["music"]=False
run.chapter()
run.CFG["voices"]["2"]=None
run.settings()
