# 场景标注指南(人工部分)

这份指南说明场景知识层里**必须由你本人完成**的工作:看片、写场景笔记、核实、写问题、给答案打分。
代码部分(解析、检查、检索、评估脚本)已经写好,见本文最后的命令速查。

核实只能靠你自己看片。AI 没有看过这部电影的画面,它"记得"的情节来自网上的文字,不能作为核实依据。

---

## 1. 整体流程

```
看第一遍(正常观看,不标注)
   ↓
选 12–15 个场景,列出场景表
   ↓
第二遍:逐场景暂停,写 sNN.md          ← 你写
   ↓
python scripts/scenes_check.py        ← 脚本检查格式和引用
   ↓
隔至少一天,带着笔记重看每个场景,逐行核对 ← 你核实
   ↓  改 verified: yes + 日期
写 40 道问题和参考答案,提交并打 tag   ← 你写,运行系统之前完成
   ↓
python scripts/run_eval.py ...        ← 脚本跑 A–E 五个条件
   ↓
在 CSV 里逐行打分                      ← 你打分
   ↓
python scripts/summarize_eval.py ...  ← 脚本汇总
   ↓
python scripts/extract_scenes.py ...  ← LLM 抽取 vs 你的标注
```

预计时间:选场景和标注 6–10 小时,核实 3–4 小时,写问题 2–3 小时,打分 2–3 小时。

---

## 2. 选哪些场景

目标是让图结构**有机会**发挥作用,同时也保留它不起作用的情况。

1. **成对的场景优先。** 《小姐》第二部分会从另一视角重述第一部分的事件。至少找 4 对"同一事件、两个视角"的场景,它们之间写 `retells` 链接。
2. **反复出现的物品。** 某个物品在相隔很远的两个场景出现,写 `same_object`。
3. **因果。** 后一个场景是前一个的直接后果,写 `follows_from`。
4. **反转。** 后一个场景揭示前一个场景看到的并非真相,写 `contradicts`。
5. **加 3–4 个独立场景**:不和其他场景相连。用来检验单场景问题,也防止整套数据只偏向图。

先在纸上或表格里列一张场景表(编号、大致时间、一句话内容、和谁相连),确定后再开始写文件。
场景编号按片中顺序:`s01`、`s02`……中间删掉的编号不用补。

---

## 3. 文件放在哪里

```
data/scenes/
├── _template/            模板,不要改
│   ├── film.md
│   └── scene.md
└── the_handmaiden/
    ├── film.md           人名、物品名和别名
    ├── s01.md            每个场景一个文件
    ├── s02.md
    └── ...
data/eval/
└── handmaiden_questions.csv   你的问题表(从 _template_questions.csv 复制)
```

新建场景文件:

```bash
python scripts/new_scene.py the_handmaiden s01
```

它会把模板复制成 `data/scenes/the_handmaiden/s01.md`,你用任意文本编辑器(VS Code、Typora 都行)打开填写。

**为什么用 Markdown 模板而不是直接写 JSON:** 手写 JSON 容易漏逗号和引号,也难读。模板里是固定的标题和列表,
`scripts/scenes_check.py` 会把它严格解析成 JSON(输出到 `results/scenes_the_handmaiden.json`),这一步**不经过 AI**,
所以 JSON 里的每个字都来自你。

---

## 4. 先填 film.md

`data/scenes/the_handmaiden/film.md` 已经按演员表预填了四个主要人物,请你**看片时核对**并补充别名:

```markdown
## Characters

- Sook-hee | <片中对她的其他称呼>
- Hideko
- Count Fujiwara | the Count, Count
- Kouzuki | Uncle Kouzuki

## Objects

- <物品规范名> | <你可能用到的其他叫法>
```

规则:

- 每行一个"规范名",`|` 后面是别名,逗号分隔。场景文件里写别名也可以,系统会统一成规范名。
- 只登记**跨场景出现**或**问题会问到**的物品。只出现一次的小物件不用登记,直接写在场景里。
- 一个物品在不同场景要用同一个名字(或登记过的别名),否则图里就连不上。

---

## 5. 怎么写一个场景文件

### 5.1 头部(front matter)

