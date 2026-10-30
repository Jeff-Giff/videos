# video at 
#! WARNING: a lot of this code was generated using a cheap AI. The resultant is AI slop. 
#! The rest was made by a guy who only just learnt manim. He made only the FLTParts, SteinerCircles and InversionDemo.
#! You do not want to reference this code.

"""
compile order: 
DomainColouring
InverseGrid
SteinerFlow
Scene1
InversionDemo
Scene2
Scene8
Scene3
"""

# Proof that this was done by an agent

# 与 CE 版的主要 API 差异（转换要点）：
# 1. `from manim import *` -> `from manimlib import *`；MathTex -> Tex；
#    ComplexPlane.add_coordinates -> ComplexPlane.add_coordinate_labels
# 2. 发光点：手写 Dot + 同心圆环 -> GlowDot（GPU 泛光，glow_factor 控制强度）
# 3. ParametricFunction -> ParametricCurve，且 t_range 是**三元组** (t0, t1, 步长)
# 4. 3D 相机：没有 move_camera / set_camera_orientation，直接操作 self.frame：
#    - manimgl 相机默认即俯视（等价 CE 的 phi=0, theta=-90°），无需设置
#    - CE 的 theta -> manimgl 的 theta + 90°（两者零方位不同）
#    - self.frame.reorient(theta_degrees, phi_degrees, gamma_degrees, center=..., height=...)
#    - frame_center -> center=...；zoom -> height = 8 * zoom
#    - 相机整周旋转用 self.frame.add_ambient_rotation(角速度) + wait
# 5. CE Surface（list_of_faces 逐面片上色）-> ParametricSurface + color_by_uv_function
#    （逐顶点上色，着色器在面片内插值，比逐面片更平滑）
# 6. ImageMobject 只接受文件路径：numpy 位图先存临时 PNG 再加载
# 7. Circle 默认描边是红色：凡给 Circle 上色必须显式 stroke_color=...
# 8. UpdateFromAlphaFunc -> ValueTracker + updater
# 9. manimgl 中 1° = DEG（= CE 的 DEGREES）


from manimlib import *
import numpy as np

from pathlib import Path
import sys
import tempfile

from PIL import Image

from manimlib.utils.bezier import interpolate
from manimlib.constants import FRAME_X_RADIUS, FRAME_Y_RADIUS

# root directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logo import make_petal_points, precompute_trajectory

# ============ 小工具 ============

def Wh(s, font_size=48):
    """This is just here for no reason."""
    return Tex(s, font_size=font_size, fill_color=WHITE, stroke_color=WHITE)


try:
    SurroundingRectangle  # noqa: F821  manimgl 部分版本没有它，这里补一个
except NameError:
    def SurroundingRectangle(mobject, color=WHITE, buff=0.0, stroke_width=2):
        rect = Rectangle(stroke_color=color, stroke_width=stroke_width)
        rect.surround(mobject, buff=buff)
        return rect


_IMAGE_CACHE = Path(tempfile.gettempdir()) / "fractional_linear_gl_assets"
_IMAGE_CACHE.mkdir(parents=True, exist_ok=True)


def _save_png(rgba_uint8, name):
    """manimgl 的 ImageMobject 只接受文件路径，numpy 数组先落盘再加载。"""
    path = _IMAGE_CACHE / name
    Image.fromarray(rgba_uint8).save(path)
    return str(path)

import numpy as np
from manimlib import *


class Angle(VGroup):
    def __init__(self, A, B, C, radius=0.35, color=YELLOW, quadrant=None,
                 label=None, label_scale=1, label_buff=1.6, label_color=WHITE, include_edges=False,
                 edge_config=None, arc_config=None, **kwargs):
        edge_config = edge_config or {}
        arc_config = arc_config or {}
        if edge_config:
            include_edges = True
        VGroup.__init__(self, **kwargs)
        self.A, self.B, self.C = A, B, C
        self.radius = radius
        self.color = color
        self.quadrant = quadrant
        self.label = label
        self.label_buff = label_buff
        self.include_edges = include_edges
        self.edge_config = edge_config
        self.arc_config = arc_config

        self._set_geometry(A, B, C)
        self.arc = self._make_arc()
        self.add(self.arc)
        if include_edges:
            self.edges = VGroup(
                Line(self.A, self.B, **edge_config),
                Line(self.C, self.B, **edge_config),
            )
            self.add(self.edges)
        if label:
            self.label_mob = Tex(label).scale(label_scale).set_color(label_color)
            self._place_label(self.label_mob)
            self.add(self.label_mob)

    # ---------- 几何核心 ----------
    def _set_geometry(self, A, B, C):
        self.A, self.B, self.C = map(np.asarray, (A, B, C))
        a1 = angle_of_vector(self.A - self.B)
        a2 = angle_of_vector(self.C - self.B)
        da = (a2 - a1 + PI) % TAU - PI
        if self.quadrant is not None and da != 0:
            # 把角规范到指定扇区方向（含优角选择）
            while not (np.sign(np.cos(a1 + da / 2)) == self.quadrant[0]
                       and np.sign(np.sin(a1 + da / 2)) == self.quadrant[1]):
                da -= np.sign(da) * TAU
                if abs(da) > 2 * TAU:
                    break
        self.a1, self.da = a1, da

    def _make_arc(self, angle=None):
        return Arc(
            arc_center=self.B,
            start_angle=self.a1,
            angle=self.da if angle is None else angle,
            radius=self.radius,
            color=self.color,
            fill_opacity=0,
            **self.arc_config
        )

    def _mid_dir(self):
        return np.array([
            np.cos(self.a1 + self.da / 2),
            np.sin(self.a1 + self.da / 2),
            0,
        ])

    def _place_label(self, label_mob):
        label_mob.move_to(self.B + self.label_buff * self.radius * self._mid_dir())
        return label_mob

    # ---------- 供 updater / 复用 ----------
    def set_points(self, A, B, C):
        """三点变化后调用：重算几何并刷新成员（arc/edges/label 身份不变）"""
        self._set_geometry(A, B, C)
        self.arc.become(self._make_arc())
        if self.include_edges:
            self.edges.become(VGroup(
                Line(self.A, self.B, **self.edge_config),
                Line(self.C, self.B, **self.edge_config),
            ))
        if self.label:
            self._place_label(self.label_mob)

    def track(self, A, B, C):
        """让角持续跟随。A/B/C 可以是坐标，也可以是带 get_center 的 mobject。"""
        get = lambda X: X.get_center() if hasattr(X, "get_center") else np.asarray(X)
        self.add_updater(lambda m, dt: m.set_points(get(A), get(B), get(C)))


class ShowAngleCreation(Animation):
    def __init__(self, angle_mob, rate_func=smooth, run_time=1.0,
                 label_fade_start=0.65, **kwargs):
        self.label_fade_start = label_fade_start
        super().__init__(angle_mob, rate_func=rate_func, run_time=run_time, **kwargs)
        if angle_mob.label:
            angle_mob.label_mob.set_opacity(0)

    def interpolate(self, alpha):
        mob = self.mobject
        # 1) 弧线：点按扫过方向排列，partial 画出 = 从起始边扫到终止边
        mob.arc.pointwise_become_partial(mob.arc, 0, alpha)
        # 2) 边（可选）：前半段依次画出 BA、BC
        if mob.include_edges:
            for i, edge in enumerate(mob.edges):
                a = np.clip(2 * alpha - i, 0, 1)
                edge.pointwise_become_partial(edge, 0, a)
        # 3) 标签：最后阶段淡入
        if mob.label:
            span = 1 - self.label_fade_start
            a = np.clip((alpha - self.label_fade_start) / span, 0, 1)
            mob.label_mob.set_opacity(a)

# ============ 颜色工具 ============
def mag_to_val(r):
    return r / (1.0 + r)


def hsv_to_rgb(h, s, v):
    h6 = (np.asarray(h) * 6) % 6
    i = np.floor(h6).astype(int)
    f = h6 - i
    p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    i = i % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def domain_colouring_image(N=480, extent=3.0):
    x = np.linspace(-extent, extent, N)
    y = np.linspace(extent, -extent, N)
    X, Y = np.meshgrid(x, y)
    Z = X + 1j * Y
    with np.errstate(divide="ignore", invalid="ignore"):
        W = 1.0 / Z
        H = (np.angle(W) / (2 * np.pi)) % 1.0
        V = mag_to_val(np.abs(W))
    V = np.nan_to_num(V, nan=1.0)
    rgb = hsv_to_rgb(H, np.ones_like(H), V)
    return (np.dstack([rgb, np.ones_like(V)]) * 255).astype(np.uint8)


def legend_image(kind, M=256, width_px=40):
    t = np.linspace(1, 0, M)
    if kind == "value":
        rgb = np.stack([t, t, t], axis=1)
    else:
        rgb = hsv_to_rgb(np.mod(t, 1), np.ones_like(t), np.ones_like(t))
    rgba = np.dstack([np.tile(rgb[:, None, :], (1, width_px, 1)),
                      np.ones((M, width_px))])
    return (rgba * 255).astype(np.uint8)


## ============ Steiner 圆系 ============
def _c2p(z):
    return np.array([complex(z).real, complex(z).imag, 0.0])

def steiner_r_circle(z1, z2, r, color=BLUE):
    """|(z-z1)/(z-z2)| = r 的 Apollonius 圆；r=1 时为 z1z2 的中垂线。
    注意：manimgl 的 Circle 默认描边是红色"""
    z1, z2 = complex(z1), complex(z2)
    if abs(r - 1.0) < 1e-9:
        m = (z1 + z2) / 2
        n = 1j * (z2 - z1) / abs(z2 - z1)
        half = 8
        return Line(_c2p(m - half * n), _c2p(m + half * n), color=color)
    center = (z1 - r * r * z2) / (1 - r * r)
    radius = r * abs(z1 - z2) / abs(1 - r * r)
    return Circle(radius=radius, stroke_color=color).move_to(_c2p(center))

def steiner_t_arc(z1, z2, theta, color=GREEN):
    """起止于 z1、z2，在 z1 处与有向弦 z1->z2 成有向角 theta 的圆弧；
    theta=0 或 pi 时为线段。"""
    z1, z2 = complex(z1), complex(z2)
    L = abs(z2 - z1)
    assert L > 1e-12, "z1, z2 不能重合"
    if abs(np.cos(theta)-1) < 1e-6:
        return Line(_c2p(z1), _c2p(z2), color=color)
    elif abs(np.cos(theta)+1) < 1e-6:
        u = (z2 - z1) / L
        ext = 8.0
        return Line(_c2p(z1 - ext * u), _c2p(z2 + ext * u), color=color)  #FIXME: This should return 2 rays 
    u = (z2 - z1) / L
    center = z1 - (L / (2 * np.sin(theta))) * 1j * np.exp(1j * theta) * u
    radius = abs(L / (2 * np.sin(theta)))
    a1 = np.angle(z1 - center)
    a2 = np.angle(z2 - center)
    def diff(x, y):
        return (x - y + np.pi) % (2 * np.pi) - np.pi    # range (-PI, PI)
    delta = diff(a2, a1)
    d2 = delta - 2 * np.pi * np.sign(delta)
    def rel(d):     # I have no idea what this does but it seems to work when the arc is "switching sides"
        g = a1 + (np.pi / 2 if d > 0 else -np.pi / 2)
        return diff(g - np.angle(u), theta)
    if abs(rel(d2)) < abs(rel(delta)):
        delta = d2
    return Arc(start_angle=a1, angle=delta, radius=radius,
               arc_center=_c2p(center), color=color)

def steiner(z1, z2, rs, thetas, rcolor=TEAL, tcolor=GREEN):
    """Steiner 圆系：VGroup(r_circles, t_arcs)。"""
    r_group = VGroup(*[steiner_r_circle(z1, z2, r, color=rcolor) for r in rs])
    t_group = VGroup(*[steiner_t_arc(z1, z2, th, color=tcolor) for th in thetas])
    return VGroup(r_group, t_group)


class SteinerCircles(Scene):
    def construct(self):
        plane = ComplexPlane(
            x_range=(-8, 8, 1), y_range=(-4, 4, 1),
            background_line_style=dict(stroke_color=BLUE, stroke_width=1),
            faded_line_style=dict(stroke_color=BLUE, stroke_width=0.5, stroke_opacity=0.5),
            faded_line_ratio=1,
        )
        self.add(plane)

        z1, z2 = -1 + 0j, 1 + 0j
        rs = [1/11, 1/5, 1/3, 1/2, 1/1.4, 1, 1.4, 2, 3, 5, 11]
        thetas = [i * PI / 6 for i in range(12)]

        circles = steiner(z1, z2, rs, thetas, rcolor=TEAL_B, tcolor=GREEN_B).set_stroke(opacity=0.1)
        r_group, t_group = circles
        self.add(circles)
        self.wait()
        self.play(r_group.animate.set_stroke(opacity=1))
        self.wait()
        self.play(r_group.animate.set_stroke(opacity=0.1),
            t_group.animate.set_stroke(opacity=1)
        )
        self.wait()

        r_tex = Tex(r"\left|\frac{z+1}{z-1}\right|=2").to_corner(UR, buff = MED_LARGE_BUFF).set_color(TEAL_B)
        t_tex = Tex(r"\arg\frac{z+1}{z-1}=\frac{2\pi}{3}").to_corner(UR, buff = MED_LARGE_BUFF).set_color(GREEN_B)
        self.play(t_group.animate.set_stroke(opacity=0.1),
            r_group[7].animate.set_stroke(opacity=1),
            FadeIn(r_tex))
        self.wait()
        self.play(r_group[7].animate.set_stroke(opacity=0.1),
            t_group[2].animate.set_stroke(opacity=1),
            Transform(r_tex, t_tex))
        self.wait(3)

        angle = Angle(plane.n2p(1), plane.n2p(-1), plane.n2p(-1+4j+4/(3**0.5)),
            edge_config = {"color": YELLOW, "stroke_width": 3},
            label = r"\pi+\theta", label_scale=1, label_buff=4
        ).set_z_index(1)
        self.play(FadeIn(angle))
        self.wait()


class SteinerFlow(Scene):
    def construct(self):
        plane = ComplexPlane(
            x_range=(-8, 8, 1), y_range=(-4, 4, 1),
            background_line_style=dict(stroke_color=BLUE, stroke_width=1),
            faded_line_style=dict(stroke_color=BLUE, stroke_width=0.5, stroke_opacity=0.5),
            faded_line_ratio=1,
        )
        self.add(plane)

        z1, z2 = -1 + 0j, 1 + 0j
        rs = [1/11, 1/5, 1/3, 1/2, 1/1.4, 1, 1.4, 2, 3, 5, 11]
        thetas = [i * PI / 6 for i in range(12)]

        # 原版 MathTex(r"z\mapsto z") 后按 part 切片；manimgl 的 Tex 子对象
        # 是逐字符的，没有 part 结构，所以直接拆成两个 Tex 组成 VGroup
        prefix = Wh(r"z\mapsto")
        mapping_tex = Wh("z")
        label = VGroup(prefix, mapping_tex).arrange(RIGHT, buff=0.15)
        label.scale(1.2).to_corner(UR)
        label.add_updater(
            lambda l: l.arrange(RIGHT, buff=0.15).to_corner(UR)
        )

        # 黄色发光点 p：manimgl 的 GPU 泛光点（TrueGlow 家族的单点版）
        p = GlowDot(color=YELLOW, radius=0.09, glow_factor=0.5)
        p.move_to(plane.c2p(0.5, 0))
        circles = steiner(z1, z2, rs, thetas)
        r_group, t_group = circles
        self.play(FadeIn(circles), FadeIn(label), FadeIn(p), run_time=1.5)
        self.wait(0.5)

        # 右缘锚点：与 to_corner(UR) 的默认边距一致，首帧无跳变
        right_edge_x = FRAME_X_RADIUS - 0.25

        def layout_pair(theta):
            """分式贴在 prefix 右侧，返回 (分式, dx)；dx 使分式右缘恒为 right_edge_x。"""
            new_frac = Tex(
                rf"\frac{{(e^{{i\cdot {theta}}}+1)z+(e^{{i\cdot {theta}}}-1)}}"
                rf"{{(e^{{i\cdot {theta}}}-1)z+(e^{{i\cdot {theta}}}+1)}}",
                t2c={theta: YELLOW},
                fill_color=WHITE, 
                stroke_color=WHITE
            ).scale(0.7)
            new_frac.next_to(prefix, RIGHT, buff=0.15)
            dx = right_edge_x - new_frac.get_right()[0]
            return new_frac, dx

        def fraction_tex(theta):
            new_frac = Tex(
                rf"\frac{{(e^{{i\cdot {theta}}}+1)z+(e^{{i\cdot {theta}}}-1)}}"
                rf"{{(e^{{i\cdot {theta}}}-1)z+(e^{{i\cdot {theta}}}+1)}}",
                t2c={theta: YELLOW},
                fill_color=WHITE, 
                stroke_color=WHITE
            ).scale(0.7)
            return new_frac

        # 展开：z -> Möbius 分式，prefix 在同一 play 里同步左移
        new_frac = fraction_tex("0.00")
        self.play(
            Transform(mapping_tex, new_frac),
        )
        self.wait(0.3)

        # 分式中的数值与 thetas 增量同步增大
        shift = ValueTracker(0.0)  # ValueTracker is basically a slider you control using commands
        def mobius_image(z0, theta):
            e = np.exp(1j * theta)
            return ((e + 1) * z0 + (e - 1)) / ((e - 1) * z0 + (e + 1))

        # point updater
        def track_p(m):
            z = mobius_image(0.5 + 0j, shift.get_value())
            m.move_to(plane.c2p(z.real, z.imag))
        p.add_updater(lambda m, dt=None: track_p(m))

        # arc updater
        for arc, th in zip(t_group, thetas):
            arc.add_updater(lambda m, dt=None, th=th: m.become(
                steiner_t_arc(z1, z2, th + shift.get_value(), color=GREEN)))

        # tex updater
        def sync(tex, dt=None):
            new_frac = fraction_tex(f"{shift.get_value():.2f}")
            tex.become(new_frac.to_corner(UR))
        mapping_tex.add_updater(sync)

        self.play(shift.animate.set_value(PI), run_time=4)

        # cleanup
        for arc in t_group:
            arc.clear_updaters()
        mapping_tex.clear_updaters()
        p.clear_updaters()

        new_frac = fraction_tex(r"\pi")
        mapping_tex.become(new_frac)
        self.wait(0.5)

        inv_mob = Wh(r"\frac{1}{z}").scale(1.2)
        inv_mob.to_corner(UR)
        self.play(
            Transform(mapping_tex, inv_mob),
            run_time=0.8,
        )
        self.wait(0.5)


