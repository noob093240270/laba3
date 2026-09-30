import colorsys
import math
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

from PIL import Image, ImageDraw, ImageTk

import raster

CANVAS_W, CANVAS_H = 900, 600
MAX_W, MAX_H = 1400, 900
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE_TYPES = [('Изображения', '*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff'),
               ('Все файлы', '*.*')]
NEAREST = getattr(Image, 'Resampling', Image).NEAREST


def rgb_to_hex(c):
    return '#%02x%02x%02x' % tuple(c[:3])


class ColorButton(ttk.Frame):
    def __init__(self, master, text, color):
        super().__init__(master)
        self.color = tuple(color)
        self.swatch = tk.Label(self, width=3, bg=rgb_to_hex(color), relief='solid', bd=1)
        self.swatch.pack(side='left', padx=(0, 6))
        ttk.Button(self, text=text, command=self.choose).pack(side='left', fill='x', expand=True)

    def choose(self):
        rgb, _ = colorchooser.askcolor(color=rgb_to_hex(self.color), parent=self)
        if rgb:
            self.color = tuple(int(v) for v in rgb)
            self.swatch.config(bg=rgb_to_hex(self.color))


class PaintCanvas(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, width=CANVAS_W, height=CANVAS_H, bg='white',
                                highlightthickness=0, cursor='crosshair')
        self.canvas.pack()
        self.image = Image.new('RGB', (CANVAS_W, CANVAS_H), WHITE)
        self.photo = ImageTk.PhotoImage(self.image)
        self.item = self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.pen_color, self.pen_width = BLACK, 1
        self._last = None

    def set_image(self, img):
        self.image = img
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.itemconfig(self.item, image=self.photo)
        self.canvas.config(width=img.width, height=img.height)

    def show(self, img=None):
        self.photo.paste(self.image if img is None else img)

    def clear(self):
        self.set_image(Image.new('RGB', (CANVAS_W, CANVAS_H), WHITE))

    def open_file(self, path):
        img = Image.open(path).convert('RGB')
        if img.width > MAX_W or img.height > MAX_H:
            img = img.crop((0, 0, min(img.width, MAX_W), min(img.height, MAX_H)))
        self.set_image(img)

    def pen_down(self, x, y):
        self._last = (x, y)
        self._segment(x, y, x, y)
        self.show()

    def pen_move(self, x, y):
        if self._last is not None:
            self._segment(*self._last, x, y)
            self._last = (x, y)
            self.show()

    def pen_up(self):
        self._last = None

    def _segment(self, x0, y0, x1, y1):
        if self.pen_width <= 1:
            px, (w, h), c = self.image.load(), self.image.size, self.pen_color

            def plot(x, y):
                if 0 <= x < w and 0 <= y < h:
                    px[x, y] = c
            raster.bresenham_line(x0, y0, x1, y1, plot)
        else:
            d, r = ImageDraw.Draw(self.image), self.pen_width / 2
            d.line((x0, y0, x1, y1), fill=self.pen_color, width=self.pen_width)
            d.ellipse((x1 - r, y1 - r, x1 + r, y1 + r), fill=self.pen_color)


def int_from(var, default):
    try:
        return int(var.get())
    except (tk.TclError, ValueError):
        return default


def default_pattern():
    img = Image.new('RGB', (24, 24), (255, 236, 179))
    d = ImageDraw.Draw(img)
    d.ellipse((3, 3, 20, 20), fill=(229, 57, 53), outline=(140, 20, 20))
    d.rectangle((10, 10, 13, 13), fill=(255, 255, 255))
    return img


def draw_sample_region(img):
    d = ImageDraw.Draw(img)
    cx, cy = img.width // 2, img.height // 2
    R = min(cx, cy) - 40
    pts = []
    for i in range(360):
        a = math.radians(i)
        r = R * (0.75 + 0.2 * math.sin(5 * a) + 0.05 * math.cos(13 * a))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.line(pts + [pts[0]], fill=BLACK, width=2)
    d.ellipse((cx - 60, cy - 60, cx + 60, cy + 60), outline=BLACK, width=2)
    d.polygon([(cx + 120, cy - 40), (cx + 190, cy - 10), (cx + 140, cy + 60)], outline=BLACK)
    d.rectangle((cx - 165, cy - 30, cx - 105, cy + 30), outline=BLACK, width=4)
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), outline=BLACK, width=2)


class FillTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=6)
        panel = ttk.Frame(self, width=240)
        panel.pack(side='left', fill='y', padx=(0, 8))
        self.board = PaintCanvas(self)
        self.board.pack(side='left', anchor='nw')

        lf = ttk.LabelFrame(panel, text='Инструмент (ЛКМ)', padding=6)
        lf.pack(fill='x')
        self.tool = tk.StringVar(value='pen')
        ttk.Radiobutton(lf, text='Карандаш — рисовать область', variable=self.tool,
                        value='pen').pack(anchor='w')
        ttk.Radiobutton(lf, text='Заливка — щелчок внутри', variable=self.tool,
                        value='fill').pack(anchor='w')
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=(6, 0))
        ttk.Label(row, text='Толщина пера:').pack(side='left')
        self.width_var = tk.StringVar(value='1')
        ttk.Spinbox(row, from_=1, to=20, width=4, textvariable=self.width_var).pack(side='left', padx=4)
        self.pen_btn = ColorButton(lf, 'Цвет пера', BLACK)
        self.pen_btn.pack(fill='x', pady=(6, 0))

        lf2 = ttk.LabelFrame(panel, text='Заливка (ПКМ — всегда заливка)', padding=6)
        lf2.pack(fill='x', pady=8)
        self.fill_mode = tk.StringVar(value='color')
        ttk.Radiobutton(lf2, text='1а — заданным цветом', variable=self.fill_mode,
                        value='color').pack(anchor='w')
        ttk.Radiobutton(lf2, text='1б — рисунком из файла', variable=self.fill_mode,
                        value='pattern').pack(anchor='w')
        self.fill_btn = ColorButton(lf2, 'Цвет заливки', (255, 140, 0))
        self.fill_btn.pack(fill='x', pady=(6, 0))
        ttk.Button(lf2, text='Загрузить рисунок…', command=self.load_pattern).pack(fill='x', pady=(6, 0))
        self.pattern_info = ttk.Label(lf2, wraplength=210)
        self.pattern_info.pack(anchor='w', pady=(4, 0))
        self.pattern_preview = ttk.Label(lf2)
        self.pattern_preview.pack(anchor='w', pady=(4, 0))
        self.set_pattern(default_pattern(), 'встроенный')

        lf3 = ttk.LabelFrame(panel, text='Холст', padding=6)
        lf3.pack(fill='x')
        ttk.Button(lf3, text='Пример области с отверстиями', command=self.sample).pack(fill='x')
        ttk.Button(lf3, text='Открыть изображение…', command=self.open_image).pack(fill='x', pady=4)
        ttk.Button(lf3, text='Сохранить…', command=self.save).pack(fill='x')
        ttk.Button(lf3, text='Очистить', command=self.board.clear).pack(fill='x', pady=(4, 0))

        self.status = ttk.Label(panel, wraplength=220, text=(
            'Нарисуйте замкнутую область (внутри можно нарисовать отверстия), '
            'выберите «Заливка» и щёлкните внутри.\n\nМаленький рисунок повторяется '
            'циклически, из большого берётся фрагмент без масштабирования; '
            'центр рисунка совмещается с точкой щелчка.'))
        self.status.pack(fill='x', pady=8)

        c = self.board.canvas
        c.bind('<ButtonPress-1>', self.on_press)
        c.bind('<B1-Motion>', lambda e: self.board.pen_move(e.x, e.y))
        c.bind('<ButtonRelease-1>', lambda e: self.board.pen_up())
        c.bind('<Button-3>', lambda e: self.do_fill(e.x, e.y))

    def on_press(self, e):
        if self.tool.get() == 'fill':
            self.do_fill(e.x, e.y)
        else:
            self.board.pen_color = self.pen_btn.color
            self.board.pen_width = max(1, int_from(self.width_var, 1))
            self.board.pen_down(e.x, e.y)

    def do_fill(self, x, y):
        img = self.board.image
        if not (0 <= x < img.width and 0 <= y < img.height):
            return
        self.board.canvas.config(cursor='watch')
        self.update_idletasks()
        t = time.perf_counter()
        try:
            if self.fill_mode.get() == 'pattern':
                n = raster.scanline_fill(img, (x, y), pattern=self.pattern)
            else:
                n = raster.scanline_fill(img, (x, y), color=self.fill_btn.color)
        except (RecursionError, MemoryError) as e:
            messagebox.showerror('Заливка', f'Не хватило стека рекурсии: {e}')
            return
        finally:
            self.board.canvas.config(cursor='crosshair')
        self.board.show()
        self.status.config(text=f'Заливка из точки ({x}, {y}): закрашено {n} пикс. '
                                f'за {(time.perf_counter() - t) * 1000:.0f} мс')

    def set_pattern(self, img, name):
        self.pattern = img.convert('RGB')
        w, h = self.pattern.size
        self.pattern_info.config(text=f'Рисунок: {name}, {w}×{h}')
        thumb = self.pattern.copy()
        thumb.thumbnail((200, 110))
        if max(w, h) < 48:
            k = 48 // max(w, h)
            thumb = self.pattern.resize((w * k, h * k), NEAREST)
        self._thumb = ImageTk.PhotoImage(thumb)
        self.pattern_preview.config(image=self._thumb)

    def load_pattern(self):
        path = filedialog.askopenfilename(parent=self, filetypes=IMAGE_TYPES,
                                          initialdir=os.path.join(HERE, 'samples'))
        if path:
            try:
                self.set_pattern(Image.open(path), os.path.basename(path))
                self.fill_mode.set('pattern')
            except OSError as e:
                messagebox.showerror('Рисунок', str(e))

    def sample(self):
        self.board.clear()
        draw_sample_region(self.board.image)
        self.board.show()

    def open_image(self):
        path = filedialog.askopenfilename(parent=self, filetypes=IMAGE_TYPES)
        if path:
            self.board.open_file(path)

    def save(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.png',
                                            filetypes=[('PNG', '*.png')])
        if path:
            self.board.image.save(path)


