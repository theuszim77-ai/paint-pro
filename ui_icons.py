"""Original, antialiased line icons; no external images or font glyphs."""
from functools import lru_cache
from PIL import Image, ImageDraw
from document import SHAPES, shape


@lru_cache(maxsize=120)
def icon(name, color='#334155', size=24):
    scale = 4
    image = Image.new('RGBA', (size*scale, size*scale))
    d = ImageDraw.Draw(image)
    def p(points): return [(round(x*size*scale/24), round(y*size*scale/24)) for x, y in points]
    def line(points, width=1.7): d.line(p(points), fill=color, width=max(1, round(width*size*scale/24)), joint='curve')
    def box(bounds, radius=0):
        a = p([(bounds[0], bounds[1]), (bounds[2], bounds[3])])
        if radius: d.rounded_rectangle(a, radius=round(radius*size*scale/24), outline=color, width=max(1, round(1.7*size*scale/24)))
        else: d.rectangle(a, outline=color, width=max(1, round(1.7*size*scale/24)))
    if name in SHAPES and name not in ('curve', 'polygon'):
        shape(image, name, p([(4, 4)])[0], p([(20, 20)])[0], color, color, max(1, round(1.5*size*scale/24)))
    elif name in ('brush', 'pencil'):
        line([(5, 16), (16, 4), (20, 8), (8, 20), (4, 21), (5, 16), (8, 19)])
        line([(14, 6), (18, 10)])
        if name == 'brush': line([(4, 19), (3, 21), (7, 21)])
    elif name == 'eraser':
        line([(3, 15), (13, 4), (21, 12), (12, 21), (8, 21), (3, 15), (8, 10), (16, 18)])
        line([(12, 21), (22, 21)])
    elif name == 'fill':
        line([(5, 9), (12, 3), (21, 12), (13, 20), (4, 12), (5, 9), (20, 9)])
        line([(8, 2), (12, 6)])
        d.ellipse(p([(20, 16), (23, 21)]), fill=color)
    elif name == 'picker':
        line([(4, 17), (15, 6), (19, 10), (8, 21), (3, 22), (4, 17)])
        line([(13, 4), (21, 12)], 2.8)
        line([(17, 5), (20, 2), (23, 5), (20, 8)], 2.4)
    elif name in ('magnify', 'zoom_in', 'zoom_out'):
        d.ellipse(p([(3, 3), (16, 16)]), outline=color, width=round(1.7*size*scale/24))
        line([(15, 15), (22, 22)], 2.4)
        line([(6, 9.5), (13, 9.5)])
        if name != 'zoom_out': line([(9.5, 6), (9.5, 13)])
    elif name == 'text':
        line([(4, 4), (20, 4)])
        line([(12, 4), (12, 21)])
        line([(8, 21), (16, 21)])
    elif name == 'select':
        for x in range(3, 20, 5):
            line([(x, 3), (x+2, 3)]); line([(x, 21), (x+2, 21)])
            line([(3, x), (3, x+2)]); line([(21, x), (21, x+2)])
    elif name == 'crop':
        line([(7, 2), (7, 17), (22, 17)])
        line([(2, 7), (17, 7), (17, 22)])
    elif name == 'resize':
        box((3, 3, 21, 21), 2)
        line([(8, 16), (16, 8), (10, 8)])
        line([(16, 8), (16, 14)])
    elif name in ('undo', 'redo', 'rotate'):
        line([(5, 8), (11, 5), (17, 6), (21, 11), (20, 17), (16, 20)])
        line([(5, 3), (5, 8), (10, 10)])
        if name == 'redo': image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif name == 'save':
        line([(4, 3), (17, 3), (21, 7), (21, 21), (3, 21), (3, 3), (4, 3)])
        box((7, 3, 16, 9)); box((7, 14, 17, 21))
    elif name == 'open':
        line([(3, 20), (3, 5), (10, 5), (12, 8), (21, 8), (21, 11)])
        line([(3, 20), (7, 11), (23, 11), (19, 20), (3, 20)])
    elif name == 'new':
        box((4, 2, 20, 22), 2)
        line([(7, 12), (17, 12)]); line([(12, 7), (12, 17)])
    elif name in ('copy', 'paste'):
        box((7, 7, 21, 22), 2)
        line([(4, 17), (2, 17), (2, 2), (16, 2), (16, 5)])
        if name == 'paste': line([(10, 12), (18, 12)]); line([(10, 16), (18, 16)])
    elif name == 'cut':
        d.ellipse(p([(2, 15), (9, 22)]), outline=color, width=round(1.7*size*scale/24))
        d.ellipse(p([(15, 15), (22, 22)]), outline=color, width=round(1.7*size*scale/24))
        line([(7, 17), (20, 2)]); line([(17, 17), (4, 2)])
    elif name == 'curve':
        line([(3, 20), (5, 13), (9, 5), (13, 3), (17, 7), (19, 15), (21, 20)])
    elif name == 'polygon': line([(3, 20), (5, 6), (16, 3), (21, 16), (12, 13), (3, 20)])
    elif name == 'palette':
        d.ellipse(p([(2, 2), (22, 22)]), outline=color, width=round(1.8*size*scale/24))
        for x, y in [(8, 6), (15, 6), (6, 13), (18, 12)]: d.ellipse(p([(x-1, y-1), (x+1, y+1)]), fill=color)
        d.ellipse(p([(10, 15), (15, 20)]), fill=color)
    elif name == 'fit':
        for x, y, dx, dy in [(3, 3, 1, 1), (21, 3, -1, 1), (3, 21, 1, -1), (21, 21, -1, -1)]:
            line([(x, y+5*dy), (x, y), (x+5*dx, y)])
    else: box((4, 4, 20, 20), 3)
    return image.resize((size, size), Image.Resampling.LANCZOS)
