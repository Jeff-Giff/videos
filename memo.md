# memo.md（ManimGL 版）

## 一、CE → manimgl API 对照（最容易写错的一张表）

| CE（docs.manim.community） | manimgl（3b1b 版） | 备注 |
|---|---|---|
| `from manim import *` | `from manimlib import *` | pip 包名是 `manimgl`，和 CE 的 `manim` 是两个包，**不要装进同一个 venv** |
| `MathTex(...)` | `Tex(...)` | 都有 `font_size`；`Tex("a", "0", "b")` 多串参数自动 isolate |
| `ParametricFunction(f, t_range=[a, b])` | `ParametricCurve(f, t_range=(a, b, 步长))` | t_range 是**三元组**，不给步长会用默认步长 0.1，曲线可能不够圆滑 |
| `plane.add_coordinates(*numbers)` | `plane.add_coordinate_labels(numbers=[...], skip_first=False, font_size=...)` | numbers 里可混 float 与 complex，complex 自动落到 y 轴并带 i |
| `UpdateFromAlphaFunc(mob, f)` | `ValueTracker` + `mob.add_updater(...)` | updater 里取 `tracker.get_value()` 当 alpha |
| `Create` | `ShowCreation` | CE 的 Create 不存在 |
| 手写 Dot + 同心圆环发光 | `GlowDot(color=, radius=, glow_factor=)` | GPU 顶点着色器泛光，glow_factor 越大光晕越强；**发光线段**没有对应 shader，仍用叠线宽 |
| `set_camera_orientation` / `move_camera` | `self.frame.reorient(theta°, phi°, gamma°, center=..., height=...)` | 详见下面"相机"一节 |
| `ImageMobject(数组)` | numpy 位图先存 PNG，再 `ImageMobject(路径)` | manimgl 只收文件路径 |
| `DEGREES` | `DEG` | 同值（1° = PI/180） |
| `VGroup` 装位图不行 → 用 `Group` | 一样 | ImageMobject 不是 VMobject，混装一律 Group |
| `mob.animate.xxx()` | 一样支持 | 包括 `tracker.animate.set_value(...)` |

## 二、manimgl 自己的坑（CE 经验覆盖不到的部分）

1. **Circle 默认描边是红色**：`Circle(color=BLUE)` 可能仍画出红边（`stroke_color=RED` 是显式默认值，会盖过 color=）。凡给 Circle 上色必须写 `stroke_color=...`。Arc / Line / Rectangle / Square 无此问题。
2. **Tex 构造后颜色会被重置**：StringMobject 在构造末尾把 fill/stroke 重置为默认色，`Tex(s, color=YELLOW)` 可能无效。两种正确写法：
   - `Tex(s, fill_color=YELLOW, stroke_color=YELLOW)`（推荐，构造时传入）
   - 事后 `.set_color(YELLOW)`——**但如果用了 t2c 局部上色，事后 set_color 会把局部颜色盖掉**，只能选第一种。
3. **公式局部上色用 t2c**：`Tex(s, t2c={"0.00": YELLOW})`。选择器内部走 `re.escape`，正则特殊字符（`.`、`\` 等）无需自行转义。
4. **Tex 的子对象是逐字符的**：没有 CE "每个字符串参数一个 part" 的结构。要按部分操作：拆成多个 Tex 组成 VGroup，或用 `isolate=[...]` / `get_parts_by_tex(...)`。
5. **每帧重建 Tex 会逐帧编译 LaTeX**：manimgl 只缓存出现过的字符串；逐帧变化的内容（如动态小数）每个新串都要真编译一遍，首渲极慢。尽量只变化一小段、或降低该段帧密度。
6. **相机默认即俯视**（等价 CE 的 phi=0, theta=-90°），开场平视图无需任何设置。需要运镜时：
   - `self.play(self.frame.animate.reorient(theta_degrees, phi_degrees, 0, center=目标点, height=8*zoom), run_time=..., rate_func=smooth)`（角度制）
   - CE 的 `theta` 要 **+90°** 再传（两版零方位不同）；`frame_center` → `center=`；`zoom` → `height = 8 × zoom`
   - 环绕一整圈**不要**用插值（四元数 slerp 会走最短路径）：`self.frame.add_ambient_rotation(角速度*DEG)` → `self.wait(秒数)` → `self.frame.clear_updaters()`
7. **3D 曲面逐点上色**：`ParametricSurface(func, u_range, v_range, resolution=(n, n))` 后调 `surf.color_by_uv_function(lambda u, v: 颜色)`（顶点色，面片内插值，比逐面片平滑）。没有 CE 的 `list_of_faces` / `checkerboard_colors`。
8. **apply_complex_function 是逐点调用**：函数收到的是单个复数标量（CE 是收整个 numpy 数组）。向量化写法（`np.maximum` 等）对标量也安全；含奇点的函数加 eps 截断。`ComplexPlane` 上先 `copy()` 再变换，坐标标签才不会被一起扭曲。
9. **prepare_for_nonlinear_transform 参数名同样是 `num_inserted_curves`**，用法与 CE 一致。
10. **pkg_resources 坑**：PyPI 版 manimgl（1.6.x，较老）首行 `import pkg_resources`，Python 3.12 的新 venv 默认不带 setuptools → 报 `No module named 'pkg_resources'`，`pip install setuptools` 即可。PyPI 版与 3.12 兼容性一般，更推荐 `pip install git+https://github.com/3b1b/manim.git`（新 API 如 GlowDot / reorient / color_by_uv_function 都来自 master）。
11. **部分版本没有 SurroundingRectangle**：用 `Rectangle(stroke_color=...); rect.surround(mob, buff=...)` 兜底（文件里已封装，见 AGENTS.md 项目结构）。
12. Square 没有 side_length 属性, 用 get_width()

## 三、通用教训（与版本无关，继续有效）

1. 位图别进 VGroup：ImageMobject 不是 VMobject，装组合一律用 Group（VGroup 只收矢量对象）。
2. 置顶用声明式：`eq.z_index = 1`，别事后 bring_to_front——play 会把新对象追加到绘制列表末尾。
3. 图像贴齐用 replace：`img.replace(target)` 比 stretch_to_fit / set_width 系列更不易留缝。
4. 相对位置从正确的锚点取：刻度、标签要从 `get_right()` / `get_corner()` 出发，从 `get_center()` 出发会画进对象内部。
5. 高亮/包围框要对准正确基准：对着"白框"做包围框，别对着包含标签的整个 group，否则大一圈。
6. dstack 的维度陷阱：一维输入会给出 (M,1,3)，统一用 `np.stack(..., axis=-1)`，保证 RGB 永远在最后。
7. 浮点不判等：退化分支用 `abs(np.sin(theta)) < eps` 而非 `theta == PI`。
8. arctan2 的角差需要归一化：`(a2-a1+π) % 2π − π` 再选解。
9. 几何要随参数连续变化：用 ValueTracker + updater 逐帧 become 重建，不要 Transform 到终态——Transform 只插值起止两态，中途状态必须逐帧重建。
10. c2p 家族不要直接吃复数——多坐标语义是"第一个实数给 x 轴"，复数会被静默截断。统一写 `plane.c2p(z.real, z.imag)`（个别版本有 `n2p` 可以吃复数，但跨版本写 c2p 两个实参最稳）。