## ============ 三维模曲面（CE Surface -> manimgl ParametricSurface） ============
def modular_surface_1_over_z(u_range=(-3, 3), v_range=(-3, 3),
                             resolution=(65, 65), h_max=3.5):
    """w = 1/z 的模曲面：z 轴高度 = |w|（在原点处 clamp 到 h_max）。
    颜色：color_by_uv_function 逐顶点上色（hue=arg w，V=mag_to_val），
    顶点色在面片内由着色器插值——比 CE 版逐面片上色更平滑，
    且天然与 2D domain colouring 同一套规则。"""
    def func(u, v):
        if u == 0 and v == 0:
            return np.array([0.0, 0.0, h_max])
        w = 1.0 / (u + 1j * v)
        return np.array([u, v, min(abs(w), h_max)])

    surf = ParametricSurface(
        func, u_range=u_range, v_range=v_range, resolution=resolution,
    )

    def uv_color(u, v):
        if u == 0 and v == 0:
            return "#FFFFFF"
        w = 1.0 / (u + 1j * v)
        hue = (np.angle(w) / (2 * np.pi)) % 1.0
        rgb = hsv_to_rgb(hue, 1.0, mag_to_val(abs(w)))
        r, g, b = (int(round(255 * float(c))) for c in rgb)
        return f"#{r:02x}{g:02x}{b:02x}"

    surf.color_by_uv_function(uv_color)
    return surf


class DomainColouring(ThreeDScene):
    # ---------- 构件 ----------
    def make_square_with_ticks(self, side=6.0, n_per_side=5, tick_len=0.14):
        square = Square(side_length=side, stroke_color=WHITE, stroke_width=3)
        ticks = VGroup()
        edges = [
            (square.get_corner(UL), square.get_corner(UR), UP),
            (square.get_corner(DL), square.get_corner(DR), DOWN),
            (square.get_corner(UL), square.get_corner(DL), LEFT),
            (square.get_corner(UR), square.get_corner(DR), RIGHT),
        ]
        for p0, p1, outward in edges:
            for i in range(1, n_per_side):
                p = interpolate(p0, p1, i / n_per_side)
                ticks.add(Line(p, p + outward * tick_len,
                               stroke_color=WHITE, stroke_width=2))
        img = ImageMobject(_save_png(domain_colouring_image(), "domain_colour.png"))
        img.replace(square)
        return Group(square, ticks, img)

    def make_legend(self, kind, height=3.2, width=0.55):
        img = ImageMobject(_save_png(legend_image(kind), f"legend_{kind}.png"))
        img.set_height(height, stretch=True)
        img.set_width(width, stretch=True)

        labels = ["0", "1", r"\infty"] if kind == "value" else ["0", r"\pi", r"2\pi"]

        ticks = VGroup()
        texts = VGroup()
        for val, lab in zip((1.0, 0.5, 0.0), labels):
            p = img.get_right() + (0.5 - val) * height * UP
            tick = Line(p, p + RIGHT * 0.14, stroke_color=WHITE, stroke_width=2)
            ticks.add(tick)
            text = Wh(lab, font_size=48).scale(0.7)
            text.next_to(tick, RIGHT, buff=0.12)
            texts.add(text)

        box = SurroundingRectangle(img, color=WHITE, buff=0.0, stroke_width=2)
        return Group(img, box, ticks, texts)

    def make_glow(self, mob, color=WHITE, n_layers=10):
        opacities = [2 / n_layers for i in range(n_layers)]
        layers = VGroup()
        for i in range(n_layers):
            layer = SurroundingRectangle(mob, color=color, buff=0.0)
            layer.set_stroke(width=24 * (i / n_layers) ** 1.5, opacity=opacities[i])
            layers.add(layer)
        layers.z_index = mob.z_index - 0.1
        return layers

    def construct(self):
        # 【关键】manimgl ThreeDScene 默认机位是斜的 reorient(-30, 70)；
        # CE 从俯视开始，先对齐。漏这行 = 整段 2D 内容全是歪的
        self.frame.reorient(0, 0, 0)

        # 1. 公式
        eq = Wh(r"w=\frac{1}{z}").scale(1.6)
        self.play(Write(eq))
        self.wait(3)
        self.play(eq.animate.to_corner(UL).scale(0.8))
        eq.z_index = 1

        # 2. a、b、c 依次淡入
        a = self.make_square_with_ticks()
        b = self.make_legend("value")
        c = self.make_legend("hue")

        group = Group(a)
        self.play(FadeIn(a), run_time=0.6)
        self.wait(0.3)

        group.add(b)
        self.play(FadeIn(b, run_time=0.6),
                  group.animate.arrange(RIGHT, buff=0.6).move_to(ORIGIN))
        self.wait(0.3)

        group.add(c)
        self.play(FadeIn(c, run_time=0.6),
                  group.animate.arrange(RIGHT, buff=0.3).move_to(ORIGIN))
        self.wait(0.1)

        # 3. b、c 依次辉光高亮
        for legend in (b, c):
            glow = self.make_glow(legend[1])
            self.play(FadeIn(glow, lag_ratio=0.2, run_time=0.8))
            self.wait(0.5)
            self.play(FadeOut(glow, run_time=0.5))
            self.wait(0.5)

        # 4. 删除 b、c，方框回中
        self.play(FadeOut(b), FadeOut(c),
                  a.animate.move_to(ORIGIN), run_time=0.8)
        self.wait(1)

        # 5. 换成"高度=模长"的三维模曲面：俯视淡入（与 2D 图重合），随后运镜
        surface = modular_surface_1_over_z()
        self.play(
            FadeOut(a[2], run_time=1.2),          # 只撤走框内位图；方框、刻度保留
            FadeIn(surface, run_time=1.2),
        )
        self.wait(0.5)

        # 6. 运镜：CE(phi=62°, theta=-35°) 经数值验证的精确等价机位
        #    manimgl: R = Rz(θ)Rx(φ)Rz(γ)，CE 视图分解为 (-180°, 62°, 125°)
        #    focal=20 对齐 CE 默认焦距（manimgl 默认 fovy=45° 透视明显更强）
        self.frame.set_focal_distance(20)
        self.play(
            self.frame.animate.reorient(55, 62, 0),
            run_time=3, rate_func=smooth,
        )
        self.wait(1)
        self.play(*[FadeOut(m) for m in self.mobjects])

def inv(z, eps=0.05):
    # z 是单个复数（manimgl 逐点调用），保持向量化写法对标量同样安全：
    # 1/z = conj(z)/|z|^2，用 eps 截断 |z| 避免 z=0 发散
    r = np.maximum(np.abs(z), eps)
    return np.conj(z) / r**2


class InverseGrid(Scene):
    def construct(self):
        c_grid = ComplexPlane(
            # x_range=(-7.111111, 7.111111, 0.5),
            # y_range=(-4, 4, 0.5),
            background_line_style=dict(stroke_color=BLUE, stroke_width=1),
            faded_line_style=dict(stroke_color=BLUE, stroke_width=0.5, stroke_opacity=0.5),
            faded_line_ratio=1,
        )

        moving = c_grid.copy()
        moving.prepare_for_nonlinear_transform(num_inserted_curves=200)

        # 刻度仍然间隔 1：x 轴 ±1..±7，y 轴 ±1i..±4i（0 不标）
        # CE 的 add_coordinates -> manimgl 的 add_coordinate_labels(numbers=...)
        labels = [float(x) for x in range(-7, 8) if x != 0] + [
            complex(0, y) for y in range(-4, 5) if y != 0
        ]
        c_grid.add_coordinate_labels(labels, skip_first=False, font_size=24)

        self.add(c_grid, moving)
        self.play(
            moving.animate.apply_complex_function(inv),
            run_time=6,
        )
        self.wait()
        self.play(*[FadeOut(m) for m in self.mobjects])


#! This is my logo. Don't copy it.
class OsmanthusDanmakuDark(Scene):
    def construct(self):
        # --------------------------------------------------------
        # 1. 花瓣形状（三层，轴对称，类似笛卡尔叶形线）
        # --------------------------------------------------------
        petal_shapes = [
            make_petal_points(lambda t: 1.1 * np.sin(2 * t), (0, np.pi / 2)),
            make_petal_points(lambda t: np.sin(2 * t), (0, np.pi / 2)),
            make_petal_points(lambda t: 0.7 * np.sin(4 * t - np.pi / 2), (np.pi / 8, 3 * np.pi / 8)),
        ]

        DEFAULT_PETAL_AXIS = 5 * np.pi / 4
        LAYER_COLORS = ["#FFCC80", "#FF9933", "#E07000"]

        # --------------------------------------------------------
        # 2. 六族轨迹配置
        # --------------------------------------------------------
        traj_configs = [
            ("L1", 0, False, 1.5, lambda t: 5 * np.pi / 4 - t, (0.0, np.pi / 3),
             lambda th: (4.5 / np.pi) * ((th - np.pi / 4) - 3 * (th - np.pi / 4) ** 2 / (4 * np.pi)),
             lambda t: 5 * np.pi / 4 - t, (np.pi / 3, np.pi)),
            ("L2", 0, True, 1.5, lambda t: t - 3 * np.pi / 4, (0.0, np.pi / 3),
             lambda th: (4.5 / np.pi) * ((np.pi / 4 - th) - 3 * (np.pi / 4 - th) ** 2 / (4 * np.pi)),
             lambda t: t - 3 * np.pi / 4, (np.pi / 3, np.pi)),
            ("M1", 1, False, 1.5, lambda t: 9 * np.pi / 8 - t, (0.0, np.pi / 3),
             lambda th: (72 / (13 * np.pi)) * ((th - np.pi / 4) - 12 * (th - np.pi / 4) ** 2 / (13 * np.pi)),
             lambda t: 9 * np.pi / 8 - t, (np.pi / 3, 7 * np.pi / 8)),
            ("M2", 1, False, 1.5, lambda t: 11 * np.pi / 8 - t, (0.0, np.pi / 3),
             lambda th: (72 / (19 * np.pi)) * ((th - np.pi / 4) - 12 * (th - np.pi / 4) ** 2 / (19 * np.pi)),
             lambda t: 11 * np.pi / 8 - t, (np.pi / 3, 9 * np.pi / 8)),
            ("S1", 2, False, 1.0, lambda t: 19 * np.pi / 8 - t, (0.0, 19 * np.pi / 24),
             lambda th: (3 / (2 * np.pi)) * ((th - np.pi / 4) - 3 * (th - np.pi / 4) ** 2 / (8 * np.pi)),
             lambda t: 19 * np.pi / 8 - t, (19 * np.pi / 24, 17 * np.pi / 8)),
            ("S2", 2, False, 1.0, lambda t: 17 * np.pi / 8 - t, (0.0, np.pi / 2),
             lambda th: (16 / (11 * np.pi)) * ((th - np.pi / 4) - 4 * (th - np.pi / 4) ** 2 / (11 * np.pi)),
             lambda t: 17 * np.pi / 8 - t, (np.pi / 2, 15 * np.pi / 8)),
        ]

        precomputed = []
        for cfg in traj_configs:
            name, layer_idx, is_flipped, r1, th1, t1r, r2f, th2, t2r, *_ = cfg
            t_s, pos_s, tan_s, t_max = precompute_trajectory(r1, th1, t1r, r2f, th2, t2r, is_flipped=is_flipped)
            precomputed.append({
                "name": name, "layer": layer_idx,
                "t_samples": t_s, "pos_samples": pos_s, "tan_samples": tan_s,
                "t_max": t_max,
            })

        TOTAL_ANIM_TIME = 4.0

        # --------------------------------------------------------
        # 3. 创建 24 片花瓣
        # --------------------------------------------------------
        all_petals = []
        top_left_petals = []

        for family_idx, pc in enumerate(precomputed):
            layer_idx = pc["layer"]
            points = petal_shapes[layer_idx]
            color = LAYER_COLORS[layer_idx]
            flipped = (family_idx in [1, 5])

            for rot_idx in range(4):
                rot_offset = -rot_idx * np.pi / 2 if flipped else rot_idx * np.pi / 2
                final_angle = np.pi / 4 + rot_offset

                petal = Polygon(
                    *points,
                    fill_color=color, fill_opacity=1.0,
                    stroke_color=color, stroke_width=1.0,
                )
                petal.template_points = np.array(petal.get_points())
                petal.meta = {
                    "family": family_idx, "rot_idx": rot_idx,
                    "final_angle": final_angle, "rot_offset": rot_offset,
                    "layer": layer_idx, "t_max": pc["t_max"],
                    "t_samples": pc["t_samples"], "pos_samples": pc["pos_samples"],
                    "tan_samples": pc["tan_samples"],
                }

                t_s = petal.meta["t_samples"]
                pos_s = petal.meta["pos_samples"]
                tan_s = petal.meta["tan_samples"]

                start_pos = pos_s[0]
                start_tangent = tan_s[0] + rot_offset
                ca, sa = np.cos(rot_offset), np.sin(rot_offset)
                rx = start_pos[0] * ca - start_pos[1] * sa
                ry = start_pos[0] * sa + start_pos[1] * ca
                start_pos_rot = np.array([rx, ry, 0.0])

                petal.set_points(petal.template_points.copy())
                petal.rotate(start_tangent - DEFAULT_PETAL_AXIS, about_point=ORIGIN)
                petal.shift(start_pos_rot)

                all_petals.append(petal)
                self.add(petal)

                if (not flipped and rot_idx == 1) or (flipped and rot_idx == 3):
                    top_left_petals.append(petal)

        # --------------------------------------------------------
        # 4. 飞入动画（linear 速度）
        #    CE 的 UpdateFromAlphaFunc -> ValueTracker + updater
        # --------------------------------------------------------
        shift_alpha = ValueTracker(0.0)

        def make_tracker_updater(petal, tracker):
            meta = petal.meta
            template = petal.template_points
            t_max = meta["t_max"]
            t_s = meta["t_samples"]
            pos_s = meta["pos_samples"]
            tan_s = meta["tan_samples"]
            rot_offset = meta["rot_offset"]
            n = len(t_s)

            def updater(mob):
                alpha = smooth(tracker.get_value())
                traj_t = alpha * t_max
                idx = int((traj_t / t_max) * (n - 1))
                idx = max(0, min(idx, n - 1))
                base_pos = pos_s[idx]
                base_tangent = tan_s[idx]
                ca, sa = np.cos(rot_offset), np.sin(rot_offset)
                rx = base_pos[0] * ca - base_pos[1] * sa
                ry = base_pos[0] * sa + base_pos[1] * ca
                pos = np.array([rx, ry, 0.0])
                tangent = base_tangent + rot_offset
                mob.set_points(template.copy())
                mob.rotate(tangent - DEFAULT_PETAL_AXIS, about_point=ORIGIN)
                mob.shift(pos)

            return updater

        for petal in all_petals:
            petal.add_updater(make_tracker_updater(petal, shift_alpha))
        self.play(
            shift_alpha.animate.set_value(1.0),
            run_time=TOTAL_ANIM_TIME,
            rate_func=smooth
        )
        for petal in all_petals:
            petal.clear_updaters()

        # --------------------------------------------------------
        # 5. 变色 + 整体上移 + 文字浮现（同一个 play，同时进行）
        # --------------------------------------------------------
        logo = VGroup(*all_petals)

        label = Text("白川桂华", font="Noto Serif SC", font_size=42)
        label.set_color(LAYER_COLORS[1])   # 中花瓣的橙 #FF9933
        label.next_to(logo, DOWN, buff=0.3)
        label.shift(UP * 0.7)              # 预加上移量，与上移后的 logo 保持相对位置

        sub = Text("+AI(对抗式协作)", font="Noto Serif SC", font_size=25)
        sub.set_color(LAYER_COLORS[0])     # 浅橙 #FFCC80
        sub.next_to(label, RIGHT, buff=0.2)

        GOLD_COLORS = ["#FFE699", "#F5C842", "#E6A800"]
        self.play(
            *[
                p.animate.shift(UP * 0.7).set_fill(GOLD_COLORS[p.meta["layer"]])
                if p in top_left_petals
                else p.animate.shift(UP * 0.7)
                for p in all_petals
            ],
            FadeIn(label, shift=UP * 0.25),
            run_time=0.8,
            rate_func=smooth,
        )
        self.wait(0.6)
        self.play(FadeIn(sub, shift=UP * 0.25))
        self.wait(1.5)
        self.play(*[FadeOut(m) for m in self.mobjects])


