# L1–L4 对照

| 层级 | 模型与数值口径 | 临界时间/h |
| --- | --- | --- |
| L1 | 原近似离散、算术平均、201点、BE 10 s | 50.652778 |
| L2 | 原近似离散、D调和、801点、BE 10 s | 50.794444 |
| L3 | 严格FVM、k/D调和、自适应BDF连续事件 | 50.824507 |
| L4 | Euler型含收缩输运项，同一L3离散 | 52.384238 |

L1与L2保留作历史基准；L3是最终主结果；L4不是更高等级，而是另一种坐标物理解释。

## 数值消融

| 实验 | 几何 | D平均 | k平均 | 时间方法 | 临界时间/h | 相对前项/min |
| --- | --- | --- | --- | --- | --- | --- |
| A0 | L1近似 | arithmetic | arithmetic | BE 10 s | 50.652778 | — |
| A1 | strict FVM | arithmetic | arithmetic | BE 10 s | 50.818924 | 9.97 |
| A2 | strict FVM | harmonic | arithmetic | BE 10 s | 50.915712 | 5.81 |
| A3 | strict FVM | harmonic | harmonic | BE 10 s | 50.915712 | 0.00 |
| A4 | strict FVM | harmonic | harmonic | adaptive BDF | 50.909116 | -0.40 |

A0–A4均在201点口径下逐项替换，用于隔离几何、界面平均和时间推进的影响；正式L3随后再将空间网格加密到3201点。
