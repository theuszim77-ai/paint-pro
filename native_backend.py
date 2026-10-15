"""Optional C++ accelerator with a Pillow fallback and no extra Python packages."""
import ctypes
import os
import sys
from pathlib import Path
from PIL import Image, ImageColor, ImageDraw

_library = None
_attempted = False


def _load():
    global _library, _attempted
    if _attempted:
        return _library
    _attempted = True
    if os.environ.get('PAINT_PRO_DISABLE_NATIVE') == '1':
        return None
    filename = 'paintpro_native.dll' if sys.platform == 'win32' else 'libpaintpro_native.dylib' if sys.platform == 'darwin' else 'libpaintpro_native.so'
    path = Path(__file__).resolve().parent / 'native' / 'bin' / filename
    try:
        lib = ctypes.CDLL(str(path))
        lib.pp_version.argtypes = []
        lib.pp_version.restype = ctypes.c_int
        if lib.pp_version() != 1:
            return None
        lib.pp_flood_fill.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]
        lib.pp_flood_fill.restype = ctypes.c_int
        _library = lib
    except (OSError, AttributeError):
        pass
    return _library


def backend_name():
    return 'C++17' if _load() is not None else 'Pillow'


def flood_fill(image, point, color):
    """Return a filled RGB image. Failed native operations cannot damage the source."""
    if image.mode != 'RGB':
        raise ValueError('Expected an RGB image')
    x, y = point
    if not (0 <= x < image.width and 0 <= y < image.height):
        raise ValueError('Point is outside the image')
    rgb = ImageColor.getrgb(color) if isinstance(color, str) else tuple(color)
    if len(rgb) != 3 or any(not isinstance(c, int) or c < 0 or c > 255 for c in rgb):
        raise ValueError('Expected an RGB color')
    lib = _load()
    if lib is not None:
        data = image.tobytes()
        buffer = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        code = lib.pp_flood_fill(buffer, len(data), image.width, image.height, x, y, *rgb)
        if code == 0:
            return Image.frombytes('RGB', image.size, bytes(buffer))
    result = image.copy()
    ImageDraw.floodfill(result, point, rgb, thresh=0)
    return result