class ZSquaredRiemann(ThreeDScene):

    # ---------- Components ----------
    def make_glow_dot(self, color=YELLOW, radius=0.1):
        dot = Group(
            TrueDot(radius=radius).make_3d(),   # 内核：写/测深度
            GlowDot(radius=radius * 3, glow_factor=1.5),  # 光晕：painter 叠加
        )
        dot.set_color(color)
        return dot

    def polar_half(self,center,deg0,deg1,color,half_side=1.5,stroke_width=2):
        grid = VGroup()

        for deg in range(deg0, deg1, 30):
            th = deg * DEG
            R = half_side / max(
                abs(np.cos(th)),
                abs(np.sin(th)),
            )

            line = Line(
                center,
                center + R * np.array([np.cos(th), np.sin(th), 0]),
                color=color,
                stroke_width=stroke_width,
            )
            line.meta = ("ray", R, th)
            grid.add(line)

        for r in (0.4, 0.8, 1.2, 1.5):
            arc = Arc(
                radius=r,
                start_angle=deg0 * DEG,
                angle=(deg1 - deg0) * DEG,
                arc_center=center,
                color=color,
                stroke_width=stroke_width,
            )
            arc.meta = ("arc", r, deg0 * DEG)
            grid.add(arc)

        return grid

    def doubled_flat(self, mob, center):
        kind, a, th = mob.meta
        color = mob.get_stroke_color()
        width = mob.get_stroke_width()

        if kind == "ray":
            return Line(
                center,
                center + a**2 * np.array([
                    np.cos(2 * th),
                    np.sin(2 * th),
                    0,
                ]),
                color=color,
                stroke_width=width,
            )

        return Arc(
            radius=a**2,
            start_angle=2 * th,
            angle=2 * PI,
            arc_center=center,
            color=color,
            stroke_width=width,
        )

    def add_ticks(self,box,x_vals,y_vals,tick_len=0.12,font_size=32):
        """Add ticks and labels along the bottom and left sides."""
        x0 = box.get_center()[0]
        y0 = box.get_center()[1]
        half = box.get_width() / 2

        group = VGroup()

        for x in x_vals:
            p = np.array([x0 + x, y0 - half, 0])

            tick = Line(
                p,
                p + DOWN * tick_len,
                color=WHITE,
                stroke_width=2,
            )
            num = Text(str(x), font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)

        for y in y_vals:
            p = np.array([x0 - half, y0 + y, 0])

            tick = Line(
                p, p + LEFT * tick_len,
                color=WHITE,
                stroke_width=2,
            )

            if y == 1:
                label = "i"
            elif y == -1:
                label = "-i"
            else:
                label = str(y)

            num = Text(label, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)

        return group

    def lifted(self, mob, center):
        """
        Lift a ray or circular arc to the surface

            (x, y, h) = (r^2 cos(2 theta),
                         r^2 sin(2 theta),
                         r sin(theta)).
        """
        kind, a, th = mob.meta
        color = mob.get_stroke_color()
        width = mob.get_stroke_width()

        if kind == "ray":
            return ParametricCurve(
                lambda t: center + np.array([
                    t**2 * np.cos(2 * th),
                    t**2 * np.sin(2 * th),
                    t * np.sin(th),
                ]),
                t_range=(0, a, 0.02),
                color=color,
                stroke_width=width,
            )

        return ParametricCurve(
            lambda t: center + np.array([
                a**2 * np.cos(2 * t),
                a**2 * np.sin(2 * t),
                a * np.sin(t),
            ]),
            t_range=(th, th + PI, 0.02), color=color, stroke_width=width,
        )

    # ---------- Glow effects ----------

    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(
                p0, p1,
                color=color, stroke_width=5,
            ),
            *[
                Line(
                    p0, p1,
                    color=color,
                    stroke_width=5 + 8 * k,
                    stroke_opacity=0.5 / k,
                )
                for k in (1, 2, 3)
            ],
        )

    def glowing_edge(
        self,
        center,
        direction,
        buff=0.05,
        length=1.5,
        colors=(RED, BLUE),
        swap=False,
    ):
        """Two glowing, parallel line segments in a flat plane."""
        if swap:
            buff *= -1

        direction = normalize(direction)
        normal_vec = rotate_vector(direction, PI / 2)

        return VGroup(
            self.glow_line(
                center + buff * normal_vec,
                center + buff * normal_vec + length * direction,
                colors[0],
            ),
            self.glow_line(
                center - buff * normal_vec,
                center - buff * normal_vec + length * direction,
                colors[1],
            ),
        )

    def lifted_glowing_edge(self, wc, direction, buff=0.2, length=1.5,
        colors=(RED, BLUE), swap=False, n_glow=3, dz=0.015
    ):
        """
        Lift both parallel secants onto the Riemann surface.
        对平面上任意方向的割线 z(s) = s*direction ± buff*normal，
        曲面点为 (Re z^2, Im z^2, Im z + k*dz)。
        """
        if swap:
            buff *= -1

        direction = normalize(direction)
        normal_vec = rotate_vector(direction, PI / 2)

        curves = VGroup()

        for side, color in zip((1, -1), colors):
            glow_group = VGroup()

            for k in range(n_glow):
                def surface_point(s, side=side, k=k):
                    z = s * direction + side * buff * normal_vec
                    x, y = z[0], z[1]
                    return wc + np.array([
                        x**2 - y**2,
                        2 * x * y,
                        y + k * dz,   # 层间微移：透明 ribbon 不再共面
                    ])

                glow_group.add(
                    ParametricCurve(
                        surface_point,
                        t_range=(0, length, 0.01),
                        color=color,
                        stroke_width=5 + 8 * k,
                        stroke_opacity=1.0 if k == 0 else 0.5 / k,
                    )
                )

            curves.add(glow_group)

        return curves

    def show_secant_pair(self, zc, wc, direction, swap=False,
                        length=1.5, buff=0.05):
        """同时显示 z 平面的平面割线和曲面上对应的 lifted 割线。"""
        flat = self.glowing_edge(
            zc, direction=direction, buff=buff,
            length=length, swap=swap,
        )
        lifted = self.lifted_glowing_edge(
            wc, direction=direction, buff=buff,
            length=length, swap=swap,
        )
        return flat, lifted

    # ---------- Point animations ----------

    def animate_point_pairs(self, zc, wc, pairs, run_time=2.0):
        """
        Animate corresponding points in the z-plane and flat w-plane.
        pairs contains (theta_start, theta_end) or (theta_start, theta_end, radius).
        """
        dots = []
        trackers = []

        for item in pairs:
            th0, th1 = item[0], item[1]
            r = item[2] if len(item) > 2 else 1.0

            pz = self.make_glow_dot()
            pw = self.make_glow_dot()
            tracker = ValueTracker(th0)

            def update_z(mob, dt=0, tr=tracker, radius=r):
                th = tr.get_value()
                mob.move_to(
                    zc + radius * np.array([
                        np.cos(th),
                        np.sin(th),
                        0,
                    ])
                )

            def update_w(mob, dt=0, tr=tracker, radius=r):
                th = tr.get_value()
                mob.move_to(
                    wc + radius**2 * np.array([
                        np.cos(2 * th), np.sin(2 * th), 0
                    ])
                )

            pz.add_updater(update_z)
            pw.add_updater(update_w)

            update_z(pz)
            update_w(pw)

            dots.extend([pz, pw])
            trackers.append((tracker, th1))

        self.play(
            *[FadeIn(dot) for dot in dots],
            run_time=0.4,
        )

        self.play(
            *[
                tracker.animate.set_value(end_angle)
                for tracker, end_angle in trackers
            ],
            run_time=run_time,
            rate_func=smooth,
        )

        self.play(
            *[FadeOut(dot) for dot in dots],
            run_time=0.4,
        )

        for dot in dots:
            dot.clear_updaters()

    def animate_point_on_surface(self, pz, ps, zc, wc,
                             radius=1.2, run_time=5.0, eps=0.0):
        """
        pz, ps 必须在 sheets 之前已 add 入场景（见 construct 第 7 段）。
        eps：光点在曲面正上方的高出量——深度严格近于曲面，
            无论绘制先后都能通过 less 深度测试。
        """
        tracker = ValueTracker(0.0)

        def update_z(mob, dt=0):
            th = tracker.get_value()
            mob.move_to(
                zc + radius * np.array([np.cos(th), np.sin(th), 0])
            )

        def update_surface(mob, dt=0):
            th = tracker.get_value()
            mob.move_to(
                wc + np.array([
                    radius**2 * np.cos(2 * th),
                    radius**2 * np.sin(2 * th),
                    radius * np.sin(th) + eps,   # ← 关键：+eps
                ])
            )

        pz.add_updater(update_z)
        ps.add_updater(update_surface)
        update_z(pz)        # 立即定位到 θ=0 起点，不等第一帧
        update_surface(ps)

        self.play(
            tracker.animate.set_value(2 * PI),
            run_time=run_time,
            rate_func=linear,
        )

        pz.clear_updaters()
        ps.clear_updaters()

    def make_surface_sheet(self, center, v0, v1, color, r_max=1.5, resolution=(24, 48), opacity=0.3):
        """
        黎曼面的一叶：w = z^2，高度 h = Im z。

        u = r ∈ [0, r_max]，v = theta ∈ [v0, v1]
            (r^2 cos 2θ, r^2 sin 2θ, r sin θ)
        """
        sheet = ParametricSurface(
            lambda u, v: center + np.array([
                u**2 * np.cos(2 * v),
                u**2 * np.sin(2 * v),
                u * np.sin(v),
            ]),
            u_range=(0, r_max),
            v_range=(v0, v1),
            resolution=resolution,
        )
        sheet.set_color(color, opacity=opacity)
        sheet.always_sort_to_camera(self.camera)
        return sheet

    # ---------- Main scene ----------

    def construct(self):
        self.frame.reorient(0, 0, 0)

        zc = LEFT * 3.4
        wc = RIGHT * 3.4

        z_box = Square(3, stroke_color=WHITE).move_to(zc)

        w_box = Square(5, stroke_color=WHITE).move_to(wc)

        z_lab = Tex("z").next_to(z_box, UP, buff=0.15)
        w_lab = Tex("w").next_to(w_box, UP, buff=0.15)
        title = Tex("w = z^2").scale(1.2).to_corner(UL)

        self.add(z_box, w_box, z_lab, w_lab, title)

        self.add(
            self.add_ticks(
                z_box, (-1, 0, 1), (-1, 0, 1)
            ),
            self.add_ticks(
                w_box, (-2, -1, 0, 1, 2), (-2, -1, 0, 1, 2)
            ),
        )

        # 1. Show the polar grids in the z-plane.
        upper = self.polar_half(zc, 0, 180, RED)
        lower = self.polar_half(zc, 180, 360, BLUE)

        self.play(FadeIn(upper), FadeIn(lower), run_time=1.2)
        self.wait(0.5)

        # Keep static copies in the z-plane.
        self.add(upper.copy(), lower.copy())

        # 2. Move the upper grid to the w-plane and apply w = z^2.
        self.play(upper.animate.shift(wc - zc), run_time=1.5)

        self.play(
            *[
                Transform(mob, self.doubled_flat(mob, wc))
                for mob in upper
            ],
            run_time=2,
        )
        self.wait(0.5)

        # 3. Do the same for the lower grid.
        self.play(lower.animate.shift(wc - zc), run_time=1.5)

        self.play(
            *[
                Transform(mob, self.doubled_flat(mob, wc))
                for mob in lower
            ],
            run_time=2,
        )
        self.wait(0.5)

        # Show corresponding points on the two flat planes.
        self.animate_point_pairs(
            zc, wc,
            [
                (PI / 6, -PI / 6, 1.0),
                (5 * PI / 6, 7 * PI / 6, 1.0),
            ],
        )

        # 4. Highlight the original flat secants.
        secant1 = VGroup(
            self.glowing_edge(zc, direction=LEFT, swap=True),
            self.glowing_edge(wc, direction=RIGHT, swap=True, length=2.4),
        )

        self.play(FadeIn(secant1), run_time=0.5)
        self.wait()
        self.play(FadeOut(secant1), run_time=0.5)

        secant2 = VGroup(
            self.glowing_edge(zc, direction=RIGHT),
            self.glowing_edge(wc, direction=RIGHT, length=2.4),
        )

        self.play(FadeIn(secant2), run_time=0.5)
        self.wait()
        self.play(FadeOut(secant2), run_time=0.5)

        # 5. Move the camera to a 3D view.
        self.frame.set_focal_distance(20)

        self.play(
            self.frame.animate.reorient(125,62,0,center=wc),
            run_time=4,
            rate_func=smooth,
        )
        self.wait(0.5)

        # 6. Lift both grids onto the Riemann surface.
        upper_3d = VGroup(
            *[self.lifted(mob, wc) for mob in upper]
        )
        lower_3d = VGroup(
            *[self.lifted(mob, wc) for mob in lower]
        )
        self.play(
            *[
                Transform(mob, target)
                for mob, target in zip(upper, upper_3d)
            ],
            *[
                Transform(mob, target)
                for mob, target in zip(lower, lower_3d)
            ],
            run_time=3,
            rate_func=smooth,
        )
        self.wait(1)

        # 7. 光点 + 两叶曲面同帧入场；点在动画参数中列于 sheets 之前，
        #    因此它们在 mobjects 列表中也排在 sheets 之前（与 3b1b 同序）
        radius = 1.2
        pz = self.make_glow_dot()
        ps = self.make_glow_dot()
        pz.move_to(zc + radius * np.array([1.0, 0.0, 0.0]))          # θ=0 起点
        ps.move_to(wc + np.array([radius**2, 0.0, 0.0]))
        flat1, lifted1 = self.show_secant_pair(zc, wc, direction=LEFT, swap=True)
        flat2, lifted2 = self.show_secant_pair(zc, wc, direction=RIGHT)

        upper_sheet = self.make_surface_sheet(wc, 0, PI, RED)
        lower_sheet = self.make_surface_sheet(wc, PI, TAU, BLUE)

        self.play(
            FadeIn(pz),
            FadeIn(ps),
            FadeIn(upper_sheet),    # sheet must be added last
            FadeIn(lower_sheet),
            run_time=1.2,
        )
        self.wait(0.5)

        # 8. 点在曲面上跑一整圈
        self.animate_point_on_surface(
            pz, ps, zc, wc, radius=radius, run_time=5.0,
        )
        self.wait(0.5)
        self.play(
            FadeOut(pz),
            FadeOut(ps),
            FadeOut(upper_sheet),    # sheet must be added last
            FadeOut(lower_sheet),
        )

        # 8. 成对显示平面割线与曲面割线
        self.frame.add_ambient_rotation(-15 * DEG)
        self.play(FadeIn(flat1), FadeIn(lifted1), run_time=0.6)
        self.wait(1)
        self.play(FadeOut(flat1), FadeOut(lifted1), run_time=0.6)
        self.wait(0.5)
        self.play(FadeIn(flat2), FadeIn(lifted2), run_time=0.6)
        self.wait(1)
        self.play(FadeOut(flat2), FadeOut(lifted2), run_time=0.6)
        self.frame.clear_updaters()
        self.wait()
        self.play(*[FadeOut(m) for m in self.mobjects])


class ExpRiemann(ThreeDScene):
    A_HALF = 1.25     # hline 的 Re z 半宽
    BAND_W = 2 * A_HALF     # 带显示宽（a 方向 ±1.3）
    BAND_H = 1.3     # 带显示高（b 方向 2π 压缩）
    GAP = 0.0
    S_W = 1.6
    TARGET = 4.2
    SCALE_B = BAND_H / (2 * PI)

    # ---------- 构件 ----------
    def rect_band(self, center, b0, color):
        scale_b = self.BAND_H / (2 * PI)
        grid = VGroup()
        for a in (-1.2, -0.6, 0.0, 0.6, 1.2):       # a=const -> w 圆
            line = Line(center + np.array([a, -self.BAND_H / 2, 0]),
                        center + np.array([a, self.BAND_H / 2, 0]),
                        color=color, stroke_width=2)
            line.meta = ("vline", a, b0)
            grid.add(line)
        for k in (1, 2, 3, 4, 5):                   # b=const -> w 射线
            b = b0 + k * PI / 3
            y = (b - b0 - PI) * scale_b
            line = Line(center + np.array([-self.BAND_W / 2, y, 0]),
                        center + np.array([self.BAND_W / 2, y, 0]),
                        color=color, stroke_width=2)
            line.meta = ("hline", b, self.A_HALF)
            grid.add(line)
        return grid

    def y_of_b(self, b):
        scale_b = self.BAND_H / (2 * PI)  # scale_b is the length that corresponds to one unit
        step = self.BAND_H + self.GAP
        if b > PI:
            return step + (b - 2 * PI) * scale_b
        if b < -PI:
            return -step + (b + 2 * PI) * scale_b
        return b * scale_b

    def mapped_flat(self, m, center):
        kind = m.meta[0]
        color, width = m.get_stroke_color(), m.get_stroke_width()
        if kind == "vline":
            _, a, b0 = m.meta
            return Arc(radius=np.exp(a), start_angle=b0, angle=2 * PI,
                       arc_center=center, color=color, stroke_width=width)
        _, b, a_half = m.meta
        d = np.array([np.cos(b), np.sin(b), 0])
        return Line(center + np.exp(-a_half) * d, center + np.exp(a_half) * d,
                    color=color, stroke_width=width)

    def lifted(self, m, center):
        kind = m.meta[0]
        color, width = m.get_stroke_color(), m.get_stroke_width()
        if kind == "vline":
            _, a, b0 = m.meta
            return ParametricCurve(
                lambda t: center + np.array([np.exp(a) * np.cos(t),
                                             np.exp(a) * np.sin(t), 0.4*t]),
                t_range=(b0, b0 + 2 * PI, 0.02), color=color, stroke_width=width)
        _, b, a_half = m.meta
        return ParametricCurve(
            lambda t: center + np.array([np.exp(t) * np.cos(b),
                                         np.exp(t) * np.sin(b), 0.4*b]),
            t_range=(-a_half, a_half, 0.02), color=color, stroke_width=width)

    def animate_point_pairs(self, zc, wc, pairs, run_time=2.5):
        dots, trackers = [], []
        for item in pairs:
            b0, b1 = item[0], item[1]
            a = item[2] if len(item) > 2 else 0.0
            pz = GlowDot(color=YELLOW, radius=0.2, glow_factor=1.5)
            pw = pz.copy()
            tracker = ValueTracker(b0)

            def update(mob, dt=None, tr=tracker, a=a, pz=pz, pw=pw):
                b = tr.get_value()
                pz.move_to(zc + np.array([a, self.y_of_b(b), 0]))
                pw.move_to(wc + np.exp(a) * np.array([np.cos(b), np.sin(b), 0]))
            pz.add_updater(update)
            pw.add_updater(update)
            update(pz)

            dots += [pz, pw]
            trackers.append((tracker, b1))

        self.play(*[FadeIn(p) for p in dots], run_time=0.4)
        self.play(*[tr.animate.set_value(v) for tr, v in trackers],
                  run_time=run_time, rate_func=smooth)
        self.play(*[FadeOut(p) for p in dots], run_time=0.4)
        for p in dots:
            p.clear_updaters()

    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(
                p0, p1,
                color=color, stroke_width=5,
            ),
            *[
                Line(
                    p0, p1,
                    color=color,
                    stroke_width=5 + 8 * k,
                    stroke_opacity=0.5 / k,
                )
                for k in (1, 2, 3)
            ],
        )

    def glowing_edge(self, center, direction, buff=0.05, len=1.5, colors=[RED, BLUE], swap = False):
        if swap:
            buff *= -1
        direction = normalize(direction) 
        normal_vec = rotate_vector(direction, PI / 2)
        lines = VGroup(
            self.glow_line(center + buff * normal_vec, center + buff * normal_vec + len * direction, colors[0]),
            self.glow_line(center - buff * normal_vec, center - buff * normal_vec + len * direction, colors[1])
        )
        return lines

    def add_ticks(self, box, x_vals, y_vals, x_labels=None, y_labels=None,
                  tick_len=0.12, font_size=32):
        x0, y0 = box.get_center()[0], box.get_center()[1]
        hx, hy = box.get_width() / 2, box.get_height() / 2
        x_labels = x_labels or [str(v) for v in x_vals]
        y_labels = y_labels or [str(v) for v in y_vals]
        group = VGroup()
        for x, lab in zip(x_vals, x_labels):
            p = np.array([x0 + x, y0 - hy, 0])
            tick = Line(p, p + DOWN * tick_len, color=WHITE, stroke_width=2)
            num = Wh(lab, font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)
        for y, lab in zip(y_vals, y_labels):
            p = np.array([x0 - hx, y0 + y, 0])
            tick = Line(p, p + LEFT * tick_len, color=WHITE, stroke_width=2)
            num = Wh(lab, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)
        return group

    # ---------- 主流程 ----------
    def construct(self):
        self.frame.reorient(0, 0, 0)
        zg, wc = LEFT * 4.0, RIGHT * 2.8
        step = self.BAND_H + self.GAP
        title = Wh(r"w=e^z").scale(1.2).to_corner(UL)
        z_frame = Rectangle(width=self.BAND_W + 0.8,
                            height=2 * step + self.BAND_H + 0.6,
                            stroke_color=WHITE).move_to(zg)
        w_box = Square(7.0, stroke_color=WHITE).move_to(wc)
        self.add(title, z_frame, w_box)
        self.add(self.add_ticks(w_box, (0, 1, 2, 3), (0, 1, 2, 3),
                                y_labels=["0", r"i", r"2i", r"3i"]))
        b_ticks = (-3 * PI, -PI, 0.0, PI, 3 * PI)
        self.add(self.add_ticks(
            z_frame,
            x_vals=(-1.2, -0.6, 0.0, 0.6, 1.2),
            y_vals=tuple(self.y_of_b(b) for b in b_ticks),
            y_labels=[r"-3\pi i", r"-\pi i", "0", r"\pi i", r"3\pi i"],
        ))

        band_defs = [(-3 * PI, TEAL, r"-3\pi<\mathrm{Im}\,z<-\pi"),
                     (-PI, RED, r"-\pi<\mathrm{Im}\,z<\pi"),
                     (PI, BLUE, r"\pi<\mathrm{Im}\,z<3\pi")]
        grids, centers = [], []
        for i, (b0, color, tex) in enumerate(band_defs):
            c = zg + (i - 1) * step * UP
            grids.append(self.rect_band(c, b0, color))
            centers.append(c)

        for idx in (1, 0, 2):
            grid = grids[idx]
            grid1 = grid.copy()
            self.play(FadeIn(grid), FadeIn(grid1), run_time=0.8)
            self.play(grid.animate.shift(wc - centers[idx]).scale(self.S_W),
                      run_time=1.5)
            self.play(*[Transform(m, self.mapped_flat(m, wc)) for m in grid],
                      run_time=2)
            self.wait(0.4)

        self.animate_point_pairs(zg, wc, [
            (PI / 2, 3 * PI / 2, 0.0),
            (-PI / 2, -3 * PI / 2, 0.6),
        ])
        
        secant1 = VGroup(
            self.glowing_edge(zg + PI * self.SCALE_B * UP + 1.2 * LEFT, direction=RIGHT, swap=True, len = 2.4),
            self.glowing_edge(wc, direction=LEFT, swap=True, len = 4),
        )
        self.play(FadeIn(secant1), run_time=0.5)
        self.wait()
        self.play(FadeOut(secant1), run_time=0.5)
    
        self.frame.set_focal_distance(20)   # CE focal=20；默认 fovy=45° 透视过强
        self.play(
            self.frame.animate
                .reorient(60, 72, 0, center=wc, height=8 / 0.7)
                .set_field_of_view(2 * np.arctan((8 / 0.7) / 40)),
            run_time=4, rate_func=smooth,
        )
        self.wait(0.5)
        self.wait(0.5)
        flat_all = VGroup(*[m for g in grids for m in g])
        targets = VGroup(*[self.lifted(m, wc) for m in flat_all])
        self.play(*[Transform(m, t) for m, t in zip(flat_all, targets)],
                  run_time=3, rate_func=smooth)
        self.wait(1)
        self.play(*[FadeOut(m) for m in self.mobjects])


