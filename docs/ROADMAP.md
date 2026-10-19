# 进度清单(从这里开始)

每次继续工作,先看这一页。做完一项就把 `[ ]` 改成 `[x]` 并提交。
详细做法不在这里重复,点链接看对应文档。

| 文档 | 用途 |
| --- | --- |
| [annotation_guide.md](annotation_guide.md) | **怎么做**:选场景、写笔记、核实、写问题、打分、AI 能做什么(中文) |
| [scene_knowledge_design.md](scene_knowledge_design.md) | **为什么这样做**:研究问题、数据模型、A–E 实验设计 |
| [../README.md](../README.md) | 项目总览、安装和启动 |

## 阶段 0:代码上 GitHub

- [x] 把 `graph-retrieval` 分支推上 GitHub(本地用 `git am graph_retrieval.patch`,或给 Claude 授权后让它推)
- [ ] 用真实 OpenAI 密钥启动一次应用,在评估页试 Graph、Graph + RAG 各一个问题
- [ ] 确认无误后把 `graph-retrieval` 合并到 `main`

## 阶段 1:数据准备(只能你做)

- [ ] 第一遍完整看《分手的决心》,不标注
- [ ] 核对 `data/scenes/decision_to_leave/film.md` 里的四个人名,补别名和其他人物 → 指南第 4 节
- [ ] 列场景表:12–15 个场景,至少 4 对前后呼应的场景(`same_object` / `refers_back_to`),3–4 个独立场景 → 指南第 2 节
- [ ] 写完前 3–4 个场景,发给 Claude 看格式和粒度
- [ ] 写完全部场景,`python scripts/scenes_check.py decision_to_leave` 输出 OK → 指南第 5 节
- [ ] 隔一天后逐场景核实,每个场景 `verified: yes` 并单独提交 → 指南第 6 节
- [ ] (可选)请朋友独立检查 3–4 个场景,记录一致率

## 阶段 2:问题集(运行系统之前)

- [ ] 写 40 道题和参考答案:L1 6 / L2_single 10 / L2_cross 12 / L3 6 / unanswerable 6 → 指南第 7 节
- [ ] 提交并 `git tag eval-questions-v1`

## 阶段 3:实验

- [ ] `run_eval.py --retrieval-only` 先看检索召回
- [ ] `run_eval.py` 跑 A–E
- [ ] 盲评打分(隐藏 mode 列)→ 指南第 9 节
- [ ] `summarize_eval.py` 生成汇总
- [ ] `extract_scenes.py`:LLM 抽取 vs 人工标注,填事件对照表
- [ ] (之后)加入干扰材料再跑 B / D / E,看谁先失效

## 阶段 4:写出来

- [ ] 在 README 写结果表、错误分析、局限
- [ ] 更新简历和动机信措辞(见下方"能说什么")

---

## 已做的决定(聊天里定下的,记在这里)

- **试点电影改为《分手的决心》**(原定《小姐》):前半部分的话、物品和地点会在后半部分再次出现,意思也变了,适合检验跨场景链接。为此新增链接类型 `refers_back_to`;`retells` 保留给其他电影。动机信已同步改为这部电影。
- **笔记用 Markdown 模板,不手写 JSON**;解析成 JSON 不经过 AI。
- **必须有条件 E(全部笔记放进 prompt)**:只有十几个场景时,不检索可能反而最好;图的价值要在资料变多后才看得出来。
- **人工标注是参照答案**:AI 不能根据它对电影的记忆补内容,不能从 Description 生成 Events,不能标 verified。
- **Hub 阈值 30**(`graph_service.py`):每部电影约 20 条边,阈值 20 会把电影本身也当成 hub;目前只有 Park Chan-wook(32 条)算 hub。
- **ChatGPT 反馈的结论**:三层问题划分、解释与事实分开、记录错误位置都采纳;它说"Claude 建议先用 TMDB 建图"与事实不符(图来自你自己写的 Markdown,TMDB 只是实时查询工具)。

## 待你核实的事

- [ ] 别名合并是否正确(`graph_build.py` 的 `ALIASES`):`Jo Yeong-wook` = `Cho Young-wuk`,`Jeong Seo-kyeong` = `Jeong Seo-kyung`,`Lady Vengeance` = `Sympathy for Lady Vengeance`
- [ ] `data/rag/Stoker.md` 标题写"Stoker（2016）",实际是 2013 年,改正标题

## 现在能说什么 / 不能说什么

- 能说:把电影资料转成知识图谱并导出 RDF;实现了图检索和图 + RAG 模式;设计并实现了场景级知识层和 A–E 评估流程。
- 不能说:提升了准确率(还没评估);实现了视频理解;能从完整电影自动构建知识图谱。
- 有了结果以后:按 `summarize_eval.py` 的表格如实写,只有一部电影、约 40 题,写"案例统计",不写"显著"。