def draw_border_example(img):
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, img.width, img.height), fill=(245, 245, 235))
    pts = [(80, 120), (260, 60), (400, 150), (360, 300), (420, 420), (200, 520), (120, 380), (160, 260)]
    d.polygon(pts, fill=(200, 230, 255))
    d.line(pts + [pts[0]], fill=(20, 60, 160), width=5)
    d.ellipse((190, 250, 290, 350), outline=(20, 60, 160), width=3)
    d.ellipse((500, 80, 820, 320), fill=(255, 240, 200), outline=(200, 30, 30), width=1)
    d.rectangle((600, 150, 660, 210), outline=(200, 30, 30), width=2)
    d.polygon([(520, 380), (860, 400), (700, 560), (650, 460), (560, 540)],
              fill=(220, 255, 220), outline=(0, 120, 0))


class BorderTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=6)
        panel = ttk.Frame(self, width=240)
        panel.pack(side='left', fill='y', padx=(0, 8))
        self.board = PaintCanvas(self)
        self.board.pack(side='left', anchor='nw')

        lf = ttk.LabelFrame(panel, text='Инструмент (ЛКМ)', padding=6)
        lf.pack(fill='x')
        self.tool = tk.StringVar(value='trace')
        ttk.Radiobutton(lf, text='Выделить границу — щелчок\nвнутри области', variable=self.tool,
                        value='trace').pack(anchor='w')
        ttk.Radiobutton(lf, text='Карандаш', variable=self.tool, value='pen').pack(anchor='w')
        row = ttk.Frame(lf)
        row.pack(fill='x', pady=(6, 0))
        ttk.Label(row, text='Толщина пера:').pack(side='left')
        self.width_var = tk.StringVar(value='1')
        ttk.Spinbox(row, from_=1, to=20, width=4, textvariable=self.width_var).pack(side='left', padx=4)

        lf2 = ttk.LabelFrame(panel, text='Параметры', padding=6)
        lf2.pack(fill='x', pady=8)
        self.tol_var = tk.IntVar(value=30)
        self.tol_label = ttk.Label(lf2, text='Допуск цвета: 30')
        self.tol_label.pack(anchor='w')
        ttk.Scale(lf2, from_=0, to=300, variable=self.tol_var,
                  command=lambda v: self.tol_label.config(text=f'Допуск цвета: {int(float(v))}')
                  ).pack(fill='x')
        self.line_btn = ColorButton(lf2, 'Цвет контура', (255, 0, 255))
        self.line_btn.pack(fill='x', pady=(6, 0))
        row2 = ttk.Frame(lf2)
        row2.pack(fill='x', pady=(6, 0))
        ttk.Label(row2, text='Толщина контура:').pack(side='left')
        self.thick_var = tk.StringVar(value='3')
        ttk.Spinbox(row2, from_=1, to=9, width=4, textvariable=self.thick_var).pack(side='left', padx=4)
        self.gradient = tk.BooleanVar(value=True)
        ttk.Checkbutton(lf2, text='Цвет по порядку обхода\n(красный → фиолетовый)',
                        variable=self.gradient).pack(anchor='w', pady=(6, 0))

        lf3 = ttk.LabelFrame(panel, text='Изображение', padding=6)
        lf3.pack(fill='x')
        ttk.Button(lf3, text='Пример изображения', command=self.example).pack(fill='x')
        ttk.Button(lf3, text='Открыть изображение…', command=self.open_image).pack(fill='x', pady=4)
        ttk.Button(lf3, text='Убрать контур', command=lambda: self.board.show()).pack(fill='x')
        ttk.Button(lf3, text='Сохранить результат…', command=self.save).pack(fill='x', pady=4)
        ttk.Button(lf3, text='Очистить', command=self.board.clear).pack(fill='x')

        self.status = ttk.Label(panel, wraplength=220, text=(
            'Щёлкните внутри области: от точки щелчка идём вправо до границы — '
            'это начальная точка (отмечена зелёным). Дальше граница обходится '
            'по часовой стрелке, точки заносятся в список. Зелёная линия — '
            'путь поиска начальной точки.'))
        self.status.pack(fill='x', pady=(8, 4))

        lst = ttk.Frame(panel)
        lst.pack(fill='both', expand=True)
        self.text = tk.Text(lst, width=26, height=10, font=('Consolas', 9))
        sb = ttk.Scrollbar(lst, command=self.text.yview)
        self.text.config(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.text.pack(side='left', fill='both', expand=True)

        c = self.board.canvas
        c.bind('<ButtonPress-1>', self.on_press)
        c.bind('<B1-Motion>', lambda e: self.board.pen_move(e.x, e.y))
        c.bind('<ButtonRelease-1>', lambda e: self.board.pen_up())
        self.example()

    def on_press(self, e):
        if self.tool.get() == 'trace':
            self.do_trace(e.x, e.y)
        else:
            self.board.pen_color = BLACK
            self.board.pen_width = max(1, int_from(self.width_var, 1))
            self.board.pen_down(e.x, e.y)

    def do_trace(self, x, y):
        img, tol = self.board.image, int(self.tol_var.get())
        start, bcolor = raster.find_border_start(img, x, y, tol)
        if start is None:
            self.status.config(text='Справа от точки щелчка граница не найдена.')
            return
        t = time.perf_counter()
        path = raster.trace_border(img, start, bcolor, tol)
        dt = (time.perf_counter() - t) * 1000

        view = img.copy()
        d, n = ImageDraw.Draw(view), len(path)
        k = max(1, int_from(self.thick_var, 1))
        lo, hi = (k - 1) // 2, k // 2
        for i, (px, py) in enumerate(path):
            if self.gradient.get():
                r, g, b = colorsys.hsv_to_rgb(0.8 * i / max(1, n - 1), 1, 1)
                col = (int(r * 255), int(g * 255), int(b * 255))
            else:
                col = self.line_btn.color
            d.rectangle((px - lo, py - lo, px + hi, py + hi), fill=col)
        sx, sy = start
        d.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), outline=(0, 170, 0), width=2)
        d.line((x, y, sx, sy), fill=(0, 170, 0))
        self.board.show(view)
        self.view = view

        lx, ly = path[-1]
        closed = n > 2 and max(abs(lx - sx), abs(ly - sy)) <= 1
        self.status.config(text=(
            f'Начальная точка ({sx}, {sy}), цвет границы {rgb_to_hex(bcolor)}.\n'
            f'Точек в списке: {n}, контур {"замкнут" if closed else "НЕ замкнут"}, '
            f'{dt:.1f} мс.'))
        limit = 5000
        lines = [f'{i:5}: ({px}, {py})' for i, (px, py) in enumerate(path[:limit])]
        if n > limit:
            lines.append(f'… ещё {n - limit}')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', '\n'.join(lines))

    def example(self):
        self.board.clear()
        draw_border_example(self.board.image)
        self.board.show()

    def open_image(self):
        path = filedialog.askopenfilename(parent=self, filetypes=IMAGE_TYPES,
                                          initialdir=os.path.join(HERE, 'samples'))
        if path:
            self.board.open_file(path)

    def save(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension='.png',
                                            filetypes=[('PNG', '*.png')])
        if path:
            getattr(self, 'view', self.board.image).save(path)


