# don't use this; it's made using manimce.

from manim import *
import numpy as np

import sys
from pathlib import Path

# 把项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logo import make_petal_points, precompute_trajectory

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


# ============ Steiner 圆系 ============
def _c2p(z):
    return np.array([complex(z).real, complex(z).imag, 0.0])


def steiner_r_circle(z1, z2, r, color=BLUE):
    """|(z-z1)/(z-z2)| = r 的 Apollonius 圆；r=1 时为 z1z2 的中垂线。"""
    z1, z2 = complex(z1), complex(z2)
    if abs(r - 1.0) < 1e-9:
        m = (z1 + z2) / 2
        n = 1j * (z2 - z1) / abs(z2 - z1)
        half = 4
        return Line(_c2p(m - half * n), _c2p(m + half * n), color=color)
    center = (z1 - r * r * z2) / (1 - r * r)
    radius = r * abs(z1 - z2) / abs(1 - r * r)
    return Circle(radius=radius, color=color).move_to(_c2p(center))


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
        ext = 8.0                          # 伸出长度，超过帧半宽 7.1 即可出屏
        return Line(_c2p(z1 - ext * u), _c2p(z2 + ext * u), color=color)
    u = (z2 - z1) / L
    center = z1 - (L / (2 * np.sin(theta))) * 1j * np.exp(1j * theta) * u
    radius = abs(L / (2 * np.sin(theta)))
    a1 = np.angle(z1 - center)
    a2 = np.angle(z2 - center)
    def diff(x, y):
        return (x - y + np.pi) % (2 * np.pi) - np.pi
    delta = diff(a2, a1)
    d2 = delta - 2 * np.pi * np.sign(delta)          # 同一圆的另一支弧
    def rel(d):                                      # 该支弧在 z1 处切线相对弦的有向角
        g = a1 + (np.pi / 2 if d > 0 else -np.pi / 2)
        return diff(g - np.angle(u), theta)
    if abs(rel(d2)) < abs(rel(delta)):
        delta = d2
    return Arc(radius=radius, start_angle=a1, angle=delta,
               arc_center=_c2p(center), color=color)  # 三处修复：乘 u、相对弦选支、传圆心


def steiner(z1, z2, rs, thetas, rcolor=TEAL, tcolor=GREEN):
    """Steiner 圆系：VGroup(r_circles, t_arcs)。"""
    r_group = VGroup(*[steiner_r_circle(z1, z2, r, color=rcolor) for r in rs])
    t_group = VGroup(*[steiner_t_arc(z1, z2, th, color=tcolor) for th in thetas])
    return VGroup(r_group, t_group)


def corner_frac(value_tex):
    """右上角 Möbius 分式，4 个角度位显示 value_tex（黄色）。"""
    m = MathTex(
        r"\frac{(e^{i\cdot", value_tex, r"}+1)z+(e^{i\cdot", value_tex,
        r"}-1)}{(e^{i\cdot", value_tex, r"}-1)z+(e^{i\cdot", value_tex, r"}+1)}",
    )
    for i in (1, 3, 5, 7):
        m[i].set_color(YELLOW)
    return m.scale(0.7)


