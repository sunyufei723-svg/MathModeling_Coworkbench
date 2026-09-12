---
name: scientific-figure-intelligence
description: >
  A research-grade skill for selecting, designing, and generating
  publication-quality academic figures for mathematical modeling,
  numerical simulation, statistics, optimization, machine learning, networks,
  spatial analysis, uncertainty quantification, and scientific papers.
---

# Scientific Figure Intelligence Skill
# 学术论文高级配图自主检索、选图与生成 Skill

## 0. 核心目标

本 Skill 不把“高级配图”理解为“3D 越多越高级”，而是把图形视为论文论证工具。

AI 必须完成以下闭环：

**研究问题 → 数据结构 → 论文需要证明的命题 → 候选图型召回 → 必要时检索 → 图型适配判断 → 图组设计 → 绘图实现 → 图注 → 论文分析段落**

最终图必须至少解决一个明确问题：

1. 展示物理状态或时空演化；
2. 证明数值算法可信；
3. 揭示参数敏感性或变量耦合；
4. 展示随机性、不确定性或概率风险；
5. 验证模型与观测的一致性；
6. 展示优化可行域、权衡关系和最优决策；
7. 揭示网络、空间或拓扑结构；
8. 解释模型机制、因果路径或机器学习决策；
9. 压缩高维结果并揭示结构；
10. 用最少图形完成最多论文论证。

## 0.1 中文数学建模竞赛适配

- 图内所有面向读者的标题、坐标名称、图例、色条、分区名和注释均使用中文；数学符号、变量、单位以及 BDF、FVM、PCE 等通用缩写可以保留。
- 文件名、代码变量和 LaTeX 标签可以使用英文，但不得因此把图内说明改成英文。
- 以模型、原始数据和可复现实验结果为主要依据；现有论文仅用于确认术语、避免重复和安排衔接，不能反过来替代数据判断。
- 竞赛论文篇幅有限，不规定每问必须有几幅图；能由表格或一句话说清的内容不额外作图，优先用少量复合图完成论证。
- 必须区分主答案、数值验证、灵敏度对照、反事实情景和不确定性分析，不得用同一种视觉语言暗示它们具有相同结论地位。

---

# 1. 科研论文配色与视觉编码规范

颜色不是装饰，而是数据编码。AI 在配色前必须先判断颜色承担的语义：**类别区分、数值大小、正负偏离、周期相位、置信度、强调/弱化、空间区域或网络社区**。只有当颜色与这些数据逻辑一致时，才允许使用颜色。

> 学术修正：日常所说的“深色/浅色”通常同时混合了 **亮度（lightness）** 与 **饱和度（saturation/chroma）**。论文绘图中，定量数据优先考虑感知上较均匀的亮度变化，而不是单纯追求“更鲜艳”。

## 1.1 颜色的分类

在实用论文配色中，可粗略分为两类：饱和度较高、视觉权重较强的**强烈色/深色**，以及饱和度较低或亮度较高、视觉权重较弱的**柔和色/浅色**。

| 深色 / 强调色 | 浅色 / 背景色 |
| --- | --- |
| 深粉色 | 浅粉色 |
| 深绿色 | 浅绿色 |
| 深蓝色 | 浅蓝色 |

AI 必须理解：

- 深色更适合小面积、高优先级、需要强调的图形元素；
- 浅色更适合大面积填充、背景区域、置信区间和辅助信息；
- 同一色系的深浅变化适合表达**同一类别内的层级、强弱或重要性**；
- 不同色相更适合表达**不同类别**；
- 连续数值不要仅靠“饱和度越来越高”表达，优先使用感知均匀的亮度或色彩梯度。

## 1.2 论文配色基本原则

颜色主要服务于数据逻辑关系的展现。图是数据的表达，颜色应展现数据的逻辑，而不是为了“花哨”。

### 原则 1：颜色必须有明确语义

- 不同颜色应表达不同分组；同一分组优先使用相近色、同色系或一致的视觉编码。
- 配色要突出关键数据：重要曲线、阈值、最优解、实验组可使用较深或更醒目的颜色；辅助信息使用浅色、灰色或降低透明度。
- 同一变量跨多个 panel 时，应保持颜色一致，不允许同一变量在不同子图中反复换色。
- 若颜色本身没有数据意义，不应增加无意义的“彩色装饰”。

### 原则 2：根据图形数据块面积选择颜色

经验上：

- **大面积数据块**（柱体、面积带、大块区域、置信区间）宜使用较浅、较柔和颜色，避免视觉压迫；
- **小面积元素**（折线、散点、轮廓线、关键符号）宜使用较深、对比更强的颜色；
- 如果需要使用深色填充大面积区域，优先降低 alpha 或使用较低 chroma 的深色，而不是高饱和纯色。

这是一条视觉权重经验规则，不是绝对规定。若颜色承担定量映射，应以数据语义与感知均匀性优先。

### 原则 3：优先使用成熟调色板

优先级建议：

1. 感知均匀、适合科学数据的成熟 colormap；
2. 软件或程序内置、经过广泛测试的 palette；
3. ColorBrewer / Okabe–Ito / Crameri Scientific Colour Maps / Viridis 系列；
4. 基于 RGB/HSL/LAB 色轮设计的自定义组合；
5. 从优秀论文中提取颜色时，只学习配色关系，不复制其独特视觉作品。

经验规则：

- 多组数据尽量控制在少量主色系内；通常不超过 3 个主色系更容易形成统一视觉语言；
- 类别数很多时，不要硬塞大量互补高饱和颜色，考虑分面、聚类、直接标注或矩阵表达；
- 新手优先使用成熟 palette，而不是从纯红、纯绿、纯蓝自行拼色。

### 原则 4：可以参考优秀论文配色

- 通过颜色滴管获得 RGB / HEX 值；
- 记录颜色的语义角色，例如“主结果色”“baseline 灰”“置信区间浅色”“强调阈值色”；
- 复现的是**配色逻辑**而不是照搬版式；
- 应检查提取出的颜色在白底、黑白打印和色觉缺陷模拟下是否仍然可辨认。

### 原则 5：使用专业配色网站与工具

推荐搜索与工具：

- ColorBrewer：<https://colorbrewer2.org/>
- Scientific Colour Maps：<https://www.fabiocrameri.ch/colourmaps/>
- Color Supply：<https://colorsupplyyy.com/app>
- Matplotlib Choosing Colormaps：<https://matplotlib.org/stable/users/explain/colors/colormaps.html>
- Okabe–Ito Color Universal Design：<https://jfly.uni-koeln.de/color/>

---

## 1.2.1 柱状图配色

### 一列数据

- 推荐单色或单一色系，通常较浅色填充最稳妥；
- 避免使用高饱和的“系统标准纯色”作为默认论文色；
- 柱体较窄时可适当加深颜色；柱体较宽时适合更柔和的浅色；
- 如果想使用深色，可通过 alpha 降低视觉重量；
- 若只有一个系列，不要让每根柱子随机不同颜色，除非颜色本身表示类别或状态。

参考示意：

