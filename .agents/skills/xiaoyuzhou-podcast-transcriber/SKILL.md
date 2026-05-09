---
name: "xiaoyuzhou-podcast-transcriber"
description: "Downloads Xiaoyuzhou podcasts, transcribes using FunASR, and generates raw, structured, and optimized text files. Invoke when user provides a Xiaoyuzhou episode link."
---

# 小宇宙播客转写助手 (Xiaoyuzhou Podcast Transcriber)

本 Skill 自动化将小宇宙 (Xiaoyuzhou) 播客单集转换为高质量文本归档的流程。

## 核心能力 (Capabilities)

1.  **下载 (Download)**：从小宇宙单集页面提取并下载音频。
2.  **转写 (Transcribe)**：使用本地部署的 Alibaba FunASR (Paraformer) 模型，实现高精度的中文语音识别。
3.  **处理 (Process)**：生成三个层级的文档：
    - `transcript_raw.txt`：逐字逐句的原始文本 (Raw Text)。
    - `podcast_full_structured.md`：保留全文但优化了可读性（包含标题、分段）的结构化文稿。
    - `podcast_optimized.md`：精简、润色后的精华摘要 (Summary) 和 Show Note。

## 前置条件 (Prerequisites)

- **Python 3.8+**
- **FFmpeg** (必须安装并添加到系统 PATH)
- **Internet Connection** (用于下载音频和模型文件)

## 工作流指南 (Workflow Instructions)

请按以下顺序执行任务。

### 第一阶段：准备与下载 (Preparation & Download)

1.  **提取音频 URL (Extract Audio URL)**：
    - 获取提供的小宇宙 (Xiaoyuzhou) 单集页面的 HTML。
    - 查找音频文件 URL（通常是 `mp3`, `m4a` 格式）。特征模式通常包含 `https://media.xyzcdn.net/...`。
    - _提示_：使用 `curl` 获取 HTML 并用 `grep` 提取 URL。

2.  **下载音频 (Download Audio)**：
    - 将音频文件下载为 `podcast.m4a` (或 `podcast.mp3`)。

3.  **格式转换与切片 (Convert & Chunk)**：
    - 将音频转换为 16kHz 单声道 WAV 格式（FunASR 模型要求）。
    - 将音频切分为 5 分钟的片段 (Chunks)，以确保稳定性并降低内存占用。
    - 命令示例：
      ```bash
      ffmpeg -i podcast.m4a -ar 16000 -ac 1 podcast.wav
      mkdir -p chunks
      ffmpeg -i podcast.wav -f segment -segment_time 300 -c copy chunks/part%03d.wav
      ```

### 第二阶段：本地转写 (Local Transcription with FunASR)

1.  **环境配置 (Environment Setup)**：
    - 如果不存在，创建一个 Python 虚拟环境 (`venv`)。
    - 安装必要的包：`modelscope`, `funasr`, `torch`, `torchaudio`。
    - _注意_：使用 `pip install modelscope funasr torch torchaudio`。

2.  **编写转写脚本 (Transcription Script)**：
    - 创建一个名为 `transcribe_chunked.py` 的 Python 脚本，包含以下逻辑：

      ```python
      import os
      import glob
      import traceback
      from funasr.auto.auto_model import AutoModel

      # Model Definitions (模型定义)
      model_id = "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
      vad_model_id = "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
      punc_model_id = "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch"

      try:
          print("Loading models...")
          model = AutoModel(
              model=model_id,
              vad_model=vad_model_id,
              punc_model=punc_model_id,
              disable_update=True
          )

          files = sorted(glob.glob("chunks/part*.wav"))
          print(f"Found {len(files)} chunks.")

          # Initialize output file (初始化输出文件)
          output_file = "transcript_raw.txt"
          with open(output_file, "w", encoding="utf-8") as f:
              f.write("")

          for i, file_path in enumerate(files):
              print(f"Processing {file_path} ({i+1}/{len(files)})...")
              try:
                  res = model.generate(
                      input=file_path,
                      batch_size_s=300,
                      # Add hotwords if relevant to the specific podcast context
                  )

                  text_part = ""
                  if isinstance(res, list):
                      for item in res:
                          if 'text' in item:
                              text_part += item['text']
                  elif isinstance(res, dict) and 'text' in res:
                      text_part = res['text']

                  with open(output_file, "a", encoding="utf-8") as f:
                      f.write(text_part + "\n")
                      f.flush()

              except Exception as inner_e:
                  print(f"Error processing {file_path}: {inner_e}")
                  traceback.print_exc()

          print("All chunks processed.")

      except Exception as e:
          print("Fatal error:")
          traceback.print_exc()
      ```

3.  **执行转写 (Execute Transcription)**：
    - 在虚拟环境中运行脚本。
    - 确保生成了 `transcript_raw.txt`。

### 第三阶段：后处理 (Post-Processing)

1.  **生成 `podcast_full_structured.md`**：
    - **目标**：创建一个阅读友好的全文 (Full Text) 版本。
    - **输入**：`transcript_raw.txt`。
    - **指令**：
      - 读取原始转写文本 (Raw Transcript)。
      - **不要删除内容**。保留原始措辞（包括能增加语感的口语填充词，但可以微调结巴重复的部分）。
      - **增加结构 (Structure)**：将长段落拆分为逻辑清晰的段落 (Paragraphs)。
      - **添加标题 (Headings)**：为不同话题/部分插入描述性的 H2/H3 标题。
      - **格式化 (Formatting)**：使用粗体 (Bold) 强调关键点。

2.  **生成 `podcast_optimized.md`**：
    - **目标**：创建一个高质量的 "Show Note" 或精华摘要 (Essence Summary)。
    - **输入**：`transcript_raw.txt` 或 `podcast_full_structured.md`。
    - **指令**：
      - **去噪 (Remove Noise)**：去除口语填充词（如 uh, um, you know）、重复句和无关闲聊。
      - **润色 (Refine)**：将句子打磨为流畅、专业的书面中文 (Written Chinese)。
      - **总结 (Summarize)**：整理成带有标题的清晰章节。
      - **高亮 (Highlight)**：提取关键洞见或“金句” (Golden Sentences)。

### 第四阶段：最终交付 (Final Output)

报告以下四个产出物 (Artifacts) 的成功创建：

1.  `podcast_optimized.md`
2.  `transcript_raw.txt`
3.  `podcast.m4a` / `podcast.wav`
4.  `podcast_full_structured.md`