class SteinerFlow(Scene):
    def construct(self):
        plane = ComplexPlane(
            # x_range=(-8, 8, 1), y_range=(-4.5, 4.5, 1),
            # x_length=14.2, y_length=8,                 # 帧是 14.22 × 8（16:9），对上即铺满
            background_line_style={"stroke_width": 1},
            faded_line_style={"stroke_opacity": 0.25},
        )
        self.add(plane)
        
        # self.add(NumberPlane())

        z1, z2 = -1 + 0j, 1 + 0j
        rs = [1/11, 1/5, 1/3, 1/2, 1/1.4, 1, 1.4, 2, 3, 5, 11]
        thetas = [i * PI / 6 for i in range(12)]

        label = MathTex(r"z\mapsto z").scale(1.2).to_corner(UR)
        # 黄色发光点 p：随演示的 Möbius 变换走轨道 p(t) = f_{θ(t)}(0.5)
        p = VGroup(Dot(color=YELLOW))
        for k in (1, 2, 3):
            p.add(Circle(radius=0.07 + 0.02 * k, stroke_color=YELLOW,
                         stroke_width=3, stroke_opacity=0.6/k))
        p.move_to(plane.c2p(0.5 + 0j))
        prefix = label[0][:3]                    # "z\mapsto" 部分，之后随分式宽度平移
        circles = steiner(z1, z2, rs, thetas)
        r_group, t_group = circles
        self.play(FadeIn(circles), FadeIn(label), FadeIn(p), run_time=1.5)
        self.wait(0.5)

        # 右缘锚点：与 to_corner(UR) 的默认边距一致，首帧无跳变
        right_edge_x = config.frame_x_radius - 0.25

        def layout_pair(value_tex):
            """分式贴在 prefix 右侧，返回 (分式, dx)；dx 使分式右缘恒为 right_edge_x。"""
            new_frac = corner_frac(value_tex)
            new_frac.next_to(prefix, RIGHT, buff=0.15)
            dx = right_edge_x - new_frac.get_right()[0]
            return new_frac, dx

        # 展开：z -> Möbius 分式，prefix 在同一 play 里同步左移（不再换行）
        frac_mob = label[0][3]
        new_frac, dx = layout_pair("0.00")
        new_frac.shift(dx * RIGHT)
        self.play(
            Transform(frac_mob, new_frac),
            prefix.animate.shift(dx * RIGHT),
            run_time=1.2,
        )
        self.wait(0.3)

        # 分式中的数值与 thetas 增量同步增大
        shift = ValueTracker(0.0)
        def mobius_image(z0, theta):
            e = np.exp(1j * theta)
            return ((e + 1) * z0 + (e - 1)) / ((e - 1) * z0 + (e + 1))

        def track_p(m):
            z = mobius_image(0.5 + 0j, shift.get_value())
            m.move_to(plane.c2p(z.real, z.imag))   # ← 拆成两个实参，虚部才不会被吞
        p.add_updater(lambda m: track_p(m))

        for arc, th in zip(t_group, thetas):
            arc.add_updater(lambda m, th=th: m.become(
                steiner_t_arc(z1, z2, th + shift.get_value(), color=GREEN)))

        def sync(m):
            new_frac, dx = layout_pair(f"{shift.get_value():.2f}")
            prefix.shift(dx * RIGHT)             # updater 内逐帧绝对定位，不会累积漂移
            m.become(new_frac.shift(dx * RIGHT))
        frac_mob.add_updater(sync)

        self.play(shift.animate.set_value(PI), run_time=4)
        for arc in t_group:
            arc.clear_updaters()
        frac_mob.clear_updaters()
        p.clear_updaters()

        # 运动结束：数字变成 \pi（保持同一套右对齐布局）
        new_frac, dx = layout_pair(r"\pi")
        prefix.shift(dx * RIGHT)
        frac_mob.become(new_frac.shift(dx * RIGHT))
        self.wait(0.5)

        # 收尾：分式变成 1/z
        inv = MathTex(r"\frac{1}{z}").scale(1.2)
        inv.next_to(prefix, RIGHT, buff=0.15)
        dx = right_edge_x - inv.get_right()[0]
        inv.shift(dx * RIGHT)
        self.play(
            Transform(frac_mob, inv),
            prefix.animate.shift(dx * RIGHT),
            run_time=0.8,
        )
        self.wait(0.5)

def modular_surface_1_over_z(u_range=(-3, 3), v_range=(-3, 3),
                             resolution=(64, 64), h_max=3.5):
    """w = 1/z 的模曲面：z 轴高度 = |w|（在原点处 clamp 到 h_max），
    面片颜色与 2D domain colouring 同一套规则（hue=arg，V=mag_to_val）。"""
    def func(u, v):
        w = 1.0 / (u + 1j * v)
        return np.array([u, v, min(abs(w), h_max)])

    surf = Surface(
        func, u_range=u_range, v_range=v_range, resolution=resolution,
        checkerboard_colors=False,      # 必须关：默认是棋盘格
        fill_opacity=1.0,
        stroke_width=0,                 # 面片间不留描边，俯视才是连续色块
    )
    for face in surf.list_of_faces:     # 逐面片着色（set_fill_by_value 同款机制）
        uc, vc = (face.u1 + face.u2) / 2, (face.v1 + face.v2) / 2
        w = 1.0 / (uc + 1j * vc)
        hue = (np.angle(w) / (2 * np.pi)) % 1.0
        rgb = hsv_to_rgb(hue, 1.0, mag_to_val(abs(w)))
        r, g, b = (int(round(255 * float(c))) for c in rgb)
        face.set_fill(color=f"#{r:02x}{g:02x}{b:02x}", opacity=1.0)
    return surf

