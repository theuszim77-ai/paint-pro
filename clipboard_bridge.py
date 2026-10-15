"""Image clipboard adapter. Copy uses Windows CF_DIB; paste uses Pillow."""
import ctypes
import io
import sys
from PIL import Image, ImageGrab


def read_image(max_pixels=16_000_000):
    try:
        content = ImageGrab.grabclipboard()
        if not isinstance(content, Image.Image):
            return None
        if content.width * content.height > max_pixels:
            return None
        rgba = content.convert('RGBA')
        image = Image.new('RGB', rgba.size, 'white')
        image.paste(rgba, mask=rgba.getchannel('A'))
        return image
    except (OSError, NotImplementedError, Image.DecompressionBombError):
        return None


def write_image(image, owner=None):
    if sys.platform != 'win32':
        return False
    # CF_DIB contains a BMP without its 14-byte file header.
    stream = io.BytesIO()
    image.convert('RGB').save(stream, format='BMP')
    data = stream.getvalue()[14:]
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel.GlobalAlloc.restype = ctypes.c_void_p
    kernel.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel.GlobalFree.argtypes = [ctypes.c_void_p]
    user.OpenClipboard.argtypes = [ctypes.c_void_p]
    user.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user.SetClipboardData.restype = ctypes.c_void_p
    memory = kernel.GlobalAlloc(0x0002, len(data))
    if not memory:
        return False
    owned = False
    try:
        address = kernel.GlobalLock(memory)
        if not address:
            return False
        ctypes.memmove(address, data, len(data))
        kernel.GlobalUnlock(memory)
        if not owner or not user.OpenClipboard(owner):
            return False
        try:
            if not user.EmptyClipboard():
                return False
            owned = bool(user.SetClipboardData(8, memory))  # CF_DIB
            return owned
        finally:
            user.CloseClipboard()
    finally:
        # After SetClipboardData succeeds Windows owns the allocation.
        if not owned:
            kernel.GlobalFree(memory)
