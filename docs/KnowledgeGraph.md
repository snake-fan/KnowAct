# Node

Node 设计原则：

``` text
1. 用户可以用 1-2 个问题暴露是否掌握  
2. 它和其他节点有明确依赖关系  
3. 它不是一个完整领域，也不是一个太小的术语  
4. 它能被定义、举例、应用、比较
```

可以参考 `ZettelKasten 笔记法`

参考：

``` JSON
{
  "id": "epistemic_uncertainty",
  "name": "Epistemic Uncertainty",
  "type": "concept",
  "definition": "Uncertainty caused by lack of knowledge or limited data.",
  "diagnostic_goal": "User can distinguish model uncertainty from data noise and explain why more data can reduce it.",
  "source": ["textbook_chapter_3", "survey_section_2.1"]
}
```

#### 1）可解释

用户应该能说清楚它是什么。

例如：

``` text
epistemic uncertainty
```

不是只知道名字，而是能解释：

``` text
模型因为缺少知识或数据而产生的不确定性。
```

---

#### 2）可诊断

你能为它设计一个问题，判断用户是否掌握。
比如：

``` text
为什么 epistemic uncertainty 可以通过增加数据减少？
```

如果一个 node 没法被问出来，它就不适合做主动探索节点。

---

#### 3）粒度适中

不要太大

``` text
Machine LearningActive LearningLLM Alignment
```

这些太大，一问问不清。
也不要太小：

``` text
符号 σ公式里的某个下标一句定义里的某个词
```

这些太碎，会让图爆炸。

比较好的粒度是：

``` text
acquisition functionepistemic uncertaintyaleatoric uncertaintyexpected information gainposterior predictive distributionpreference model ensembleadapter ensemblediversity sampling
```

判断标准是：

> 一个 node 最好能用 1-3 个诊断问题判断掌握程度。

---

#### 4）稳定

node 不应该依赖某篇论文的表述方式，而应该是领域里相对稳定的知识单位。
比如：

``` text
BALDexpected information gainuncertainty samplingknowledge tracingprerequisite relation
```

比某篇论文里临时命名的模块更适合作为 node。

---

#### 5）有证据来源

每个 node 最好能追溯到：

``` text
教材章节课程 slidesurvey paper经典论文术语表领域专家确认
```

从 textbook 构建 concept map 的研究通常会把 key concept extraction 和 concept relationship identification 作为两个核心子问题；这说明“节点是什么”和“节点之间是什么关系”本身就是可以系统构建和验证的。
