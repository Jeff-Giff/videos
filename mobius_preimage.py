# -*- coding: utf-8 -*-
r"""
Möbius 变换下坐标线原像的动画（manim community edition）
运行: manim -pqh mobius_preimage.py Pullback
      manim -pqh mobius_preimage.py GridMorph
      manim -pqh mobius_preimage.py PolarGridMorph

LaTeX / 中文说明:
  * 数学公式一律用 MathTex（自动进入数学模式；\dfrac 等命令在 Tex 的
    文本模式下会直接报 LaTeX 错）。默认模板已加载 amsmath/amssymb。
  * 中文标签用 Text（Pango 渲染，不经过 LaTeX，无需任何额外安装）。
  * 若想把中文和公式混排在同一个 LaTeX 对象里，改用 ctex 模板:
        my_tpl = TexTemplateLibrary.ctex
        title = Tex(r"$w=\dfrac{z-1}{z+1}$ 平面", tex_template=my_tpl)
    前提是系统装有 ctex 宏包与 xelatex（TeX Live:
    `tlmgr install ctex` 或发行版包 texlive-lang-chinese）。
"""
from manim import *
import numpy as np

# w = f(z) = (z - 1)/(z + 1):  z = 1 -> w = 0,  z = -1 -> w = ∞
def _mobius_core(z, a, b, s=1.0):
    """z -> s(z+a)/(z+b)，极点为 -b；输入可以是标量或数组，
    极点处沿原方向甩到 1e6 远处（模拟无穷远）"""
    z_arr = np.atleast_1d(np.asarray(z, dtype=complex))
    with np.errstate(all="ignore"):
        w = s * (z_arr + a) / (z_arr + b)
    bad = ~np.isfinite(w)
    if np.any(bad):
        dz = z_arr[bad] + b
        w[bad] = 1e6 * dz / (np.abs(dz) + 1e-12)
    return w

def mobius(z):
    w = _mobius_core(z, -1.0, 1.0)   # f(z)   = (z-1)/(z+1)
    return w[0] if np.ndim(z) == 0 else w

def mobius_inv(w):
    z = _mobius_core(w, 1.0, -1.0, s=-1.0)   # f^{-1}(w) = (w+1)/(1-w)
    return z[0] if np.ndim(w) == 0 else z

# ---------- 精确原像曲线（w=(z-1)/(z+1) 的特例，焦点为 ±1） ----------
def apollonius_circle(r):
    """|w| = r 的原像: |z-1| = r|z+1|，即关于 ±1 的阿波罗尼奥斯圆"""
    if abs(r - 1.0) < 1e-6:
        return Line([0, -4, 0], [0, 4, 0])            # r=1 -> 虚轴
    c = (1 + r**2) / (1 - r**2)
    rad = 2 * r / abs(1 - r**2)
    return Circle(radius=rad).shift(c * RIGHT)

def through_foci_circle(theta):
    """arg w = θ 的原像: 过 z=±1 的圆（圆心 -i cotθ，半径 cscθ）"""
    if abs(np.sin(theta)) < 1e-6:
        return VGroup(Line([-4, 0, 0], [-1, 0, 0]), Line([1, 0, 0], [4, 0, 0]))
    c = -1.0 / np.tan(theta)
    rad = 1.0 / abs(np.sin(theta))
    return Circle(radius=rad).shift(c * UP)

RS = [0.35, 0.55, 0.8, 1.25, 1.8, 2.9]
THETAS = [np.pi/12, np.pi/6, np.pi/4, np.pi/3, 5*np.pi/12]

def polar_grid():       # w 平面中的极坐标网
    circles = VGroup(*[Circle(radius=r) for r in RS])
    rays = VGroup(*[Line([0, 0, 0], [4*np.cos(t), 4*np.sin(t), 0]) for t in THETAS])
    return VGroup(circles, rays)

def bipolar_grid():     # 极坐标网在 z 平面的原像
    apo = VGroup(*[apollonius_circle(r).set_color(BLUE) for r in RS])
    thr = VGroup(*[through_foci_circle(t).set_color(RED) for t in THETAS])
    return VGroup(apo, thr)

