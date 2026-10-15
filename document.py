"""Raster operations and history, independent of the desktop interface."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

SHAPES = {
    "line": "Linha", "curve": "Curva", "ellipse": "Elipse",
    "rectangle": "Retângulo", "rounded": "Retângulo arredondado",
    "polygon": "Polígono", "triangle": "Triângulo", "right_triangle": "Triângulo retângulo",
    "diamond": "Losango", "pentagon": "Pentágono", "hexagon": "Hexágono",
    "right_arrow": "Seta à direita", "left_arrow": "Seta à esquerda",
    "up_arrow": "Seta para cima", "down_arrow": "Seta para baixo",
    "star4": "Estrela de quatro pontas", "star5": "Estrela de cinco pontas",
    "star6": "Estrela de seis pontas", "callout": "Balão retangular",
    "oval_callout": "Balão oval", "cloud": "Balão em nuvem", "heart": "Coração", "lightning": "Raio",
}

def shape(image, kind, start, end, color, background, width, outline=True, fill=False):
    draw = ImageDraw.Draw(image)
    if kind == "line":
        draw.line((start, end), fill=color, width=width)
        return
    x0, x1 = sorted((start[0], end[0]))
    y0, y1 = sorted((start[1], end[1]))
    box = (x0, y0, x1, y1)
    stroke, interior = color if outline else None, background if fill else None
    if not outline and not fill:
        return
    if kind in ("ellipse", "rectangle", "rounded"):
        method = {"ellipse": draw.ellipse, "rectangle": draw.rectangle, "rounded": draw.rounded_rectangle}[kind]
        kwargs = {"radius": max(1, min(x1-x0, y1-y0)//5)} if kind == "rounded" else {}
        method(box, fill=interior, outline=stroke, width=width, **kwargs)
        return
    coords = {
        "triangle": [(.5, 0), (1, 1), (0, 1)], "right_triangle": [(0, 0), (1, 1), (0, 1)],
        "diamond": [(.5, 0), (1, .5), (.5, 1), (0, .5)],
        "right_arrow": [(0, .3), (.6, .3), (.6, 0), (1, .5), (.6, 1), (.6, .7), (0, .7)],
        "lightning": [(.4, 0), (1, 0), (.62, .4), (.9, .4), (.1, 1), (.35, .55), (0, .55)],
        "callout": [(0, 0), (1, 0), (1, .75), (.45, .75), (.2, 1), (.25, .75), (0, .75)],
    }
    if kind in ("left_arrow", "up_arrow", "down_arrow"):
        points = coords["right_arrow"]
        if kind == "left_arrow": points = [(1-x, y) for x, y in points]
        elif kind == "up_arrow": points = [(y, 1-x) for x, y in points]
        else: points = [(y, x) for x, y in points]
    elif kind in ("pentagon", "hexagon") or kind.startswith("star"):
        n = int(kind[-1]) if kind.startswith("star") else {"pentagon": 5, "hexagon": 6}[kind]
        star = kind.startswith("star")
        count = n*2 if star else n
        points = [(.5+.5*(.42 if star and i%2 else 1)*math.cos(-math.pi/2+i*2*math.pi/count),
                   .5+.5*(.42 if star and i%2 else 1)*math.sin(-math.pi/2+i*2*math.pi/count)) for i in range(count)]
    elif kind == "heart":
        points = []
        for i in range(100):
            t = i*2*math.pi/100
            points.append((.5+16*math.sin(t)**3/34, .48-(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))/32))
    elif kind == "cloud":
        points = []
        for i in range(160):
            t = i*2*math.pi/160
            radius = 1 + .09*math.sin(t*9)
            points.append((.5+.44*radius*math.cos(t), .4+.34*radius*math.sin(t)))
        points += [(.3, .7), (.12, 1), (.42, .72)]
    elif kind == "oval_callout":
        draw.ellipse((x0, y0, x1, y0+(y1-y0)*.8), fill=interior, outline=stroke, width=width)
        points = [(.25, .65), (.15, 1), (.45, .76)]
    else:
        points = coords[kind]
    absolute = [(round(x0+x*(x1-x0)), round(y0+y*(y1-y0))) for x, y in points]
    if interior: draw.polygon(absolute, fill=interior)
    if stroke: draw.line(absolute+[absolute[0]], fill=stroke, width=width, joint="curve")

class Document:
    MAX_PIXELS = 16_000_000

    def __init__(self, size=(1152, 648)):
        self.image = Image.new("RGB", size, "white")
        self.undo_stack, self.redo_stack = [], []
        self.saved = self.image.copy()
        self.path = None

    @property
    def dirty(self):
        return self.image.size != self.saved.size or self.image.tobytes() != self.saved.tobytes()

    def snapshot(self):
        self.undo_stack.append(self.image.copy())
        budget, keep = 0, []
        for item in reversed(self.undo_stack):
            budget += item.width*item.height*3
            if keep and (len(keep) >= 30 or budget > 128*1024*1024): break
            keep.append(item)
        self.undo_stack = list(reversed(keep))
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.image.copy())
            self.image = self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.image.copy())
            self.image = self.redo_stack.pop()

    def open(self, path):
        with Image.open(path) as source:
            if source.width*source.height > self.MAX_PIXELS:
                raise ValueError("A imagem deve ter até 16 milhões de pixels.")
            source = ImageOps.exif_transpose(source).convert("RGBA")
            image = Image.new("RGB", source.size, "white")
            image.paste(source, mask=source.getchannel("A"))
        self.image = image
        self.saved, self.path = image.copy(), str(path)
        self.undo_stack.clear()
        self.redo_stack.clear()

    def save(self, path):
        if Path(path).suffix.lower() not in (".png", ".jpg", ".jpeg", ".bmp"):
            raise ValueError("Use PNG, JPG, JPEG ou BMP.")
        self.image.save(path, quality=95)
        self.saved, self.path = self.image.copy(), str(path)

    def resize(self, size):
        if min(size) < 1 or size[0]*size[1] > self.MAX_PIXELS:
            raise ValueError("Dimensões inválidas: use até 16 milhões de pixels.")
        self.snapshot()
        self.image = self.image.resize(size, Image.Resampling.LANCZOS)