class DomainColouring(ThreeDScene):                      # ← Scene 改 ThreeDScene（向后兼容 2D）
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
        img = ImageMobject(domain_colouring_image())
        img.replace(square)
        return Group(square, ticks, img)

    def make_legend(self, kind, height=3.2, width=0.55):
        img = ImageMobject(legend_image(kind))
        img.stretch_to_fit_height(height)
        img.stretch_to_fit_width(width)

        labels = ["0", "1", r"\infty"] if kind == "value" else ["0", r"\pi", r"2\pi"]

        ticks = VGroup()
        texts = VGroup()
        for val, lab in zip((1.0, 0.5, 0.0), labels):
            p = img.get_right() + (0.5 - val) * height * UP
            tick = Line(p, p + RIGHT * 0.14, stroke_color=WHITE, stroke_width=2)
            ticks.add(tick)
            text = MathTex(lab, color=WHITE).scale(0.7)
            text.next_to(tick, RIGHT, buff=0.12)
            texts.add(text)

        box = SurroundingRectangle(img, color=WHITE, buff=0.0, stroke_width=2)
        return Group(img, box, ticks, texts)

    def make_glow(self, mob, color=WHITE, n_layers=10):
        opacities = [1.5 / n_layers for i in range(n_layers)]
        layers = VGroup()
        for i in range(n_layers):
            layer = SurroundingRectangle(mob, color=color, buff=0.0)
            layer.set_stroke(width=24 * (i / n_layers) ** 1.5, opacity=opacities[i])
            layers.add(layer)
        layers.z_index = mob.z_index - 0.1
        return layers

    # ---------- 主流程 ----------
    def construct(self):
        # 1. 公式
        eq = MathTex(r"w=\frac{1}{z}").scale(1.6)
        self.play(Write(eq))
        self.wait(0.5)
        self.play(eq.animate.to_corner(UL).scale(0.8))
        eq.z_index = 1

        # 2. a,b,c 依次淡入
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
        self.wait(0.5)

        # 3. b、c 依次辉光高亮
        for legend in (b, c):
            glow = self.make_glow(legend[1])
            self.play(FadeIn(glow, lag_ratio=0.2, run_time=0.8))
            self.wait(0.6)
            self.play(FadeOut(glow, run_time=0.5))
            self.wait(0.5)

        # 4. 删除 b、c，方框回中
        self.play(FadeOut(b), FadeOut(c),
                  a.animate.move_to(ORIGIN), run_time=0.8)
        self.wait(1)

        # 5. 换成"高度=模长"的三维模曲面：俯视淡入（与 2D 图重合），随后运镜
        surface = modular_surface_1_over_z()
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES)  # 显式俯视
        self.play(
            FadeOut(a[2], run_time=1.2),          # 只撤走框内位图；方框、刻度保留
            FadeIn(surface, run_time=1.2),
        )
        self.wait(0.5)

        # 3b1b 式运镜：长时长 + smooth，缓缓转向倾斜视角
        self.move_camera(phi=62 * DEGREES, theta=-35 * DEGREES,
                         run_time=6, rate_func=smooth)
        self.wait(1)

def inv(z, eps=0.05):
    # z 是 numpy 复数数组，必须向量化处理
    # 1/z = conj(z)/|z|^2，用 eps 截断 |z| 避免 z=0 发散
    r = np.maximum(np.abs(z), eps)
    return np.conj(z) / r**2

class InverseGrid(Scene):
    def construct(self):
        c_grid = ComplexPlane(
            x_range=(-7.111111, 7.111111, 0.5),   # 刻线步长 0.5
            y_range=(-4, 4, 0.5),
            background_line_style={"stroke_opacity": 0.6},
        )

        moving = c_grid.copy()
        moving.prepare_for_nonlinear_transform(num_inserted_curves=200)

        # 刻度仍然间隔 1：x 轴 -7..7，y 轴 ±1i..±4i（0 不标，和默认行为一致）
        labels = [float(x) for x in range(-7, 8)] + [
            complex(0, y) for y in range(-4, 5) if y != 0
        ]
        c_grid.add_coordinates(*labels)

        self.add(c_grid, moving)
        self.play(
            moving.animate.apply_complex_function(inv),
            run_time=6,
        )
        self.wait()

class OsmanthusDanmakuDark(Scene):
    def construct(self):
        # 1. 默认黑色背景：不再设置 camera.background_color

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
        # --------------------------------------------------------
        def make_updater(petal):
            meta = petal.meta
            template = petal.template_points
            t_max = meta["t_max"]
            t_s = meta["t_samples"]
            pos_s = meta["pos_samples"]
            tan_s = meta["tan_samples"]
            rot_offset = meta["rot_offset"]
            n = len(t_s)

            def updater(mob, alpha):
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

        fly_in_anims = [UpdateFromAlphaFunc(p, make_updater(p)) for p in all_petals]
        self.play(
            AnimationGroup(*fly_in_anims, lag_ratio=0.0),
            run_time=TOTAL_ANIM_TIME,
            rate_func=linear,                    # ← 改：smooth → linear
        )

        # --------------------------------------------------------
        # 5. 变色 + 整体上移 + 文字浮现（同一个 play，同时进行）
        # --------------------------------------------------------
        logo = VGroup(*all_petals)

        # 文字定位：先挂在当前 logo 下方，再预加上 0.7 的上移量，
        # 使它与上移后的 logo 保持相对位置
        label = Text("白川桂华", font="Noto Serif SC", color=LAYER_COLORS[1], font_size=42)  # 中花瓣的橙 #FF9933
        label.next_to(logo, DOWN, buff=0.3)
        label.shift(UP * 0.7)

        sub = Text("+AI(对抗式协作)", font="Noto Serif SC",
                   color=LAYER_COLORS[0], font_size=20)      # 浅橙 #FFCC80，与大字同族分层
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

