import unittest
from unittest.mock import patch
import tkinter as tk
from types import SimpleNamespace
from PIL import Image
import clipboard_bridge
from editor_dialogs import SizeDialog


class ClipboardAndSizeTests(unittest.TestCase):
    def test_clipboard_alpha_and_unavailable(self):
        with patch('clipboard_bridge.ImageGrab.grabclipboard', return_value=Image.new('RGBA', (4, 4), (0, 0, 0, 0))):
            self.assertEqual(clipboard_bridge.read_image().getpixel((0, 0)), (255, 255, 255))
        with patch('clipboard_bridge.ImageGrab.grabclipboard', return_value=['a.txt']):
            self.assertIsNone(clipboard_bridge.read_image())
        with patch('clipboard_bridge.ImageGrab.grabclipboard', side_effect=OSError):
            self.assertIsNone(clipboard_bridge.read_image())
        with patch('clipboard_bridge.sys.platform', 'linux'):
            self.assertFalse(clipboard_bridge.write_image(Image.new('RGB', (2, 2))))

    def test_size_lock_and_percentage(self):
        interp = tk.Tcl()
        obj = SimpleNamespace(changing=False, lock=tk.BooleanVar(interp, True), canvas_mode=False, original=(400, 200),
                              unit=tk.StringVar(interp, 'Pixels'), width_value=tk.StringVar(interp, '200'), height_value=tk.StringVar(interp, '200'))
        SizeDialog.sync(obj, True)
        self.assertEqual(obj.height_value.get(), '100')
        obj.unit.set('Porcentagem')
        obj.width_value.set('50')
        SizeDialog.sync(obj, True)
        self.assertEqual(obj.height_value.get(), '50')
        obj.anchor = tk.StringVar(interp, 'Centro')
        obj.destroy = lambda: None
        SizeDialog.accept(obj)
        self.assertEqual(obj.result, ((200, 100), 'Centro'))
