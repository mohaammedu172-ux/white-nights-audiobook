#!/bin/bash
# One-time per Kaggle session for the Arabic (Mu'allaqat) pipeline.
set -e
pip -q uninstall -y onnxruntime >/dev/null 2>&1 || true
pip -q install "onnxruntime-gpu>=1.22" "transformers>=5.20" "huggingface_hub>=1.0" librosa soundfile
python - <<'P'
import onnxruntime, transformers, torch
print("onnxruntime", onnxruntime.__version__, onnxruntime.get_available_providers())
print("transformers", transformers.__version__, "| torch", torch.__version__, "| cuda", torch.cuda.is_available())
from transformers import CohereAsrForConditionalGeneration  # judge model class must exist
P
echo installed