class ZSquaredRiemann(ThreeDScene):
    # ---------- 构件 ----------
    def polar_half(self, center, deg0, deg1, color, half_side=1.5, stroke_width=2):
        grid = VGroup()
        for deg in range(deg0, deg1, 30):
            th = deg * DEGREES
            R = half_side / max(abs(np.cos(th)), abs(np.sin(th)))
            line = Line(center, center + R * np.array([np.cos(th), np.sin(th), 0]),
                        color=color, stroke_width=stroke_width)
            line.meta = ("ray", R, th)
            grid.add(line)
        for r in (0.4, 0.8, 1.2, 1.5):
            arc = Arc(radius=r, start_angle=deg0 * DEGREES,
                      angle=(deg1 - deg0) * DEGREES,
                      arc_center=center, color=color, stroke_width=stroke_width)
            arc.meta = ("arc", r, deg0 * DEGREES)
            grid.add(arc)
        return grid

    def doubled_flat(self, m, center):
        kind, a, th = m.meta
        color, width = m.get_stroke_color(), m.get_stroke_width()
        if kind == "ray":
            return Line(center, center + a**2 * np.array([np.cos(2 * th), np.sin(2 * th), 0]),
                        color=color, stroke_width=width)
        return Arc(radius=a**2, start_angle=2 * th, angle=2 * PI,
                   arc_center=center, color=color, stroke_width=width)

    def add_ticks(self, box, x_vals, y_vals, tick_len=0.12, font_size=20):
        """方形 plane 的左、下边沿外侧加刻度线并标数值；y 轴 1 标 i。"""
        x0, y0 = box.get_center()[0], box.get_center()[1]
        half = box.side_length / 2
        group = VGroup()
        for x in x_vals:
            p = np.array([x0 + x, y0 - half, 0])
            tick = Line(p, p + DOWN * tick_len, color=WHITE, stroke_width=2)
            num = MathTex(str(x), color=WHITE, font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)
        for y in y_vals:
            p = np.array([x0 - half, y0 + y, 0])
            tick = Line(p, p + LEFT * tick_len, color=WHITE, stroke_width=2)
            lab = "i" if y == 1 else (r"-i" if y == -1 else str(y))
            num = MathTex(lab, color=WHITE, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)
        return group

    def lifted(self, m, center):
        kind, a, th = m.meta
        color, width = m.get_stroke_color(), m.get_stroke_width()
        if kind == "ray":
            return ParametricFunction(
                lambda t: center + np.array([t**2 * np.cos(2 * th),
                                             t**2 * np.sin(2 * th),
                                             t * np.sin(th)]),
                t_range=[0, a], color=color, stroke_width=width)
        return ParametricFunction(
            lambda t: center + np.array([a**2 * np.cos(2 * t),
                                         a**2 * np.sin(2 * t),
                                         a * np.sin(t)]),
            t_range=[th, th + PI], color=color, stroke_width=width)

    def make_glow_dot(self):
        p = VGroup(Dot(color=YELLOW))
        for k in (1, 2, 3):
            p.add(Circle(radius=0.07 + 0.02 * k, stroke_color=YELLOW,
                         stroke_width=3, stroke_opacity=0.6 / k))
        return p

    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(p0, p1, color=color, stroke_width=5),
            *[Line(p0, p1, color=color, stroke_width=5 + 8 * k, stroke_opacity=0.5 / k)
              for k in (1, 2, 3)],
        )

    def animate_point_pair(self, zc, wc, th0, th1, run_time=2.0):
        """z 平面单位圆上 θ: th0→th1 的发光点，与 w=z² 的像（角度加倍）同步移动。"""
        pz, pw = self.make_glow_dot(), self.make_glow_dot()
        tracker = ValueTracker(th0)

        def update(_):
            th = tracker.get_value()
            pz.move_to(zc + np.array([np.cos(th), np.sin(th), 0]))
            pw.move_to(wc + np.array([np.cos(2 * th), np.sin(2 * th), 0]))
        pz.add_updater(update)
        pw.add_updater(update)

        self.play(FadeIn(pz), FadeIn(pw), run_time=0.4)
        self.play(tracker.animate.set_value(th1), run_time=run_time, rate_func=smooth)
        self.play(FadeOut(pz), FadeOut(pw), run_time=0.4)
        pz.clear_updaters()
        pw.clear_updaters()

    def animate_point_pairs(self, zc, wc, pairs, run_time=2.0):
        """同时播放多组发光点对。pairs: [(th0, th1, r), ...]，
        r 是 z 平面圆半径（w 像半径 r²），可省略（默认 1.0）。"""
        dots, trackers = [], []
        for item in pairs:
            th0, th1 = item[0], item[1]
            r = item[2] if len(item) > 2 else 1.0
            pz, pw = self.make_glow_dot(), self.make_glow_dot()
            tracker = ValueTracker(th0)

            def update(_, tr=tracker, r=r, pz=pz, pw=pw):   # ← 默认参数绑定，闭包不共享
                th = tr.get_value()
                pz.move_to(zc + r * np.array([np.cos(th), np.sin(th), 0]))
                pw.move_to(wc + r**2 * np.array([np.cos(2 * th), np.sin(2 * th), 0]))
            pz.add_updater(update)
            pw.add_updater(update)
            update(pz)          # ← 立即定位到路径起点，不等第一帧
            update(pw) 

            dots += [pz, pw]
            trackers.append((tracker, th1))

        self.play(*[FadeIn(p) for p in dots], run_time=0.4)
        self.play(*[tr.animate.set_value(b1) for tr, b1 in trackers],
                  run_time=run_time, rate_func=smooth)
        self.play(*[FadeOut(p) for p in dots], run_time=0.4)
        for p in dots:
            p.clear_updaters()

    def mapped_glow_line(self, direction, side, color, wc, Lz=1.5, off=0.02, n_glow=3):
        """z 实轴一侧边沿在 w=z^2 下的像：dz = s·dir + i·side·off，像为 dz^2 的抛物线段。
        side=+1 上沿 / -1 下沿；负实轴的像自动落到 w 正实轴（并与正实轴红蓝交叉）。"""
        dir_x = 1 if np.allclose(direction, RIGHT) else -1

        def w_of(s):
            dz = s * dir_x + 1j * side * off
            w = dz * dz
            return wc + np.array([w.real, w.imag, 0])

        return VGroup(*(
            ParametricFunction(w_of, t_range=[0, Lz], color=color,
                               stroke_width=5 + 8 * k,
                               stroke_opacity=1.0 if k == 0 else 0.5 / k)
            for k in range(n_glow + 1)
        ))

    def edge_flash(self, zc, wc, direction, run_time=0.5, hold=1.0):
        """z 实轴一侧（上红下蓝）与其 w=z^2 像（抛物线段）同步突出、同步淡出。"""
        Lz, off = 1.5, 0.05
        lines = VGroup(
            self.glow_line(zc + off * UP, zc + Lz * direction + off * UP, RED),
            self.glow_line(zc - off * UP, zc + Lz * direction - off * UP, BLUE),
            self.mapped_glow_line(direction, +1, RED, wc),
            self.mapped_glow_line(direction, -1, BLUE, wc),
        )
        self.play(FadeIn(lines, run_time=run_time))
        self.wait(hold)
        self.play(FadeOut(lines, run_time=run_time))

    # ---------- 主流程 ----------
    def construct(self):
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES)

        zc, wc = LEFT * 3.4, RIGHT * 3.4
        z_box = Square(3, stroke_color=WHITE).move_to(zc)
        w_box = Square(5, stroke_color=WHITE).move_to(wc)
        z_lab = MathTex("z").next_to(z_box, UP, buff=0.15)
        w_lab = MathTex("w").next_to(w_box, UP, buff=0.15)
        title = MathTex(r"w=z^2").scale(1.2).to_corner(UL)
        self.add(z_box, w_box, z_lab, w_lab, title)
        self.add(
            self.add_ticks(z_box, (-1, 0, 1), (-1, 0, 1)),       
            self.add_ticks(w_box, (-2, -1, 0, 1, 2), (-2, -1, 0, 1, 2)), 
        )

        # 1. 极网格入场，z 平面保留静态副本
        upper = self.polar_half(zc, 0, 180, RED,stroke_width=4)
        lower = self.polar_half(zc, 180, 360, BLUE)
        self.play(FadeIn(upper), FadeIn(lower), run_time=1.2)
        self.wait(0.5)
        self.add(upper.copy(), lower.copy())          # z 平面的常驻副本

        # 2. 上半平面：平移到 w，角度加倍（第一叶）
        self.play(upper.animate.shift(wc - zc), run_time=1.5)
        self.play(*[Transform(m, self.doubled_flat(m, wc)) for m in upper], run_time=2)
        self.wait(0.5)

        # 3. 下半平面：同上（第二叶）
        self.play(lower.animate.shift(wc - zc), run_time=1.5)
        self.play(*[Transform(m, self.doubled_flat(m, wc)) for m in lower], run_time=2)
        self.wait(0.5)

        self.animate_point_pairs(zc, wc, [
            (PI / 6, -PI / 6, 1.0),    
            (5*PI / 6, 7*PI / 6, 1.0)
        ])

        # 新增2b/2c：负实轴、正实轴的上下边沿同步高亮
        self.edge_flash(zc, wc, LEFT)
        self.edge_flash(zc, wc, RIGHT)

        # 4. 运镜
        self.move_camera(phi=62 * DEGREES, theta=-35 * DEGREES,
                         frame_center=wc, run_time=4, rate_func=smooth)
        self.wait(0.5)

        # 5. 赋予竖直坐标：平摊双叶连续"长"成立体黎曼面（Transform 逐点插值）
        upper_3d = VGroup(*[self.lifted(m, wc) for m in upper])
        lower_3d = VGroup(*[self.lifted(m, wc) for m in lower])
        self.play(
            *[Transform(m, t) for m, t in zip(upper, upper_3d)],
            *[Transform(m, t) for m, t in zip(lower, lower_3d)],
            run_time=3,
            rate_func=smooth,
        )
        self.wait(1)

