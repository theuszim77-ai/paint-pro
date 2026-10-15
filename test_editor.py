"""Functional checks. Run with: python -m unittest -v"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image, ImageChops, ImageDraw
from document import Document, SHAPES, shape
from classic import PaintPro


class DocumentTests(unittest.TestCase):
    def test_history_branch_and_saved_state(self):
        doc = Document((40, 30))
        doc.snapshot()
        doc.image.putpixel((5, 5), (0, 0, 0))
        self.assertTrue(doc.dirty)
        doc.undo()
        self.assertFalse(doc.dirty)
        doc.redo()
        self.assertEqual(doc.image.getpixel((5, 5)), (0, 0, 0))
        doc.undo()
        doc.snapshot()
        self.assertEqual(doc.redo_stack, [])

    def test_formats_transparency_and_failed_open(self):
        with tempfile.TemporaryDirectory() as temp:
            doc = Document((40, 30))
            doc.image.putpixel((3, 3), (255, 0, 0))
            for extension in ('png', 'jpg', 'bmp'):
                path = Path(temp) / ('test.' + extension)
                doc.save(path)
                self.assertFalse(doc.dirty)
                other = Document()
                other.open(path)
                self.assertEqual(other.image.size, (40, 30))
            alpha = Path(temp) / 'transparent.png'
            Image.new('RGBA', (10, 10), (0, 0, 0, 0)).save(alpha)
            doc.open(alpha)
            self.assertEqual(doc.image.getpixel((0, 0)), (255, 255, 255))
            with self.assertRaises(OSError): doc.open(Path(temp) / 'missing.png')
            self.assertEqual(doc.image.size, (10, 10))

    def test_all_geometries_and_reverse_drag(self):
        for tool in SHAPES:
            if tool in ('curve', 'polygon'): continue
            with self.subTest(tool=tool):
                image = Image.new('RGB', (80, 80), 'white')
                shape(image, tool, (65, 65), (5, 5), 'black', 'red', 3, True, True)
                self.assertIsNotNone(ImageChops.difference(image, Image.new('RGB', image.size, 'white')).getbbox())


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = PaintPro()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.destroy()

    def setUp(self):
        self.app.cancel()
        self.app.doc = Document()
        self.app.color, self.app.secondary = '#000000', '#ffffff'
        self.app.clip = None
        self.app.grid_on.set(False)
        self.app.rulers_on.set(False)
        self.app.set_zoom(1)
        self.app.canvas.xview_moveto(0)
        self.app.canvas.yview_moveto(0)
        self.app.show_tab('home')
        self.app.update()

    def event(self, x, y, num=1):
        a = self.app
        return SimpleNamespace(x=a.origin+x*a.zoom-a.canvas.canvasx(0), y=a.origin+y*a.zoom-a.canvas.canvasy(0), num=num)

    def gesture(self, tool, start=(20, 20), end=(60, 60), num=1):
        a = self.app
        a.select_tool(tool)
        a.pointer_down(self.event(*start, num))
        a.pointer_move(self.event(*end, num))
        a.pointer_up(self.event(*end, num))

    def test_drawing_colors_fill_and_history(self):
        a = self.app
        a.secondary = '#ff0000'
        self.gesture('brush', num=3)
        self.assertEqual(a.image.getpixel((40, 40)), (255, 0, 0))
        a.undo()
        self.assertEqual(a.image.getpixel((40, 40)), (255, 255, 255))
        a.redo()
        self.assertEqual(a.image.getpixel((40, 40)), (255, 0, 0))
        self.gesture('eraser')
        self.assertEqual(a.image.getpixel((40, 40)), (255, 0, 0))
        a.color = '#0000ff'
        self.gesture('fill', (200, 200), (200, 200))
        self.assertEqual(a.image.getpixel((300, 300)), (0, 0, 255))
        self.gesture('picker', (300, 300), (300, 300))
        self.assertEqual(a.color, '#0000ff')

    def test_selection_move_copy_crop_resize_rotate(self):
        a = self.app
        ImageDraw.Draw(a.image).rectangle((20, 20, 60, 60), fill='red')
        self.gesture('select')
        a.copy()
        self.assertEqual(a.clip.size, (41, 41))
        a.pointer_down(self.event(30, 30))
        a.pointer_move(self.event(130, 130))
        a.pointer_up(self.event(130, 130))
        self.assertEqual(a.image.getpixel((30, 30)), (255, 255, 255))
        self.assertEqual(a.image.getpixel((130, 130)), (255, 0, 0))
        a.crop()
        self.assertEqual(a.image.size, (41, 41))
        a.undo()
        self.assertEqual(a.image.size, (1152, 648))
        a.paste()
        self.assertEqual(a.image.getpixel((0, 0)), (255, 0, 0))
        a.transform('right')
        self.assertEqual(a.image.size, (648, 1152))
        with patch('classic.simpledialog.askinteger', side_effect=[200, 100]): a.resize_image()
        self.assertEqual(a.image.size, (200, 100))

    def test_polygon_curve_text_and_zoom_coordinates(self):
        a = self.app
        a.select_tool('polygon')
        for point in ((10, 10), (60, 10), (60, 60)): a.pointer_down(self.event(*point))
        a.finish_polygon()
        self.assertEqual(a.image.getpixel((40, 10)), (0, 0, 0))
        self.gesture('curve', (100, 100), (180, 100))
        self.assertTrue(a.curve_stage)
        a.pointer_down(self.event(140, 160))
        a.pointer_up(self.event(140, 160))
        self.assertFalse(a.curve_stage)
        self.assertEqual(a.image.getpixel((140, 130)), (0, 0, 0))
        with patch('classic.simpledialog.askstring', return_value='Teste'), patch('classic.simpledialog.askinteger', return_value=20):
            self.gesture('text', (200, 200), (200, 200))
        self.assertIsNotNone(ImageChops.difference(a.image.crop((200, 200, 300, 250)), Image.new('RGB', (100, 50), 'white')).getbbox())
        a.set_zoom(4)
        a.scroll('x', 'moveto', .2)
        a.scroll('y', 'moveto', .2)
        self.assertEqual(a._canvas_point(self.event(400, 200)), (400, 200))
        a.grid_on.set(True)
        a.rulers_on.set(True)
        a._render()
        a.show_tab('view')
        a.update()
        self.assertTrue(a.view.winfo_ismapped())

    def test_save_cancel_and_failed_load(self):
        a = self.app
        self.gesture('pencil')
        with patch('classic.messagebox.askyesnocancel', return_value=None):
            self.assertFalse(a.confirm_discard())
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / 'image.png')
            with patch('classic.filedialog.asksaveasfilename', return_value=path):
                self.assertTrue(a.save_file())
            self.assertFalse(a.doc.dirty)
            with patch('classic.filedialog.askopenfilename', return_value=path): a.open_file()
            self.assertEqual(a.image.size, (1152, 648))


if __name__ == '__main__':
    unittest.main()
