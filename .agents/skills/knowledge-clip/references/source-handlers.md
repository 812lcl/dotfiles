# 各来源抓取手册

每种来源给出：URL 模式、抓取命令、关键元字段提取方式、失败回退。

## 1. 小宇宙播客（默认 show notes，可选完整转写）

**URL 模式**：`https://www.xiaoyuzhoufm.com/episode/<id>`

**默认方案：defuddle 抓 show notes + xiaoyuzhou_meta.py 抓元字段（推荐，秒级）**

```bash
# 1. 正文（show notes）—— defuddle 处理得很好
defuddle parse "<url>" --md -o /tmp/clip.md

# 2. 元字段 —— defuddle 的 og:image / title 都是播客级（每期一样），用专用脚本拿单期数据
python3 scripts/xiaoyuzhou_meta.py "<url>"
# → {"cover": "...", "title": "...", "pub_date": "...", "podcast": "...", "duration_sec": N}
```

元字段映射：

| frontmatter | 来源 |
|---|---|
| `type` | `播客` |
| `media` | `小宇宙` |
| `source` | 原 URL |
| `author` | `xiaoyuzhou_meta.py` → `podcast` 字段（即播客名，如「面基」「无人知晓」） |
| `published` | `xiaoyuzhou_meta.py` → `pub_date`，截到 `YYYY-MM-DD` |
| `cover` | `xiaoyuzhou_meta.py` → `cover`（单期封面，**不要用 defuddle `-p image`**，那是播客级） |

**为何不用 defuddle 的元字段**：小宇宙页面里 `og:image` 和首个 `title` 都是播客级（同播客所有期相同）。`xiaoyuzhou_meta.py` 解析页面里嵌入的 episode JSON 数据，拿到真正的单期信息。

**升级方案：完整转写**（用户说"完整版/逐字稿/--full"时）

```bash
# 调用现有 skill
# 参考 ~/.claude/skills/xiaoyuzhou-podcast-transcriber/SKILL.md
```

注意：转写耗时 5-30 分钟，仅在用户明确要求时启动。

## 2. 网页文章（公众号、少数派、博客等）

**URL 模式**：除已识别的特殊域名外所有 `http(s)://...`

**抓取**：

```bash
defuddle parse "<url>" --md -o /tmp/clip.md
defuddle parse "<url>" -p title
defuddle parse "<url>" -p author
defuddle parse "<url>" -p published
defuddle parse "<url>" -p description
defuddle parse "<url>" -p image     # 封面
defuddle parse "<url>" -p domain
```

**media 映射**（按 domain）：

| domain 包含 | media |
|---|---|
| `mp.weixin.qq.com` | 微信公众号 |
| `sspai.com` | 少数派 |
| `zhuanlan.zhihu.com` / `zhihu.com` | 知乎 |
| `weibo.com` | 微博 |
| `substack.com` | Substack |
| `medium.com` | Medium |
| 其它 | 博客（默认） |

## 3. YouTube

**URL 模式**：`youtube.com/watch?v=` / `youtu.be/`

**抓取**：

```bash
# 元数据 + 字幕
yt-dlp --skip-download --write-info-json --write-auto-sub \
       --sub-lang "zh-Hans,zh,en" --sub-format vtt \
       -o "/tmp/yt_%(id)s.%(ext)s" "<url>"

# 字幕处理：vtt → 纯文本（去时间戳）
```

元字段：从 `info.json` 读 `title / uploader / upload_date / thumbnail / description`。

**失败回退**：无字幕时，给用户两个选项 — (a) 用 description 当正文；(b) 调 transcriber（需音频下载 + ASR，慢）。

## 4. B站

**URL 模式**：`bilibili.com/video/` / `b23.tv/`

**抓取**：`yt-dlp` 同 YouTube，部分视频字幕从 `--write-subs` 拿到 CC 字幕。

**media**: `B站`

**失败回退**：用 autocli bilibili 抓视频简介 + 评论区高赞。

## 5. X / Twitter

**URL 模式**：`x.com/<user>/status/` / `twitter.com/`

**抓取**：

```bash
# 优先 autocli（复用浏览器登录态，能拿到长推 / 线程）
autocli twitter get "<url>"
```

元字段：作者 = `@handle`，published = 推文时间，type = `推文`。

**线程处理**：autocli 自动展开同作者下方相邻推文为完整线程。

## 6. PDF / 本地文件

**判定**：路径以 `/` 开头或带 `.pdf/.md/.txt` 后缀。

**PDF 文本抽取**：

```bash
# 优先 pdftotext (poppler)
pdftotext -layout "<path>" -

# 失败回退：python pdfplumber
python3 -c "import pdfplumber; ..."
```

**Markdown / txt**：直接 `cat`。

元字段：`title` 从文件名或正文首行，`author/published` 留空由用户填，`source` 为绝对路径。`media`: `本地`。

## 7. 容错策略（统一）

| 失败 | 处理 |
|---|---|
| 抓取超时 / HTTP 错误 | 重试一次；仍失败则报错给用户，问要不要继续（用 description 当正文） |
| AI 摘要超时 | frontmatter `summary` 写入 `(待补充)`，正文保留，提示用户 |
| 封面抓不到 | `cover` 留空 |
| 作者识别失败 | `author` 留空 |
| 重复 source 已存在 | 不覆盖；问用户：覆盖 / 新建带 (2) 后缀 / 跳过 |

## 8. 工具可用性自检

skill 启动时按需检测：

```bash
command -v defuddle || echo "❌ 缺少 defuddle: npm install -g defuddle"
command -v yt-dlp || echo "❌ 缺少 yt-dlp（仅视频源用到）"
command -v pdftotext || echo "❌ 缺少 pdftotext（仅 PDF 用到）"
command -v autocli || echo "❌ 缺少 autocli（仅 X/B站 用到）"
```

只对**用到的来源**报错，其他静默。