class CosRiemann(ThreeDScene):
    BAND_XW = 1.5        # 带显示宽（π 压缩）
    BAND_YH = 5.0        # 带显示高（y ±5 压缩）
    SCALE_X = BAND_XW / PI
    SCALE_Y = BAND_YH / 4.0
    GAP = 0.0
    S_ZW = 1.2
    R_MAX = 3.0
    BANDS = [(0.0, -1.0), (0.0, +1.0), (2 * PI, -1.0)]
    RHO_LIST = (0.4, 0.8, 1.2, 1.8, 2.4, 3.0)

    # ---------- 坐标换算 ----------
    def band_center_x(self, b):
        off, sgn = self.BANDS[b]
        return off + sgn * PI / 2

    def z_screen(self, z, b):
        sx = self.BAND_XW / PI
        sy = self.BAND_YH / 4.0
        return self.centers[b] + np.array([(z.real - self.band_center_x(b)) * sx,
                                           z.imag * sy, 0])

    def band_z(self, w, b):
        off, sgn = self.BANDS[b]
        return off + sgn * np.arccos(w)

    # ---------- z 平面网格与 w 侧目标 ----------
    def band_grid(self, b, color):
        eps = 0.0005
        segs = VGroup()
        for rho in self.RHO_LIST:
            ivals = [(0.01, PI-0.01), (PI+0.01, 2 * PI - 0.01)]
            for t0, t1 in ivals:
                def f(t, rho=rho):
                    return self.z_screen(self.band_z(rho * np.exp(1j * t), b), b)
                s = ParametricCurve(f, t_range=(t0, t1, 0.02), color=color, stroke_width=2)
                s.meta = ("wcirc", rho, t0, t1)
                segs.add(s)
        for j in range(16):                      # 角度间隔 pi/8
            phi = j * PI / 8
            if j % 8 == 0:
                phi += eps
            def f(t, phi=phi):
                return self.z_screen(self.band_z(t * np.exp(1j * phi), b), b)
            #* REUSE: ParametricCurve takes an function gamma(t): R -> R^3, a t range, and styles.
            s = ParametricCurve(f, t_range=(0.15, self.R_MAX, 0.02), color=color, stroke_width=2)
            s.meta = ("wray", phi)
            segs.add(s)
        return segs

    def w_target(self, meta, color, width):
        """与 z 侧源同参数同区间（含步长），保证 Transform 点序一一对应。"""
        if meta[0] == "wcirc":
            _, rho, t0, t1 = meta
            def f(t, rho=rho):
                return self.wc + rho * np.array([np.cos(t), np.sin(t), 0])
            return ParametricCurve(f, t_range=(t0, t1, 0.02), color=color,
                                   stroke_width=width, use_smoothing=False)
        phi = meta[1]
        def f(t, phi=phi):
            return self.wc + t * np.array([np.cos(phi), np.sin(phi), 0])
        return ParametricCurve(f, t_range=(0.15, self.R_MAX, 0.02), color=color,
                               stroke_width=width, use_smoothing=False)

    def lifted_seg(self, meta, b, color, width):
        def pt(w):
            z = self.band_z(w, b)
            return self.wc + np.array([w.real, w.imag, 0.8*z.real])
        if meta[0] == "wcirc":
            _, rho, t0, t1 = meta
            def f(t, rho=rho):
                return pt(rho * np.exp(1j * t))
            return ParametricCurve(f, t_range=(t0, t1, 0.02), color=color, stroke_width=width)
        phi = meta[1]
        def f(t, phi=phi):
            return pt(t * np.exp(1j * phi))
        return ParametricCurve(f, t_range=(0.15, self.R_MAX, 0.02), color=color, stroke_width=width)

    # ---------- 通用构件 ----------
    def make_glow_dot(self, color=YELLOW, radius=0.1):
        dot = Group(
            TrueDot(radius=radius).make_3d(),   # 内核：写/测深度
            GlowDot(radius=radius * 3, glow_factor=1.5),  # 光晕：painter 叠加
        )
        dot.set_color(color)
        return dot


    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(p0, p1, color=color, stroke_width=5),
            *[Line(p0, p1, color=color, stroke_width=5 + 8 * j, stroke_opacity=0.5 / j)
              for j in (1, 2, 3)],
        )

    def glowing_edge(self, center, direction, buff=0.05, len=1.5, colors=[RED, BLUE], swap = False):
        if swap:
            buff *= -1
        direction = normalize(direction) 
        normal_vec = rotate_vector(direction, PI / 2)
        lines = VGroup(
            self.glow_line(center + buff * normal_vec, center + buff * normal_vec + len * direction, colors[0]),
            self.glow_line(center - buff * normal_vec, center - buff * normal_vec + len * direction, colors[1])
        )
        return lines

    def add_ticks(self, box, x_vals, y_vals, x_labels=None, y_labels=None,
                  tick_len=0.12, font_size=30):
        x0, y0 = box.get_center()[0], box.get_center()[1]
        hx, hy = box.get_width() / 2, box.get_height() / 2
        x_labels = x_labels or [str(v) for v in x_vals]
        y_labels = y_labels or [str(v) for v in y_vals]
        group = VGroup()
        for x, lab in zip(x_vals, x_labels):
            p = np.array([x0 + x, y0 - hy, 0])
            tick = Line(p, p + DOWN * tick_len, color=WHITE, stroke_width=2)
            num = Wh(lab, font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)
        for y, lab in zip(y_vals, y_labels):
            p = np.array([x0 - hx, y0 + y, 0])
            tick = Line(p, p + LEFT * tick_len, color=WHITE, stroke_width=2)
            num = Wh(lab, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)
        return group

    def animate_point_pairs(self, pairs, run_time=2.5):
        dots, trackers = [], []
        for z0, z1 in pairs:
            pw = GlowDot(color = YELLOW, radius = 0.2, glow_factor = 1.5)
            pz = pw.copy()
            tracker = ValueTracker(0.0)

            def update(mob, dt=None, tr=tracker, z0=z0, z1=z1, pw=pw, pz=pz):
                z = z0 + tr.get_value() * (z1 - z0)
                w = np.cos(z)
                pz.move_to(self.z_screen(z, 2))
                pw.move_to(self.wc + np.array([w.real, w.imag, 0]))
            pw.add_updater(update)
            pz.add_updater(update)
            update(pw)

            dots += [pw, pz]
            trackers.append((tracker, 1.0))

        self.play(*[FadeIn(p) for p in dots], run_time=0.4)
        self.play(*[tr.animate.set_value(v) for tr, v in trackers],
                  run_time=run_time, rate_func=smooth)
        self.play(*[FadeOut(p) for p in dots], run_time=0.4)
        for p in dots:
            p.clear_updaters()

    def edge_flash(self, run_time=0.5, hold=1.0):
        off, hy = 0.05, self.BAND_YH / 2
        xe = self.centers[1] + self.BAND_XW / 2 * RIGHT
        lines = VGroup(
            self.glow_line(xe - off * RIGHT + hy * DOWN, xe - off * RIGHT + hy * UP, RED),
            self.glow_line(xe + off * RIGHT + hy * DOWN, xe + off * RIGHT + hy * UP, BLUE),
        )
        for side, color in ((+1, RED), (-1, BLUE)):
            def w_of(t, side=side):
                w = np.cos((PI + side * off) + 1j * t)
                return self.wc + np.array([w.real, w.imag, 0])
            for j in range(4):
                lines.add(ParametricCurve(
                    w_of, t_range=(-2.5, 2.5, 0.02), color=color,
                    stroke_width=5 + 8 * j, stroke_opacity=1.0 if j == 0 else 0.5 / j))
        self.play(FadeIn(lines, run_time=run_time))
        self.wait(hold)
        self.play(FadeOut(lines, run_time=run_time))

    # ---------- 主流程 ----------
    def construct(self):
        self.frame.reorient(0, 0, 0)
        self.zg, self.wc = LEFT * 3.8, RIGHT * 3.2 + UP * 0.1
        step = self.BAND_XW + self.GAP
        self.centers = {b: self.zg + (b - 1) * step * RIGHT for b in (0, 1, 2)}

        title = Wh(r"w=\cos z").scale(1.2).to_corner(UL)
        z_frame = Rectangle(width=3 * self.BAND_XW + 0.8,
                            height=self.BAND_YH + 0.8,
                            stroke_color=WHITE).move_to(self.zg)
        w_box = Square(6.6, stroke_color=WHITE).move_to(self.wc)
        self.add(title, z_frame, w_box)
        self.add(self.add_ticks(w_box, (1, 2, 3), (1, 2, 3),
                                y_labels=["i", r"2i", r"3i"]))
        xe = self.BAND_XW / 2
        self.add(self.add_ticks(
            z_frame,
            x_vals=[-step - xe, -xe, xe, step + xe],
            y_vals=[-2 * self.BAND_YH / 4, 0, 2 * self.BAND_YH / 4],
            x_labels=[r"-\pi", "0", r"\pi", r"2\pi"],
            y_labels=["-2", "0", "2"],
        ))

        w_segs = []
        for b, color in [(1, RED), (0, TEAL), (2, BLUE)]:
            grid = self.band_grid(b, color)
            home = grid.copy()
            self.play(FadeIn(grid), FadeIn(home), run_time=0.8)
            self.play(grid.animate.shift(self.wc - self.centers[b]).scale(self.S_ZW),
                      run_time=1.5)
            anims = []
            for seg in grid:
                seg.key = (seg.meta, b)
                w_segs.append(seg)
                anims.append(Transform(seg, self.w_target(seg.meta, color, 2)))
            self.play(*anims, run_time=2.5)
            self.wait(0.4)

        self.animate_point_pairs([(2.5 + 1j, 3.8 + 1j)])
        secant1 = VGroup(
            self.glowing_edge(self.zg + 0.5*PI*self.SCALE_X * RIGHT + 2 * self.SCALE_Y * DOWN, direction=UP, len = 4 * self.SCALE_Y),
            self.glowing_edge(self.wc + LEFT, direction=LEFT, swap=True, len = 2, buff = 0),
        )
        self.play(FadeIn(secant1), run_time=0.5)
        self.wait()
        self.play(FadeOut(secant1), run_time=0.5)

        # 运镜：CE move_camera(phi=72, theta=-30, frame_center=wc, zoom=0.7)
        self.frame.set_focal_distance(20)
        self.play(
            self.frame.animate
                .reorient(60, 72, 0, center=self.wc + [0,0,0.4], height=8 / 0.7)
                .set_field_of_view(2 * np.arctan((8 / 0.7) / 40)),
            run_time=4, rate_func=smooth,
        )
    
        self.play(*[
            Transform(seg, self.lifted_seg(seg.key[0], seg.key[1],
                                           seg.get_stroke_color(), 2))
            for seg in w_segs
        ], run_time=2.5, rate_func=smooth)
        self.wait(0.5)

        # 环绕竖直轴一整圈：增量式旋转（CE 里直接 theta+360 插值；
        # manimgl 用环境旋转 updater，45°/s × 8s = 360°，匀速）
        self.frame.add_ambient_rotation(45 * DEG)
        self.wait(8)
        self.frame.clear_updaters()
        self.wait(1)
        self.play(*[FadeOut(m) for m in self.mobjects])


class SpiralSteinerFlow(Scene):
    """(w+1)/(w-1) = λ (z+1)/(z-1)，λ = 2e^{iπ/3}：Steiner 圆系的螺旋流动。"""

    def construct(self):
        plane = ComplexPlane(
            x_range=(-8, 8, 1), y_range=(-4, 4, 1),
            background_line_style=dict(stroke_color=BLUE, stroke_width=1),
            faded_line_style=dict(stroke_color=BLUE, stroke_width=0.5, stroke_opacity=0.5),
            faded_line_ratio=1,
        )
        self.add(plane)

        z1, z2 = -1 + 0j, 1 + 0j
        rs = [1/11, 1/5, 1/3, 1/2, 1/1.4, 1, 1.4, 2, 3, 5, 11]
        thetas = [i * PI / 6 for i in range(12)]

        
        def label_gen(r, theta):
            return Tex(
                rf"\frac{{w+1}}{{w-1}}={r}e^{{i {theta}}} \frac{{z+1}}{{z-1}}",
                t2c = {r:TEAL, theta:GREEN}
            )
        label = label_gen("2", r"\pi/3")
        label.to_corner(UR)


        p = GlowDot(color=YELLOW, radius=0.09, glow_factor=0.5)
        p.move_to(plane.c2p(0.5, 0))

        circles = steiner(z1, z2, rs, thetas)   # 圆 TEAL、弧 GREEN（函数默认）
        r_group, t_group = circles
        self.play(FadeIn(circles), FadeIn(label), FadeIn(p), run_time=1.5)
        self.wait(0.5)

        modulus = ValueTracker(1.0)    # |λ|
        argument = ValueTracker(0.0)   # arg λ

        def mobius_image(z0, lam):
            return ((lam + 1) * z0 + (lam - 1)) / ((lam - 1) * z0 + (lam + 1))


        # updaters
        def track_p(m, dt=None):
            lam = modulus.get_value() * np.exp(1j * argument.get_value())
            w = mobius_image(0.5 + 0j, lam)
            m.move_to(plane.c2p(w.real, w.imag))
        p.add_updater(track_p)

        # r-圆 -> |λ|r-圆；θ-弧 -> (θ+argλ)-弧
        for circle, r in zip(r_group, rs):
            circle.add_updater(lambda m, dt=None, r=r: m.become(
                steiner_r_circle(z1, z2, r * modulus.get_value(), color=TEAL)))
        for arc, th in zip(t_group, thetas):
            arc.add_updater(lambda m, dt=None, th=th: m.become(
                steiner_t_arc(z1, z2, th + argument.get_value(), color=GREEN)))

        # Phase A：λ 从 1（恒等、圆系静止）流动到 2e^{iπ/3}（边胀边旋）
        self.play(
            modulus.animate.set_value(2.0),
            argument.animate.set_value(PI / 3),
            run_time=4, rate_func=smooth,
        )
        self.wait(0.5)

        label1 = label_gen("2.00", r"1.05").to_corner(UR)
        self.play(
            TransformMatchingTex(
                label, label1, 
                key_map = {"2":"2.00", "\pi/3":"1.05"}
            ),
            run_time = 0.8
        )
        # tex updater
        def sync(tex, dt=None):
            new_label = label_gen(f"{modulus.get_value():.2f}", f"{argument.get_value():.2f}")
            tex.become(new_label.to_corner(UR))
        label1.add_updater(sync)


        # Phase B：|λ|: 2.00 -> 3.00 -> 2.00
        self.play(modulus.animate.set_value(4.0), run_time=2.5, rate_func=smooth)
        self.play(modulus.animate.set_value(2.0), run_time=2, rate_func=smooth)

        # Phase C：arg λ: 1.05 -> 2.00
        self.play(argument.animate.set_value(2.0), run_time=2.5, rate_func=smooth)
        self.wait(0.5)
        self.play(*[FadeOut(m) for m in self.mobjects])

def im_inv_circle(v, color=GREEN):
    """Im(ω/z) = v（ω = ρe^{iα}）：过 0、切向 α 的圆；|ω| 放大 => 标定圆绕 0 缩放 ρ。"""
    if abs(v) < 1e-9:
        return Line(LEFT * 8, RIGHT * 8, color=color)
    cc = 0.5j / v    # 圆心 = ρe^{iα}·(-i/2v)
    return Circle(radius=abs(0.5 / v), stroke_color=color).move_to(_c2p(cc))

def re_inv_circle(u, color=TEAL):
    """Re(ω/z) = u（ω = ρe^{iα}）：过 0、切向 α+π/2 的圆。"""
    if abs(u) < 1e-9:
        return Line(DOWN * 4, UP * 4, color=color)
    cc = 0.5 / u
    return Circle(radius=abs(0.5 / u), stroke_color=color).move_to(_c2p(cc))