class GridMorph(Scene):
    """直角坐标网格在 w=(z-1)/(z+1) 下的像"""
    def construct(self):
        grid = NumberPlane(x_range=[-5, 5, 1], y_range=[-3.5, 3.5, 1])
        grid.prepare_for_nonlinear_transform()
        formula = MathTex(r"w=\dfrac{z-1}{z+1}").to_corner(UR)
        self.add(grid, formula)
        self.play(grid.animate.apply_complex_function(mobius), run_time=8)
        self.wait()

class PolarGridMorph(Scene):
    """极坐标网被 f^{-1} 拉回 z 平面 -> 双极坐标网（阿波罗尼奥斯圆 + 过 ±1 的圆）"""
    def construct(self):
        pg = polar_grid()
        pg[0].set_color(BLUE); pg[1].set_color(RED)
        self.add(pg)
        self.wait()
        self.play(pg.animate.apply_complex_function(mobius_inv), run_time=8)
        self.wait()

class Pullback(Scene):
    """左右对照: 左 z 平面画精确原像(双极坐标网), 右 w 平面画极坐标网,
       动点沿对应曲线同步移动, 展示一一对应"""
    def construct(self):
        plane_z = ComplexPlane(x_range=[-4, 4], y_range=[-3, 3])
        plane_w = ComplexPlane(x_range=[-4, 4], y_range=[-3, 3])
        label_z = Text("z 平面", font_size=34).next_to(plane_z, DOWN)
        label_w = Text("w 平面", font_size=34).next_to(plane_w, DOWN)
        gz = VGroup(plane_z, label_z, bipolar_grid())
        gw = VGroup(plane_w, label_w, polar_grid())
        gz[2][0].set_color(BLUE); gz[2][1].set_color(RED)
        gw[2][0].set_color(BLUE); gw[2][1].set_color(RED)
        gz.scale(0.72).shift(LEFT * 3.4)
        gw.scale(0.72).shift(RIGHT * 3.4)
        self.add(gz, gw)

        title = MathTex(r"w=\dfrac{z-1}{z+1}", font_size=44).to_edge(UP)
        self.play(Write(title))

        # 对应关系 1: |w|=1.8 的圆  <->  阿波罗尼奥斯圆
        r = 1.8
        dot_z = Dot(color=YELLOW)
        dot_w = Dot(color=YELLOW)
        gz.add(dot_z); gw.add(dot_w)
        t = ValueTracker(0.0)
        # z 在 |z-1| = r|z+1| 上: 圆心 c0, 半径 rad0
        c0 = (1 + r**2) / (1 - r**2); rad0 = 2 * r / abs(1 - r**2)
        dot_z.add_updater(lambda d: d.move_to(
            (c0 + rad0*np.cos(t.get_value())) * RIGHT
            + rad0*np.sin(t.get_value()) * UP))
        dot_w.add_updater(lambda d: d.move_to(
            r*np.cos(r*0 + t.get_value()) * RIGHT + r*np.sin(t.get_value()) * UP))
        self.add(dot_z, dot_w)
        self.play(t.animate.set_value(TAU), run_time=6, rate_func=linear)
        self.wait(0.5)

        # 对应关系 2: arg w = π/4 的射线  <->  过 ±1 的圆
        theta = np.pi/4
        dot2_z = Dot(color=GREEN)
        dot2_w = Dot(color=GREEN)
        gz.add(dot2_z); gw.add(dot2_w)
        t2 = ValueTracker(0.01)
        cc = -1/np.tan(theta); rr = 1/abs(np.sin(theta))
        dot2_z.add_updater(lambda d: d.move_to(
            cc * UP + rr*np.cos(t2.get_value()) * RIGHT + rr*np.sin(t2.get_value()) * UP))
        dot2_w.add_updater(lambda d: d.move_to(
            t2.get_value() * np.cos(theta) * RIGHT + t2.get_value() * np.sin(theta) * UP))
        self.add(dot2_z, dot2_w)
        self.play(t2.animate.set_value(3.6), run_time=5, rate_func=linear)
        self.wait()