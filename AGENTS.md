# AGENTS.md — ManimGL 动画项目调试协议

## 项目概况

- 项目：B站科普视频动画（ManimGL 制作，RVC 配音）
- 技术栈：ManimGL（3b1b 版，`from manimlib import *`）+ Python + ffmpeg + 人工配音
- 运行环境：Windows，终端为 PowerShell/CMD
- 包管理：pip 包名 `manimgl`，与 Manim Community 的 `manim` **互不兼容**，必须独立 venv，禁止同环境混装

## 黄金法则

1. 渲染片段化：每次只渲染一个 Scene 或一个镜头（3~5 秒），不要一次性渲染全片
2. 先读代码再动手：修改任何 scene 文件前，先读完整个文件和相关配置
3. 每次改动只做一件事，改完立即重新渲染验证
4. 不要臆造 API：不确定的类/方法/参数名，必须先查文档（见下文"查文档协议"）
5. 做一个视频只修改对应的那个 python 文件，不要修改项目里的其他文件

## 查文档协议（强制）

- memo.md 包含易错点清单（CE→manimgl 对照表在最前面），先查它
- ManimGL 中文文档：https://docs.manim.org.cn/
- 源码即文档（最权威，优先直接看源码核对签名与默认值）：
  - https://github.com/3b1b/manim 的 `manimlib/` 目录
  - 常用：`manimlib/mobject/geometry.py`（Line/Arc/Circle 签名）、`manimlib/camera/camera_frame.py`（reorient/相机）、`manimlib/mobject/types/surface.py`、`manimlib/extract_scene.py`（命令行参数）
- 参考实现：https://github.com/3b1b/videos 、仓库自带 `example_scenes.py`
- 优先顺序：
  1. 先看 memo.md 是否包含需要的内容
  2. 抓 docs.manim.org.cn 对应页或直接抓 GitHub 源码，核对类签名、参数名、默认值
  3. 搜不到时按模块名定位源码文件再抓
  4. 仍无解才用 web 搜索，并回到源码交叉验证
- 重要：Manim Community 官方文档（docs.manim.community）**不适用于**本项目；网上中文教程（含 cai-hust/manim-tutorial-CN、老博客）多基于 CE 或更老的 cairo 版 manimlib，API 差异大，一律以 manimgl 源码为准
- 本项目锁定 ManimGL，不要建议迁移到 Manim Community 或其他分支

## 调试协议（渲染-抽帧-看图循环）

### 第 1 步：渲染

```powershell
manimgl 2026/someproject.py <SceneName>        # 弹窗实时预览（调试用）
manimgl 2026/someproject.py <SceneName> -w     # 写入视频文件
manimgl 2026/someproject.py -w -a              # 一次渲染文件里的所有场景
manimgl 2026/someproject.py <SceneName> -w -r 2560x1440   # 指定分辨率
```

- 分辨率也可写进运行目录的 `custom_config.yml`：`camera_resolutions: { default: [2560, 1440] }`；快捷档 `-l / -m / --hd / --uhd`
- 渲染失败：完整阅读报错堆栈，定位到具体 scene 文件行号再修改
- 常见问题速查：
  - `No module named 'pkg_resources'`：`pip install setuptools`（Python 3.12 venv 默认不带）；PyPI 版 manimgl 偏老，3.12 建议装 GitHub master
  - `LaTeX Error`：改用 `Text()` 代替 `Tex()`，或检查 MiKTeX 安装
  - `ModuleNotFoundError` / 属性不存在：大概率混用了 CE API（MathTex / Create / add_coordinates / move_camera 等），对照 memo.md 第一节替换
  - 红边圆：Circle 必须显式 `stroke_color=...`
  - 物体位置重叠/出界：检查坐标系和 `buff`、`arrange` 参数

### 第 2 步：抽帧生成拼图

渲染成功后，用 ffmpeg 把视频抽成一张关键帧拼图（不要一张一张读，费 token）：

```powershell
ffmpeg -y -i <输出目录>/<SceneName>.mp4 -vf "select='not(mod(n\,15))',scale=960:-2,tile=5x5" -frames:v 1 debug_<SceneName>.png
```

- 输出目录以 `custom_config.yml` 的配置为准（找到 `-w` 生成的 mp4 所在路径即可）
- 说明：每 15 帧抽一帧（30fps 即每 0.5 秒），拼成 5x5 网格，一张图覆盖约 12 秒
- 短视频拼图看不清时：改 `select='not(mod(n\,5))'` 提高密度
- 需要看时序衔接时：对相邻镜头各抽一张做对比

### 第 3 步：视觉检查

读取 debug_<SceneName>.png，对照分镜文档逐镜头检查：

- [ ] 布局：有无重叠、出界、错位
- [ ] 时序：出现/消失/变换时机是否与分镜一致
- [ ] 样式：颜色、字号、线宽是否符合分镜设定
- [ ] 文本：有无乱码、换行错误（中文检查 `Text()` 的 `font=` 是否指向系统中文字体）
- [ ] 相机：3D 场景方位角是否符合预期（manimgl 的 theta = CE theta + 90°，方向反了就取负）

### 第 4 步：修复并重渲染

- 在检查清单里勾选确认所有问题后，一次性修改，再回到第 1 步
- 连续 2 轮渲染仍有同类问题：停下来重新读原始代码和文档，换思路，不要重复同样的修改

## 项目文件结构

```
project/
  AGENTS.md            # 本文件
  memo.md              # 易错点清单（CE→manimgl 对照 + 通用教训）
  shared_stuff.py      # 共用的一些 scene 会放在根目录
  2026/                # 项目 scene 文件放在此处，我会把文件创建好
    someproject.md     # 分镜文档（镜头编号、时长、画面描述、Scene 类名）
    someproject.py     # manimgl 文件（from manimlib import *）
  audio/               # 配音 wav（不要更改）
  videos/              # manimgl 渲染输出（路径以 custom_config.yml 为准，不要手动改）
  debug_*.png          # 抽帧拼图（可随时删除）
```

## 分镜文档（storyboard.md）约定

- 我不一定提供完整的分镜文档。
- 每个镜头包含：编号 / 目标时长 / 画面内容描述 / 配色与样式 / 对应 Scene 类名，默认不添加配音
- Agent 生成新镜头时：如果有文档的话先读 storyboard.md，然后在文件实现，并把 Scene 类名登记回分镜表

## 禁忌

- 不要修改渲染输出目录下的任何文件
- 不要全局重命名已有 Scene 类（分镜表和文件名可能引用）
- 不要引入任何 Manim Community 插件或代码片段（API 不兼容）
- 不要在 scene 文件里写 `from manim import *`，一律 `from manimlib import *`
- 不要混用 CE 命令行参数（`-pqm / -pqh` 等），manimgl 用 `-w / -r / -a`（见调试协议）