def parabolic_coef_label(c_tex, scale=0.9):
    """参数 c（GREEN）。独立 Tex + {} 包裹，t2c 选择子不可能串扰。"""
    return Tex(rf"{{{c_tex}}}", t2c={rf"{{{c_tex}}}": GREEN},
               fill_color=WHITE, stroke_color=WHITE).scale(scale)

def omega_badge(rho_tex, alpha_tex, scale=0.8):
    """ω = ρe^{iα}：ρ、α 均 TEAL（两个选择子取值永不相同，无串扰）。"""
    s = rf"\omega={rho_tex}e^{{i{alpha_tex}}}"
    return Tex(s, t2c={rho_tex: TEAL, alpha_tex: TEAL},
               fill_color=WHITE, stroke_color=WHITE).scale(scale)


class ParabolicSteinerFlow(Scene):
    """抛物型 ω/(w-a) = ω/(z-a) + c（a=0, ω=ρe^{iα}, c∈R）四段演示：
    A: c 抛物流；B: c 计数胀缩；C: arg ω 旋转圆系；D: |ω| 涨缩标定圆系。"""

    def construct(self):
        plane = ComplexPlane(
            x_range=(-8, 8, 1), y_range=(-4, 4, 1),
            background_line_style=dict(stroke_color=BLUE, stroke_width=1),
            faded_line_style=dict(stroke_color=BLUE, stroke_width=0.5, stroke_opacity=0.5),
            faded_line_ratio=1,
        )
        self.add(plane)

        # 标签 = 左式 + 独立参数块（右缘锚定）
        # label = Wh(r"\frac{1}{w}=\frac{1}{z}+c")
        # coef = parabolic_coef_label("c")
        # VGroup(left, coef).arrange(RIGHT, buff=0).to_corner(UR)
        # right_edge_x = VGroup(left, coef).get_right()[0]
        # coef_y = coef.get_center()[1]

        def label_gen(omega, c):
            return Tex(
                rf"\frac{1}{{w}}=\frac{1}{{z}}+{c}",
                t2c = {c:TEAL}                
            )
        label = label_gen("1", "2").to_corner(UR)

        fixed = GlowDot(color=RED, radius=0.07, glow_factor=0.8)
        a_lab = Wh("a").scale(0.7).next_to(fixed, DR, buff=0.1)

        params = [-2, -1, -0.5, -0.25, 0.25, 0.5, 1, 2]
        c1_group = VGroup(*[im_inv_circle(v, color=GREEN) for v in params])
        c2_group = VGroup(*[re_inv_circle(u, color=TEAL) for u in params])

        z0 = 0.5 + 0.5j
        p = GlowDot(color=YELLOW, radius=0.09, glow_factor=0.5)
        p.move_to(plane.c2p(z0.real, z0.imag))

        self.play(FadeIn(c1_group), FadeIn(c2_group), FadeIn(label),
                  FadeIn(fixed), FadeIn(a_lab), FadeIn(p), run_time=1.5)
        self.wait(0.5)

        # c = x + iy
        x = ValueTracker(0.0)       
        y = ValueTracker(0.0)  

        # w = z0 / (1 + (c)·z0)
        def track_p(m, dt=None):
            w = z0 / (1.0 + (x.get_value() + 1j * y.get_value()) * z0)
            m.move_to(plane.c2p(w.real, w.imag))
        p.add_updater(track_p)

        for circle, v in zip(c1_group, params):
            circle.add_updater(lambda m, dt=None, v=v: m.become(
                im_inv_circle(v - y.get_value(), color=GREEN)))
        for circle, u in zip(c2_group, params):
            circle.add_updater(lambda m, dt=None, u=u: m.become(
                re_inv_circle(u + x.get_value(), color=TEAL)))

        # ---- Phase A：c: 0 -> 2 ----
        self.play(x.animate.set_value(2.0), run_time=4, rate_func=smooth)
        self.wait(0.5)

        label1 = label_gen("1","2.00 + 0.00 i").to_corner(UR)
        self.play(
            TransformMatchingTex(
                label, label1, 
                key_map = {"2":"2.00 + 0.00 i"}
            ),
            run_time = 0.8
        )
        
        def label_update(tex, dt=None):
            new_label = label_gen("1", rf"{x.get_value():.2f}+{y.get_value():.2f}i")
            tex.become(new_label.to_corner(UR))
        label1.add_updater(label_update)

        # ---- Phase B：c: 2.00 -> 0.00 ----
        self.play(x.animate.set_value(0.0), run_time=2.5, rate_func=smooth)
        self.play(y.animate.set_value(1.0), x.animate.set_value(1.0), 
            run_time=3, rate_func=smooth
        )
        self.wait()

        self.play(*[FadeOut(m) for m in self.mobjects])


class InversionDemo(Scene):
    def construct(self):
        plane = ComplexPlane((-3,3), (-3,3)).scale(1.5)
        plane.add_coordinate_labels().scale(0.6)
        tex = Tex(r"w=\frac1z")
        tex.to_corner(UL, buff = MED_LARGE_BUFF)
        wtex = VGroup(Tex("w").set_color(GOLD).set_stroke(BLACK, width=4),
            Tex("w").set_color(GOLD).set_stroke(BLACK)
        )
        ztex = VGroup(Tex("z").set_color(YELLOW).set_stroke(BLACK, width=4),
            Tex("z").set_color(YELLOW).set_stroke(BLACK)
        )
        w = GlowDot(color=GOLD, radius=0.09, glow_factor=0.5)
        z = GlowDot(color=YELLOW, radius=0.09, glow_factor=0.5)
        w.move_to(plane.n2p(1))
        z.move_to(plane.n2p(1))
        wtex.add_updater(
            lambda x: x.next_to(w, UR, buff = SMALL_BUFF)
        )
        ztex.add_updater(
            lambda x: x.next_to(z, DR, buff = SMALL_BUFF)
        )
        unit_circle = Circle(
            radius=plane.n2p(1j)[1] - plane.n2p(0)[1],
            stroke_color=WHITE,
        ).move_to(plane.n2p(0))

        self.play(Write(tex))
        self.play(ShowCreation(plane), run_time = 2, rate_func = smooth)
        self.play(ShowCreation(unit_circle))
        self.wait()
        self.play(FadeIn(w), FadeIn(z), FadeIn(wtex), FadeIn(ztex))
        self.wait()
        t = ValueTracker(0.0)
        z.add_updater(
            lambda x: x.move_to(plane.n2p(1 + 0.5*t.get_value() + 1j*t.get_value()))
        )
        w.add_updater(
            lambda x: x.move_to(plane.n2p(1/(1 + 0.5*t.get_value() + 1j*t.get_value())))
        )
        self.play(t.animate.set_value(2.0), run_time=2)

        z.clear_updaters()
        w.clear_updaters()
        t.set_value(0.0)
        z.add_updater(
            lambda x: x.move_to(plane.n2p(2+2j-1j*t.get_value()))
        )
        w.add_updater(
            lambda x: x.move_to(plane.n2p(1/(2+2j-1j*t.get_value())))
        )
        self.play(t.animate.set_value(3.0), run_time=2)

        z.clear_updaters()
        w.clear_updaters()
        t.set_value(0.0)
        z.add_updater(
            lambda x: x.move_to(plane.n2p((2-1j)*np.exp(-1j * t.get_value())))
        )
        w.add_updater(
            lambda x: x.move_to(plane.n2p(np.exp(1j * t.get_value())/(2-1j)))
        )
        self.play(t.animate.set_value(2.5), run_time=2)

        z.clear_updaters()
        w.clear_updaters()
        t.set_value(1.0)
        z.add_updater(
            lambda x: x.move_to(plane.n2p((2-1j)*np.exp(-1j * 2.5))/t.get_value())
        )
        w.add_updater(
            lambda x: x.move_to(plane.n2p(np.exp(1j * 2.5)*t.get_value()/(2-1j)))
        )
        self.play(t.animate.set_value(3.0), run_time=2)
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects])

# -------------------------- texts --------------------------
CN_FONT = "Noto Serif SC"

def CText(s, t2c=None):
    return (Text(s, font=CN_FONT, t2c=t2c) if t2c else Text(s, font=CN_FONT)) if CN_FONT else Text(s)