class LinesTab(ttk.Frame):
    SCALES = ('1', '2', '4', '6', '8', '12', '16')

    def __init__(self, master):
        super().__init__(master, padding=6)
        panel = ttk.Frame(self, width=240)
        panel.pack(side='left', fill='y', padx=(0, 8))
        self.canvas = tk.Canvas(self, width=CANVAS_W, height=CANVAS_H, bg='white',
                                highlightthickness=0, cursor='crosshair')
        self.canvas.pack(side='left', anchor='nw')

        lf = ttk.LabelFrame(panel, text='Алгоритм', padding=6)
        lf.pack(fill='x')
        self.algo = tk.StringVar(value='bres')
        ttk.Radiobutton(lf, text='Брезенхем (целочисленный)', variable=self.algo,
                        value='bres').pack(anchor='w')
        ttk.Radiobutton(lf, text='Ву (сглаживание)', variable=self.algo,
                        value='wu').pack(anchor='w')
        self.color_btn = ColorButton(lf, 'Цвет отрезка', BLACK)
        self.color_btn.pack(fill='x', pady=(6, 0))

        lf2 = ttk.LabelFrame(panel, text='Вид', padding=6)
        lf2.pack(fill='x', pady=8)
        row = ttk.Frame(lf2)
        row.pack(fill='x')
        ttk.Label(row, text='Увеличение пиксела:').pack(side='left')
        self.scale_var = tk.StringVar(value='6')
        cb = ttk.Combobox(row, values=self.SCALES, width=4, state='readonly', textvariable=self.scale_var)
        cb.pack(side='left', padx=4)
        cb.bind('<<ComboboxSelected>>', lambda e: self.new_image())
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(lf2, text='Сетка пикселов', variable=self.grid_var,
                        command=self.draw_grid).pack(anchor='w', pady=(6, 0))

        ttk.Button(panel, text='Сравнение (веер отрезков)', command=self.demo).pack(fill='x')
        ttk.Button(panel, text='Очистить', command=self.new_image).pack(fill='x', pady=4)
        self.status = ttk.Label(panel, wraplength=220, text=(
            'Нажмите ЛКМ в начальной точке и отпустите в конечной.\n'
            'Крупные пикселы помогают рассмотреть работу алгоритмов.'))
        self.status.pack(fill='x', pady=8)

        self.canvas.bind('<ButtonPress-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_release)
        self.start = None
        self.new_image()

    def new_image(self):
        self.s = int(self.scale_var.get())
        self.lw, self.lh = CANVAS_W // self.s, CANVAS_H // self.s
        self.image = Image.new('RGB', (self.lw, self.lh), WHITE)
        self.canvas.delete('all')
        self.photo = ImageTk.PhotoImage(self.image.resize((self.lw * self.s, self.lh * self.s), NEAREST))
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.draw_grid()

    def show(self):
        self.photo.paste(self.image.resize((self.lw * self.s, self.lh * self.s), NEAREST))

    def draw_grid(self):
        self.canvas.delete('grid')
        if self.grid_var.get() and self.s >= 4:
            s, W, H = self.s, self.lw * self.s, self.lh * self.s
            for x in range(0, W + 1, s):
                self.canvas.create_line(x, 0, x, H, fill='#e2e2e2', tags='grid')
            for y in range(0, H + 1, s):
                self.canvas.create_line(0, y, W, y, fill='#e2e2e2', tags='grid')
            self.canvas.tag_raise('label')

    def draw_line(self, x0, y0, x1, y1, algo):
        px, color, count = self.image.load(), self.color_btn.color, [0]
        w, h = self.lw, self.lh

        def plot(x, y):
            if 0 <= x < w and 0 <= y < h:
                px[x, y] = color
                count[0] += 1

        def plot_wu(x, y, a):
            if 0 <= x < w and 0 <= y < h and a > 0:
                old = px[x, y]
                px[x, y] = tuple(round(o + (c - o) * a) for o, c in zip(old, color))
                count[0] += 1

        if algo == 'bres':
            raster.bresenham_line(x0, y0, x1, y1, plot)
        else:
            raster.wu_line(x0, y0, x1, y1, plot_wu)
        return count[0]

    def cell(self, e):
        return (min(max(e.x // self.s, 0), self.lw - 1), min(max(e.y // self.s, 0), self.lh - 1))

    def on_press(self, e):
        self.start = self.cell(e)
        c = self.s // 2
        x, y = self.start[0] * self.s + c, self.start[1] * self.s + c
        self.canvas.delete('preview')
        self.canvas.create_line(x, y, e.x, e.y, fill='#3a7bd5', dash=(4, 3), tags='preview')

    def on_drag(self, e):
        if self.start:
            c = self.s // 2
            self.canvas.coords('preview', self.start[0] * self.s + c, self.start[1] * self.s + c, e.x, e.y)

    def on_release(self, e):
        if not self.start:
            return
        self.canvas.delete('preview')
        (x0, y0), (x1, y1) = self.start, self.cell(e)
        self.start = None
        algo = self.algo.get()
        t = time.perf_counter()
        n = self.draw_line(x0, y0, x1, y1, algo)
        dt = (time.perf_counter() - t) * 1000
        self.show()
        name = 'Брезенхем' if algo == 'bres' else 'Ву'
        self.status.config(text=f'{name}: ({x0}, {y0}) → ({x1}, {y1}), '
                                f'закрашено пикселов: {n}, {dt:.2f} мс')

    def demo(self):
        self.new_image()
        R = min(self.lw // 4, self.lh // 2) - 4
        for algo, cx in (('bres', self.lw // 4), ('wu', 3 * self.lw // 4)):
            cy = self.lh // 2 + 2
            for k in range(0, 360, 15):
                a = math.radians(k)
                self.draw_line(cx, cy, cx + round(R * math.cos(a)), cy - round(R * math.sin(a)), algo)
            self.canvas.create_text(cx * self.s, 14, text='Брезенхем' if algo == 'bres' else 'Ву',
                                    font=('Segoe UI', 12, 'bold'), fill='#1f4e9a', tags='label')
        self.show()
        self.status.config(text='Слева — алгоритм Брезенхема, справа — алгоритм Ву. '
                                'Отрезки во всех восьми октантах.')


def main():
    root = tk.Tk()
    root.title('Лабораторная работа №3. Растровые алгоритмы')
    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True)
    nb.add(FillTab(nb), text='  1а, 1б — Заливка  ')
    nb.add(BorderTab(nb), text='  1в — Выделение границы  ')
    nb.add(LinesTab(nb), text='  2 — Отрезки (Брезенхем, Ву)  ')
    root.mainloop()


if __name__ == '__main__':
    main()
