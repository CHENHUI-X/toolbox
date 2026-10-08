---
name: audio-transcription
description: Transcribe voice/audio messages to text (WeChat SILK, wav).
---

# 语音/音频转文字

## 触发条件
消息里出现 `[voice message could not be transcribed automatically; the audio is available at: /root/.hermes/cache/audio/*.silk]`（网关自带转写没成功），或用户发来 wav/mp3/amr/ogg 要文字。先尝试网关自带转写；本技能是**兜底**路径——把音频文件转成文字。

## 标准流程

### 1. 判断格式
微信语音是 **SILK v3**，文件头为 `\x02#!SILK_V3`。其它平台可能是 wav/mp3/ogg/amr，先 `head -c 10` 看魔术字节。

### 2. SILK → PCM（用 silk-python，不是 pilk）
```
pip install silk-python -q          # 提供 import pysilk；在 py3.14 下能装
# pilk / pysilk-mod 会 "Failed to build installable wheels"（Cython/C 轮子编不过），别在它们上耗时间
import pysilk
with open(src,'rb') as fi, open('/root/.hermes/cache/scratch/audio.pcm','wb') as fo:
    pysilk.decode(fi, fo, 24000)     # (输入文件对象, 输出文件对象, 采样率)
```
- 采样率试 **24000**（微信常用），不行再试 16000/12000/8000；解码成功时 PCM 字节数 ≈ 时长秒 × 采样率 × 2（16bit 单声道）。字节数只有几百 = 采样率不对。
- `pysilk.decode` 只吃**文件对象**，不是路径/bytes。

### 3. PCM → WAV（ffmpeg 在本机的固定路径）
```
/root/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg -y -f s16le -ar 24000 -ac 1 -i audio.pcm audio.wav
```

### 4. STT（Groq，OpenAI 兼容）
```
curl -s -X POST https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -F file=@audio.wav -F model=whisper-large-v3 -F language=zh -F response_format=json
```
返回 JSON 的 `text` 即转写结果。

## 坑（都实际踩过）
- **读 .env 里的 Groq key 必须只匹配"生效"那一行**：`~/.hermes/.env` 里同时有注释占位 `# GROQ_API_KEY=` 和真正的 `export GROQ_API_KEY=...`。朴素正则 `GROQ_API_KEY\s*=` 会先命中注释行 → 空 key → `Invalid API Key`。用 `re.search(r'export\s+GROQ_API_KEY\s*=\s*["\']?([^\s"\'\n]+)', env)`（或先过滤掉 `#` 开头行）取，key 取出后先 strip 再验。
- 微信 .silk 常自带 `\x02#!SILK_V3` 头；pysilk 能直接吃带头文件，通常无需手动剥离。
- 转写结果可能有同音错字（如「妞妞/牛牛」「兑换/对接」），按上下文还原意思后再答，别照抄错字。

## 交付
把转写文字**先回显给用户确认**（尤其带同音错字时），再执行语音里的指令，别默默按猜的做。