class FLTParts(InteractiveScene):
    """所有镜头的动画都写成 part_2x() 方法，供单场景类和 Scene2All 复用。
    每个 part 结尾都把画面清空（全体 FadeOut），合并渲染时即自然转场。"""

    def part1(self):
        """镜头1：反演 w = 1/z，|OP'| = R^2/|OP|（FadeIn / FadeOut）"""
        title = VGroup(Tex(R"w=\frac{1}{z}"), CText("反演")).arrange(RIGHT, buff=0.6)
        title.to_edge(UP)

        R = 2.2
        circle = Circle(radius=R, color=WHITE)
        center_dot = Dot(ORIGIN)
        o_label = Tex("O").next_to(center_dot, DL, buff=0.12)

        radius_line = Line(ORIGIN, R * DOWN, stroke_color=YELLOW, stroke_width=3)
        r_label = Tex("R", color=YELLOW).next_to(radius_line, RIGHT, buff=0.08)

        # 外部点 P 与反演点 P'（P' = R^2 / |OP|^2 * P）
        theta = 20 * DEG
        p = 4.4 * np.array([np.cos(theta), np.sin(theta), 0])
        p_prime = (R**2 / np.linalg.norm(p)**2) * p
        ray = Arrow(ORIGIN, p, buff=0, stroke_color=GREY_A)
        p_dot = Dot(p, color=RED)
        p_label = Tex("P", color=RED).next_to(p_dot, UR, buff=0.08)
        pp_dot = Dot(p_prime, color=GREEN)
        pp_label = Tex(R"P'", color=GREEN).next_to(pp_dot, UP, buff=0.1)

        formula = Tex(R"|OP'|=\frac{R^2}{|OP|}").to_edge(DOWN)

        self.wait()
        self.play(FadeIn(title[0]))
        self.wait(0.8)
        self.play(FadeIn(title[1]))
        self.wait(2)
        self.play(ShowCreation(circle), FadeIn(center_dot), FadeIn(o_label), ShowCreation(radius_line), FadeIn(r_label))
        self.play(FadeIn(ray), FadeIn(p_dot), FadeIn(p_label), FadeIn(pp_dot), FadeIn(pp_label))
        self.play(FadeIn(formula))
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part2(self):
        t2c = {"{a}": RED, "{b}": BLUE, "{c}": YELLOW, "{d}": GREEN}

        line1 = CText("分式线性变换")
        line2 = CText("fractional linear transformation")
        line3a = Tex(R"w=\frac{{a}z+{b}}{{c}z+{d}}", t2c=t2c)
        line3b = Tex(R"{a}{d}-{b}{c}\neq 0", t2c=t2c)
        line3 = VGroup(line3a, line3b).arrange(RIGHT, buff=LARGE_BUFF)

        line4a = Tex(R"({c},{d})=(0,1)", t2c=t2c)
        line4b = Tex(R"w=\frac{{{a}z+{b}}}{0\cdot z+1}", t2c=t2c)
        line4 = VGroup(line4a, line4b).arrange(RIGHT, buff=LARGE_BUFF)
        line4b_simplif = Tex(R"w={{a}z+{b}}", t2c=t2c)          # 只创建，先不对位

        line5a = Tex(R"({a},{b},{c},{d})=(0,1,1,0)", t2c=t2c)
        line5b = Tex(R"w=\frac{0\cdot z+1}{1\cdot z+0}", t2c=t2c)
        line5 = VGroup(line5a, line5b).arrange(RIGHT, buff=LARGE_BUFF)
        line5b_simplif = Tex(R"w=\frac{1}{z}", t2c=t2c)   # 只创建，先不对位

        lines = VGroup(line1, line2, line3, line4, line5).arrange(DOWN).to_edge(UP)
        line4b_simplif.move_to(line4b)                    # 排版定型后再对位
        line5b_simplif.move_to(line5b).shift(0.5 * LEFT)

        self.play(Write(line1), Write(line2))
        self.wait(2)
        self.play(Write(line3))
        self.wait(2)

        # 代入 (c,d) = (0,1)
        self.play(Write(line4a))
        self.play(TransformMatchingTex(line3a.copy(), line4b))  # TransformMatchingTex keeps the latter object
        self.play(
            Transform(line4b[2:6].copy(), line4b_simplif[2:6].copy(), remover=True),
            Transform(line4b[0:2].copy(), line4b_simplif[0:2].copy(), remover=True),
            FadeOut(line4b, time_span = (0, 0.3)),
            FadeIn(line4b_simplif, time_span = (0.7, 1))
        )
        self.wait(2)

        # 代入 (a,b,c,d) = (0,1,1,0)
        self.play(Write(line5a))
        self.add(line3a.copy())
        self.play(Transform(line3a, line5b))          # 原公式飞到第5行变成 (0z+1)/(1z+0)
        self.play(
            Transform(line5b[6].copy(), line5b_simplif[2].copy(), remover=True),
            Transform(line5b[0:2].copy(), line5b_simplif[0:2].copy(), remover=True),
            Transform(line5b[10].copy(), line5b_simplif[-1].copy(), remover=True),
            Transform(line5b[7].copy(), line5b_simplif[-2].copy(), remover=True),
            FadeOut(line3a, time_span = (0, 0.3)),
            FadeIn(line5b_simplif, time_span = (0.7, 1))
        )  # 同位置继续化简成 1/z
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part3(self):
        t2c = {
            "S_1": TEAL,
            "a_1": TEAL,
            "b_1": TEAL,
            "c_1": TEAL,
            "d_1": TEAL,
            "S_2": TEAL_A,
            "a_2": TEAL_A,
            "b_2": TEAL_A,
            "c_2": TEAL_A,
            "d_2": TEAL_A,
        }
        line1 = CText("1. 分式线性变换的复合是分式线性变换")
        line2a = Tex("w=")
        line2b = Tex(r"\frac{{a}z+{b}}{{c}z+{d}}")
        line2a1 = Tex(r"\frac{w_1}{w_2}=")
        line2b1 = Tex(r"\frac{{a}\frac{z_1}{z_2}+{b}}{{c}\frac{z_1}{z_2}+{d}}")
        line2b2 = Tex(r"\frac{{a}z_1+{b}z_2}{{c}z_1+{d}z_2}")
        line3_subsa = Tex(
            r"w=\frac{w_1}{w_2}"
        )
        line3_subsb = Tex(
            r"z=\frac{z_1}{z_2}"
        )
        line3_subs_sup = CText("齐次坐标（不唯一）").scale(0.6).set_color(TEAL)
        line3a = CText("令")
        line3b_pre = VGroup(
            Tex("w_1=az_1+bz_2"),
            Tex("w_2=cz_1+dz_2")
        ).arrange(DOWN, buff = MED_SMALL_BUFF)
        line3_sup = CText("（反正不唯一）").scale(0.6).set_color(TEAL)
        line3b = Tex(
            R"\begin{pmatrix} w_1 \\ w_2 \end{pmatrix}"
            R"=\begin{pmatrix} {a} & {b} \\ {c} & {d} \end{pmatrix}"
            R"\begin{pmatrix} z_1 \\ z_2 \end{pmatrix}"
        )
        line4a = CText("记")
        line4b = Tex(r"S_1z=\frac{{a_1}z+{b_1}}{{c_1}z+{d_1}}", t2c = t2c)
        line4c = Tex(r"S_2z=\frac{{a_2}z+{b_2}}{{c_2}z+{d_2}}", t2c = t2c)
        line4 = VGroup(line4a, line4b, line4c).arrange(RIGHT)
        line5 = Tex("w = S_1S_2z", t2c = t2c)
        line6 = Tex(
            R"\begin{pmatrix} w_1 \\ w_2 \end{pmatrix}"
            R"=\begin{pmatrix} {a_1} & {b_1} \\ {c_1} & {d_1} \end{pmatrix}"
            R"\begin{pmatrix} (S_2z)_1 \\ (S_2z)_2 \end{pmatrix}",
            t2c = t2c
        )
        line6_full = Tex(
            R"\begin{pmatrix} w_1 \\ w_2 \end{pmatrix}"
            R"=\begin{pmatrix} {a_1} & {b_1} \\ {c_1} & {d_1} \end{pmatrix}"
            R"\begin{pmatrix} {a_2} & {b_2} \\ {c_2} & {d_2} \end{pmatrix}"
            R"\begin{pmatrix} z_1 \\ z_2 \end{pmatrix}",
            t2c = t2c
        )
        line7 = Tex(
            R"\begin{pmatrix} w_1 \\ w_2 \end{pmatrix}"
            R"=\begin{pmatrix} {a_1a_2+b_1c_2} & {a_1b_2+b_1d_2} \\ {c_1a_2+d_1c_2} & {c_1b_2+d_1d_2} \end{pmatrix}"
            R"\begin{pmatrix} z_1 \\ z_2 \end{pmatrix}",
            t2c = t2c
        )
        line8 = Tex(r"w=\frac{{(a_1a_2+b_1c_2)}z+{(a_1b_2+b_1d_2)}}{{(c_1a_2+d_1c_2)}z+{(c_1b_2+d_1d_2)}}", t2c=t2c)
        line2 = VGroup(line2a, line2b).arrange(RIGHT)
        line3 = VGroup(line3a, line3b).arrange(RIGHT)
        line3b_pre.move_to(line3b.get_center()).shift(0.35 * DOWN)
        lines = VGroup(line1, line2, line3, line5).arrange(DOWN, buff = MED_LARGE_BUFF).move_to(0.5 * UP)
        line2_1 = VGroup(line2a1, line2b1).arrange(RIGHT).next_to(line1, DOWN, buff=MED_LARGE_BUFF)
        line2_2 = VGroup(line2a1, line2b2).arrange(RIGHT).next_to(line1, DOWN, buff=MED_LARGE_BUFF)
        line3_subs = VGroup(line3_subsa, line3_subsb).arrange(RIGHT, buff=LARGE_BUFF).next_to(line2, DOWN, buff=MED_LARGE_BUFF)
        line3_sup.next_to(line3, RIGHT, buff = MED_SMALL_BUFF)
        line3_subs_sup.next_to(line3_subs, RIGHT, buff = MED_SMALL_BUFF)
        
        

        self.play(Write(line1))
        self.wait()
        self.play(Write(line2))
        self.wait()
        self.play(FadeIn(line3_subs))
        self.wait(0.5)
        self.play(FadeIn(line3_subs_sup))
        self.wait()
        self.play(
            TransformMatchingTex(
                line2a, line2a1,
                key_map = {"w": r"\frac{w_1}{w_2}"}
            ),
            TransformMatchingTex(
                line2b, line2b1,
                key_map = {"z": r"\frac{z_1}{z_2}"}
            )
        )
        self.play(
            Transform(line2b1[0].copy(), line2b2[0].copy(), remover=True),
            Transform(line2b1[1:3].copy(), line2b2[1:3].copy(), remover=True),
            Transform(line2b1[4:6].copy(), line2b2[5:7].copy(), remover=True),
            Transform(line2b1[6:8].copy(), line2b2[3:5].copy(), remover=True),
            Transform(line2b1[9].copy(), line2b2[9].copy(), remover=True),
            Transform(line2b1[10:12].copy(), line2b2[10:12].copy(), remover=True),
            Transform(line2b1[13:15].copy(), line2b2[13:15].copy(), remover=True),
            Transform(line2b1[15:17].copy(), line2b2[12:14].copy(), remover=True),
            FadeIn(line2b2, time_span=(0.25, 1)),
            FadeOut(line2b1, time_span=(0, 0.75)),
            FadeOut(line3_subs),
            FadeOut(line3_subs_sup)
        )
        self.wait(0.5)
        self.play(FadeIn(line3a), FadeIn(line3b_pre))
        self.wait(0.5)
        self.play(FadeIn(line3_sup))
        self.wait()
        self.play(
            FadeOut(line3_sup),
            Transform(line3b_pre[0][0:2].copy(), line3b[1:3].copy(), remover=True),
            Transform(line3b_pre[1][0:2].copy(), line3b[3:5].copy(), remover=True),
            Transform(line3b_pre[0][4:6].copy(), line3b[14:16].copy(), remover=True),
            Transform(line3b_pre[0][7:9].copy(), line3b[16:18].copy(), remover=True),
            Transform(line3b_pre[0][3].copy(), line3b[8].copy(), remover=True),
            Transform(line3b_pre[0][7].copy(), line3b[9].copy(), remover=True),
            Transform(line3b_pre[1][3].copy(), line3b[10].copy(), remover=True),
            Transform(line3b_pre[1][7].copy(), line3b[11].copy(), remover=True),
            FadeOut(line3b_pre, time_span = (0, 0.3)),
            FadeIn(line3b, time_span = (0.7, 1))
        )
        self.play(
            FadeOut(line2_2),
            line3.animate.next_to(line1, DOWN, buff = MED_LARGE_BUFF)
        )
        line4.next_to(line3, DOWN, buff = MED_LARGE_BUFF)
        s1z_rect = SurroundingRectangle(line4b["S_1z"], buff = SMALL_BUFF)
        s1z_words = VGroup(Text("also").scale(0.9), Tex("S_1(z)")).arrange(RIGHT, buff = 2 * SMALL_BUFF).scale(0.7)
        VGroup(s1z_rect, s1z_words).set_color(TEAL)
        s1z_words.next_to(s1z_rect, DOWN, 2 * SMALL_BUFF)

        self.play(
            LaggedStart(
                Write(line4), Write(line5),
                lag_ratio=0.3,
                run_time = 1.8))
        self.wait()

        line6.next_to(line4, DOWN, buff = MED_LARGE_BUFF) 
        line6_full.next_to(line4, DOWN, buff = MED_LARGE_BUFF) 
        line7.next_to(line4, DOWN, buff = MED_LARGE_BUFF) 
        line8.next_to(line4, DOWN, buff = MED_LARGE_BUFF) 
        self.play(
            Transform(line5["S_2z"][0].copy().replicate(2), VGroup(*[line6[i] for i in [19,20,21,25,26,27]].copy()), path_arc=0, remover=True),
            Transform(line5["w"][0].copy().replicate(2), line6[1:5].copy(), path_arc=0, remover=True),
            Transform(line5["S_1"][0].copy().replicate(2), line6[7:17].copy(), remover=True),
            FadeIn(line6, time_span=(0.25, 1)),
            FadeOut(line5)
        )
        self.wait()
        self.play(
            Transform(VGroup(*line6[0:18].copy()), VGroup(*line6_full[0:18].copy()), remover=True),
            Transform(line6[-1].copy(), line6_full[-1].copy(), remover=True),
            Transform(VGroup(*line6[18:-1].copy()), VGroup(*line6_full[18:-1].copy()), remover=True),
            FadeOut(line6, time_span=(0, 0.00001)),
            FadeIn(line6_full, time_span=(0.99999, 1))
        )
        self.wait()
        self.play(LaggedStart(
            ShowCreation(s1z_rect),
            FadeIn(s1z_words, lag_ratio=0.1),
        ))
        self.wait()
        self.play(
            FadeOut(s1z_rect), FadeOut(s1z_words)
        )
        self.wait()
        self.play(
            Transform(VGroup(*line6_full[0:8].copy()), VGroup(*line7[0:8].copy()), remover=True),
            Transform(VGroup(*line6_full[8:10].copy().replicate(2)), VGroup(*[line7[i] for i in [8,9,17,18]].copy()), remover=True),
            Transform(VGroup(*line6_full[10:12].copy().replicate(2)), VGroup(*[line7[i] for i in [13,14,22,23]].copy()), remover=True),
            Transform(VGroup(*line6_full[12:14].copy().replicate(2)), VGroup(*[line7[i] for i in [26,27,35,36]].copy()), remover=True),
            Transform(VGroup(*line6_full[14:16].copy().replicate(2)), VGroup(*[line7[i] for i in [31,32,40,41]].copy()), remover=True),
            Transform(VGroup(*line6_full[18:20].copy().replicate(2)), VGroup(*[line7[i] for i in [10,11,28,29]].copy()), remover=True),
            Transform(VGroup(*line6_full[20:22].copy().replicate(2)), VGroup(*[line7[i] for i in [19,20,37,38]].copy()), remover=True),
            Transform(VGroup(*line6_full[22:24].copy().replicate(2)), VGroup(*[line7[i] for i in [15,16,33,34]].copy()), remover=True),
            Transform(VGroup(*line6_full[24:26].copy().replicate(2)), VGroup(*[line7[i] for i in [24,25,42,43]].copy()), remover=True),
            Transform(VGroup(*line6_full[-7:].copy()), VGroup(*line7[-7:].copy()), remover=True),
            FadeOut(line6_full, time_span=(0, 0.3)),
            FadeIn(line7, time_span=(0.7, 1))
            
        )
        # self.add(show_tex_indices(line7))
        self.wait()
        self.play(
            Transform(VGroup(line7[1].copy()), VGroup(line8[0].copy()), remover=True),
            Transform(VGroup(*line7[8:17].copy()), VGroup(*line8[3:12].copy()), remover=True),
            Transform(VGroup(*line7[17:26].copy()), VGroup(*line8[16:25].copy()), remover=True),
            Transform(VGroup(*line7[26:35].copy()), VGroup(*line8[28:37].copy()), remover=True),
            Transform(VGroup(*line7[35:44].copy()), VGroup(*line8[41:50].copy()), remover=True),
            Transform(VGroup(line7[46].copy()), VGroup(line8[13].copy()), remover=True),
            Transform(VGroup(line7[48].copy()), VGroup(line8[38].copy()), remover=True),
            FadeOut(line7, time_span=(0, 0.3)),
            FadeIn(line8, time_span=(0.7, 1))
        )
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part4(self):
        line1 = CText("2. 所有分式线性变换都有逆变换")
        line2a = CText("注意到")
        line2b = Tex(
            R"\begin{pmatrix} a & b \\ c & d \end{pmatrix}"
            R"=\begin{pmatrix} d & -b \\ -c & a \end{pmatrix}"
            R"=\begin{pmatrix} ad-cb & 0 \\ 0 & ad-cb \end{pmatrix}"
        )
        line2 = VGroup(line2a, line2b).arrange(RIGHT, buff = MED_LARGE_BUFF)
        line3a = CText("表示的变换恰好是")
        line3b = Tex(r"w=\frac{(ad-cb)z}{(ad-cb)}")
        line3b1 = Tex(r"w=z")
        line3 = VGroup(line3a, line3b).arrange(RIGHT, buff = MED_LARGE_BUFF)
        line4a = CText("故")
        line4b = Tex(r"S(z)=\frac{{a}z+{b}}{{c}z+{d}} \Rightarrow S^{-1}(z)=\frac{{d}z-{b}}{-{c}z+{a}}")
        line4 = VGroup(line4a, line4b).arrange(RIGHT, buff = MED_LARGE_BUFF)
        line5a = Tex(r"S(-\frac{d}{c})\to\infty")
        line5b = Tex(r"S(\infty)\to\frac{a}{c}")
        line5c = CText("在极限意义上成立")
        line5 = VGroup(line5a, line5b, line5c).arrange(RIGHT, buff = MED_LARGE_BUFF)
        line6 = Tex()
        line7 = CText("一一到上，连续，有连续逆映射")
        line8 = CText("3. 分式线性变换是复平面到自身的同胚映射")

        lines = VGroup(line1, line2, line3, line4).arrange(DOWN, buff = MED_LARGE_BUFF).shift(0.5 * UP)



        self.play(Write(line1))
        self.wait()
        self.play(Write(line2), run_time=2)
        self.wait()
        self.play(Write(line3))
        self.wait(0.4)
        line3b1.move_to(line3b)
        self.play(
            Transform(VGroup(*line3b[0:2].copy()), VGroup(*line3b1[0:2].copy()), remover=True),
            Transform(VGroup(line3b[9].copy()), VGroup(line3b1[-1].copy()), remover=True),
            FadeOut(line3b, time_span=(0, 0.5)),
            FadeIn(line3b1, time_span=(0.99, 1))
        )
        self.wait()
        self.play(Write(line4))
        self.wait()
        self.play(
            line4.animate.next_to(line1, DOWN, buff = MED_LARGE_BUFF),
            FadeOut(line2),
            FadeOut(line3a),
            FadeOut(line3b1)
        )
        self.wait()

        line5.next_to(line4, DOWN, buff = MED_LARGE_BUFF)
        line7.next_to(line5, DOWN, buff = MED_LARGE_BUFF)
        line8.next_to(line5, DOWN, buff = LARGE_BUFF)
        self.play(Write(line5))
        self.wait()
        self.play(Write(line7["一一到上，"]))
        self.wait(0.5)
        self.play(Write(line7["连续，"]))
        self.wait(0.5)
        self.play(Write(line7["有连续逆映射"]))
        self.wait(2)
        self.play(
            Transform(line7, line8)
        )
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part5(self):
        t2c = {"{a}": RED, "{b}": BLUE, "{c}": YELLOW, "{d}": GREEN}
        line1 = CText("4. 分式线性变换的部分分式展开")
        line2 = Tex(r"w = \frac{{a}z+{b}}{{c}z+{d}}", t2c = t2c).scale(1.5)
        line3 = Tex(r"w = \frac{{a}z+\frac{{a}{d}}{{c}}+{b}-\frac{{a}{d}}{{c}}}{{c}z+{d}}", t2c = t2c).scale(1.5)
        line4 = Tex(r"w = \frac{{a}}{{c}}+\frac{{b}{c}-{a}{d}}{{c}({c}z+{d})}", t2c = t2c).scale(1.5)
        line5 = Tex(r"w = \frac{{a}}{{c}}+\frac{{b}{c}-{a}{d}}{{c}^2(z+\frac{{d}}{{c}})}", t2c = t2c).scale(1.5)
        line6 = Tex(r"w = \frac{{a}}{{c}}+\frac{{b}{c}-{a}{d}}{{c}^2} \frac{1}{z+\frac{{d}}{{c}}}", t2c = t2c).scale(1.5)
        line1.shift(3 * UP)

        self.play(Write(line1))
        self.play(Write(line2))
        self.wait()
        self.play(
            Transform(line2[5].copy(), line3[10].copy(), remover=True),
            Transform(line2[0:4].copy(), line3[0:4].copy(), remover=True),
            Transform(line2[-5:].copy(), line3[-5:].copy(), remover=True),
            FadeIn(line3, time_span=(0.25, 1)),
            FadeOut(line2, time_span=(0, 0.75)),
        )
        self.wait()
        self.play(
            Transform(line3[2:10].copy(), line4[2].copy(), remover=True),
            Transform(line3[0:2].copy(), line4[0:2].copy(), remover=True),
            Transform(line3[-5:].copy(), line4[-5:].copy(), remover=True),
            Transform(line3[-5:].copy(), line4[4].copy(), remover=True),
            Transform(line3[10].copy(), line4[6].copy(), remover=True),
            Transform(line3[15].copy(), line4[7].copy(), remover=True),
            Transform(line3[12:14].copy(), line4[9:11].copy(), remover=True),
            FadeIn(line4, time_span=(0.25, 1)),
            FadeOut(line3, time_span=(0, 0.75)),
        )
        self.wait()
        self.play(
            Transform(line4[0:13].copy(), line5[0:13].copy(), remover=True),
            Transform(line4[13].copy(), line5[14].copy(), remover=True),
            Transform(line4[14].copy(), line5[19].copy(), remover=True),
            Transform(line4[15:18].copy(), line5[15:18].copy(), remover=True),
            Transform(line4[-1].copy(), line5[-1].copy(), remover=True),
            FadeIn(line5, time_span=(0.25, 1)),
            FadeOut(line4, time_span=(0, 0.75)),
        )
        self.wait()
        self.play(
            Transform(line5[0:14].copy(), line6[0:14].copy(), remover=True),
            Transform(line5[-6:-1].copy(), line6[-5:].copy(), remover=True),
            FadeIn(line6, time_span=(0.25, 1)),
            FadeOut(line5, time_span=(0, 0.75)),
        )
        self.wait(0.8)
        self.play(line6.animate.set_color(WHITE))
        self.wait()

        shift1_rect = SurroundingRectangle(line6[r"z+\frac{{d}}{{c}}"], buff = 0)
        shift1_words = CText("平移").scale(0.8).next_to(shift1_rect, DOWN, buff=SMALL_BUFF)
        inv_rect = SurroundingRectangle(line6[r"\frac{1}{z+\frac{{d}}{{c}}}"], buff = 0.05)
        inv_words = CText("反演").scale(0.8).next_to(inv_rect, UP, buff=SMALL_BUFF)
        mult_rect = SurroundingRectangle(line6[r"\frac{{b}{c}-{a}{d}}{{c}^2}"])
        mult_words = CText("缩放+旋转").scale(0.8).next_to(mult_rect, DOWN, buff=SMALL_BUFF)
        shift2_rect = SurroundingRectangle(line6[r"\frac{{a}}{{c}}"], buff=SMALL_BUFF)
        shift2_words = CText("平移").scale(0.8).next_to(shift2_rect, DOWN, buff=SMALL_BUFF)
        VGroup(shift1_words, shift1_rect, shift2_words, shift2_rect).set_color(TEAL_E)
        VGroup(inv_words, inv_rect).set_color(TEAL_A)
        VGroup(mult_words, mult_rect).set_color(TEAL_B)
        self.play(LaggedStart(
            line6[r"z+\frac{{d}}{{c}}"].animate.set_color(TEAL_E),
            FadeIn(shift1_words, lag_ratio=0.1),
        ))
        self.wait()
        self.play(LaggedStart(
            ShowCreation(inv_rect),
            FadeIn(inv_words, lag_ratio=0.1),
        ))
        self.wait()
        self.play(LaggedStart(
            line6[r"\frac{{b}{c}-{a}{d}}{{c}^2}"].animate.set_color(TEAL_B),
            FadeIn(mult_words, lag_ratio=0.1),
        ))
        self.wait()
        self.play(LaggedStart(
            ShowCreation(shift2_rect),
            FadeIn(shift2_words, lag_ratio=0.1),
        ))
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects])
    
    def part6(self):
        line1 = CText("5. 分式线性变换具有保圆性")
        line2 = CText("广义圆：直线也是一种圆")
        line3 = VGroup(
            CText("变换前的圆"),
            Tex(r"\rightarrow"),
            CText("任意四点交比为实数")
        ).arrange(RIGHT, buff=MED_SMALL_BUFF).scale(0.8)
        line4 = Tex(r"\downarrow").scale(0.8)
        line5 = VGroup(
            CText("变换后还是圆"),
            Tex(r"\leftarrow"),
            CText("变换后任意四点交比仍为实数")
        ).arrange(RIGHT, buff=MED_SMALL_BUFF).scale(0.8)
        lines = VGroup(line1, line2, line3, line4, line5).arrange(DOWN, buff=MED_SMALL_BUFF)
        VGroup(line1, line2).shift(UP)
        line4.shift(1.6*RIGHT)
        self.play(Write(line1))
        self.play(Write(line2))
        self.wait(2)
        for item in line3:
            self.play(Write(item))
            self.wait(0.5)
        self.play(Write(line4))
        self.wait(1.5)
        for i in range(len(line5)):
            self.play(Write(line5[len(line5)-i-1]))
            self.wait(0.5)
        self.wait()

    def part7(self):
        line1 = CText("6. 分式线性变换保交比")
        line2 = Tex(r"S(z)=\frac{z-z_3}{z-z_4} \frac{z_2-z_4}{z_2-z_3}")
        line3 = VGroup(Tex(r"S(z_2)=1"), Tex(r"S(z_3)=0"), Tex(r"S(z_4)=\infty")
        ).arrange(RIGHT, buff=LARGE_BUFF)
        line4 = VGroup(
            CText("交比"),
            Tex("S(z)=(z, z_2, z_3, z_4)")
        ).arrange(RIGHT, buff = LARGE_BUFF)
        lines = VGroup(line2, line3, line4).arrange(DOWN, buff=MED_LARGE_BUFF)
        line1.shift(3*UP)

        linf1 = VGroup(CText("不动点"), Tex(r"z=\frac{az+b}{cz+d}"), 
        Tex(r"cz^2+(d-a)z-b=0")).arrange(RIGHT, buff=LARGE_BUFF)
        linf2 = VGroup(
            Tex(r"c=0"),
            Tex(r"a=d"),
            Tex(r"-b = 0?!")
        ).arrange(RIGHT, buff=LARGE_BUFF, aligned_edge=DOWN)
        linf2a = Tex(r"z=z+\frac{b}{a}")
        linf2b = Tex(r"z_1=\infty")
        linf3 = VGroup(
            Tex(r"c=0"),
            Tex(r"a\neq d"),
            Tex(r"z_1 = \frac{d}{b-a}"),
            Tex(r"z_2=\infty")
        ).arrange(RIGHT, buff=LARGE_BUFF, aligned_edge=DOWN)
        linf4 = VGroup(
            Tex(r"c\neq0"),
            Tex(r"(d-a)^2+4bc=0"),
            Tex(r"z_1 = \sqrt{-\frac{b}{c}}")
        ).arrange(RIGHT, buff=LARGE_BUFF, aligned_edge=DOWN)
        linf5 = VGroup(
            Tex(r"c=0"),
            Tex(r"a\neq d"),
            Tex(r"z_{1,2} = \frac{-(d-a)\pm\sqrt{(d-a)^2+4bc}}{2c}")
        ).arrange(RIGHT, buff=LARGE_BUFF, aligned_edge=DOWN)
        linfs = VGroup(linf1, linf2, linf3, linf4, linf5).arrange(DOWN, buff=MED_LARGE_BUFF)
        linf2a.move_to(linf2[2], aligned_edge=DOWN)
        linf2b.move_to(linf2[2], aligned_edge=DOWN)
        naive_rect = SurroundingRectangle(linf2[2], buff=SMALL_BUFF)
        naive_words = CText("愚蠢！").scale(0.7)
        VGroup(naive_rect, naive_words).set_color(RED)
        naive_words.next_to(naive_rect, RIGHT, buff = SMALL_BUFF)

        ling1 = VGroup(Tex(r"\forall T,"),Tex("(Tz_1, Tz_2, Tz_3, Tz_4)=(z_1, z_2, z_3, z_4)")
        ).arrange(RIGHT, buff = MED_LARGE_BUFF)
        ling2 = VGroup(CText("令"), Tex("Sz = (z, z_2, z_3, z_4)")).arrange(RIGHT, buff = MED_SMALL_BUFF)
        ling3 = VGroup(
            CText("则"),
            Tex(r"ST^{-1}"),
            CText("将"),
            Tex(r"Tz_1, Tz_2, Tz_3"),
            CText("映射至"),
            Tex(r"1,0,\infty")
        ).arrange(RIGHT, buff = MED_SMALL_BUFF)
        ling4 = CText("由交比的定义")
        ling5 = Tex(r"(Tz_1, Tz_2, Tz_3, Tz_4)=ST^{-1}(Tz_1)=Sz_1=(z_1, z_2, z_3, z_4)")
        lings = VGroup(ling1, ling2, ling3, ling4, ling5).arrange(DOWN, buff = MED_SMALL_BUFF).shift(0.1*DOWN)



        self.play(Write(line2))
        self.wait(3)
        self.play(Write(line3), run_time = 2)
        self.wait(2)
        rect = SurroundingRectangle(line2, buff=SMALL_BUFF).set_color(YELLOW)
        self.play(ShowCreation(rect))
        self.wait(2)
        self.play(FadeOut(VGroup(line2, line3, rect)))
        self.wait()
        self.play(Write(linf1[0:2]), run_time=1.6)
        self.wait()
        self.play(
            Transform(linf1[1].copy(), linf1[2], remover=True),
            FadeIn(linf1[2], time_span=(0.9, 1))
        )
        self.wait()
        self.play(
            Write(linf2[0:2])
        )
        self.wait()
        self.play(Write(linf2[2]))
        self.wait()
        self.play(LaggedStart(
            ShowCreation(naive_rect),
            FadeIn(naive_words, lag_ratio=0.1),
        ))
        self.wait()
        self.play(FadeOut(naive_rect), FadeOut(naive_words))
        self.wait()
        self.play(Transform(linf2[2], linf2a))
        self.wait()
        self.play(Transform(linf2[2], linf2b))
        self.wait()

        append_rect = SurroundingRectangle(linf2[2], buff=SMALL_BUFF)
        append_words = VGroup(
            VGroup(Tex("b=0"), CText("时")).arrange(RIGHT, buff = SMALL_BUFF), 
            CText("整个复平面都是不动点")
        ).scale(0.6).arrange(DOWN, buff=SMALL_BUFF).next_to(append_rect, RIGHT, buff=SMALL_BUFF)
        VGroup(append_rect, append_words).set_color(TEAL_A)
        self.play(FadeIn(VGroup(append_rect, append_words)))

        self.wait()
        self.play(LaggedStart(
            FadeIn(linf3),
            FadeIn(linf4),
            FadeIn(linf5),
            lag_ratio = 0.5,
            run_time = 2
        ))
        self.wait(3)
        self.play(
            FadeOut(linfs),
            FadeOut(VGroup(append_rect, append_words))
        )
        self.wait(0.5)
        self.play(FadeIn(lines[0:2]))
        self.wait(2)
        self.play(FadeIn(line4))
        self.wait()
        self.play(Write(line1))
        self.wait(2)
        self.play(FadeOut(lines))
        self.wait()

        for ling in lings[0:4]:
            self.play(Write(ling))
            self.wait(1.5)
        self.play(Write(ling5), run_time=8)
        self.wait(3)
        self.play(FadeOut(lings))
        

        plane = ComplexPlane((-3,3), (-3,3)).scale(1.2).to_edge(RIGHT, buff=LARGE_BUFF).shift(0.2*DOWN)
        plane.add_coordinate_labels().scale(0.75)
        statement = VGroup(
            CText("四个复数的交比为实数"),
            CText("当且仅当它们"),
            CText("在复平面上共线或共圆")
        ).arrange(DOWN, buff= SMALL_BUFF).set_color(BLUE_B).next_to(plane, LEFT, buff= MED_LARGE_BUFF).scale(0.8)

        math = VGroup(
            Tex(r"\arg (z_1, z_2, z_3, z_4)"),
            Tex(r"=\arg \frac{z_1-z_3}{z_1-z_4} - \arg \frac{z_2-z_3}{z_2-z_4}")
        ).arrange(DOWN, buff=MED_SMALL_BUFF, aligned_edge=LEFT).next_to(plane, LEFT, buff= MED_LARGE_BUFF).scale(0.9).shift(DOWN)
        matha = Tex(r"=32.5^\circ-32.5^\circ=0^\circ", t2c = {r"32.5^\circ": YELLOW}).move_to(
            math[1], aligned_edge=LEFT
        )
        mathb = Tex(r"=32.5^\circ-(-147.5)^\circ=180^\circ", t2c = {r"32.5^\circ": YELLOW, r"(-147.5)^\circ": GOLD}).move_to(
            math[1], aligned_edge=LEFT
        )

        
        def make_updater(s):
            def updater(mob):
                mob.next_to(zs[s], UR, buff=SMALL_BUFF)
            return updater
        zs = Group()
        ztexs = VGroup()
        zvecs = []
        for s, i in enumerate([60, 105, -50, -115]):
            ztemp = GlowDot(color=YELLOW, radius=0.09, glow_factor=0.5).move_to(
                plane.n2p(0.5 - 0.2j + 1.5*np.exp(1j* i * DEGREES)))
            zs.add(ztemp)   # add() works like append()
            ztexs.add(
                VGroup(Tex(f"z_{s+1}").set_color(YELLOW).set_stroke(BLACK, width=4),
                Tex(f"z_{s+1}").set_color(YELLOW).set_stroke(BLACK)))
            ztexs[s].add_updater(
                make_updater(s)     # what a hard fix
            )
            zvecs.append(plane.n2p(0.5 - 0.2j + 1.5*np.exp(1j* i * DEGREES)))
        ztexs.set_z_index(1)
        angle1 = Angle(
            zvecs[2], zvecs[0], zvecs[3],
            radius = 0.3, color=YELLOW,
            edge_config = {"color":YELLOW, "stroke_width":3}
        ).set_opacity(0.3)
        angle2 = Angle(
            zvecs[2], zvecs[1], zvecs[3],
            radius = 0.3, color=YELLOW,
            edge_config = {"color":YELLOW, "stroke_width":3}
        ).set_opacity(0.3)
        circle = Circle(
            radius=plane.n2p(1.5)[0] - plane.n2p(0)[0],
            stroke_color=YELLOW,
            stroke_width=2
        ).move_to(plane.n2p(0.5-0.2j))
        
        self.play(Write(statement))
        self.play(FadeIn(plane))
        self.wait()
        self.play(FadeIn(zs), FadeIn(ztexs))
        self.wait()
        self.play(LaggedStart(statement.animate.shift(UP),
            FadeIn(math),
            lag_ratio = 0.5
        ))
        self.wait()
        self.play(LaggedStart(
            FadeIn(angle1),
            FadeIn(angle2),
            lag_ratio=0.5
        ))
        self.wait()
        self.play(
            angle1.animate.set_opacity(1)
        )
        self.wait()
        edgetemp = angle1.edges[0].copy()
        self.play(
            edgetemp.animate.rotate(angle=angle1.da, about_point=angle1.B)
        )
        self.remove(edgetemp)
        self.wait()
        self.play(
            Transform(math[1][1:13].copy(), matha[1:6].copy(), remover=True),
            Transform(math[1][0].copy(), matha[0].copy(), remover=True),
            Transform(math[1][13].copy(), matha[6].copy(), remover=True),
            Transform(math[1][14:26].copy(), matha[7:12].copy(), remover=True),
            FadeIn(matha, time_span=(0.7,1)),
            FadeOut(math[1], time_span=(0, 0.3))
        )
        self.wait()
        self.play()
        self.wait(2.5)
        self.play(ShowCreation(circle))
        self.wait()
        self.play(FadeOut(angle2))
        self.play(zs[1].animate.rotate(angle=PI, about_point=plane.n2p(0.5-0.2j)))
        zvecs[1] = plane.n2p(0.5 - 0.2j - 1.5*np.exp(1j* 105 * DEGREES))
        angle2 = Angle(
            zvecs[2], zvecs[1], zvecs[3],
            radius = 0.3, color=GOLD,
            edge_config = {"color":GOLD, "stroke_width":3}
        ).set_opacity(1)
        self.play(FadeIn(angle2))
        self.wait()
        self.play(
            Transform(matha[0:7].copy(), mathb[0:7].copy(), remover=True),
            Transform(matha[7:12].copy(), mathb[7:16].copy(), remover=True),
            Transform(matha[12:].copy(), mathb[16:].copy(), remover=True),
            FadeIn(mathb, time_span=(0.7,1)),
            FadeOut(matha, time_span=(0, 0.3))
        )
        self.wait(3)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part8(self):
        line1 = CText("分式线性变换")
        line2_ell = CText("1. ...")
        line3_ell = CText("2. ...")
        line4_ell = CText("3. ...")
        line5_ell = CText("4. ...")
        line6_ell = CText("5. ...")
        line7_ell = CText("6. ...")
        line2 = CText("1. 分式线性变换的复合是分式线性变换")
        line3 = CText("2. 所有分式线性变换都有逆变换", t2c = {"逆变换": TEAL_B})
        line4 = CText("3. 分式线性变换是复平面到自身的同胚映射")
        line5 = CText("4. 分式线性变换的部分分式展开")
        line6 = CText("5. 分式线性变换具有保圆性（保广义圆）", t2c = {"保圆性": TEAL_B})
        line7 = CText("6. 分式线性变换保交比", t2c = {"保交比": TEAL_B})
        line1.shift(3 * UP)
        lines = VGroup(
            line2, line3, line4, line5, line6, line7
        ).arrange(DOWN, aligned_edge = LEFT, buff=MED_SMALL_BUFF).next_to(line1, DOWN, buff=MED_SMALL_BUFF)
        lines_ell = VGroup(
            line2_ell, line3_ell, line4_ell, line5_ell, line6_ell, line7_ell
        )
        for i in range(len(lines_ell)):
            lines_ell[i].align_to(lines[i], LEFT)
            lines_ell[i].set_y(lines[i].get_y())
        
        abstract_words = CText("形而上学讨论(纯抽象)")
        abstract_rect = SurroundingRectangle(VGroup(line2_ell, line3_ell, line4_ell), buff = SMALL_BUFF)
        VGroup(abstract_words, abstract_rect).set_color(TEAL)
        abstract_words.next_to(abstract_rect, RIGHT, LARGE_BUFF)
        less_abstract_words = CText("更加形象化的内容") 
        less_abstract_rect = SurroundingRectangle(VGroup(line5_ell, line6_ell, line7_ell), buff = SMALL_BUFF)
        VGroup(less_abstract_words, less_abstract_rect).set_color(TEAL_B)
        less_abstract_words.next_to(less_abstract_rect, RIGHT, LARGE_BUFF)

        self.play(FadeIn(line1))
        self.play(LaggedStart(
            [Write(line) for line in lines_ell],
            lag_ratio = 0.5,
            run_time = 3
        ))
        self.wait()
        self.play(LaggedStart(
            ShowCreation(abstract_rect),
            FadeIn(abstract_words, lag_ratio=0.1),
        ))
        self.wait(2)
        self.play(LaggedStart(
            ShowCreation(less_abstract_rect),
            FadeIn(less_abstract_words, lag_ratio=0.1),
        ))
        self.wait(2)
        self.play(
            FadeOut(less_abstract_rect), FadeOut(less_abstract_words),
            FadeOut(abstract_rect), FadeOut(abstract_words)
        )
        self.wait()
        self.play(FadeOut(lines_ell), FadeIn(lines))
        self.wait(4)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part9(self):
        """镜头9：Steiner 圆系的确定与退化。
        a,b,z0 -> a,b,w0 唯一决定分式线性变换；像仍是 Steiner 圆系；
        令 b=a+eps 一阶展开得抛物型变换 1/(w-a)=1/(z-a)+c。
        所有 lines 转场均为手写 index 的 Transform(..., remover=True)。"""

        t2c_ab = {"{a}": RED, "{b}": BLUE}

        line1 = CText("7. Steiner 圆系")
        line1.shift(3 * UP)

        # 7.1 三对对应点
        line_map = VGroup(
            CText("三对对应点"),
            Tex(r"({a},{a}),\ ({b},{b}),\ (z_0,w_0)",
                t2c={**t2c_ab, "z_0": YELLOW, "w_0": YELLOW})
        ).arrange(RIGHT, buff=MED_SMALL_BUFF)
        line_map.next_to(line1, DOWN, buff=MED_LARGE_BUFF)

        line2 = Tex(
            r"\frac{w-{a}}{w-{b}}\,\frac{{w_0}-{b}}{{w_0}-{a}}"
            r"=\frac{z-{a}}{z-{b}}\,\frac{{z_0}-{b}}{{z_0}-{a}}",
            t2c=t2c_ab).scale(1.1)
        line2.next_to(line_map, DOWN, buff=MED_LARGE_BUFF)

        # FIXME: 原骨架右侧误写为 z0 的交比，应为 z 的交比
        line2_simp = Tex(
            r"\frac{w-{a}}{w-{b}}={c}\,\frac{z-{a}}{z-{b}}",
            t2c={**t2c_ab, "{c}": TEAL}).scale(1.1)
        line2_simp.move_to(line2)

        line3 = VGroup(
            Tex(r"\left|\frac{z-{a}}{z-{b}}\right|=r",
                t2c={**t2c_ab}),
            Tex(r"\arg\frac{z-{a}}{z-{b}}=\theta",
                t2c={**t2c_ab}),
        ).arrange(RIGHT, buff=LARGE_BUFF)
        line3.next_to(line2, DOWN, buff=MED_LARGE_BUFF)

        # FIXME: 原骨架第二式左边误写为 z 的交比，应为 w
        line3_w = VGroup(
            Tex(r"\left|\frac{w-{a}}{w-{b}}\right|=r|c|",
                t2c={**t2c_ab, "c": TEAL}),
            Tex(r"\arg\frac{w-{a}}{w-{b}}=\theta+\arg c",
                t2c={**t2c_ab, "c": TEAL}),
        ).arrange(RIGHT, buff=LARGE_BUFF)
        line3_w.move_to(line3)

        # 7.2 退化 b = a + eps
        b_eps = Tex(r"{b}={a}+\epsilon,\quad \epsilon\to0",
                    t2c={**t2c_ab, r"\epsilon": YELLOW})
        b_eps.next_to(line1, DOWN, buff=MED_LARGE_BUFF)

        linf2 = Tex(r"\frac{w-a}{w-a-\epsilon}\,\frac{w_0-a-\epsilon}{w_0-a}"
                    r"=\frac{z-a}{z-a-\epsilon}\,\frac{z_0-a-\epsilon}{z_0-a}").scale(0.8)
        linf3 = Tex(r"\left(1+\frac{\epsilon}{w-a}\right)"
                    r"=\left(1+\frac{\epsilon}{w_0-a}\right)"
                    r"\left(1-\frac{\epsilon}{z_0-a}\right)"
                    r"\left(1+\frac{\epsilon}{z-a}\right)").scale(0.75)
        linf4 = Tex(r"\frac{\epsilon}{w-a}"
                    r"=\frac{\epsilon}{w_0-a}-\frac{\epsilon}{z_0-a}"
                    r"+\frac{\epsilon}{z-a}").scale(0.85)
        linf5 = Tex(r"\frac{\epsilon}{w-a}=r+\frac{\epsilon}{z-a}",
                    t2c={"r": TEAL}).scale(1.0)
        linf5_simp = Tex(r"\frac{1}{w-a}=\frac{1}{z-a}+\frac{r}{\epsilon}").scale(1.0)
        linf5_simp1 = Tex(r"\frac{1}{w-a}=\frac{1}{z-a}+c",
                          t2c={"c": TEAL}).scale(1.2)
        linf2.next_to(b_eps, DOWN, buff=MED_LARGE_BUFF)
        for mob in (linf3, linf4, linf5, linf5_simp, linf5_simp1):
            mob.move_to(linf2)

        # ---------- 动画 ----------
        self.play(Write(line_map))
        self.wait(0.5)
        self.play(Write(line2))
        self.wait()
        # line2 -> line2_simp：两个分式原地保留，中间 z0/w0 交比飞散、c 飞入
        self.play(
            Transform(line2[0:7].copy(), line2_simp[0:7].copy(), remover=True),
            Transform(line2[16].copy(), line2_simp[7].copy(), remover=True),
            Transform(line2[17:24].copy(), line2_simp[9:16].copy(), remover=True),
            FadeOut(line2, time_span=(0, 0.3)),
            FadeIn(line2_simp, time_span=(0.7, 1)),
        )
        c_rect = SurroundingRectangle(line2_simp["{c}"])
        c_words = VGroup(Tex("c").scale(1.2), CText("由"), Tex("z_0, w_0").scale(1.2), CText("决定")).arrange(RIGHT, buff=SMALL_BUFF).scale(0.7)
        c_words.next_to(c_rect, DOWN, buff=MED_LARGE_BUFF)
        c_words1 = VGroup(Tex("c=1").scale(1.2), CText("时表示恒等变换")).arrange(RIGHT, buff=SMALL_BUFF).scale(0.7)
        c_words1.next_to(c_rect, DOWN, buff=MED_LARGE_BUFF)
        VGroup(c_rect, c_words, c_words1).set_color(TEAL)
        self.play(ShowCreation(c_rect), FadeIn(c_words, lag_ratio=0.1))
        self.wait()
        self.play(FadeIn(c_words1, time_span=(0.7, 1)),
                  FadeOut(c_words, time_span=(0, 0.3)))
        self.wait()
        self.play(FadeOut(VGroup(c_rect, c_words1)))
        self.wait(0.5)
        self.play(FadeIn(line3))
        self.wait(2)
        self.play(Write(line1))
        self.wait(2)
        # line3 -> line3_w：z→w（index 2、5），|c| 与 +\arg c 飞入
        self.play(
            Transform(line3[0][0:2].copy(), line3_w[0][0:2].copy(), remover=True),
            Transform(line3[0][2].copy(), line3_w[0][2].copy(), remover=True),
            Transform(line3[0][3:5].copy(), line3_w[0][3:5].copy(), remover=True),
            Transform(line3[0][5].copy(), line3_w[0][5].copy(), remover=True),
            Transform(line3[0][6:17].copy(), line3_w[0][6:17].copy(), remover=True),
            Transform(line3[1][0:2].copy(), line3_w[1][0:2].copy(), remover=True),
            Transform(line3[1][2].copy(), line3_w[1][2].copy(), remover=True),
            Transform(line3[1][3:5].copy(), line3_w[1][3:5].copy(), remover=True),
            Transform(line3[1][5].copy(), line3_w[1][5].copy(), remover=True),
            Transform(line3[1][6:12].copy(), line3_w[1][6:12].copy(), remover=True),
            Transform(line2_simp["{c}"].copy(), line3_w[0][18].copy(), remover=True),
            Transform(line2_simp["{c}"].copy(), line3_w[1][16].copy(), remover=True),
            FadeOut(line3, time_span=(0, 0.3)),
            FadeIn(line3_w, time_span=(0.9, 1)),
        )
        self.wait()

        # ---- 退化极限 ----
        self.play(FadeOut(line_map), FadeOut(line2_simp), FadeOut(line3_w))
        self.play(Write(b_eps))
        self.play(Write(linf2))
        self.wait(0.5)
        note1 = CText("一阶近似").scale(0.7)
        note1.next_to(linf3, DOWN, buff=MED_SMALL_BUFF)
        # linf2 -> linf3：1/(1-ε/·) -> (1+ε/·)；
        # 分子 w-a / w_0-a / z-a / z_0-a 与 ε 搬到对应槽位，分数线与外壳飞散
        self.play(
            Transform(linf2[0:3].copy(), linf3[5:8].copy(), remover=True),
            Transform(linf2[8].copy(), linf3[3].copy(), remover=True),
            Transform(linf2[9:13].copy(), linf3[15:19].copy(), remover=True),
            Transform(linf2[14].copy(), linf3[13].copy(), remover=True),
            # Transform(linf2[19].copy(), linf3[8].copy(), remover=True),
            Transform(linf2[21:24].copy(), linf3[35:38].copy(), remover=True),
            Transform(linf2[29].copy(), linf3[33].copy(), remover=True),
            Transform(linf2[30:34].copy(), linf3[25:29].copy(), remover=True),
            Transform(linf2[35].copy(), linf3[23].copy(), remover=True),
            FadeOut(linf2, time_span=(0, 0.2)),
            FadeIn(linf3, time_span=(0.7, 1)),
        )
        self.play(FadeIn(note1))
        self.wait(0.5)
        note2 = CText("继续只保留到一阶（零阶项两边都是1）").scale(0.7).move_to(note1)
        # linf3 -> linf4：剥掉每个因子的 (1+·) 外壳与括号
        self.play(
            Transform(linf3[3].copy(), linf4[0].copy(), remover=True),
            Transform(linf3[4].copy(), linf4[1].copy(), remover=True),
            Transform(linf3[5:8].copy(), linf4[2:5].copy(), remover=True),
            Transform(linf3[9].copy(), linf4[5].copy(), remover=True),
            Transform(linf3[13].copy(), linf4[6].copy(), remover=True),
            Transform(linf3[14].copy(), linf4[7].copy(), remover=True),
            Transform(linf3[15:19].copy(), linf4[8:12].copy(), remover=True),
            Transform(linf3[22].copy(), linf4[12].copy(), remover=True),
            Transform(linf3[23].copy(), linf4[13].copy(), remover=True),
            Transform(linf3[24].copy(), linf4[14].copy(), remover=True),
            Transform(linf3[25:29].copy(), linf4[15:19].copy(), remover=True),
            Transform(linf3[32].copy(), linf4[19].copy(), remover=True),
            Transform(linf3[33].copy(), linf4[20].copy(), remover=True),
            Transform(linf3[34].copy(), linf4[21].copy(), remover=True),
            Transform(linf3[35:38].copy(), linf4[22:25].copy(), remover=True),
            Transform(note1, note2),
            FadeOut(linf3, time_span=(0, 0.3)),
            FadeIn(linf4, time_span=(0.7, 1)),
        )
        self.wait(0.5)
        note3 = VGroup(CText("前三项打包成一个常数"), Tex("r").scale(1.2)).arrange(RIGHT, buff=SMALL_BUFF).scale(0.7).move_to(note1)
        # linf4 -> linf5：中间两个分式飞散，r 飞入
        self.play(
            Transform(linf4[0:5].copy(), linf5[0:5].copy(), remover=True),
            Transform(linf4[5].copy(), linf5[5].copy(), remover=True),
            Transform(linf4[19].copy(), linf5[7].copy(), remover=True),
            Transform(linf4[20].copy(), linf5[8].copy(), remover=True),
            Transform(linf4[21].copy(), linf5[9].copy(), remover=True),
            Transform(linf4[22:25].copy(), linf5[10:13].copy(), remover=True),
            Transform(note1, note3),
            FadeOut(linf4, time_span=(0, 0.3)),
            FadeIn(linf5, time_span=(0.7, 1)),
        )
        self.wait(0.5)
        note4 = VGroup(CText("两边除以"), Tex(r"\epsilon").scale(1.2)).arrange(RIGHT, buff=SMALL_BUFF).scale(0.7).move_to(note1)
        # linf5 -> linf5_simp：ε->1，第二个分式整体左移，+ 归位
        self.play(
            Transform(linf5[0].copy(), linf5_simp[0].copy(), remover=True),
            Transform(linf5[1].copy(), linf5_simp[1].copy(), remover=True),
            Transform(linf5[2:5].copy(), linf5_simp[2:5].copy(), remover=True),
            Transform(linf5[5].copy(), linf5_simp[5].copy(), remover=True),
            Transform(linf5[7].copy(), linf5_simp[11].copy(), remover=True),
            Transform(linf5[8].copy(), linf5_simp[6].copy(), remover=True),
            Transform(linf5[9].copy(), linf5_simp[7].copy(), remover=True),
            Transform(linf5[10:13].copy(), linf5_simp[8:11].copy(), remover=True),
            Transform(note1, note4),
            FadeOut(linf5, time_span=(0, 0.3)),
            FadeIn(linf5_simp, time_span=(0.7, 1)),
        )
        self.wait(0.5)
        # r/ε = 1/(w0-a) - 1/(z0-a) 是常数
        note5 = Tex(r"\frac{r}{\epsilon}=c", t2c={"c": TEAL}).scale(0.8).move_to(note1).shift(0.3 * DOWN)
        # linf5_simp -> linf5_simp1：r/ε -> c，其余整体保留
        self.play(
            Transform(linf5_simp[0:12].copy(), linf5_simp1[0:12].copy(), remover=True),
            Transform(note1, note5),
            FadeOut(linf5_simp, time_span=(0, 0.3)),
            FadeIn(linf5_simp1, time_span=(0.7, 1)),
        )
        self.wait(1)
        final_rect = SurroundingRectangle(linf5_simp1, buff=SMALL_BUFF)
        self.play(ShowCreation(final_rect))
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part10(self):
        """镜头10：w=1/z 是 Steiner 流的特例——固定 a=-1, b=1，c=e^{iπ}。
        |c|=1 圆大小不变，arg c=π 弧整体转半圈。"""

        line2 = Tex(r"\frac{w+1}{w-1}=-\frac{z+1}{z-1}")
        line3 = Tex(r"\frac{w+1}{w-1}=e^{i\pi}\frac{z+1}{z-1}",
                    t2c={r"\pi": YELLOW})
        # FIXME: 原骨架 line4 与 line3 重复，改为 c=e^{iπ} 的注记行
        line4 = VGroup(
            Tex(r"c=e^{i\pi}:\quad |c|=1,\ \arg c=\pi",
                t2c={"c": TEAL, r"\pi": YELLOW}),
            CText("r圆大小不变，theta弧整体旋转半圈").scale(0.7),
        ).arrange(DOWN, buff=SMALL_BUFF)

        line5 = Tex(r"w=\frac{(e^{i\pi}+1)z+(e^{i\pi}-1)}"
                    r"{(e^{i\pi}-1)z+(e^{i\pi}+1)}",
                    t2c={r"\pi": YELLOW})
        line1 = Tex(r"w=\frac1z")

        lines = VGroup(line1, line2, line4
        ).arrange(DOWN, buff = MED_SMALL_BUFF)
        line3.next_to(line1, DOWN, buff = MED_SMALL_BUFF)
        line5.next_to(line2, DOWN, buff = MED_SMALL_BUFF)

        self.play(Write(line1))
        self.wait()
        self.play(Write(line2))
        self.wait()
        # line2 -> line3：两个分式原地保留，负号飞散、e^{iπ} 飞入
        # index：line2 共 16 个（0-15），line3 共 18 个（0-17）
        self.play(
            Transform(line2[0:8].copy(), line3[0:8].copy(), remover=True),
            Transform(line2[9:16].copy(), line3[11:18].copy(), remover=True),
            FadeOut(line2, time_span=(0, 0.3)),
            FadeIn(line3, time_span=(0.7, 1)),
        )
        self.play(FadeIn(line4))
        self.wait(2)
        self.play(FadeOut(line4))
        self.play(Write(line5))
        self.wait()
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

    def part11(self):
        """镜头11：Steiner 圆系的退化推导。
        b=a+ε, r=e^{αε}, θ=βε ⇒ Re/Im 1/(z-a) = 常数，
        配方为过 a 的圆 |z-a|=|c-a|，圆心分别在实、虚方向上。"""

        t2c_eps = {r"\epsilon": YELLOW}

        line1 = CText("8. 两点重合时 Steiner 圆系的极限")
        line1.shift(3 * UP)

        s1 = Tex(r"{b}={a}+\epsilon,\quad \epsilon\to0",
                 t2c={**t2c_eps})
        s2 = Tex(r"r=e^{{\alpha}\epsilon},\quad \theta={\beta}\epsilon",
                 t2c={**t2c_eps, r"{\alpha}": TEAL, r"{\beta}": GREEN, "r": TEAL, r"\theta": GREEN})
        s1.next_to(line1, DOWN, buff=MED_LARGE_BUFF)
        s2.next_to(s1, DOWN, buff=MED_LARGE_BUFF)

        e1 = Tex(r"\log\frac{z-a}{z-a-\epsilon}",
                 r"=-\log\left(1-\frac{\epsilon}{z-a}\right)",
                 r"=\frac{\epsilon}{z-a}+O(\epsilon^2)=\log re^{i\theta}",
                 t2c=t2c_eps).scale(0.9)
        e1.next_to(s2, DOWN, buff=MED_LARGE_BUFF)

        e2 = Tex(r"\mathrm{Re}\,\frac{\epsilon}{z-a}+O(\epsilon^2)=\ln r={\alpha}\epsilon",
                 t2c={**t2c_eps, "r": TEAL, r"{\alpha}": TEAL}).scale(0.9)
        e3 = Tex(r"\mathrm{Im}\,\frac{\epsilon}{z-a}+O(\epsilon^2)=\theta={\beta}\epsilon",
                 t2c={**t2c_eps, r"{\beta}": GREEN, r"\theta": GREEN}).scale(0.9)
        pair1 = VGroup(e2, e3).arrange(DOWN, buff=MED_SMALL_BUFF, aligned_edge=LEFT)
        pair1.move_to(e1).shift(0.5*DOWN)

        r1 = Tex(r"\mathrm{Re}\,\frac{1}{z-a}={\alpha}",
                 t2c={r"{\alpha}": TEAL}).scale(0.9)
        r2 = Tex(r"\mathrm{Im}\,\frac{1}{z-a}={\beta}",
                 t2c={r"{\beta}": GREEN}).scale(0.9)
        pair2 = VGroup(r1, r2).arrange(DOWN, buff=MED_SMALL_BUFF, aligned_edge=LEFT)
        pair2.move_to(pair1)

        c1 = Tex(r"\left|z-a-\frac{1}{2{\alpha}}\right|=\left|\frac{1}{2{\alpha}}\right|",
                 t2c={r"{\alpha}": TEAL}).scale(0.9)
        c2 = Tex(r"\left|z-a+\frac{i}{2{\beta}}\right|=\left|\frac{i}{2{\beta}}\right|",
                 t2c={r"{\beta}": GREEN}).scale(0.9)
        pair3 = VGroup(c1, c2).arrange(DOWN, buff=MED_SMALL_BUFF, aligned_edge=LEFT)
        pair3.move_to(pair1)

        concl = Tex(r"|z-a|=|{c}-a|", t2c={"{c}": YELLOW}).scale(1.2)
        concl.move_to(UP * 0.3)
        concl_words = VGroup(
            CText("模族：c 沿水平方向（实数）", t2c={"c": YELLOW}).scale(0.8),
            CText("幅角族：c 沿垂直方向（虚数）", t2c={"c": YELLOW}).scale(0.8),
        ).arrange(DOWN, buff=SMALL_BUFF, aligned_edge=LEFT)
        concl_words.next_to(concl, DOWN, buff=MED_LARGE_BUFF)

        # ---------- 动画 ----------
        self.play(Write(line1))
        self.play(Write(s1))
        self.play(Write(s2))
        note0 = CText("注意力时刻").scale(0.65)
        note0.next_to(s2, RIGHT, buff=LARGE_BUFF)
        self.wait(2)
        self.play(FadeIn(note0))
        self.wait(3)
        self.play(FadeIn(e1))
        note1 = CText("展开到一阶").scale(0.7)
        note1.next_to(pair1, RIGHT, buff=MED_LARGE_BUFF)
        self.wait()
        # e1 -> pair1：实部式、虚部式从同一行分裂飞出（源对象重用副本）。
        # index：e1 共 40 个（0-39），e2 共 19 个（0-18），e3 共 18 个（0-17）
        self.play(
            FadeOut(e1, time_span=(0, 0.3)),
            FadeOut(note0, time_span=(0, 0.3)),
            FadeIn(note1, time_span=(0.7, 1)),
            FadeIn(pair1, time_span=(0.7, 1)),
        )
        self.wait()
        # pair1 -> pair2：ε -> 1，+O(ε²)、\ln r、\theta 飞散
        self.play(
            Transform(e2[0:2].copy(), r1[0:2].copy(), remover=True),
            Transform(e2[2].copy(), r1[2].copy(), remover=True),
            Transform(e2[3].copy(), r1[3].copy(), remover=True),
            Transform(e2[4:7].copy(), r1[4:7].copy(), remover=True),
            Transform(e2[17].copy(), r1[7].copy(), remover=True),
            Transform(e2[18].copy(), r1[8].copy(), remover=True),
            Transform(e3[0:2].copy(), r2[0:2].copy(), remover=True),
            Transform(e3[2].copy(), r2[2].copy(), remover=True),
            Transform(e3[3].copy(), r2[3].copy(), remover=True),
            Transform(e3[4:7].copy(), r2[4:7].copy(), remover=True),
            Transform(e3[15].copy(), r2[7].copy(), remover=True),
            Transform(e3[16].copy(), r2[8].copy(), remover=True),
            FadeOut(pair1, time_span=(0, 0.3)),
            FadeIn(pair2, time_span=(0.9, 1)),
        )
        self.wait()
        note3 = CText("配方").scale(0.7).move_to(note1)
        # pair2 -> pair3：Re/Im 飞散，|·| 外壳飞入，右端从同一源再分裂一次
        self.play(
            Transform(r1[4:7].copy(), c1[4:7].copy(), remover=True),
            Transform(r1[-1].copy(), c1[11].copy(), remover=True),
            Transform(r1[-1].copy(), c1[-5].copy(), remover=True),
            Transform(r2[4:7].copy(), c2[4:7].copy(), remover=True),
            Transform(r2[-1].copy(), c2[11].copy(), remover=True),
            Transform(r2[-1].copy(), c2[-5].copy(), remover=True),
            Transform(note1, note3),
            FadeOut(pair2, time_span=(0, 0.3)),
            FadeIn(pair3, time_span=(0.7, 1)),
        )
        self.wait()
        # 两个圆心方向
        rect1 = SurroundingRectangle(c1, buff=SMALL_BUFF)
        w1 = CText("圆心沿实轴，圆过 a").scale(0.65)
        w1.next_to(rect1, RIGHT, buff=SMALL_BUFF)
        VGroup(rect1, w1).set_color(TEAL)
        rect2 = SurroundingRectangle(c2, buff=SMALL_BUFF)
        w2 = CText("圆心延虚轴，圆过 a").scale(0.65)
        w2.next_to(rect2, RIGHT, buff=SMALL_BUFF)
        VGroup(rect2, w2).set_color(GREEN)
        self.play(LaggedStart(ShowCreation(rect1), FadeIn(w1, lag_ratio=0.1)))
        self.wait()
        self.play(LaggedStart(ShowCreation(rect2), FadeIn(w2, lag_ratio=0.1)))
        self.wait(2)
        # 结论
        self.play(FadeOut(pair3), FadeOut(rect1), FadeOut(w1),
                  FadeOut(rect2), FadeOut(w2),
                  FadeOut(note1))
        self.play(FadeIn(concl), FadeIn(concl_words))
        self.wait(2)
        self.play(*[FadeOut(m) for m in self.mobjects])

# ---------- 单镜头场景类（名字与之前一致，单独渲染/调试用） ----------

class Scene1(FLTParts):
    def construct(self):
        self.part1()

class Scene2(FLTParts):
    def construct(self):
        self.part2()

class Scene3(FLTParts):
    def construct(self):
        self.part3()

class Scene4(FLTParts):
    def construct(self):
        self.part4()

class Scene5(FLTParts):
    def construct(self):
        self.part5()

class Scene6(FLTParts):
    def construct(self):
        self.part6()

class Scene7(FLTParts):
    def construct(self):
        self.part7()

class Scene8(FLTParts):
    def construct(self):
        self.part8()

class Scene9(FLTParts):
    def construct(self):
        self.part9()

class Scene10(FLTParts):
    def construct(self):
        self.part10()

class Scene11(FLTParts):
    def construct(self):
        self.part11()

class EmptyScene(Scene):
    def construct(self):
        self.wait(3)

#* REUSE: debugger
class TexDebug(Scene):
    def construct(self):
        line = Tex(
            r"S(z)=\frac{az+b}{cz+d}"
        )

        self.add(line)
        self.add(index_labels(line))
        self.wait()