class ExpRiemann(ThreeDScene):
    A_HALF = 1.3     # hline 的 Re z 半宽（映射安全范围，|w|=e^a 一个数量级）
    BAND_W = 2.6     # 带显示宽（a 方向 ±1.3）
    BAND_H = 1.3     # 带显示高（b 方向 2π 压缩）
    GAP = 0.0            # 三条带之间无间隔
    S_W = 1.6            # 平移过程中的缩放：2.6 × 1.6 ≈ 4.2（目标框边长）
    TARGET = 4.2         # w 框内的落点矩形边长

    # ---------- 构件 ----------
    def rect_band(self, center, b0, color):
        """横放带：水平=a，竖直=b（压缩）。meta 存真实值。"""
        sb = self.BAND_H / (2 * PI)
        grid = VGroup()
        for a in (-1.2, -0.6, 0.0, 0.6, 1.2):       # a=const -> 竖直线 -> w 圆
            line = Line(center + np.array([a, -self.BAND_H / 2, 0]),
                        center + np.array([a, self.BAND_H / 2, 0]),
                        color=color, stroke_width=2)
            line.meta = ("vline", a, b0)
            grid.add(line)
        for k in (1, 2, 3, 4, 5):                   # b=const -> 水平线 -> w 射线
            b = b0 + k * PI / 3
            y = (b - b0 - PI) * sb
            line = Line(center + np.array([-self.BAND_W / 2, y, 0]),
                        center + np.array([self.BAND_W / 2, y, 0]),
                        color=color, stroke_width=2)
            line.meta = ("hline", b, self.A_HALF)
            grid.add(line)
        return grid

    def y_of_b(self, b):
        """数学 b -> 屏幕 y（三条带竖直叠放；带间有 GAP）。"""
        sb = self.BAND_H / (2 * PI)
        step = self.BAND_H + self.GAP
        if b > PI:
            return step + (b - 2 * PI) * sb
        if b < -PI:
            return -step + (b + 2 * PI) * sb
        return b * sb

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
            return ParametricFunction(
                lambda t: center + np.array([np.exp(a) * np.cos(t),
                                             np.exp(a) * np.sin(t), 0.5*t]),
                t_range=[b0, b0 + 2 * PI], color=color, stroke_width=width)
        _, b, a_half = m.meta
        return ParametricFunction(
            lambda t: center + np.array([np.exp(t) * np.cos(b),
                                         np.exp(t) * np.sin(b), 0.5*b]),
            t_range=[-a_half, a_half], color=color, stroke_width=width)

    def make_glow_dot(self):
        p = VGroup(Dot(color=YELLOW))
        for k in (1, 2, 3):
            p.add(Circle(radius=0.07 + 0.02 * k, stroke_color=YELLOW,
                         stroke_width=3, stroke_opacity=0.6 / k))
        return p

    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(p0, p1, color=color, stroke_width=5),
            *[Line(p0, p1, color=color, stroke_width=5 + 8 * k, stroke_opacity=0.5 / k)
              for k in (1, 2, 3)],
        )

    def mapped_glow_line(self, side, color, wc, off=0.02, n_glow=3):
        """接缝 b=π 一侧：z = t + i(π + side·off) 的像 w = e^t·e^{i(π+side·off)}。"""
        def w_of(t):
            w = np.exp(t + 1j * (PI + side * off))
            return wc + np.array([w.real, w.imag, 0])
        return VGroup(*(
            ParametricFunction(w_of, t_range=[-self.A_HALF, self.A_HALF], color=color,
                               stroke_width=5 + 8 * k,
                               stroke_opacity=1.0 if k == 0 else 0.5 / k)
            for k in range(n_glow + 1)
        ))

    def animate_point_pairs(self, zc, wc, pairs, run_time=2.5):
        """多对发光点：z 点竖直移动（可跨带缝），w 点同步绕圆。"""
        dots, trackers = [], []
        for item in pairs:
            b0, b1 = item[0], item[1]
            a = item[2] if len(item) > 2 else 0.0
            pz, pw = self.make_glow_dot(), self.make_glow_dot()
            tracker = ValueTracker(b0)

            def update(_, tr=tracker, a=a, pz=pz, pw=pw):
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

    def edge_flash(self, zc, wc, run_time=0.5, hold=1.0):
        """接缝 = 主带上边缘（b=π）：z 侧横线上下沿红蓝，w 侧为负实轴弯曲射线。"""
        yj, off = self.BAND_H / 2, 0.05
        lines = VGroup(
            self.glow_line(zc + np.array([-1.3, yj - off, 0]),
                           zc + np.array([1.3, yj - off, 0]), RED),    # b→π⁻
            self.glow_line(zc + np.array([-1.3, yj + off, 0]),
                           zc + np.array([1.3, yj + off, 0]), BLUE),   # b→π⁺
            self.mapped_glow_line(+1, RED, wc),
            self.mapped_glow_line(-1, BLUE, wc),
        )
        self.play(FadeIn(lines, run_time=run_time))
        self.wait(hold)
        self.play(FadeOut(lines, run_time=run_time))

    def add_ticks(self, box, x_vals, y_vals, x_labels=None, y_labels=None,
                  tick_len=0.12, font_size=30):
        x0, y0 = box.get_center()[0], box.get_center()[1]
        hx, hy = box.width / 2, box.height / 2
        x_labels = x_labels or [str(v) for v in x_vals]
        y_labels = y_labels or [str(v) for v in y_vals]
        group = VGroup()
        for x, lab in zip(x_vals, x_labels):
            p = np.array([x0 + x, y0 - hy, 0])
            tick = Line(p, p + DOWN * tick_len, color=WHITE, stroke_width=2)
            num = MathTex(lab, color=WHITE, font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)
        for y, lab in zip(y_vals, y_labels):
            p = np.array([x0 - hx, y0 + y, 0])
            tick = Line(p, p + LEFT * tick_len, color=WHITE, stroke_width=2)
            num = MathTex(lab, color=WHITE, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)
        return group

    # ---------- 主流程 ----------
    def construct(self):
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES)

        zg, wc = LEFT * 4.0, RIGHT * 2.8
        step = self.BAND_H + self.GAP
        title = MathTex(r"w=e^z").scale(1.2).to_corner(UL)
        # 大 z 框：包住三带（半高 step + BAND_H/2 + 标签）与横向余量；关键字参数
        z_frame = Rectangle(width=self.BAND_W + 0.8,
                            height=2 * step + self.BAND_H + 0.6,
                            stroke_color=WHITE).move_to(zg)
        w_box = Square(7.6, stroke_color=WHITE).move_to(wc)
        self.add(title, z_frame, w_box)
        self.add(self.add_ticks(w_box, (0, 1, 2, 3), (0, 1, 2, 3),
                                y_labels=["0", r"i", r"2i", r"3i"]))
        b_ticks = (-3 * PI, -PI, 0.0, PI, 3 * PI)
        self.add(self.add_ticks(
            z_frame,
            x_vals=(-1.2, -0.6, 0.0, 0.6, 1.2),                 # Re z，恰在网格线上
            y_vals=tuple(self.y_of_b(b) for b in b_ticks),      # Im z 的屏幕位置
            y_labels=[r"-3\pi i", r"-\pi i", "0", r"\pi i", r"3\pi i"],
        ))

        # 三条带竖直叠放
        band_defs = [(-3 * PI, TEAL, r"-3\pi<\mathrm{Im}\,z<-\pi"),
                     (-PI, RED, r"-\pi<\mathrm{Im}\,z<\pi"),
                     (PI, BLUE, r"\pi<\mathrm{Im}\,z<3\pi")]
        grids, centers = [], []
        for i, (b0, color, tex) in enumerate(band_defs):
            c = zg + (i - 1) * step * UP
            grids.append(self.rect_band(c, b0, color))
            centers.append(c)

        # 依次映射：主带 -> 下带 -> 上带
        for idx in (1, 0, 2):
            grid = grids[idx]
            grid1 = grid.copy()
            self.play(FadeIn(grid), FadeIn(grid1), run_time=0.8)
            self.play(grid.animate.shift(wc - centers[idx]).scale(self.S_W),
                      run_time=1.5)                       # 飞入 + 收拢到目标框
            self.play(*[Transform(m, self.mapped_flat(m, wc)) for m in grid],
                      run_time=2)                          # 从矩形展开成极网格
            self.wait(0.4)

        self.animate_point_pairs(zg, wc, [
            (PI / 2, 3 * PI / 2, 0.0),
            (-PI / 2, -3 * PI / 2, 0.6),
        ])
        self.edge_flash(zg, wc)

        self.move_camera(phi=72 * DEGREES, theta=-30 * DEGREES,
                         frame_center=wc, zoom=0.55,
                         run_time=5, rate_func=smooth)
        self.wait(0.5)
        flat_all = VGroup(*[m for g in grids for m in g])
        targets = VGroup(*[self.lifted(m, wc) for m in flat_all])
        self.play(*[Transform(m, t) for m, t in zip(flat_all, targets)],
                  run_time=3, rate_func=smooth)
        self.wait(1)