```
---
scene_id: s03
part: 1
start: 00:18:00
end: 00:20:30
pov: Sook-hee
location: <地点>
verified: no
verified_on:
---
```

- `start` / `end`:播放器显示的时间,精确到分钟即可,格式 `00:18:00`。
- `pov`:这场戏从谁的视角讲述。《小姐》每部分的视角不同,这个字段很重要。
- `verified`:先写 `no`。核实之后才改成 `yes`,并填写 `verified_on: 2026-10-25`。

### 5.2 Description(最重要)

用你自己的话,按时间顺序写 3–6 句话,只写**看到和听到的**。

- 这一段是 LLM 抽取实验的**唯一输入**,所以下面 Events 里的每件事,都应该能从这段里读出来。
- 不写动机、不写象征、不写"她很害怕"这类内心判断,这些放到 Interpretations。
- 不抄字幕和剧本原文。

> ✗ 她假装顺从,其实心里在盘算逃跑。(内心判断)
> ✓ 她低头答应,等对方离开后,把钥匙放进袖子里。(可观察)

建议**先写 Description,再写下面的结构化部分**,写结构化部分时不要回头改 Description 去迎合它。

### 5.3 Characters

出场的人物,每行一个 `- 名字`。

### 5.4 Events(每行一个可观察的动作)

```
- e1 | Jon | slips a folded note into a red book | objects: letter, red book
- e2 | Mara | watches him leave | uncertain
```

格式:`编号 | 谁做的 | 做了什么 | objects: 物品, 物品 | uncertain`(例子里的 Jon、Mara 是测试用的虚构人物,完整示例见 `backend/tests/fixtures/scenes/demo_film/`)

- 编号 `e1, e2, ...`,按画面顺序。
- 一行只写一个动作。"她拿起信、读完、烧掉"拆成三行。
- `objects:` 里的物品必须也写在下面的 Objects 里(检查脚本会报错提醒)。
- 不确定的(画面暗、看不清、你记不清)加 `| uncertain`。**宁可标不确定,也不要猜。**
- 不知道是谁做的,写 `unknown`。
- 建议用英文写。问题也用英文,这样检索时名字和物品能直接匹配上。如果你更习惯中文,见第 8 节关于翻译的规则。

### 5.5 Objects、Dialogue summary、Camera

- **Objects**:本场景出现的、有意义的物品,每行一个。
- **Dialogue summary**:用你的话转述对剧情有用的对白。原话最多引用几个词。
- **Camera**:你注意到的构图、运镜、光线、声音。没有特别注意到就留空。不要从影评里抄。

### 5.6 Links(跨场景关系)

```
- e1 retells s09.e2 | note: same event seen from Hideko's side
- e1 same_object s01.e3
- scene follows_from s02
- e2 contradicts s04.e1 | unverified
```

格式:`本场景的事件编号(或 scene) 关系 目标场景或目标事件 | unverified | note: ...`

| 关系 | 什么时候用 |
| --- | --- |
| `retells` | 两个场景展示**同一事件**,视角或信息不同 |
| `same_object` | 本场景的某个物品和那个场景的是**同一个实物**(不只是同一种东西) |
| `follows_from` | 本场景的事件是那个场景事件的直接后果 |
| `contradicts` | 本场景揭示那个场景看到的(或暗示的)不是真相 |

- 方向约定:**写在后面的场景里,指向前面的场景**。系统检索时两个方向都会走,所以每对场景只写一次。
- 能指向具体事件(`s09.e2`)就不要只指向场景(`s09`)。
- 你觉得有关系但不能从画面确认的,加 `| unverified`。评估时会分开看已核实和未核实的链接。

### 5.7 Interpretations(解释,和事实分开)

```
- c1 | my reading | <你的解读> | supports: s03.e1, s09.e2
- c2 | <影评人名, 出处> | <对方的解读> | supports: s03.e2
```

- 每条必须写清楚**是谁的解读**,以及**依据哪些事件**(`supports:` 不能为空)。
- 引用别人的观点要写出处,不要把别人的观点写成 `my reading`。
- 不是每个场景都需要解释。全片有 6–10 条就够了,集中在你会问 L3 问题的场景。

### 5.8 写完一个场景就检查

