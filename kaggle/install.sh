#!/bin/bash
# One-time per Kaggle session: speech recognition + audio tools, VibeVoice code, its pinned libraries, the model.
set -e
pip -q install openai-whisper pydub pyarrow "audioop-lts; python_version>='3.13'" ml-collections absl-py
mkdir -p /tmp/wn
[ -d /tmp/wn/VibeVoice ] || git clone --quiet --depth 1 https://github.com/vibevoice-community/VibeVoice.git /tmp/wn/VibeVoice
[ -d /tmp/wn/vvlib/transformers ] || pip -q install --no-deps --target /tmp/wn/vvlib "transformers==4.51.3" "tokenizers==0.21.1" "huggingface_hub==0.30.2" "accelerate==1.6.0" "diffusers==0.33.1"
[ -f /tmp/wn/models/VibeVoice-1.5B/config.json ] || python -c "from huggingface_hub import snapshot_download; snapshot_download('microsoft/VibeVoice-1.5B', local_dir='/tmp/wn/models/VibeVoice-1.5B')"
echo installed