class CosRiemann(ThreeDScene):
    BAND_XW = 1.5        # 带显示宽（π 压缩）
    BAND_YH = 5.0        # 带显示高（y ±5 压缩）
    GAP = 0.0            # 带间无间隔
    S_ZW = 1.2           # z 网格飞入 w 时的缩放
    R_MAX = 3.0          # w 网格半径上限（圆与射线同）
    # 三条 π 宽带：z = off + sgn·arccos(w)
    BANDS = [(0.0, -1.0), (0.0, +1.0), (2 * PI, -1.0)]
    RHO_LIST = (0.4, 0.8, 1.2, 1.8, 2.4, 3.0)   # 圆排到 r=3（>1 分段）

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
            # rho>1 的圆跨 arccos 分支切：拆两段，段内连续
            ivals = [(0, 2 * PI)] if rho < 1 else [(0.02, PI), (PI, 2 * PI - 0.02)]
            for t0, t1 in ivals:
                def f(t, rho=rho):
                    return self.z_screen(self.band_z(rho * np.exp(1j * t), b), b)
                s = ParametricFunction(f, t_range=[t0, t1], color=color, stroke_width=2)
                s.meta = ("wcirc", rho, t0, t1)
                segs.add(s)
        for j in range(16):                      # 角度间隔 pi/8
            phi = j * PI / 8
            if j % 8 == 0:
                phi += eps
            def f(t, phi=phi):
                return self.z_screen(self.band_z(t * np.exp(1j * phi), b), b)
            s = ParametricFunction(f, t_range=[0.15, self.R_MAX], color=color, stroke_width=2)
            s.meta = ("wray", phi)
            segs.add(s)
        return segs

    def w_target(self, meta, color, width):
        """与 z 侧源同参数同区间，保证 Transform 点序一一对应（消除扫掠 chord）。"""
        if meta[0] == "wcirc":
            _, rho, t0, t1 = meta
            def f(t, rho=rho):
                return self.wc + rho * np.array([np.cos(t), np.sin(t), 0])
            return ParametricFunction(f, t_range=[t0, t1], color=color, stroke_width=width, use_smoothing=False)
        phi = meta[1]
        def f(t, phi=phi):
            return self.wc + t * np.array([np.cos(phi), np.sin(phi), 0])
        return ParametricFunction(f, t_range=[0.15, self.R_MAX], color=color, stroke_width=width, use_smoothing=False)

    def lifted_seg(self, meta, b, color, width):
        """w 平面上的黎曼面曲线：底面 (Re w, Im w)，高度 Re z。"""
        def pt(w):
            z = self.band_z(w, b)
            return self.wc + np.array([w.real, w.imag, 0.8*z.real])
        if meta[0] == "wcirc":
            _, rho, t0, t1 = meta
            def f(t, rho=rho):
                return pt(rho * np.exp(1j * t))
            return ParametricFunction(f, t_range=[t0, t1], color=color, stroke_width=width)
        phi = meta[1]
        def f(t, phi=phi):
            return pt(t * np.exp(1j * phi))
        return ParametricFunction(f, t_range=[0.15, self.R_MAX], color=color, stroke_width=width)

    # ---------- 通用构件 ----------
    def make_glow_dot(self):
        p = VGroup(Dot(color=YELLOW))
        for k in (1, 2, 3):
            p.add(Circle(radius=0.07 + 0.02 * k, stroke_color=YELLOW,
                         stroke_width=3, stroke_opacity=0.6 / k))
        return p

    def glow_line(self, p0, p1, color):
        return VGroup(
            Line(p0, p1, color=color, stroke_width=5),
            *[Line(p0, p1, color=color, stroke_width=5 + 8 * j, stroke_opacity=0.5 / j)
              for j in (1, 2, 3)],
        )

    def add_ticks(self, box, x_vals, y_vals, x_labels=None, y_labels=None,
                  tick_len=0.12, font_size=20):
        x0, y0 = box.get_center()[0], box.get_center()[1]
        hx, hy = box.width / 2, box.height / 2
        x_labels = x_labels or [str(v) for v in x_vals]
        y_labels = y_labels or [str(v) for v in y_vals]
        group = VGroup()
        for x, lab in zip(x_vals, x_labels):
            p = np.array([x0 + x, y0 - hy, 0])
            tick = Line(p, p + DOWN * tick_len, color=WHITE, stroke_width=2)
            num = MathTex(lab, color=WHITE, font_size=font_size)
            num.next_to(tick, DOWN, buff=0.08)
            group.add(tick, num)
        for y, lab in zip(y_vals, y_labels):
            p = np.array([x0 - hx, y0 + y, 0])
            tick = Line(p, p + LEFT * tick_len, color=WHITE, stroke_width=2)
            num = MathTex(lab, color=WHITE, font_size=font_size)
            num.next_to(tick, LEFT, buff=0.08)
            group.add(tick, num)
        return group

    def animate_point_pairs(self, pairs, run_time=2.5):
        """pairs: [(z0, z1), ...]。z 点沿线段 z0→z1 移动，w=cos(z) 同步移动。
        z0/z1 须落在同一条带内；本例带 (π,2π) 为 BANDS[2]。"""
        dots, trackers = [], []
        for z0, z1 in pairs:
            pw = self.make_glow_dot()
            pz = self.make_glow_dot()
            tracker = ValueTracker(0.0)

            def update(_, tr=tracker, z0=z0, z1=z1, pw=pw, pz=pz):
                z = z0 + tr.get_value() * (z1 - z0)          # 直线插值
                w = np.cos(z)
                pz.move_to(self.z_screen(z, 2))              # 带 (π,2π)
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
                lines.add(ParametricFunction(
                    w_of, t_range=[-2.5, 2.5], color=color,
                    stroke_width=5 + 8 * j, stroke_opacity=1.0 if j == 0 else 0.5 / j))
        self.play(FadeIn(lines, run_time=run_time))
        self.wait(hold)
        self.play(FadeOut(lines, run_time=run_time))

    # ---------- 主流程 ----------
    def construct(self):
        self.set_camera_orientation(phi=0 * DEGREES, theta=-90 * DEGREES)
        self.zg, self.wc = LEFT * 4.2, RIGHT * 2.9
        step = self.BAND_XW + self.GAP
        self.centers = {b: self.zg + (b - 1) * step * RIGHT for b in (0, 1, 2)}

        title = MathTex(r"w=\cos z").scale(1.2).to_corner(UL)
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
        self.edge_flash()

        self.move_camera(phi=72 * DEGREES, theta=-30 * DEGREES,
                         frame_center=self.wc, zoom=0.7,
                         run_time=4, rate_func=smooth)
        self.wait(0.5)
        self.play(*[
            Transform(seg, self.lifted_seg(seg.key[0], seg.key[1],
                                           seg.get_stroke_color(), 2))
            for seg in w_segs
        ], run_time=2.5, rate_func=smooth)
        self.wait(0.5)

        # 环绕竖直轴一整圈（theta +360°，匀速）
        self.move_camera(theta=(-30 + 360) * DEGREES,
                         run_time=8, rate_func=linear)
        self.wait(1)