```bash
python scripts/scenes_check.py the_handmaiden --show s03
```

它会列出所有问题(时间格式不对、人物不在名单里、物品没登记、链接指向不存在的场景、解释没有依据等),
`--show s03` 会打印这个场景**交给模型时的样子**。没有问题时最后输出 `OK`。

---

## 6. 核实(只能你自己做)

是的,只能靠你自己重看。具体做法:

1. 写完所有场景后**至少隔一天**再核实。刚写完马上核对,容易只是在确认自己的记忆。
2. 打开播放器和场景文件,逐个场景播放,**逐行**对照 Events:
   - 画面确实如此 → 保留;
   - 有出入 → 修改;
   - 看不清或有歧义 → 加 `| uncertain`;
   - 画面里没有 → 删除。
3. 核对 Links:两边的事件都重看一遍。不能确认的加 `| unverified`。
4. 核对时间:误差在 30 秒内即可。
5. 一个场景核完,把 `verified: yes` 和 `verified_on: <日期>` 填上,单独提交一次:
   ```bash
   git add data/scenes/the_handmaiden/s03.md
   git commit -m "Verify s03 against the film"
   ```
   这样 git 历史就是你的核实记录,面试时可以展示。
6. **可选,但能明显加分:** 请一位看过这部电影的朋友独立检查 3–4 个场景,只看你的 Events 判断对错。
   记下"朋友认为正确的事件数 / 总事件数",写进 README。这是最简单的标注质量指标。
7. 剧情百科和影评只能用来**发现**你可能记错的地方,发现之后仍要回到画面确认,不能直接照抄。

---

## 7. 写问题(在运行任何系统之前完成)

复制模板:

```bash
cp data/eval/_template_questions.csv data/eval/handmaiden_questions.csv
```

用 Excel、Numbers 或 Google Sheets 打开编辑,保存为 CSV(UTF-8)。列的含义:

| 列 | 内容 |
| --- | --- |
| `qid` | q01, q02, ... |
| `type` | `L1` / `L2_single` / `L2_cross` / `L3` / `unanswerable` |
| `question` | 英文问题 |
| `reference_answer` | 简短的参考答案;L3 写"好答案必须提到什么";无法回答的写 `NOT_COVERED` |
| `evidence` | 答案依据的场景或事件,分号分隔,如 `s03.e1;s09.e2`。L1 和 unanswerable 留空 |
| `answerable` | `yes` / `no` |
| `notes` | 备注 |

数量建议:L1 6 题,L2_single 10 题,L2_cross 12 题,L3 6 题,unanswerable 6 题。

规则:

- **写问题前不要看任何系统的回答**,否则会不自觉地写出对某个系统有利的问题。
- L2_cross 要真正需要两个场景才能回答;其中一部分用和笔记**不同的词**来问(例如笔记写 note,问题问 letter),
  检验检索能否跨越措辞差异。
- unanswerable 问题要像真问题,不要写明显荒谬的问题。
- 写完后提交并打 tag,冻结问题集:
  ```bash
  git add data/eval/handmaiden_questions.csv
  git commit -m "Freeze evaluation questions v1"
  git tag eval-questions-v1
  ```
  之后如果要改问题,另存为 v2,两份结果分开报告。

---

## 8. AI 能做什么、不能做什么

整个实验的前提是"人工标注是参照答案"。如果 AI 参与生成标注内容,LLM 抽取实验就成了拿 AI 的输出去比 AI 的输出,没有意义。

| 可以让 AI 做 | 不可以让 AI 做 |
| --- | --- |
| 修格式错误(漏了 `|`、标题拼错、时间格式) | 根据它对电影的"记忆"补事件、补链接、补解释 |
| 根据 `scenes_check.py` 的报错提示你哪里不一致 | 从你的 Description 里自动生成 Events(这正是抽取实验要测的) |
| 把你写的中文**逐句**翻成英文(你逐行检查) | 把 `verified` 改成 `yes` |
| 跑脚本、汇总结果、画表 | 替你判断答案对错(打分必须你来) |
| 检查问题表格式 | 根据系统回答修改问题或参考答案 |

### 怎么让 Claude Code 只做格式整理

如果你更想先随手写自由笔记,再整理成模板,可以这样做:

1. 自由笔记放在仓库外面,或者放进 `data/scenes/the_handmaiden/drafts/`(这个目录不会被解析)。
2. 对 Claude Code 说(原样复制,替换文件名):

   > Reformat my draft `data/scenes/the_handmaiden/drafts/s03.txt` into `data/scenes/the_handmaiden/s03.md`
   > following `data/scenes/_template/scene.md`. Rules: do not add, remove, merge or reword any content;
   > every event line must correspond to one sentence or clause in my draft; if something in the draft does
   > not fit a section, put it in a `<!-- unplaced: ... -->` comment instead of guessing; leave `verified: no`;
   > do not use any knowledge of the film. Then run `python scripts/scenes_check.py the_handmaiden` and show me
   > the diff. Do not commit.

3. 用 `git diff` 逐行看它改了什么,确认没有新增内容后再自己提交。
4. 在提交信息里注明,例如 `Add s03 (formatted with Claude Code from my draft)`。如实写就行,不影响实验。

翻译同理:让它逐句翻译,不改写、不合并;你逐行对照。Description 如果是 AI 翻译的,在 README 里说明
"抽取实验的输入是人工撰写、AI 辅助翻译的英文描述"。

---

## 9. 打分(运行之后)

```bash
python scripts/run_eval.py data/eval/handmaiden_questions.csv
```

结果在 `results/eval/handmaiden_questions_<时间>.csv`。每个问题 × 每个条件一行,`evidence_recall` 已自动算好
(系统给模型看的场景里,包含了多少你标的依据场景)。你需要填最后五列:

| 列 | 取值 | 怎么判断 |
| --- | --- | --- |
| `correctness` | `correct` / `partial` / `wrong` | 对照 reference_answer。L3 看是否基于正确的事件、是否把解释和事实分开 |
| `evidence_ok` | `yes` / `no` | 回答里引用的场景编号,是否真的支持它说的话 |
| `abstention_ok` | `yes` / `no` | 只填 answerable = no 的行:它是否说了"笔记没有覆盖" |
| `error_location` | 见下 | 只给 partial 和 wrong 填 |
| `grader_notes` | 自由文字 | |

`error_location` 按这个顺序判断,取第一个成立的:

1. `missing_knowledge`:你的笔记里本来就没有这个信息;
2. `retrieval_miss`:笔记里有,但 `retrieved_scenes` 里没有对应场景;
3. `bad_note_or_link`:检索到了,但笔记或链接本身有错(这时回去修笔记,并记录下来);
4. `wrong_with_evidence`:证据都在,模型还是答错了。

建议**盲评**:打分时把 `mode` 和 `condition` 两列先隐藏,打完再显示。

打完分运行:

```bash
python scripts/summarize_eval.py results/eval/handmaiden_questions_<时间>.csv
```

会生成同名的 `_summary.md`,按条件和题型汇总。只有一部电影、约 40 题,结果只能当作**案例统计**,
不要写"显著提升"。

---

## 10. 版权

- 仓库里只放:你自己写的简短描述、时间位置、出处引用。
- 不放:视频、截图、字幕文件、剧本原文、大段对白。
- Dialogue summary 用转述;原话最多引用几个词。

---

## 命令速查

```bash
pip install -r backend/requirements.txt

python scripts/new_scene.py the_handmaiden s01           # 新建场景文件
python scripts/scenes_check.py the_handmaiden            # 检查全部场景,导出 JSON
python scripts/scenes_check.py the_handmaiden --show s01 # 看模型拿到的样子

export OPENAI_API_KEY=...
python scripts/run_eval.py data/eval/handmaiden_questions.csv --retrieval-only  # 只看检索,不调用回答
python scripts/run_eval.py data/eval/handmaiden_questions.csv                   # A–E 全部
python scripts/summarize_eval.py results/eval/<文件>.csv                         # 打分后汇总
python scripts/extract_scenes.py the_handmaiden                                  # LLM 抽取 vs 人工标注

cd backend && python -m pytest -q tests                  # 代码自测(用虚构的示例电影,不需要密钥)
```

在前端评估页可以勾选 Scenes (vector) / Scenes (graph) / Scenes (all notes),对单个问题手动比较。
