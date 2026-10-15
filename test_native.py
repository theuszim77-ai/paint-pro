import ctypes
import os
import random
import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import native_backend as backend


class NativeTests(unittest.TestCase):
    def test_fallback_and_source_immutability(self):
        source = Image.new('RGB', (10, 10), 'white')
        ImageDraw.Draw(source).rectangle((2, 2, 7, 7), outline='black')
        with patch.object(backend, '_load', return_value=None):
            result = backend.flood_fill(source, (4, 4), '#ff0000')
        self.assertEqual(result.getpixel((4, 4)), (255, 0, 0))
        self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(source.getpixel((4, 4)), (255, 255, 255))

    def test_errors_and_native_failure_fallback(self):
        image = Image.new('RGB', (5, 5), 'white')
        with self.assertRaises(ValueError): backend.flood_fill(image, (-1, 0), 'red')
        with self.assertRaises(ValueError): backend.flood_fill(image, (0, 0), (999, 0, 0))
        with patch.object(backend, '_load') as load:
            load.return_value.pp_flood_fill.return_value = -2
            self.assertEqual(backend.flood_fill(image, (0, 0), 'red').getpixel((0, 0)), (255, 0, 0))

    def test_native_matches_pillow(self):
        lib = backend._load()
        if lib is None:
            if os.environ.get('PAINT_PRO_REQUIRE_NATIVE') == '1': self.fail('Native library is required but unavailable')
            self.skipTest('Build optional C++ library to run parity checks')
        rng = random.Random(42)
        for _ in range(25):
            source = Image.new('RGB', (24, 18))
            source.putdata([rng.choice([(0, 0, 0), (255, 255, 255)]) for _ in range(24*18)])
            point = rng.randrange(24), rng.randrange(18)
            expected = source.copy()
            ImageDraw.floodfill(expected, point, (255, 0, 0), thresh=0)
            self.assertEqual(backend.flood_fill(source, point, 'red').tobytes(), expected.tobytes())
        self.assertEqual(lib.pp_flood_fill(None, 0, 0, 0, 0, 0, 0, 0, 0), -1)
        tiny = (ctypes.c_uint8 * 3)(0, 0, 0)
        self.assertEqual(lib.pp_flood_fill(tiny, 3, 2, 2, 0, 0, 1, 2, 3), -1)