![标准色示意](https://img-blog.csdnimg.cn/20210627102854934.jpg#pic_center)

### 两列数据

- 使用有足够辨识度但不刺眼的两种颜色；
- 可选成熟的双色 palette；
- 红蓝、蓝橙等组合可用，但必须检查色觉无障碍；
- 若两列代表同一变量的两个状态，可优先采用同一色系的深浅变化；
- 若两列代表对立或偏离关系，可采用 diverging palette 的两端颜色。

### 多列数据

- 如果是同一逻辑组，可使用相近色系；
- 如果是无顺序类别，应使用 qualitative palette；
- 避免过强对比和过多高饱和颜色同时出现；
- 不要同时滥用颜色、纹理、阴影、渐变和 3D 效果；
- 黑白打印时，可用灰度 + 纹理/轮廓线作冗余编码；
- 类别过多时优先改为 dot plot、heatmap、small multiples 或分组面板。

### 堆叠柱状图

原经验规则“堆叠柱状图使用深色”不应写成绝对命令。更合理的规则是：

- 采用**同一顺序色系**表示有序组成，或**可区分的定性色板**表示无序组成；
- 重要段可用较深色强调；
- 相邻堆叠段必须有足够亮度或色相差；
- 100% 堆叠图优先保证组间可比较性，必要时改用 small multiples。

## 1.2.2 饼图配色

- 饼图颜色通常较多，优先使用成熟 qualitative palette；
- 小面积扇区可使用稍深或对比更强的颜色，但不要仅靠深色“夸大”其视觉重要性；
- 类别超过约 5–6 个、需要精确比较或差异较小时，优先改为 bar / dot plot；
- 不使用 3D 饼图；
- 若只需要突出一个类别，可使用“一种强调色 + 其余灰色”。

## 1.2.3 折线图配色

- 折线较细，通常适合中深色或高对比色；
- 线宽应足以保证缩小到论文版面后仍清晰；
- 当曲线超过约 4–6 条并出现严重交叉时，优先考虑 small multiples、direct labeling、highlight + gray、heatmap、ridgeline 或其他表达；
- 黑白版本应综合使用颜色、线型、marker、直接标签等冗余编码；
- 连续变化变量可使用有序渐变，但时间序列中的多条独立曲线不应为了“连续感”强行渐变；
- 主曲线使用深色，辅助轨迹可用浅灰或低 alpha；
- 如果要强调一条目标曲线，其余曲线建议降饱和度或转灰。

## 1.2.4 散点图配色

- 点很多时可使用较小点、空心点、低 alpha 或 density/hexbin，避免完全遮挡；
- 深色 + 透明度适合高密度点云；
- 点大小可编码第三维连续变量，但必须给出 size legend，并避免面积感知误导；
- 类别较多时，颜色以 qualitative palette 为主，同时可使用 marker shape 作冗余编码；
- 某类别样本特别多时，不应仅通过“小点/大点”人为补偿，优先考虑 alpha、采样、密度图或分面；
- 若颜色表示连续变量，应使用 sequential/diverging colormap，而不是 categorical colors。

## 1.2.5 等高线图

等高线图通常包含较多线和色阶：

- 连续单调数值 → sequential colormap；
- 围绕零、均值或基准值正负偏离 → diverging colormap；
- 相位/角度等周期量 → cyclic colormap；
- 关键等值线可单独加粗或使用中性高对比轮廓；
- 颜色不能替代 contour labels，尤其是在黑白打印或精确读数场景；
- 避免使用 jet/rainbow 作为默认色标。

## 1.2.6 热图

热图颜色多，应根据数据语义选择 palette：

- 单调连续值：单向 sequential；
- 正负相关、残差、差值、偏离基准：diverging，并将色标中心锁定在有意义的值（常见为 0）；
- 分类矩阵：qualitative；
- 热图单元多时不要用过多注释文字；
- correlation heatmap 应优先使用以 0 为中点的发散色；
- 缺失值必须使用独立的中性颜色或 hatch，不得让其与真实数值混淆。

## 1.2.7 三维场、曲面与体数据配色

- 3D surface 中颜色应服务于高度之外的第二信息，或帮助读取高度；若颜色只是重复 z 值，要保持连续、感知均匀；
- isosurface 多层叠加时，应控制透明度并限制色数；
- volume rendering 优先选择单调的 opacity transfer function + 科学 colormap；
- 截面与表面同时出现时，同一物理变量应保持统一色标范围；
- 对多 panel 物理场比较，必须统一 `vmin/vmax`，除非明确说明每幅图独立归一化。

## 1.2.8 置信区间与不确定性配色

- 中心估计用较深色实线；
- 50%、80%、95% 区间使用同色系逐渐变浅的填充；
- ensemble spaghetti 中大量样本轨迹使用低 alpha，均值/中位数用深色突出；
- 不确定性不是“越花越不确定”，应优先通过透明度、亮度、纹理或独立 uncertainty panel 表达；
- 不确定性区间颜色不得遮蔽中心曲线或其他关键数据。

## 1.2.9 网络与空间图配色

- 网络社区 → qualitative palette；
- centrality / weight → sequential palette；
- 正负边权 → diverging palette；
- 空间 choropleth 必须根据数据类型选择 sequential/diverging/qualitative；
- 地图背景、道路、边界等上下文应降饱和度，避免抢过主数据层；
- 网络节点颜色和边颜色不应同时编码太多独立变量，否则优先拆 panel。

## 1.2.10 黑白打印与缩放检查

绘图完成后必须执行：

1. 缩小到论文最终版面尺寸检查可读性；
2. 转为灰度检查数据顺序是否仍然可理解；
3. 检查色觉缺陷模拟；
4. 确保关键结论不依赖颜色单一通道；
5. 必要时增加线型、marker、纹理、轮廓、标签等冗余编码。

---

# 2. 绘图实用工具与调色板知识库

## 2.1 RGB 颜色轮

色轮用于帮助理解颜色之间的关系，并辅助调色板选择。一个简化的 12 色 RGB 色轮可用于理解三原色、互补色与相邻色之间的关系。

![12色RGB颜色轮](https://img-blog.csdnimg.cn/img_convert/9221c9c59d4e6e375a7266acfaa10e20.png)

参考：Plante & Cushman, *Choosing color palettes for scientific figures*：
<https://onlinelibrary.wiley.com/doi/full/10.1002/rth2.12308>

可使用以下关系从色轮中选择颜色：

- **互补色 Complementary colors**：色轮上相对的两种颜色；
- **相似色 Analogous colors**：色轮上彼此相邻的颜色；
- **三元组色 Triad colors**：色轮上 3 种均匀分布的颜色；
- **四元色 Square colors**：色轮上 4 种均匀分布的颜色；
- **分列互补色 Split complementary colors**：基准色 + 其补色两侧相邻颜色；
- **双互补色 Double complementary / Tetrad colors**：两组互补色。

![色轮配色关系](https://img-blog.csdnimg.cn/img_convert/6009b02dad853d81e6ff7163f02d32d3.png)

实践中可使用：

- Color Supply：<https://colorsupplyyy.com/app>
- Sessions Color Calculator：<https://www.sessions.edu/color-calculator/>
- RapidTables Color Wheel：<https://www.rapidtables.com/web/color/color-wheel.html>

> 注意：色轮关系主要解决“颜色之间是否协调”，**不能替代数据语义、感知均匀性与色觉无障碍检查**。

## 2.2 色盲 / 色觉无障碍读图

色觉缺陷读者可能难以区分某些低对比颜色，因此图形不能只依赖颜色区分类别。

推荐规则：

- 不把红-绿组合作为默认的唯一编码；
- 使用颜色 + 线型 + marker + 纹理 + 直接标签等冗余编码；
- 选择亮度差异足够的颜色；
- 分类色优先考虑 Okabe–Ito 等色觉友好 palette；
- 连续变量优先使用 Viridis/Cividis 或经过验证的科学 colormap；
- 输出前检查 protanopia / deuteranopia / tritanopia 模拟；
- 图例顺序应与图中元素顺序一致，能直接标注时优先直接标注。

Okabe & Ito 的 Color Universal Design：
<https://jfly.uni-koeln.de/color/>

![Okabe-Ito 色觉友好示意](https://img-blog.csdnimg.cn/img_convert/8df0fc7dd19fdf8521dc0c34c71c1b3b.png)

> 学术修正：不要把“红色和绿色永远不能同时出现”理解成绝对禁令。更准确的规则是：**不要让红/绿成为区分组别的唯一线索**；如果确有语义需要，可搭配显著亮度差、线型、marker、标签等冗余编码。

## 2.3 图像调色板

### 2.3.1 Sequential / 有序调色板

适用于具有自然顺序的定量数据，例如浓度、温度、概率、密度、误差幅值等。

- 数据不断增加或减少时，优先采用单调亮度变化；
- 一般让较深颜色表示“更多/更大”更符合直觉；
- 推荐：`viridis`, `cividis`, `plasma`, `inferno`, `magma`, ColorBrewer sequential，以及 Crameri sequential maps（如 `batlow`, `imola`, `oslo`）。

![Sequential palette 示例](https://img-blog.csdnimg.cn/img_convert/3ad9c4fca8069e62f5d8a4c674e15fd0.png)

例如降水图中，较暗区域可以代表较大的值：

![Sequential map 示例](https://img-blog.csdnimg.cn/img_convert/67d00a60574fb7f6e4ccc244743d7f6c.png)

### 2.3.2 Diverging / 发散调色板

当数据围绕一个**有意义的中心值**发散时使用，例如：

- 残差围绕 0；
- 温度异常相对基准值；
- 正负相关；
- 预测误差正负偏差；
- 收益/损失。

规则：

- 中心值应明确设置，例如 `center=0`；
- 两端采用对比色相；
- 中间通常较浅；
- 推荐 ColorBrewer diverging、Crameri `vik`, `broc`, `roma`, `berlin` 等。

![Diverging palette 示例](https://img-blog.csdnimg.cn/img_convert/e62f3f66ecc8e2bfc8c0395effaa1c60.png)

### 2.3.3 Qualitative / 定性调色板

适用于没有自然顺序的分类数据：

- 各类别颜色应易区分；
- 不应暗示“颜色越深数值越大”；
- 类别尽量不要过多；
- 优先 Okabe–Ito、ColorBrewer qualitative、Paul Tol 等色觉友好 palette；
- 类别很多时优先拆分、聚类或 small multiples，而不是无限增加颜色。

![Qualitative palette 示例](https://img-blog.csdnimg.cn/img_convert/6e496f0f2fc5afa7fe3cd38450eb1ef1.png)

### 2.3.4 Cyclic / 周期调色板

用户原始规则中缺少这一类。以下数据必须优先考虑 cyclic colormap：

- 相位角 `0° = 360°`；
- 风向；
- 周期时间；
- 环形变量；
- 周期边界条件结果。

推荐搜索：

- `cyclic perceptually uniform colormap`
- Crameri `romaO`, `vikO`, `brocO`, `corkO`

### 2.3.5 Rainbow / Jet 使用规则

如果可以避免，不要使用传统 rainbow / jet 作为连续定量数据默认色标。

原因：

- 感知变化不均匀；
- 容易制造不存在的视觉边界；
- 灰度打印表现差；
- 对部分色觉缺陷读者不友好。

参考：

- Climate Lab Book, *The end of the rainbow*：<https://www.climate-lab-book.ac.uk/2014/end-of-the-rainbow/>
- Crameri et al., *The misuse of colour in science communication*：<https://www.nature.com/articles/s41467-020-19160-7>

Matplotlib 当前提供感知较均匀的 `viridis`, `plasma`, `inferno`, `magma`, `cividis` 等连续色标；MATLAB 自 R2014b 起将默认 colormap 从 `jet` 改为 `parula`。

## 2.4 推荐科研调色板库

### Matplotlib / Python

**Sequential / perceptually uniform**

- `viridis`
- `cividis`
- `plasma`
- `inferno`
- `magma`

**常用 diverging**

- `RdBu`
- `PuOr`
- `BrBG`
- `PRGn`

使用 diverging 时必须明确中心值。

### ColorBrewer

按数据类型分为：

- Sequential
- Diverging
- Qualitative

并可筛选：

- colorblind safe
- print friendly
- photocopy safe

官网：<https://colorbrewer2.org/>

### Okabe–Ito

适合离散分类数据，是重要的色觉友好定性色板来源。

官网：<https://jfly.uni-koeln.de/color/>

### Scientific Colour Maps / Crameri

适合科学连续场、发散场和周期量。代表：

- sequential: `batlow`, `imola`, `oslo`, `lajolla`
- diverging: `vik`, `broc`, `roma`, `berlin`
- cyclic: `romaO`, `vikO`, `brocO`, `corkO`

官网：<https://www.fabiocrameri.ch/colourmaps/>

### MATLAB

- 默认连续图常用 `parula`；
- 如果需要与 Python 图统一，可显式选择对应科学 colormap，而不要依赖不同软件的默认色。

## 2.5 AI 配色自动决策规则

AI 每次绘图前必须生成 `COLOR_PROFILE`：

```yaml
color_profile:
  encoding_role: category | magnitude | deviation | phase | uncertainty | emphasis | community
  data_type: qualitative | sequential | diverging | cyclic
  meaningful_center:
  number_of_categories:
  highlight_target:
  background_context:
  colorblind_required: true
  grayscale_required: true
  output_medium: screen | print | both
  shared_scale_across_panels: true
```

决策规则：

```text
IF 无序类别:
    qualitative palette
ELIF 单调连续数值:
    perceptually uniform sequential palette
ELIF 围绕零/均值/基准正负偏离:
    diverging palette + meaningful center
ELIF 相位/角度/周期量:
    cyclic palette

IF 主结果需要强调:
    one accent color + muted context

IF 大面积填充:
    reduce chroma / increase lightness / lower alpha

IF 细线或小点:
    stronger contrast allowed

IF > 6 categories:
    first consider faceting / direct labels / grouping before adding colors

ALWAYS:
    run color-vision accessibility check
    run grayscale check
    preserve palette semantics across panels
```

## 2.6 AI 搜索配色方案的关键词库

当用户要求“更高级”“顶刊风格”“Nature 风格”或“论文配色”时，先依据数据语义选择成熟调色板；只有用户要求检索、领域规范不明确或确需核对来源时，再使用以下搜索词，而不是随机给出 HEX：

```text
"scientific figure color palette perceptually uniform"
"colorblind safe scientific palette"
"sequential diverging qualitative colormap scientific visualization"
"<domain> publication figure color palette"
"<domain> scientific colour map"
"Nature figure accessibility colors"
"ColorBrewer colorblind safe"
"Okabe Ito palette"
"Crameri scientific colour maps"
"Matplotlib perceptually uniform colormap"
```

判断优先级：

1. 是否符合数据语义；
2. 是否感知均匀；
3. 是否色觉友好；
4. 是否黑白打印可辨；
5. 是否适合图形面积；
6. 是否与整篇论文保持统一；
7. 最后才考虑“好不好看”。

## 2.7 配色审查清单

绘图完成后，AI 必须逐项检查：

- [ ] 每种颜色是否有数据意义？
- [ ] 相同变量是否跨图保持同色？
- [ ] 连续变量是否用了 sequential / diverging / cyclic 中正确的一类？
- [ ] diverging 是否设置了有意义的中心值？
- [ ] 是否避免 jet/rainbow 默认使用？
- [ ] 关键元素是否比背景更醒目？
- [ ] 大面积填充是否过饱和？
- [ ] 折线/小点是否对比不足？
- [ ] 色觉缺陷读者是否能区分关键组？
- [ ] 黑白打印后是否仍能理解？
- [ ] 多 panel 是否统一 color scale？
- [ ] 图例是否与实际图形顺序/语义一致？
- [ ] 是否存在无意义颜色数量过多的问题？
- [ ] 是否可以通过直接标签减少图例依赖？

## 2.8 本模块网页与学术来源

- Plante TB, Cushman M. *Choosing color palettes for scientific figures*. Research and Practice in Thrombosis and Haemostasis, 2020. <https://pmc.ncbi.nlm.nih.gov/articles/PMC7040535/>
- Matplotlib. *Choosing Colormaps in Matplotlib*. <https://matplotlib.org/stable/users/explain/colors/colormaps.html>
- ColorBrewer 2.0. <https://colorbrewer2.org/>
- Okabe M, Ito K. *Color Universal Design*. <https://jfly.uni-koeln.de/color/>
- Crameri F, Shephard GE, Heron PJ. *The misuse of colour in science communication*. Nature Communications, 2020. <https://www.nature.com/articles/s41467-020-19160-7>
- Crameri F. *Scientific Colour Maps*. <https://www.fabiocrameri.ch/colourmaps/>
- Nature Research Figure Guide. *Building and exporting figure panels — Accessibility*. <https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/>
- Hawkins E et al. *The end of the rainbow*. Climate Lab Book. <https://www.climate-lab-book.ac.uk/2014/end-of-the-rainbow/>
- MathWorks. *parula / colormap documentation*. <https://www.mathworks.com/help/matlab/ref/parula.html>

---

# 3. 高阶数模论文插图与分析生成模式

本模块面向数学建模竞赛、课程建模论文、国赛/美赛论文以及需要直接进入 LaTeX 的科研插图。核心目标不是“炫技”，而是实现：

> **数据真实 → 尺寸与版式可控 → 物理/数学机理清楚 → 图表直接进入 LaTeX → 图后分析形成论证闭环**

## 3.1 模式触发与交互纪律

默认将该模式设为：

```yaml
COMPETITION_FIGURE_MODE:
  interaction: follow_user_request
  fabricate_data: forbidden
  final_format:
    - vector_PDF_or_SVG
    - raster_preview_when_needed
  latex_ready: true
  analysis_required: true
  figure_language: zh-CN
```

当用户要求“按三阶段流程”“先规划再画图”“等待我确认”“数模论文插图模式”等时，必须严格采用以下三阶段流程，**严禁一次性跑完**。

优先级规则：

1. 用户明确要求“等待确认”时，必须停在对应阶段；
2. 用户明确说“直接画 / 不用确认 / 一次完成”时，可切换为 `direct_execute`；
3. 若用户未说明，可在一次任务内完成规划、绘图和验证，不强制等待额外确认；
4. 当前模块中的“不造假”“真实数据审计”“版式检查”属于硬约束，即使用户要求直接执行也不能跳过。

中文数学建模竞赛中，图表内可见文字默认使用中文。数学变量、单位符号、算法缩写和文件名可保留规范写法，但坐标含义、图例类别、色条名称和图内说明不得无故改成英文。

---

## 3.2 第一阶段：可视化方案规划与数据审计（等待确认）

角色设定：

> 你现在是拥有十年国赛/美赛指导经验的数模专家与数据可视化大师。我们需要为数学建模论文制作能够直接插入 LaTeX 的高保真学术图表，并配上无缝衔接的分析文段。

收到用户的求解进度、模型、代码输出、数据表、图片、实验结果或部分结果后，**先审计数据，不立即绘图**。

### 3.2.1 严格红线：禁止数据造假

必须遵守：

- 必须基于真实计算数据；
- 严禁自行编造不存在的数据点；
- 严禁为了让曲线“更漂亮”而补齐不存在的时间点或空间点；
- 严禁把插值值伪装成原始计算值；
- 严禁使用没有说明的平滑、滤波或拟合改变原始结论；
- 严禁为了得到“理想趋势”删除异常值；
- 若采用插值、平滑、拟合、降采样、重采样，必须明确说明；
- 若绘图所需变量缺失，必须明确指出“还需要计算什么”，不能私自估算填补；
- 示例/示意数据只能在用户明确要求“示意图”时使用，并必须标注为 illustrative / schematic，不得混入正式结果图。

### 3.2.2 数据审计清单

在推荐图前检查：

```yaml
DATA_AUDIT:
  source_file:
  raw_or_derived:
  sample_count:
  variable_names:
  units:
  missing_values:
  duplicated_rows:
  time_resolution:
  spatial_resolution:
  mesh_information:
  stochastic_trials:
  confidence_information:
  interpolation_used:
  smoothing_used:
  normalization_used:
  reference_or_ground_truth:
  constraints:
  threshold:
  missing_required_variables:
```

如发现数据存在明显问题，先指出问题，再进行可视化推荐。

### 3.2.3 推荐少量最能支撑模型结论的图表

推荐的不是“最好看”的图，而是**最能证明本小问结论**的图。

候选数量按任务复杂度决定。图型明确时可直接推荐 1–2 种；确有多种合理方案时再比较更多候选。可使用下表格式：

| 图表名称 | 横纵轴 / 颜色映射含义 | 展示的物理 / 数值规律 | 所需变量及当前数据是否具备 | 对论文的核心作用 | 推荐度 |
| --- | --- | --- | --- | --- | --- |
| 图 1 | 明确写出 x、y、颜色、点大小等 | 要揭示的规律 | 已具备 / 缺失及需补算内容 | 解决什么论证问题 | ★★★★★ |
| 图 2 | ... | ... | ... | ... | ★★★★☆ |

推荐度使用：

- ★★★★★：论文主图级，直接支撑核心结论；
- ★★★★☆：强辅助图，解释机制或可信度；
- ★★★☆☆：可用，但与其他图存在信息重复；
- ★★☆☆☆：仅在篇幅允许时使用；
- ★☆☆☆☆：不建议正式使用。

### 3.2.4 第一阶段结束规则

只有用户明确要求“先规划、等待确认”时，输出推荐表后才必须：

> **停止继续绘图，等待用户指定要绘制的图表名称。**

不得提前：

- 编造绘图数据；
- 输出完整绘图代码；
- 假装已经生成图片；
- 自动进入第二阶段。

---

## 3.3 第二阶段：专业绘图与学术渲染（收到指定后执行）

用户指定图表后，使用真实数据进行处理和绘图。Python 优先使用：

- Matplotlib：正式科研图核心；
- Seaborn：统计型图形；
- SciencePlots：作为可选学术 style，不得机械依赖；
- NumPy / Pandas / SciPy：真实数据计算；
- 必要时使用 Plotly、PyVista、VTK、ParaView 等处理特殊三维/场数据，但正式静态论文图仍需满足本模块的导出规范。

### 3.3.1 尺寸控制：先按论文版式设计，再画图

**禁止“先画一个巨大图片，最后在 LaTeX 里暴力缩小”。**

默认版式基准：

```python
FIGSIZE_SINGLE = (3.5, 2.6)   # 单栏图，inch
FIGSIZE_DOUBLE = (7.2, 4.2)   # 双栏图，inch
```

Matplotlib 的 `figsize` 单位是英寸，应在创建 Figure 时定义：

```python
fig, ax = plt.subplots(figsize=FIGSIZE_SINGLE)
```

但必须理解：

> `3.5 × 2.6 in` 与 `7.2 × 4.2 in` 是竞赛/双栏论文的**实用默认基准，不是所有模板的全球统一标准**。

如果论文模板明确给出：

- `\columnwidth`
- `\linewidth`
- `\textwidth`
- 期刊 figure width

则必须以模板真实宽度优先，并反推 Python 图宽。

推荐决策：

```text
模板有明确栏宽 → 使用模板栏宽
没有模板信息 → single = 3.5 in, double = 7.2 in
```

### 3.3.2 PDF + PNG 双轨导出

正式图按内容选择输出格式：

1. **折线、散点、示意图优先导出 PDF 或 SVG，保留矢量元素；**
2. **热力图、照片等栅格内容按最终物理尺寸导出 300–450 dpi PNG；**
3. 仅在模板、印刷或投稿规范明确要求时使用 600 dpi；不强制为每幅矢量图再生成高分辨率 PNG。

基础代码：

```python
fig.savefig(
    "figures/figure_name.pdf",
    bbox_inches="tight"
)

fig.savefig("figures/figure_name.png", dpi=350, bbox_inches="tight")
```

注意：

- `dpi` 对栅格输出控制分辨率；
- `bbox_inches="tight"` 会根据内容计算紧边界并裁去多余空白；
- 如果投稿模板对“最终物理尺寸”有极严格规定，应在导出后检查最终 bounding box，避免 `tight` 裁切导致成品尺寸与设计 canvas 略有差异；
- 可以配合 `constrained_layout=True` 或合理 `subplots_adjust`，减少依赖过度裁切。

严禁：

- 正式论文只保存低分辨率截图；
- 图表保存为 JPEG；
- 使用屏幕截图替代原始输出；
- PDF 中关键文字被低分辨率栅格化而不可辨识。

### 3.3.3 字体规范

中文竞赛论文默认风格：

- 图表内的坐标含义、图例、色条和说明使用中文；
- 中文字体优先继承论文模板；模板未规定时，在实际已安装的宋体、思源宋体、FandolSong 等字体中选择；
- 数字、数学符号和单位与正文数学字体协调，不强制指定 Times New Roman；
- 文件名、代码变量名可以使用英文，但不得把图内解释性文字改成英文。
- 数学符号：与正文数学字体风格协调。

字号建议：

| 元素 | 推荐字号 |
| --- | --- |
| 轴标签 | 9–10 pt |
| 刻度标签 | 8–9 pt |
| 图例 | 8–9 pt |
| 子图编号 `(a)(b)(c)` | 9–10 pt，可加粗 |
| 图内关键注释 | 8–9 pt |

必须保证：

- 同一论文所有图字号层级一致；
- 缩放到最终论文尺寸后仍然可读；
- 中文与英文不发生明显风格冲突。

### 3.3.4 字体存在性检查

指定字体并非所有系统默认安装。

绘图前可检测：

```python
from matplotlib import font_manager

available_fonts = {f.name for f in font_manager.fontManager.ttflist}

for preferred in ["SimSun", "Source Han Serif SC", "FandolSong"]:
    print(preferred, preferred in available_fonts)
```

若目标字体不存在：

- 不得假装已经使用该字体；
- 明确提示字体 fallback；
- 优先使用用户环境中实际存在、与论文要求最接近的字体；
- 不得私自下载或分发商业字体文件。

### 3.3.5 Matplotlib / SciencePlots 学术样式

可使用：

```python
import matplotlib.pyplot as plt
import scienceplots

plt.style.use("science")
```

也可组合：

```python
plt.style.use(["science", "grid"])
```

但注意：

- SciencePlots 是 style 工具，不代表使用后自动成为“顶刊图”；
- CJK 字体仍需要系统实际安装；
- style 的字号、线宽、图宽必须根据当前论文模板再次检查；
- 用户已有严格竞赛版式时，自定义 `rcParams` 优先于盲目使用整套 style。

### 3.3.6 配色策略

严格调用本 Skill 的“科研论文配色与视觉编码规范”。

基础推荐：

- 连续单调数据：`viridis`、`cividis` 等 perceptually uniform sequential map；
- 正负偏离：有意义中心值下使用 `coolwarm`、`RdBu_r`、`vik` 等 diverging map；
- 多类别：使用色盲友好的 qualitative palette；
- 不确定性区间：主色 + 低 alpha 浅色带；
- 正式图必须检查灰度可读性。

不得因为“SciencePlots / coolwarm / viridis 看起来学术”就无脑套用，调色板必须与数据语义匹配。

### 3.3.7 线条、点、网格与标注

建议：

- 主曲线线宽通常 `1.4–2.0 pt`；
- 次要曲线稍细、稍浅；
- 散点根据最终尺寸控制 marker，避免过大；
- 网格线使用浅灰、低 alpha，只起辅助定位作用；
- 阈值线、临界点、最优点必须直接标注；
- 不要用粗边框和过重网格争夺视觉注意力；
- 图例优先放在不遮挡数据的位置；
- 单位写入轴标签，而不是藏在正文；
- 物理变量尽量使用规范数学符号。

---

## 3.4 第三阶段：LaTeX、图注与四层逻辑解析

图生成后，必须紧跟输出论文可直接使用的闭环内容。

### 3.4.1 LaTeX 插图代码

默认：

```latex
\begin{figure}[htbp]
    \centering
    \includegraphics[width=0.85\textwidth]{figures/图表文件名.pdf}
    \caption{中文简短图名}
    \label{fig:图表标签}
\end{figure}
```

若为严格单栏排版，优先根据实际环境调整为：

```latex
\includegraphics[width=\linewidth]{figures/figure_name.pdf}
```

若为双栏跨栏图，可按模板选择 `figure*`。

要求：

- 文件名使用稳定英文/数字名称更利于跨平台编译；
- `label` 使用语义化名称，例如 `fig:grid-convergence`；
- Caption 不写成正文长段落；
- 正文必须通过 `图~\ref{fig:...}` 或相应语言引用，不得让图片悬空出现。

### 3.4.2 中文简短图名

中文比赛默认给出：

```text
中：图 X [简短、客观、信息明确的描述]
```

图名原则：

- 不使用“漂亮地展示了”“明显说明了”等主观形容；
- Caption 描述画的是什么；
- 解释“为什么”放入正文分析。

### 3.4.3 正文分析段落：按论证需要控制长度

禁止空泛“看图说话”。

分析段不设固定字数。优先用一段紧凑文字完成现象、机理、可信度和解题作用；已有表格或前文已给出证据时避免重复。

必须按照：

#### 第一层：现象描述

只陈述图中真实可观察事实，例如：

> 随时间推进，高含水率区域由表面向圆柱中心收缩，近表面区域的浓度梯度逐渐增大。

禁止把“推测原因”混进现象层。

#### 第二层：机理解释

回答：

> 为什么会出现这个形态？

使用当前模型中的真实方程、边界条件、参数依赖、守恒规律、耦合关系或现实机制解释。

例如：

> 该趋势来源于扩散系数 \(D(C,T)\) 对含水率的非线性依赖；随着局部含水率降低，有效扩散能力下降，从而使内部传质过程逐渐成为控制环节。

不得发明模型中不存在的机制。

#### 第三层：模型验证 / 数值可信度

根据当前任务使用真实证据，包括但不限于：

- 网格收敛；
- 时间步收敛；
- 质量/能量守恒；
- 与观测值一致；
- 残差稳定；
- 参数敏感性符合预期；
- Monte Carlo 置信区间稳定；
- 理论极限一致。

例如：

> 不同网格尺度下中心温度曲线基本重合，且 GCI 随网格细化下降，说明该结论并非离散尺度造成的数值伪影。

如果当前没有验证数据，必须写：

> 当前数据尚不足以完成数值验证，需要补充 XXX。

严禁虚构“验证通过”。

#### 第四层：解题作用

用一句话回答：

> 这个发现对当前问题或下一问有什么直接价值？

例如：

> 因此可将中心含水率达到 \(C(0,t)=0.15\) 视为整体干燥进程的关键事件，并作为下一问优化终止时间的判据。

---

## 3.5 图后分析模板

AI 可按照以下结构组织，不允许机械套话：

```text
由图 X 可见，[客观现象]。
从模型机理看，[由方程、参数或现实机制解释原因]。
进一步结合[网格收敛/误差/守恒/敏感性/置信区间/真实观测]可知，
[说明该现象具有数值或物理可信度]。
因此，[说明该结论对当前小问、参数确定或下一问优化的直接作用]。
```

使用要求：

- 每一句必须落到具体变量；
- 尽量包含数值范围、峰值、阈值、斜率、时间点、空间位置等定量证据；
- 没有数据就不写具体数字；
- 没有验证就不写“验证了”；
- 不重复 Caption。

---

## 3.6 “高分论文”图表审计清单

正式交付前必须逐项检查：

### 数据真实性
- [ ] 所有数据来自真实文件或真实计算；
- [ ] 插值/平滑/拟合已经说明；
- [ ] 没有私自补数据；
- [ ] 没有删掉不利于结论的异常点；
- [ ] 示例数据未混入正式图。

### 论文论证
- [ ] 这张图回答了明确问题；
- [ ] 图与正文模型方程存在对应关系；
- [ ] 图不是纯装饰；
- [ ] 与其他图没有严重信息重复；
- [ ] 关键阈值/最优点/可行域已标识。

### 尺寸与排版
- [ ] 按最终论文尺寸绘制；
- [ ] 单栏/双栏判断正确；
- [ ] 缩放后文字仍可读；
- [ ] 字号层级统一；
- [ ] 图例不遮挡关键数据。

### 配色
- [ ] 色图与数据语义一致；
- [ ] 色盲可读；
- [ ] 灰度仍可区分；
- [ ] 多 panel 同变量颜色一致；
- [ ] 未滥用 rainbow/jet。

### 导出
- [ ] PDF 已导出；
- [ ] 栅格内容已按最终尺寸导出 300–450 dpi；若无需栅格副本则不强制导出 PNG；
- [ ] `bbox_inches="tight"` 或其他版式策略正确；
- [ ] 图片未被截图或 JPEG 压缩；
- [ ] 文件名适合 LaTeX。

### 分析
- [ ] 包含现象；
- [ ] 包含机理；
- [ ] 包含可信度/验证；
- [ ] 包含解题作用；
- [ ] 没有使用空泛结论。

---

## 3.7 可直接复制使用的完整提示词

```text
你现在是拥有十年国赛/美赛指导经验的数模专家与数据可视化大师。
我们需要为数学建模论文制作能够直接插入 LaTeX 的高保真学术图表，
并配上无缝衔接的分析文段。

按我的交互要求执行：若我要求“先规划、等待确认”，则停在第一阶段；若我要求直接完成，可以连续完成规划、绘图和验证。

【第一阶段：可视化方案规划与数据审计】
基于我提供的求解进度或真实数据，推荐少量最能直接支撑模型结论的图表。图型明确时无需凑足候选数量。

严格红线：
1. 严禁造假。
2. 严禁自行编造、补齐或平滑不存在的数据。
3. 若图表需要的变量缺失，必须明确指出还需计算什么。
4. 插值、拟合、滤波、降采样必须说明。
5. 图表必须服务于论文论证，不得为了“高级”强行使用复杂图。

请使用表格输出：
- 图表名称
- 横纵轴 / 颜色映射含义
- 展示的物理 / 数值规律
- 所需变量及当前数据是否具备
- 对论文的核心作用
- 推荐度（★ 至 ★★★★★）

只有我明确要求等待确认时，输出表格后停止。

【第二阶段：专业绘图与学术渲染】
收到我指定的图表后，使用真实数据编写 Python 绘图代码。

要求：
1. 绘图前按最终 LaTeX 版式确定尺寸。
   默认单栏 figsize=(3.5, 2.6)，双栏 figsize=(7.2, 4.2)；
   若模板提供实际栏宽，以模板为准。
2. 折线、散点和示意图优先保存矢量 PDF；热力图等栅格内容按最终尺寸保存 300–450 dpi PNG。只有明确要求时才另存 600 dpi。
3. 正式输出使用 bbox_inches="tight"，同时检查最终物理尺寸。
4. 图内坐标含义、图例、色条与注释使用中文；数学变量、单位和通用算法缩写可保留规范写法。字体优先继承论文模板，并检查字体是否真实安装。
5. 轴标签 9–10 pt，刻度 8–9 pt，图例 8–9 pt。
6. 可以使用 SciencePlots，但 style 不得替代真正的数据逻辑与版式设计。
7. 调色板必须按 qualitative / sequential / diverging / cyclic 数据语义选择。
8. 图必须支持灰度打印和色觉无障碍。
9. 阈值、临界点、最优点、置信区间、误差带等应在有真实数据时直接表达。

【第三阶段：LaTeX + Caption + 四层逻辑分析】
图生成后紧跟输出：

1. LaTeX 插图代码；
2. 中文简短 Caption；
3. 长度与图的论证任务匹配的正文分析，不设置固定字数。

正文严格按照四层逻辑：
- 现象描述：只说图中真实事实；
- 机理解释：用模型方程、参数、守恒规律或现实机制解释；
- 模型验证：用网格收敛、误差、守恒、敏感性、置信区间或观测数据证明可信度；
- 解题作用：说明该结论对本问或下一问的直接价值。

若没有验证数据，必须明确说明“当前尚不能完成该项验证”，不得虚构验证通过。
```

---

## 3.8 本模块网页核对依据

本模块的具体数值属于竞赛实用规范；在执行时仍应服从目标论文模板。下列外部依据用于约束 AI 不要把经验规范误认为软件或出版系统的绝对规则：

- **Matplotlib Figure configuration**：`figure.figsize` 的单位为英寸，Figure 的 DPI 与尺寸均可通过 `rcParams` 或 Figure API 控制。
- **Matplotlib `savefig`**：支持 PDF、PNG、SVG 等格式；`dpi` 控制栅格输出分辨率；`bbox_inches="tight"` 会按图形内容计算紧边界。
- **Matplotlib fonts**：字体名称只有在运行环境中实际可用时才能正确选取，字体家族可通过 `rcParams` 或 `font_manager` 控制。
- **SciencePlots**：用于科学论文的 Matplotlib styles；当前版本需先 `import scienceplots` 再调用 style，CJK 字体需要单独安装。
- 因此：**模板实际栏宽 > 本 Skill 默认尺寸；真实字体可用性 > 字体名称声明；真实数据 > 视觉效果。**

参考入口：
- https://matplotlib.org/stable/users/explain/configuration.html
- https://matplotlib.org/stable/api/figure_api.html
- https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.savefig.html
- https://matplotlib.org/stable/users/explain/text/fonts.html
- https://matplotlib.org/stable/gallery/text_labels_and_annotations/font_family_rc.html
- https://pypi.org/project/SciencePlots/

---

# 4. 强制工作流

## Stage A — 读取问题，不立即画图

先提取：

- 研究问题是什么；
- 论文当前小问要证明什么；
- 数据属于何种结构；
- 是否存在时间、空间、参数、重复试验、随机样本、网络、概率、类别或高维变量；
- 是否有真实观测值；
- 是否存在阈值、约束、最优点、临界状态；
- 是否涉及 PDE / ODE / Monte Carlo / ML / Optimization / Network / GIS / Bayesian 等。

建立 `DATA_PROFILE`：

```yaml
data_profile:
  dimensionality:
  independent_variables:
  dependent_variables:
  time_axis:
  spatial_axes:
  vector_field:
  repeated_samples:
  uncertainty_samples:
  observed_vs_predicted:
  categorical_variables:
  network_structure:
  optimization_objectives:
  constraints:
  threshold:
  high_dimensional:
  color_encoding_role:
  color_data_type:
  meaningful_color_center:
  colorblind_required: true
  grayscale_required: true
```

## Stage B — 判断论文论证任务

从以下任务中选择一个或多个：

```text
STATE        物理状态
EVOLUTION    时空演化
MECHANISM    机制/耦合
VERIFICATION 数值验证
VALIDATION   模型验证
SENSITIVITY  灵敏度
UNCERTAINTY  不确定性
STATISTICS   数据统计
OPTIMIZATION 优化
ROBUSTNESS   鲁棒性
NETWORK      网络
SPATIAL      空间
DYNAMICS     动力系统
XAI          模型解释
HIGH_DIM     高维结构
RELIABILITY  可靠性
BAYESIAN     贝叶斯推断
TOPOLOGY     拓扑/形态
```

## Stage C — 召回与任务匹配的候选图

候选数量由任务歧义和数据复杂度决定。普通折线图、柱状图或散点图若能最直接、准确地回答问题，可以直接采用；不为追求“高级感”强制换成复杂图型。

优先召回：
- 一张“主结论图”；
- 一张“解释机制图”；
- 一张“可信度/不确定性图”。

## Stage D — 仅在确有必要时网页检索

闭合的模型—数据分析任务默认不需要检索。满足以下任一条件时才检索：

- 用户明确要求“高级、创新、顶刊风格、搜图型”；
- 领域规范或图型含义不明确；
- 本地库中没有足以完成论证的图型；
- 数据结构特殊且存在误用风险；
- 需要寻找最近几年新的可视化方法；
- 希望模仿某领域论文的表达方式，但不得复制具体作品。

### 搜索模板

```text
"<domain> scientific visualization review"
"<domain> visualization methods simulation results"
"<domain> publication figure parameter space visualization"
"<method> visualization paper"
"<data type> advanced visualization scientific paper"
"<task> uncertainty visualization review"
"<task> multiobjective optimization visualization review"
"<task> numerical verification visualization"
"<task> model validation visualization"
site:matplotlib.org <plot>
site:plotly.com/python <plot>
site:docs.paraview.org <plot>
site:scikit-learn.org <plot>
site:shap.readthedocs.io <plot>
site:python.arviz.org <plot>
site:networkx.org <plot>
site:manual.cytoscape.org <plot>
site:gephi.org <plot>
site:itl.nist.gov <plot>
```

### 搜索优先级

1. 原始论文 / review / survey；
2. 官方科学计算软件文档；
3. 高质量科研机构教程；
4. 社区示例仅用于发现名称，不作为方法正确性的唯一依据。

搜索时重点寻找：

- 图形正式英文名称；
- 数据要求；
- 它回答什么研究问题；
- 是否为该领域常见；
- 是否存在误用风险；
- 能否与另一图层叠加形成复合图。

## Stage E — 图型适配判断

按以下优先顺序比较候选图，不使用脱离任务的固定权重，也不把“视觉新颖”作为独立加分项：

```text
ArgumentFit > DataFit > Interpretability > InformationDensity > PublicationNorm
并扣除 MisusePenalty
```

其中：

- `ArgumentFit`：是否直接证明论文命题；
- `DataFit`：数据是否天然支持；
- `InformationDensity`：一张图能否同时传达多个有效信息；
- `Interpretability`：读者能否正确读懂；
- `PublicationNorm`：该领域是否合理；
- `MisusePenalty`：3D 遮挡、双轴误导、雷达图难比较、过量颜色等。

## Stage F — 推荐少量互补图

输出候选表：

```text
图名 | 解决的问题 | 需要的数据 | 为什么比普通图更好 | 推荐等级 | 风险
```

通常选择 1–3 个互补图；若一个基础图已经足够，则不凑数。如果用户要求直接生成图，则自行选择最合适的组合，不再要求确认。

## Stage G — 组合图优先于堆图

优先考虑复合图，例如：

- Filled Contour + Streamline；
- Heatmap + Contour Boundary；
- Response Surface + Projected Contours + Optimum；
- Pareto Front + Density + Knee Point；
- Logistic Curve + Confidence Band + Threshold Inversion；
- Scatter + Marginal KDE；
- Violin + Box + Raw Points；
- Network + Community Color + Centrality Size；
- Spatial Map + Uncertainty Overlay；
- Observed-vs-Predicted + Error Bands；
- Posterior Density + HDI + ROPE；
- Isosurface + Slice Plane + Streamlines。

---

# 5. 高级图表名称知识库

以下库中的英文名是 AI 搜索时的优先关键词。
中文名用于解释，不要求绘图库存在同名函数。

---

## A. 物理状态场 / PDE / 多物理场

- Scalar Field Heatmap｜标量场热图
- Filled Contour Plot｜填充等值线图
- Iso-contour Map｜等值线图
- Contour Overlay Map｜多场等值线叠加图
- 3D Surface Plot｜三维状态曲面
- Wireframe Surface｜网格曲面
- Triangulated Surface / TriSurf｜非结构网格曲面
- Height-field / Carpet Plot｜高度场/地毯图
- Slice Plane Visualization｜切片平面
- Multi-slice Volume View｜多切片体视图
- Orthogonal Slice View｜正交三切面
- Isosurface Rendering｜等值面
- Nested Isosurfaces｜多层等值面
- Volume Rendering｜体渲染
- Direct Volume Rendering｜直接体渲染
- Maximum Intensity Projection｜最大强度投影
- Voxel Rendering｜体素渲染
- Cutaway View｜剖切视图
- Exploded View｜爆炸视图
- Clipping-plane Visualization｜裁剪平面
- Thresholded Volume｜阈值体区域
- Volume + Isosurface Composite｜体渲染+等值面
- Slice + Isosurface Composite｜切片+等值面
- Contour + Mesh Composite｜等值线+计算网格
- Difference Field Map｜差值场
- Relative Error Field Map｜相对误差场
- Normalized Field Map｜归一化场
- Gradient Magnitude Map｜梯度模场
- Laplacian Field Map｜拉普拉斯场
- Multi-field Bivariate Map｜双变量场映射
- Bivariate Colormap Field｜二维色标场
- Small-multiple Field Panels｜多时刻场小 multiples
- Space-filling Field Mosaic｜多方案场矩阵
- Phase-field Map｜相场图
- Level-set Interface Plot｜水平集界面
- Signed-distance Field Plot｜符号距离场
- Interface Curvature Map｜界面曲率图
- Boundary-layer Profile Map｜边界层剖面图
- Cross-sectional State Map｜截面状态图
- Axial Profile Evolution｜轴向剖面演化
- Radial Profile Evolution｜径向剖面演化
- Polar Field Map｜极坐标场图
- Cylindrical Unwrapped Map｜圆柱展开场图
- Spherical Surface Heatmap｜球面热图
- Mesh-quality Map｜网格质量场图

适用关键词：
`PDE, heat transfer, diffusion, CFD, finite element, finite volume, multiphysics, field`

---

## B. 矢量场 / 流场 / 传输机制

- Quiver Plot｜矢量箭头场
- Vector Glyph Field｜矢量 Glyph 场
- Streamline Plot｜流线图
- Streamtube Plot｜流管图
- Pathline Plot｜迹线
- Streakline Plot｜脉线
- Particle Trajectory Plot｜粒子轨迹
- Line Integral Convolution (LIC)｜线积分卷积
- Texture Advection Visualization｜纹理平流可视化
- Stream Surface｜流面
- Stream Ribbon｜流带
- Stream Rake｜流线耙
- Cone Glyph Field｜锥形矢量场
- Hedgehog Plot｜刺猬图
- Flux Vector Map｜通量矢量图
- Gradient Vector Field｜梯度矢量场
- Velocity Magnitude + Streamline｜速度云图+流线
- Pressure Contour + Velocity Vectors｜压力等值线+速度矢量
- Vorticity Map｜涡量图
- Q-criterion Isosurface｜Q准则涡结构
- Lambda-2 Isosurface｜λ2 涡结构
- Swirling-strength Map｜旋涡强度图
- Vortex-core Line｜涡核线
- Wall Shear Stress Map｜壁面剪切应力图
- Skin-friction Line Plot｜壁面摩擦线
- Flux Tube｜通量管
- Sankey-style Energy Flux Diagram｜能量通量 Sankey
- Vector-field Topology Plot｜矢量场拓扑图
- Critical-point / Separatrix Map｜临界点-分离线图
- Tensor Glyph / Ellipsoid Glyph｜张量椭球 Glyph
- Stress Tensor Glyph｜应力张量 Glyph

---

## C. 时空演化 / 传播 / 动态场

- Hovmöller Diagram｜时空 Hovmöller 图
- Space–Time Heatmap｜时空热图
- Space–Time Cube｜时空立方体
- Waterfall Plot｜瀑布剖面图
- Ridgeline Over Time｜时间脊线密度图
- Time-colored State Trajectory｜时间着色状态轨迹
- Evolution Surface｜演化曲面
- Temporal Small Multiples｜时序小 multiples
- Snapshot Matrix｜状态快照矩阵
- Front Propagation Map｜传播前沿图
- Arrival-time Map｜到达时间图
- Time-to-threshold Map｜阈值到达时间图
- Kymograph｜运动/传播时空图
- Event Raster Plot｜事件栅格图
- Temporal Raster Heatmap｜时间栅格热图
- Calendar Heatmap｜日历热图
- Horizon Graph｜地平线图
- ThemeRiver / Streamgraph｜主题河流图
- Spiral Time Plot｜螺旋时间图
- Cycle Plot｜周期模式图
- Seasonal Subseries Plot｜季节子序列图
- Animated Contour / Field Sequence｜动态等值场
- Trajectory Bundle Plot｜轨迹束
- Time-gradient Path Plot｜时间渐变路径
- Change-point Annotated Series｜变点标注时间序列

---

## D. 数值算法 Verification / 收敛性

- Grid Convergence Plot｜网格收敛图
- Mesh Refinement Study｜网格细化研究图
- Grid Convergence Index (GCI) Plot｜GCI 图
- Richardson Extrapolation Plot｜Richardson 外推图
- Time-step Convergence Plot｜时间步收敛图
- Order-of-Accuracy Plot｜精度阶验证图
- Log–Log Error vs Grid Size｜误差-网格 log-log 图
- Error vs Degrees of Freedom｜误差-自由度图
- Error vs Computational Cost｜误差-计算成本图
- Accuracy–Runtime Tradeoff Plot｜精度-耗时权衡
- Residual Convergence Curve｜残差收敛曲线
- Semi-log Residual History｜半对数残差历程
- Nonlinear Iteration History｜非线性迭代收敛
- Krylov Residual History｜Krylov 残差历史
- Solver Comparison Convergence Plot｜求解器收敛对比
- Convergence Rate Bar / Slope Plot｜收敛阶对比
- Energy-norm Error Plot｜能量范数误差
- L1/L2/L∞ Error Comparison｜多范数误差
- Mass-conservation Error Plot｜质量守恒误差
- Energy-conservation Error Plot｜能量守恒误差
- Constraint Violation History｜约束违反收敛图
- Primal–Dual Residual Plot｜原始-对偶残差图
- Mesh Quality vs Error Plot｜网格质量-误差
- Adaptive Mesh Refinement Map｜自适应网格细化图
- Local Error Indicator Map｜局部误差指示器
- Manufactured-solution Error Field｜制造解误差场
- Stability-region Plot｜数值稳定域
- CFL Stability Map｜CFL 稳定性图
- Spectral Radius Plot｜谱半径稳定性图

---

## E. 模型 Validation / 观测一致性 / 预测诊断

- Observed vs Predicted Scatter｜观测-预测散点
- Parity Plot｜一致性图
- Identity-line Agreement Plot｜1:1 参考线图
- Prediction Interval Parity Plot｜带预测区间的一致性图
- Residual vs Fitted Plot｜残差-拟合值
- Standardized Residual Plot｜标准化残差图
- Studentized Residual Plot｜学生化残差
- Residual vs Time｜残差时间图
- Residual vs Covariate｜残差-自变量
- Residual Heatmap｜残差热图
- Residual Spatial Map｜空间残差图
- Residual ACF / PACF｜残差自相关/偏自相关
- Residual Lag Plot｜残差滞后图
- Normal Q–Q Plot｜正态 Q-Q 图
- P–P Plot｜P-P 图
- Probability Plot｜概率图
- Bland–Altman Plot｜Bland–Altman 一致性图
- Difference-vs-Mean Plot｜均差图
- Limits-of-Agreement Plot｜一致性界限图
- Taylor Diagram｜Taylor 综合评价图
- Target Diagram｜Target 模型评价图
- Skill Score Diagram｜技巧评分图
- Error Component Diagram｜误差分量图
- Reliability / Calibration Diagram｜概率校准图
- Calibration Belt｜校准带
- PIT Histogram｜概率积分变换直方图
- PIT ECDF｜PIT 经验分布图
- Rootogram｜根图
- Posterior Predictive Check｜后验预测检验
- Coverage Plot｜覆盖率图
- Prediction Interval Coverage Plot｜预测区间覆盖图
- Error Distribution Ridge Plot｜误差分布脊线图
- Error Quantile Plot｜误差分位数图
- Relative-error CDF｜相对误差 CDF
- Error Map + Histogram Composite｜误差场+直方图复合图

---

## F. 不确定性量化 / Monte Carlo / 概率风险

- Confidence Ribbon｜置信带
- Prediction Ribbon｜预测带
- Quantile Fan Chart｜分位数扇形图
- Fan Plot｜扇形预测图
- Ensemble Spaghetti Plot｜集合轨迹意大利面图
- Ensemble Density Plot｜集合密度图
- Ensemble Mean ± Spread｜集合均值-离散带
- Probability Density Evolution｜概率密度演化图
- Quantile Evolution Plot｜分位数演化
- Probability Exceedance Map｜超越概率图
- Threshold-exceedance Curve｜阈值超越曲线
- Risk Heatmap｜风险热图
- Failure Probability Surface｜失效概率响应面
- Reliability Surface｜可靠度响应面
- Uncertainty Heatmap｜不确定性热图
- Variance Field Map｜方差场
- Standard-deviation Field Map｜标准差场
- Coefficient-of-variation Map｜变异系数场
- Entropy Map｜熵图
- Credible Interval Map｜可信区间地图
- Uncertainty Glyph Map｜不确定性 Glyph 图
- Probabilistic Isosurface｜概率等值面
- Ensemble Isosurface Envelope｜集合等值面包络
- Confidence Tube｜置信管
- Monte Carlo Running Mean｜MC 运行均值
- Monte Carlo Convergence Plot｜MC 收敛图
- MC Estimate + Wilson Interval｜MC估计+Wilson区间
- Bootstrap Distribution Plot｜Bootstrap 分布
- Bootstrap Confidence Interval Plot｜Bootstrap CI
- Bootstrap Forest Plot｜Bootstrap 森林图
- Empirical CDF｜经验 CDF
- CCDF / Survival-style Tail Plot｜互补CDF/尾部图
- Return-level Plot｜重现水平图
- Extreme-value Return-period Plot｜极值重现期图
- Uncertainty Budget Decomposition｜不确定性预算分解
- Variance Decomposition Plot｜方差分解图
- Aleatory vs Epistemic Uncertainty Plot｜随机/认知不确定性分解
- Probability Box / P-box Visualization｜概率盒
- Scenario Envelope Plot｜情景包络
- Tornado Uncertainty Plot｜不确定性 Tornado
- Joint Uncertainty Ellipse｜联合不确定性椭圆
- Confidence Ellipse Plot｜置信椭圆
- Highest Density Region Plot｜最高密度区域

---

## G. 统计分布 / 样本比较

- Histogram｜直方图
- KDE Plot｜核密度
- ECDF Plot｜经验累计分布
- Box Plot｜箱线图
- Notched Box Plot｜缺口箱线图
- Violin Plot｜小提琴图
- Split Violin Plot｜分裂小提琴图
- Half Violin Plot｜半小提琴
- Raincloud Plot｜雨云图
- Half-eye Plot｜半眼图
- Sina Plot｜Sina 密度散点
- Beeswarm Plot｜蜂群散点
- Strip Plot｜条带散点
- Jitter Plot｜抖动散点
- Dot Plot｜点图
- Wilkinson Dot Plot｜Wilkinson 点图
- Ridgeline / Joy Plot｜脊线密度
- Density Ridge with Quantiles｜带分位数脊线图
- Letter-value Plot / Boxen Plot｜字母值图
- Bean Plot｜Bean 分布图
- Pirate Plot｜Pirate 图
- Gardner–Altman Estimation Plot｜Gardner–Altman 估计图
- Cumming Estimation Plot｜Cumming 估计图
- Forest Plot｜森林图
- Caterpillar Plot｜毛毛虫区间图
- Interval Plot｜区间图
- Dot-and-Whisker Plot｜点-须图
- Quantile Dot Plot｜分位数点图
- Q–Q Plot｜分位数-分位数图
- P–P Plot｜概率-概率图
- Worm Plot｜去趋势 Q-Q / worm 图
- Probability Plot Correlation Coefficient Plot｜PPCC 图
- Weibull Probability Plot｜Weibull 概率图
- Lognormal Probability Plot｜对数正态概率图
- Two-sample Density Difference Plot｜双样本密度差
- Shift Function Plot｜分位数差异图
- Bagplot｜二维箱线图
- HDR Boxplot｜最高密度区域箱线图
- Functional Boxplot｜函数型箱线图
- Depth Plot｜数据深度图
- Violin + Box + Raw Points Composite｜小提琴+箱线+原始点
- Scatter + Marginal Histogram｜散点+边际直方图
- Scatter + Marginal KDE｜散点+边际 KDE

---

## H. 相关性 / 多变量 / 高维参数空间

- Scatter Plot Matrix (SPLOM)｜散点矩阵
- Pair Plot｜变量配对图
- Correlation Heatmap｜相关热图
- Clustered Correlation Heatmap｜聚类相关热图
- Covariance Heatmap｜协方差热图
- Partial Correlation Network｜偏相关网络
- Correlogram｜相关图
- Parallel Coordinates Plot｜平行坐标
- Bundled Parallel Coordinates｜捆绑平行坐标
- Density Parallel Coordinates｜密度平行坐标
- Parallel Categories｜平行类别图
- Parallel Sets｜平行集合图
- Hammock Plot｜吊床图
- RadViz｜径向可视化
- Star Coordinates｜星形坐标
- Andrews Curves｜Andrews 曲线
- Grand Tour Projection｜高维 Grand Tour
- Projection Pursuit Plot｜投影寻踪
- Biplot｜双标图
- PCA Biplot｜PCA 双标图
- Loading Plot｜载荷图
- Score Plot｜得分图
- Contribution Plot｜贡献图
- Variable Factor Map｜变量因子图
- Scatterplot Matrix + Density Diagonal｜SPLOM+对角密度
- Hexbin Plot｜六边形密度
- 2D Histogram｜二维直方图
- 2D KDE Contour｜二维 KDE 等密度
- Density Scatter｜密度着色散点
- Joint Plot｜联合分布图
- Corner Plot｜角图
- Pairwise Posterior Plot｜后验变量配对图
- Correlation Circle｜相关圆
- Ellipse Correlation Plot｜相关椭圆矩阵
- Bubble Matrix｜气泡矩阵
- Glyph Matrix｜Glyph 矩阵
- Chernoff Faces｜Chernoff 人脸（慎用）
- Radar / Spider Plot｜雷达图（仅少量对象，慎用）

---

## I. 灵敏度分析 / DOE / 参数响应

- Tornado Plot｜龙卷风灵敏度图
- One-at-a-Time Response Curve｜OAT 参数响应
- Spider Sensitivity Plot｜蜘蛛灵敏度
- Sensitivity Heatmap｜灵敏度热图
- Local Derivative Sensitivity Plot｜局部导数灵敏度
- Elasticity Plot｜弹性系数图
- Sobol First-order Bar Plot｜Sobol 一阶指数
- Sobol Total-order Bar Plot｜Sobol 总效应
- Sobol S1–ST Dumbbell Plot｜Sobol 哑铃图
- Sobol Interaction Heatmap｜Sobol 二阶交互热图
- Sobol Network｜Sobol 交互网络
- Morris μ*–σ Plot｜Morris 均值-标准差图
- Morris Elementary Effects Distribution｜Morris 基本效应分布
- FAST Sensitivity Spectrum｜FAST 灵敏度谱
- PAWN Sensitivity Plot｜PAWN 灵敏度
- Delta Moment-independent Sensitivity Plot｜Delta 灵敏度
- Shapley Effects Plot｜Shapley 全局灵敏度
- Main Effects Plot｜主效应图
- Interaction Plot｜交互效应图
- Interaction Effects Matrix｜交互效应矩阵
- Half-normal Effects Plot｜半正态效应图
- Normal Effects Plot｜正态效应图
- Pareto Chart of Standardized Effects｜标准化效应 Pareto
- DOE Contour Plot｜DOE 等高线
- Response Surface Plot｜响应面
- Response Surface + Contour Projection｜响应面+底部等高线
- Slice Response Surface｜响应面切片
- Partial Dependence Surface｜偏依赖响应面
- Factorial Cube Plot｜因子立方图
- Design-space Map｜试验设计空间图
- Desirability Surface｜期望度响应面
- Parameter Sweep Heatmap｜参数扫描热图
- Phase/Regime Map｜参数状态区域图
- Sensitivity vs Parameter Value｜局部敏感性演化
- Sensitivity Ranking with CI｜带置信区间敏感性排名

---

## J. 优化 / 可行域 / 多目标决策

- Objective Landscape｜目标函数景观
- Fitness Landscape｜适应度景观
- Loss Landscape｜损失景观
- 2D Response Surface｜二维响应面
- 3D Objective Surface｜三维目标面
- Contour Optimization Map｜优化等高线
- Feasible Region Map｜可行域图
- Constraint Boundary Map｜约束边界图
- Active-constraint Map｜活跃约束图
- Feasibility Probability Map｜可行概率图
- Cost–Performance Tradeoff｜成本-性能权衡
- Pareto Front｜Pareto 前沿
- Pareto Set Plot｜Pareto 解集
- 3D Pareto Surface｜三维 Pareto 面
- Pareto Scatter Matrix｜Pareto 散点矩阵
- Parallel-coordinate Pareto Plot｜Pareto 平行坐标
- Pareto Heatmap｜Pareto 热图
- Density-colored Pareto Front｜密度 Pareto 前沿
- Uncertainty-aware Pareto Front｜不确定性 Pareto
- Robust Pareto Front｜鲁棒 Pareto
- Knee Point Visualization｜膝点图
- Compromise Solution Map｜折中解图
- Hypervolume Convergence Plot｜超体积收敛
- Generational Distance Plot｜GD 指标收敛
- Inverted Generational Distance Plot｜IGD
- Epsilon Indicator Plot｜ε 指标
- Dominance Rank Plot｜支配等级图
- Objective-space Cluster Map｜目标空间聚类
- Decision-space Projection｜决策空间投影
- Problem Landscape Visualization｜问题景观
- Self-organizing Map of Pareto Set｜Pareto SOM
- RadViz Pareto Map｜RadViz Pareto
- Hyperspace Pareto Frontier｜超空间 Pareto
- Attainment Surface｜达成面
- Empirical Attainment Function｜经验达成函数
- Probability of Improvement Surface｜改进概率面
- Expected Improvement Surface｜EI 采集函数
- Lower Confidence Bound Surface｜LCB/UCB 面
- Gaussian-process Mean + Uncertainty Surface｜GP均值+不确定性
- Bayesian Optimization Acquisition Map｜贝叶斯优化采集函数图
- Optimization Trajectory on Landscape｜优化轨迹叠加景观
- Population Evolution Plot｜种群演化图
- Convergence + Diversity Plot｜收敛性-多样性
- Decision Boundary + Optimum Composite｜决策边界+最优点
- Cost Contour + Feasible Probability + Optimum｜成本等高线+可行概率+最优点

---

## K. 非线性动力学 / 稳定性 / 临界现象

- Phase Portrait｜相图
- Phase Plane｜相平面
- 3D Phase-space Trajectory｜三维相空间轨迹
- Nullcline Plot｜零增长线
- Vector Field + Nullclines｜向量场+零流线
- Bifurcation Diagram｜分岔图
- 2-parameter Bifurcation Map｜双参数分岔图
- Stability Diagram｜稳定性区域图
- Basin of Attraction Map｜吸引域图
- Lyapunov Exponent Plot｜Lyapunov 指数图
- Lyapunov Spectrum｜Lyapunov 谱
- Poincaré Section｜Poincaré 截面
- Return Map｜返回映射
- Cobweb Plot｜蛛网图
- Recurrence Plot｜递归图
- Recurrence Quantification Map｜RQA 图
- Hysteresis Loop｜滞回环
- Limit-cycle Plot｜极限环
- State Transition Diagram｜状态转移图
- Regime Transition Map｜状态转换图
- Critical Slowing-down Indicator Plot｜临界减速指标
- Early-warning Signal Plot｜临界预警图
- Potential Landscape｜势能景观
- Quasi-potential Landscape｜拟势景观
- Energy Landscape｜能量景观
- Phase Diagram｜相图/状态相图
- Critical Boundary Map｜临界边界
- Phase Transition Band｜相变带
- Logistic Threshold Inversion Plot｜Logistic 阈值反演图

---

## L. 机制 / 因果 / 流程 / 系统结构

- Mechanism Schematic｜机制示意图
- Conceptual Framework Diagram｜概念框架
- Causal DAG｜因果有向无环图
- Structural Equation Model Diagram｜SEM 路径图
- Path Diagram｜路径图
- Mediation Diagram｜中介效应图
- Moderation Interaction Diagram｜调节效应图
- Feedback-loop Diagram｜反馈回路
- Causal Loop Diagram｜因果回路图
- Stock-and-flow Diagram｜存量-流量图
- System Dynamics Diagram｜系统动力学图
- Influence Diagram｜影响图
- Dependency Graph｜依赖图
- Algorithm Flowchart｜算法流程图
- Computational Pipeline｜计算管线图
- Methodology Framework｜方法框架图
- Data–Model–Decision Pipeline｜数据-模型-决策闭环
- Sankey Flow Diagram｜Sankey 流图
- Alluvial Diagram｜冲积图
- Energy-flow Diagram｜能量流
- Mass-balance Flow Diagram｜质量平衡流图
- Waterfall Contribution Plot｜瀑布贡献图
- Decomposition Tree｜分解树
- Cause–Effect Fishbone Diagram｜鱼骨图
- Layered Architecture Diagram｜分层架构图
- Multi-scale Mechanism Diagram｜多尺度机制图

---

## M. 网络 / 图结构

- Force-directed Network｜力导向网络
- ForceAtlas2 Network｜ForceAtlas2 网络
- Fruchterman–Reingold Layout｜FR 布局
- Kamada–Kawai Layout｜KK 布局
- Spectral Layout｜谱布局
- Circular Network｜环形网络
- Radial Network｜径向网络
- Hierarchical Network｜层次网络
- Sugiyama Layered Graph｜Sugiyama 分层图
- Bipartite Network｜二部图
- Multipartite Network｜多部图
- Ego Network｜自我中心网络
- Community Network｜社区网络
- Modularity Network｜模块度网络
- Centrality-encoded Network｜中心性编码网络
- Degree-sized Network｜度中心性节点大小图
- Betweenness Network｜介数中心性图
- Weighted Network｜加权网络
- Signed Network｜符号网络
- Directed Flow Network｜有向流网络
- Temporal Network｜动态网络
- Multilayer Network｜多层网络
- Multiplex Network｜多重网络
- Hypergraph Visualization｜超图
- Network Small Multiples｜网络小 multiples
- Network Difference Map｜网络差异图
- Edge Bundling Network｜边捆绑网络
- Hierarchical Edge Bundling｜层次边捆绑
- Arc Diagram｜弧图
- Chord Diagram｜弦图
- Circos Plot｜Circos 环形关系图
- Hive Plot｜Hive 网络图
- Adjacency Matrix｜邻接矩阵
- Clustered Adjacency Matrix｜聚类邻接矩阵
- Node-link + Matrix Hybrid｜节点连线+矩阵混合
- Sankey Network｜流量网络
- Flow Map Network｜流向网络
- Minimum Spanning Tree｜最小生成树
- Steiner Tree Visualization｜Steiner 树
- Shortest-path Highlight Network｜最短路高亮图
- Network Backbone Plot｜网络骨架
- k-core Decomposition Plot｜k-core 分解图
- Community Alluvial Plot｜社区演化冲积图
- Network Centrality Distribution｜中心性分布图
- Motif Frequency Plot｜网络模体频率
- Degree Distribution Log-log Plot｜度分布 log-log
- Assortativity Mixing Matrix｜同配性混合矩阵

---

## N. 空间 / GIS / 地理统计

- Choropleth Map｜分级设色地图
- Graduated Symbol Map｜分级符号地图
- Proportional Symbol Map｜比例符号地图
- Bubble Map｜气泡地图
- Point Density Map｜点密度地图
- Kernel Density Map｜核密度地图
- Spatial Heatmap｜空间热力图
- Hexbin Map｜六边形网格地图
- Grid-cell Map｜规则网格地图
- Dot Density Map｜点密度地图
- Flow Map｜流向地图
- Desire-line Map｜OD 期望线图
- Origin–Destination Flow Map｜OD 流图
- Great-circle Arc Map｜大圆弧线地图
- Isochrone Map｜等时圈图
- Isodistance Map｜等距圈图
- Accessibility Surface｜可达性表面
- Travel-time Surface｜出行时间面
- Voronoi / Thiessen Map｜Voronoi/泰森多边形
- Delaunay Triangulation Map｜Delaunay 三角网
- Cartogram｜变形统计地图
- Dorling Cartogram｜Dorling 圆形变形图
- Dasymetric Map｜密度映射图
- Bivariate Choropleth｜双变量分级设色
- Trivariate Map｜三变量空间图
- Moran Scatterplot｜Moran 散点
- LISA Cluster Map｜局部空间自相关聚类图
- Hot Spot Getis–Ord Gi* Map｜热点分析图
- Spatial Residual Map｜空间残差
- Semivariogram｜半变异函数图
- Variogram Cloud｜变异函数云
- Correlogram Map｜空间相关图
- Kriging Prediction Map｜克里金预测面
- Kriging Variance Map｜克里金方差图
- Uncertainty Map｜空间不确定性图
- Space–Time Cube｜空间-时间立方体
- Trajectory Map｜轨迹地图
- GPS Density Map｜轨迹密度图
- Movement Rose / Directional Rose｜移动方向玫瑰图
- Spatial Network Overlay｜空间网络叠加图

---

## O. 机器学习 / 可解释 AI

- Feature Importance Bar Plot｜特征重要性
- Permutation Importance Plot｜置换重要性
- SHAP Beeswarm｜SHAP 蜂群
- SHAP Summary Bar｜SHAP 汇总条形
- SHAP Waterfall｜SHAP 瀑布
- SHAP Decision Plot｜SHAP 决策路径
- SHAP Heatmap｜SHAP 热图
- SHAP Dependence Plot｜SHAP 依赖
- SHAP Interaction Heatmap｜SHAP 交互热图
- Partial Dependence Plot (PDP)｜偏依赖
- ICE Plot｜个体条件期望
- Centered ICE｜中心化 ICE
- PDP + ICE Composite｜PDP+ICE
- ALE Plot｜累积局部效应
- 2D ALE Surface｜二维 ALE
- Surrogate Tree｜替代决策树
- Decision Boundary Map｜决策边界
- Classification Probability Surface｜分类概率面
- ROC Curve｜ROC
- Precision–Recall Curve｜PR
- DET Curve｜检测误差权衡
- Lift Curve｜提升曲线
- Cumulative Gain Chart｜累计增益
- Calibration Curve｜校准曲线
- Confusion Matrix Heatmap｜混淆矩阵
- Threshold Metric Curve｜阈值-指标曲线
- Learning Curve｜学习曲线
- Validation Curve｜验证曲线
- Training/Validation Loss Curve｜训练验证损失
- Bias–Variance Tradeoff Plot｜偏差-方差
- Embedding Projection｜嵌入投影
- Activation Map｜激活图
- Saliency Map｜显著性图
- Grad-CAM｜梯度类激活
- Attention Heatmap｜注意力热图
- Attention Flow｜注意力流
- Embedding Similarity Matrix｜嵌入相似矩阵
- Prototype Map｜原型图
- Counterfactual Path Plot｜反事实路径图

---

## P. Bayesian / MCMC / 概率模型

- Posterior Density Plot｜后验密度
- Prior vs Posterior Overlay｜先验-后验对比
- Posterior Forest Plot｜后验森林图
- Highest Density Interval Plot｜HDI 图
- ROPE Plot｜实际等价区间图
- Trace Plot｜MCMC 轨迹
- Rank Plot｜MCMC rank 图
- Autocorrelation Plot｜MCMC 自相关
- ESS Evolution Plot｜有效样本量演化
- Local ESS Plot｜局部 ESS
- MCSE Plot｜Monte Carlo 标准误
- Energy Plot｜HMC 能量诊断
- Divergence Pair Plot｜发散样本配对图
- Parallel Coordinates with Divergences｜发散平行坐标
- Posterior Pair Plot｜后验 pair plot
- Corner Plot｜Corner 图
- Posterior Predictive Distribution｜后验预测分布
- Posterior Predictive Interval Plot｜后验预测区间
- Posterior Predictive Check｜PPC
- LOO-PIT Plot｜LOO-PIT
- Prior Predictive Check｜先验预测检验
- Posterior Calibration Plot｜后验校准
- Bayes Factor Evidence Plot｜Bayes 因子证据图
- Model Weight Plot｜贝叶斯模型权重
- Sensitivity-to-prior Plot｜先验敏感性
- Ridge Plot for Multiple Models｜多模型后验脊线

---

## Q. 可靠性 / 生存分析 / 风险

- Kaplan–Meier Curve｜KM 生存曲线
- Nelson–Aalen Cumulative Hazard｜累计风险
- Hazard Function Plot｜风险函数
- Bathtub Curve｜浴盆曲线
- Reliability Function Plot｜可靠度函数
- Failure Probability Curve｜失效概率
- Weibull Probability Plot｜Weibull 概率图
- Lognormal Probability Plot｜对数正态概率图
- Mean Residual Life Plot｜平均剩余寿命
- Competing Risks CIF Plot｜竞争风险累计发生
- Cause-specific Hazard Plot｜原因特异风险
- Survival Forest Plot｜生存森林图
- Event-history Plot｜事件历史图
- Reliability Block Diagram｜可靠性框图
- Fault Tree Diagram｜故障树
- Event Tree Diagram｜事件树
- Bow-tie Risk Diagram｜蝴蝶结风险图
- Risk Matrix｜风险矩阵
- Fragility Curve｜易损性曲线
- Vulnerability Curve｜脆弱性曲线
- Return-period Risk Curve｜重现期风险
- Reliability Contour｜可靠性等高线
- FORM Design-point Plot｜FORM 设计点
- Limit-state Surface｜极限状态面

---

## R. 降维 / 聚类 / 流形 / 高维结构

- PCA Score Plot｜PCA 得分
- PCA Biplot｜PCA 双标
- t-SNE Map｜t-SNE
- UMAP Embedding｜UMAP
- Isomap Embedding｜Isomap
- MDS Map｜多维尺度
- LLE Embedding｜局部线性嵌入
- Diffusion Map｜扩散映射
- PHATE Plot｜PHATE
- Self-organizing Map (SOM)｜自组织映射
- U-matrix｜SOM U 矩阵
- Component Plane｜SOM 分量平面
- Clustered Heatmap｜聚类热图
- Dendrogram｜树状图
- Radial Dendrogram｜径向树状图
- Icicle Dendrogram｜冰柱树
- Clustergram｜聚类图
- Silhouette Plot｜轮廓系数图
- Elbow Plot｜肘部图
- Gap Statistic Plot｜Gap 统计
- Cluster Stability Plot｜聚类稳定性
- Consensus Matrix Heatmap｜共识矩阵
- Cluster Transition Alluvial｜聚类转换冲积图
- Density-based Cluster Map｜密度聚类图
- Manifold Trajectory Plot｜流形轨迹
- Latent-space Density Map｜潜空间密度

注意：t-SNE/UMAP 中簇间距离和全局几何不能未经验证直接作物理解释。

---

## S. 拓扑数据分析 / 形态 / 几何结构

- Persistence Diagram｜持久同调图
- Persistence Barcode｜持久条码
- Persistence Landscape｜持久景观
- Persistence Image｜持久图像
- Betti Curve｜Betti 曲线
- Mapper Graph｜Mapper 图
- Reeb Graph｜Reeb 图
- Contour Tree｜等值轮廓树
- Merge Tree｜合并树
- Morse–Smale Complex｜Morse–Smale 复形
- Skeleton / Medial Axis｜骨架/中轴
- Alpha-shape Plot｜Alpha shape
- Convex Hull Plot｜凸包
- Voronoi Tessellation｜Voronoi 剖分
- Delaunay Triangulation｜Delaunay 三角剖分
- Shape-space Embedding｜形状空间嵌入
- Curvature Distribution Plot｜曲率分布
- Fractal Dimension Plot｜分形维数
- Minkowski Functional Plot｜Minkowski 泛函
- Euler Characteristic Curve｜Euler 特征曲线
- Contact Network｜接触网络
- Pore-network Visualization｜孔隙网络
- Grain-boundary Map｜晶界图
- Orientation Distribution Function｜取向分布函数
- Pole Figure｜极图
- Inverse Pole Figure｜反极图

---

## T. 时间序列 / 信号 / 频域

- Time-series Line Plot｜时间序列
- Multi-resolution Time Series｜多分辨率序列
- ACF Plot｜自相关
- PACF Plot｜偏自相关
- Lag Plot｜滞后图
- Seasonal Decomposition Plot｜季节分解
- STL Decomposition｜STL
- Change-point Plot｜变点图
- Control Chart｜控制图
- Run Chart｜运行图
- CUSUM Chart｜累积和图
- EWMA Chart｜指数加权移动均值
- Spectrum / Periodogram｜功率谱
- PSD Plot｜功率谱密度
- Spectrogram｜频谱图
- Wavelet Scalogram｜小波尺度图
- Continuous Wavelet Transform Map｜CWT
- Cross-spectrum Plot｜互谱图
- Coherence Plot｜相干谱
- Cross-correlation Plot｜互相关
- Recurrence Plot｜递归图
- Phase Synchronization Plot｜相位同步
- Hilbert Spectrum｜Hilbert 谱
- Hilbert–Huang Spectrum｜HHT
- Envelope Plot｜包络图
- Event-triggered Average Plot｜事件触发平均
- Horizon Graph｜Horizon
- Calendar Heatmap｜日历热图
- Cycle Plot｜周期图
- Ridgeline by Time Window｜时间窗口脊线

---

## U. 组合数据 / 成分 / 三元及单纯形

- Ternary Plot｜三元图
- Gibbs Triangle｜Gibbs 三角
- Ternary Contour Plot｜三元等高线
- Ternary Heatmap｜三元热图
- Ternary Phase Diagram｜三元相图
- 3D Ternary Prism｜三元棱柱
- Simplex Plot｜单纯形图
- Barycentric Plot｜重心坐标图
- Compositional Biplot｜成分双标图
- Balance Dendrogram｜成分平衡树
- CLR Biplot｜中心化对数比双标图
- Aitchison Geometry Plot｜Aitchison 几何图
- Mixing Triangle｜混合三角图
- Phase-fraction Ternary Map｜相分数三元图

---

## V. 层级 / 类别 / 流转 / 构成

- Treemap｜矩形树图
- Sunburst｜旭日图
- Icicle Plot｜冰柱图
- Circle Packing｜圆形打包
- Dendrogram｜树状图
- Radial Tree｜径向树
- Sankey Diagram｜Sankey
- Alluvial Diagram｜冲积图
- Parallel Sets｜平行集合
- Parallel Categories｜平行类别
- Mosaic Plot｜马赛克图
- Marimekko Plot｜Marimekko
- Association Plot｜关联图
- Spine Plot｜脊柱图
- Nested Bar Plot｜嵌套条形图
- 100% Stacked Bar｜百分比堆积
- Waffle Chart｜华夫图（慎用于严肃定量）
- UpSet Plot｜集合交集图
- Venn Diagram｜Venn（集合少时）
- Euler Diagram｜Euler 图
- Set Matrix｜集合矩阵
- Flow Tree｜流转树
- State-transition Sankey｜状态转移 Sankey
- Cohort Flow Diagram｜队列流图

---

## W. 比较、排名与综合评价

- Dumbbell Plot｜哑铃图
- Lollipop Plot｜棒棒糖图
- Slopegraph｜斜率图
- Bump Chart｜排名变化图
- Cleveland Dot Plot｜Cleveland 点图
- Forest Plot｜森林图
- Dot-and-whisker Plot｜点须图
- Butterfly Chart｜蝴蝶图
- Diverging Bar Chart｜发散条形
- Bullet Chart｜子弹图
- Heatmap Scorecard｜热图评分卡
- Glyph Scorecard｜Glyph 评分卡
- Small Multiples｜小 multiples
- Sparklines Matrix｜迷你趋势矩阵
- Taylor Diagram｜Taylor 图
- Target Diagram｜Target 图
- Radar Plot｜雷达图（维度少且只做概览）
- Multi-criteria Heatmap｜多准则热图
- Rank Heatmap｜排名热图
- Rank-frequency Plot｜排名-频率
- Pareto 80/20 Chart｜Pareto 80/20
- Benchmark Frontier Plot｜基准前沿
- Performance Profile｜性能剖面
- Dolan–Moré Performance Profile｜优化算法性能剖面

---

## X. 图像、矩阵、结构纹理

- Matrix Heatmap｜矩阵热图
- Clustered Matrix｜聚类矩阵
- Confusion Matrix｜混淆矩阵
- Distance Matrix｜距离矩阵
- Similarity Matrix｜相似矩阵
- Kernel Matrix｜核矩阵
- Gram Matrix｜Gram 矩阵
- Contact Map｜接触图
- Attention Matrix｜注意力矩阵
- Recurrence Matrix｜递归矩阵
- Transition Matrix｜转移矩阵
- Adjacency Matrix｜邻接矩阵
- Sparsity Pattern / Spy Plot｜稀疏结构图
- Block Matrix Diagram｜块矩阵图
- Image Difference Map｜图像差异图
- Edge Map｜边缘图
- Segmentation Overlay｜分割叠加图
- Uncertainty Overlay｜不确定性叠加
- Error Overlay｜误差叠加
- Saliency Overlay｜显著性叠加
- Multi-channel Composite｜多通道复合图

---

# 6. 复合图模板库

AI 优先搜索或构造以下“论文级组合”。

## 3.1 物理机制
- `Filled Contour + Streamline + Critical Points`
- `Scalar Field + Quiver + Boundary Annotation`
- `Isosurface + Slice Plane + Streamtube`
- `Volume Rendering + Semi-transparent Isosurface`
- `Temperature Field + Heat Flux Streamlines`
- `Concentration Field + Gradient Vectors`
- `Stress Field + Deformation Wireframe`
- `Pressure Field + Velocity Streamlines`
- `Vorticity Field + Q-criterion Isosurface`

## 3.2 数值验证
- `Log-log Error Curve + Theoretical Slope`
- `Error vs Mesh Size + Runtime Secondary Panel`
- `Residual History + Constraint Violation`
- `Grid Convergence + Richardson Extrapolated Limit`
- `Adaptive Mesh + Local Error Indicator`

## 3.3 统计
- `Raincloud + Pairwise Significance`
- `Scatter + Marginal KDE + Confidence Ellipse`
- `Violin + Box + Raw Samples`
- `Forest Plot + Effect-size Reference Line`
- `ECDF + Quantile Markers`

## 3.4 不确定性
- `Median Curve + 50/80/95% Fan Bands`
- `Ensemble Spaghetti + Mean + Quantile Envelope`
- `Probability Surface + 90% Feasibility Boundary`
- `Spatial Mean Field + Uncertainty Hatching`
- `MC Estimate + Wilson CI + Target Threshold`

## 3.5 灵敏度
- `Sobol S1–ST Dumbbell + Interaction Heatmap`
- `Morris μ*–σ + Parameter Labels`
- `Response Surface + Main-effect Marginals`
- `Tornado + Baseline Marker + Directional Effects`

## 3.6 优化
- `Pareto Front + Density + Knee Point`
- `Objective Surface + Contour Projection + Search Trajectory`
- `Cost Contours + Feasible Probability + Optimal Point`
- `Pareto Front + Parallel Coordinates`
- `GP Mean Surface + Uncertainty + Acquisition Function`
- `Feasible Region + Active Constraints + Robust Optimum`

## 3.7 模型验证
- `Parity Plot + 1:1 Line + ±10% Bands`
- `Parity Plot + Marginal Error Distribution`
- `Taylor Diagram + Metric Table`
- `Bland–Altman + Limits of Agreement + CI`
- `Residual-vs-Fitted + QQ + Residual Distribution`
- `Calibration Curve + Probability Histogram`

## 3.8 高维结构
- `UMAP/PCA + Density Contours + Cluster Hulls`
- `Parallel Coordinates + Cluster Bundling`
- `Clustered Heatmap + Dendrogram`
- `Embedding + Objective-value Color`
- `SOM U-matrix + Component Planes`

---

# 7. AI 自主选图规则

## 4.1 如果数据有 “时间 × 空间 × 状态”
优先：
1. Hovmöller / Space-time Heatmap
2. Snapshot Matrix
3. Front Propagation Map
4. Evolution Surface
5. Space–Time Cube

如果还有矢量：
`Contour + Streamline` 优先于单纯 3D Surface。

## 4.2 如果有两个连续参数 + 一个输出
优先：
1. Filled Contour / Response Surface
2. Contour + Optimum
3. Regime Map
4. Uncertainty-aware Surface

如果存在约束：
叠加 `Feasible Boundary`。

## 4.3 如果存在 Monte Carlo
优先：
- MC convergence
- quantile fan
- ECDF/CCDF
- failure probability
- uncertainty decomposition

不要只画 histogram。

## 4.4 如果存在模型预测与真实值
至少从：
- Parity Plot
- Residual diagnostics
- Taylor Diagram
- Bland–Altman（只有“方法一致性”问题时）
- Calibration Curve（概率预测）
中选择。

## 4.5 如果存在多个参数的灵敏度
优先顺序：
`Sobol / Morris > response surface > tornado > radar`

Tornado 适合局部或确定性 one-at-a-time；
Sobol 适合全局方差分解；
Morris 适合高维筛选。

## 4.6 如果存在多目标优化
二维目标：
`Pareto Front + Knee Point`

3–5 目标：
`Pareto + Parallel Coordinates`

更高维：
`Parallel Coordinates / Heatmap / RadViz / SOM / dimensionality reduction`

不要把 7 个目标硬塞进 radar 作为唯一证据。

## 4.7 如果有网络
小网络：
`Node-link`

大而稠密：
`Edge Bundling / Adjacency Matrix / Hive Plot`

社区演化：
`Temporal Network + Alluvial`

空间网络：
`Map + Network Overlay`

## 4.8 如果有高维样本
探索结构：
`PCA + UMAP`

解释变量关系：
`SPLOM / Parallel Coordinates / Correlation Heatmap`

不得根据 t-SNE/UMAP 中“簇间距离”直接声称真实物理距离。

## 4.9 如果数据是分布比较
不要默认柱状图 + error bar。

优先：
`Raincloud / Violin + Raw Points / ECDF / Estimation Plot`

## 4.10 如果论文需要“机制”
机制不是“相关性热图”的同义词。

优先：
- 物理传输：flux / streamlines / gradient；
- 因果假设：DAG；
- 系统反馈：causal loop；
- 变量交互：interaction surface / Sobol interaction；
- 状态转换：phase portrait / regime map；
- 流量机制：Sankey；
- 网络机制：centrality/community/motif。

---

# 8. 图型适配自检

绘图 AI 每次收到新论文内容后，在内部执行：

```text
我先判断最常见的折线图、柱状图或散点图能否直接、准确地证明论文命题；若能，就保留基础图型，若不能，再比较更合适的表达。

先回答：
1. 这张图在论文中要证明什么？
2. 数据具有哪些结构：时间、空间、重复、随机、高维、网络、矢量、阈值、约束？
3. 当前知识库中有哪些正式学术图型能更直接证明结论？
4. 是否存在该领域专用图型？
5. 现有方法是否确实不足，或用户是否要求通过网页搜索寻找更专业、更新的可视化方法？

如果值得搜索：
使用英文关键词搜索 review、survey、official documentation 和近年论文。
寻找足以覆盖主要备选方向的候选方法，不规定固定数量。
去重后比较数据要求、解释能力、视觉复杂度、论文规范性与误用风险。
最后选 1–3 个互补图，而不是选择 3 个表达相同信息的图。

禁止因为“看起来高级”而强行选择 3D、雷达图、桑基图或复杂网络。
高级 = 更强的信息表达与论证能力，而不是装饰复杂。
```

---

# 9. 图表检索 Query Generator

根据任务自动生成搜索式。

### 物理状态
```text
"<domain> scalar field visualization paper"
"<domain> contour streamline composite visualization"
"<domain> volume rendering isosurface scientific visualization"
```

### 数值验证
```text
"<numerical method> convergence visualization"
"grid convergence index visualization"
"numerical verification error convergence plot"
```

### 灵敏度
```text
"global sensitivity visualization Sobol Morris review"
"<domain> sensitivity analysis visualization"
```

### 不确定性
```text
"uncertainty visualization simulation ensemble review"
"probability field visualization uncertainty map"
"Monte Carlo convergence visualization"
```

### 优化
```text
"multiobjective optimization visualization review"
"many objective Pareto visualization"
"optimization landscape visualization"
"feasible region uncertainty optimization visualization"
```

### 网络
```text
"large network visualization edge bundling hive plot review"
"<domain> network visualization community centrality"
```

### GIS
```text
"spatial statistics visualization LISA kriging uncertainty"
"<domain> geospatial flow map visualization"
```

### 动力学
```text
"nonlinear dynamics visualization bifurcation basin phase portrait"
"<model> regime map visualization"
```

### 模型验证
```text
"model validation visualization Taylor diagram parity residual"
"probabilistic forecast calibration visualization"
```

### Bayesian
```text
"Bayesian workflow visualization posterior predictive MCMC diagnostics"
```

---

# 10. 绘图质量规范

> 配色必须同时遵循本 Skill 第 1–2 节的“科研论文配色与视觉编码规范”和“调色板知识库”。颜色选择优先级为：**数据语义 > 感知均匀性 > 无障碍 > 黑白可辨 > 全文一致性 > 审美**。

## 必须

- 论文风格，少装饰；
- 单位完整；
- 色条有物理量名称与单位；
- 色图与数据语义一致；
- sequential 数据用顺序色图；
- diverging 数据必须有有意义的中心点；
- categorical 使用离散色；
- 避免彩虹色图作为默认；
- 坐标轴、标题、图注统一；
- 多 panel 使用 `(a) (b) (c)`；
- 图例不遮挡数据；
- 关键阈值、最优点、边界直接标注；
- 网页搜索到的图只学习“图型和信息结构”，不复制具体图的版权表达。

## 默认导出

```text
vector: PDF / SVG
raster: 需要栅格化时使用 PNG，按最终版面尺寸保存 300–450 dpi
font: 与中文论文模板一致
```

## 面向 LaTeX

优先：
- PDF
- SVG 转 PDF
- 热力图等栅格内容使用 300–450 dpi PNG；只有模板明确要求时才使用 600 dpi

避免：
- 截图；
- JPEG 图表；
- 小字号；
- 超长标题直接写在图内。

---

# 11. 禁用与降级规则

以下图型不是永远禁止，但必须有充分理由：

### 3D Bar Chart
默认禁止。
遮挡严重，定量比较差。

### Pie / Donut
类别超过 5–6 个时优先改 bar/dot。

### Radar
只有少数对象、少数归一化指标用于概览时可用。
不能代替严谨多指标比较。

### Dual Y-axis
除非变量关系具有明确意义，否则优先分 panel 或标准化。

### Sankey
只有存在明确“流量/转移量”时使用。
不能把普通相关关系硬画成流。

### Chord / Circos
关系密度较大且“整体交互模式”是重点时使用。
如果要精确读数，改矩阵。

### 3D Surface
必须满足：
- 两个自变量 + 一个连续响应；
- 3D 能揭示峰谷/非线性；
否则优先 contour。

### t-SNE / UMAP
用于结构探索，不把二维几何关系未经验证解释为真实物理距离。

### Smoothed Curve
不得用平滑制造不存在的趋势。
必须保留或说明原始数据。

---

# 12. AI 输出格式

每次执行选图任务时输出：

## 9.1 数据诊断
```text
数据结构：
论文目标：
需要证明的核心命题：
```

## 9.2 候选方案
| Rank | 图型 | 解决的问题 | 数据要求 | 高级点 | 风险 |
|---|---|---|---|---|---|

## 9.3 最终推荐
```text
主图：
辅图：
验证图：
```

## 9.4 推荐复合方式
描述图层、轴、颜色变量、annotation、CI、阈值、最优点。

## 9.5 如果用户要求绘制
直接：
1. 读取数据；
2. 清洗；
3. 绘图；
4. 导出；
5. 给 LaTeX 插图代码；
6. 生成图题；
7. 生成论文分析段。

---

# 13. 图型适配提醒

只有备选图能带来实质信息增益时才替换用户提出的基础图型；以下条目用于比较，不是强制升级或强制搜索：

用户说：

- “折线图” → 可比较 `confidence ribbon / fan chart / slopegraph / trajectory`
- “热图” → 可比较 `clustered heatmap / bivariate map / contour overlay / uncertainty heatmap`
- “散点图” → 可比较 `density scatter / hexbin / joint KDE / confidence ellipse`
- “箱线图” → 可比较 `raincloud / violin / boxen / estimation plot`
- “响应面” → 可比较 `response surface + contours + feasible boundary + optimum`
- “网络图” → 可比较 `community / centrality / edge bundling / hive / matrix`
- “地图” → 可比较 `bivariate choropleth / KDE / flow / LISA / kriging uncertainty`
- “Pareto图” → 可比较 `knee / density / uncertainty / parallel coordinates / attainment surface`
- “Monte Carlo图” → 可比较 `convergence / fan / ECDF / exceedance / failure probability`
- “灵敏度图” → 可比较 `Sobol / Morris / interaction / Shapley effects`
- “误差图” → 可比较 `parity / residual diagnostics / Taylor / target / Bland–Altman`
- “状态演化” → 可比较 `Hovmöller / phase portrait / regime map / front propagation`

---

# 14. 论文图组设计原则

不规定每一问的固定图数。中文数学建模竞赛篇幅有限，通常每问 0–2 幅即可；能够合并为清晰复合图时优先合并，整篇总图数由论证缺口和版面预算决定。

最推荐的逻辑链：

```text
图 A：发生了什么？
状态/结果

图 B：为什么发生？
机制/耦合/敏感性

图 C：结果是否可信？
收敛/验证/不确定性

图 D：应如何决策？
优化/阈值/可行域
```

若只能放 1 张图：
选择信息密度最高的复合图。

若只能放 2 张：
优先 “结果 + 可信度”。

---

# 15. 搜索来源锚点

执行网页研究时优先参考：

- Matplotlib plot types / gallery
- Plotly scientific charts
- ParaView User Guide
- VTK Examples
- NIST/SEMATECH e-Handbook of Statistical Methods
- SALib documentation
- scikit-learn visualization / inspection
- SHAP documentation
- ArviZ visualization / Bayesian workflow
- NetworkX documentation
- Cytoscape manual
- Gephi documentation
- 原始 visualization paper / review / survey
- 领域顶刊近年论文

重点学术方法包括但不限于：

- Taylor Diagram
- Raincloud Plot
- Bland–Altman Plot
- Parallel Sets
- Hive Plot
- Persistence Diagram / Mapper
- Pareto visualization
- Visual Parameter Space Exploration
- Simulation-space / Parameter-space / Feature-space visualization

---

# 16. 最终系统提示词（可直接给画图 AI）

你是一名“科研可视化专家 + 数值建模专家 + 学术论文审稿人”。

你的任务不是把数据机械地画出来，而是为论文选择最能证明结论的图。

收到任何问题、数据、代码输出或论文小问后：

1. 先识别论文要证明的命题；
2. 自动判断数据结构；
3. 从 Scientific Figure Intelligence 图表库召回候选；
4. 仅在用户要求检索、领域规范不明确或现有图型不足时，检索 review、survey、论文和官方科学绘图库；
5. 比较足以支持决策的候选图，普通折线、柱状或散点若最合适可以直接采用；
6. 按 ArgumentFit、DataFit、Interpretability、InformationDensity、PublicationNorm 和 MisusePenalty 判断，不给视觉新颖性单独加分；
7. 推荐少量真正互补的方案，不为数量凑图；
8. 选择 1–3 个最终图；
9. 优先构造“复合科研图”而不是堆积重复图；
10. 明确每个轴、颜色、点大小、线型、置信区间、阈值、最优点、可行域的含义；
11. 不允许捏造数据；
12. 不允许因为追求高级感而滥用 3D、雷达、Sankey、Chord 或双 Y 轴；
13. 图必须能够直接进入学术论文；
14. 绘图前自动建立 COLOR_PROFILE，并按 qualitative / sequential / diverging / cyclic 选择调色板；必须检查色觉无障碍、灰度和多 panel 色标一致性；
15. 图内标题、坐标、图例、色条和注释使用中文，数学符号、单位与通用算法缩写可保留；
16. 完成绘图后自动给出：
   - 中文图题；
   - 中文图注；
   - 论文正文分析；
   - LaTeX 插图代码；
   - 如果图不能充分完成论证，根据数据和审阅意见继续迭代；只有确有必要时再检索。

判断标准：
“高级”不等于复杂。
真正高级的科研图，是一张图可以同时完成
**结果展示 + 机制解释 + 可信度证明 + 决策支持**
中的两个或更多任务。
