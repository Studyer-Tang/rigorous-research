# Li 式 (14)：D-free 二维正权重 stage-1 实现报告

日期：2026-09-07  
状态：**本地非 workspace-runner smoke；严格区间组件完成，但数值远未闭门；案卷继续 `INCONCLUSIVE`。**

## 1. 新文件

- producer：`artifacts/certify_li_equation14_d_free_positive_weight_stage1.py`
- 本地输出：`agent-drafts/li-equation14-d-free-positive-weight-stage1-local-smoke.json`

producer 没有修改或覆盖任何旧 producer、旧 JSON 证书或 run 目录。本次没有启动
`scripts/research_workspace.py run`；输出将自己标为
`LOCAL_NON_WORKSPACE_SMOKE_UNTIL_RUNNER_ADOPTION_AND_INDEPENDENT_AUDIT`。

本次 smoke 对应的哈希为：

- producer SHA-256：
  `055807224aa43d93a3c691f53f1c546290422cce511fd723595d02ae96aae6e8`
- local JSON SHA-256：
  `b6715192f00c8131c6cc5b339677e53b22323edab1580360d9ffd74445844ff5`

## 2. 数学合同

固定 affine winner 与纤维 (L\le z\le U)，producer 直接使用

\[
\int_L^U\frac{g(e+D/z)}{xyz^2}\,dz
=\frac{1/L-1/U}{xy}
 \int_0^1 g\bigl((1-t)s_U+t s_L\bigr)\,dt.
\]

外部没有 (1/D)，也没有两个全局 primitive 点值之差。三角形重心 (c) 上的
(A(c)) 由新 `StrictGPrefix` 给出：

1. 保留 literal directed anchored subtraction
   \([P_\beta^- -P_\alpha^+,P_\beta^+-P_\alpha^-]\)；
2. 独立累加仅与 \([\alpha,\beta]\) 相交的 delay-cell 模型；
3. 断言 local cell-sum 包含于 anchored directed interval，再取交；
4. 不对两个前缀取中点后相减。

随后严格使用

\[
\iint WA
=A(c)\mu_{00}+A_x(c)\mu_{10}+A_y(c)\mu_{01}+R,
\]

\[
|R|\le
\frac12\|A_{xx}\|_\infty\mu^{\rm abs}_{20}
+\|A_{xy}\|_\infty\mu^{\rm abs}_{11}
+\frac12\|A_{yy}\|_\infty\mu^{\rm abs}_{02}.
\]

这里的 signed/absolute moments 使用 (W=(U-L)/(xyLU)\ge0)；每个矩先沿
重心轴作精确有理 sign cut，再以正因子 range 包围。即使 (g'') 在 (s=3)
有有限跳跃，首阶 Taylor 余项只要求沿线一阶导数绝对连续和二阶导数的 essential
supremum；程序在精确 (s=3) 处显式取两侧 (g'') 的 hull。

## 3. 前缀和自检

下列自检全部通过：

- (s<1) 跨 cell 查询与独立有理 `log_interval` 包含检查；
- 从左侧穿过 (s=1)；
- 从左侧到达 (s=3)；
- (3/4\le s\le3) 长区间 exact (q-2/s) 积分检查；
- 普通 (s>3) delay 查询的 local additivity；
- 零宽查询；
- (s=3) 左右 cell 的点值共同包含；
- 常权重、二次 (A) 的制造数据 weighted-Taylor 检查。

96-bit、16 次 delay 多项式给出的全域 `g_prefix_model_radius` 只有

\[
7.72722\times10^{-13},
\]

其中 uniform remainder 传播子预算约

\[
2.1748\times10^{-16}.
\]

因此本阶段没有数值理由把 delay 表从 96 bits 提到 128 bits。

## 4. 几何重验

本实现没有只读取旧 JSON 结论，而是重新构造并断言：

- 12 个 theta winner polytopes；
- 28 个原始 vertical fibre cells；
- 271 个现有 (x/y/L/U) relative-precut fibre cells；
- 494 个有理预切三角形；
- 每个 winner 的原始纤维体积和 relative-precut 纤维体积分别等于其 polytope
  体积；
- 两条全域体积和均等于

\[
\frac{15052756571371}{22127721750000000};
\]

- 顶点上最小 (x=y=L=U=1/500)，最小 (D=53/206)；
- (U-L\ge0)，零值只允许出现在纤维接触边界；每个正面积计算三角形的重心
  厚度严格为正；
- 实际端点参数范围为
  \(59/100\le s\le18909/64<300\)。

JSON 为所有 494 个贡献保存 identity hash、严格区间和逐项预算，并为最宽 24
个三角形保存完整几何及矩数据。按 encounter order 拼接后的 triangle identity
digest 也保存在 JSON 中。

## 5. stage-1 数值结果

参数为：

```text
mesh=8, degree=16, max_s=300, dyadic_bits=96
prefix_origin=1/2, t_panels=16, moment_depth=0, accum_bits=160
```

所得本地严格 smoke 区间为

\[
T_3\in[-61460.244271206121485252,\ 61459.765061170696947343].
\]

它当然没有达到所需

\[
T_3>-0.202861608442051918\ldots,
\]

因此固定 verdict 为 `D_FREE_POSITIVE_WEIGHT_STAGE1_INCONCLUSIVE`。

加性对称半径分解为：

| 分量 | 半径上界 |
|---|---:|
| g-prefix 模型 | (7.72722\times10^{-13}) |
| 重心一阶导数的 (t)-panel range | (9.338157032639941243) |
| W-weighted moment range | (0.784346031883320756) |
| 系数与矩区间的交互 | (51.993080118896162817) |
| 平面 Taylor Hessian 余项 | (61397.889083004989018762) |

结论非常明确：prefix 已不是瓶颈，96-bit delay 也不是瓶颈；当前损失几乎全在
494 个粗三角形上一次取 (A_{ij}) 全范围，再乘绝对二阶矩。加大 `t_panels`
或 delay bits 不能解决这个数量级。

## 6. 推荐正式参数与下一步

若先把这一 stage-1 作为正式基线采用，推荐参数保持：

```text
mesh=8, degree=16, max_s=300, dyadic_bits=96
prefix_origin=1/2, t_panels=16, moment_depth=0, accum_bits=160
```

理由是 prefix 误差低于主误差约 (10^{17}) 倍，`moment_depth` 只细化 (W)
range，也不会消除主导的平面 Hessian 余项。正式采用前必须由 workspace runner
重新产生、由独立实现核验 prefix、494 个 identity 与三重体积等式。

真正的下一阶段应是以下二者之一，而不是调大上述非主导参数：

1. 对预切三角形作最大 `taylor_hessian_remainder_radius` 优先的平面四分，并在
   每个子三角形重新计算 (A_{ij}) 与 W-moments；
2. 实现 `li-equation14-positive-weight-analytic-route.md` 第 5 节的“解析 (y)
   + 严格一维 (x)”矩积分，并最终转向完整 delay-slab 正矩公式 (10)。

建议下一个有限 smoke 只实现选项 1 的 0、256、1024、4096 次 split checkpoint，
逐项报告 Hessian 余项的经验下降率；若外推叶数仍不可接受，再投入完整解析矩。

本报告和本地 JSON 都不改变 W050 或总案卷判定，也不声称证明 Li 式 (14) 或
强哥德巴赫猜想。
