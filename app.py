"""Launch Paint Pro, or run a packaged-app integration smoke check."""
from classic import PaintPro


def smoke_test(require_native=False):
    import tempfile
    from pathlib import Path
    from PIL import ImageDraw
    from native_backend import backend_name, flood_fill
    app = PaintPro()
    app.withdraw()
    try:
        app.update()
        app.doc.snapshot()
        ImageDraw.Draw(app.image).rectangle((10, 10, 40, 40), outline='black', width=2)
        app.image = flood_fill(app.image, (20, 20), 'red')
        assert app.image.getpixel((20, 20)) == (255, 0, 0)
        app.undo()
        assert app.image.getpixel((20, 20)) == (255, 255, 255)
        app.redo()
        app.select_tool('text')
        app.add_text((100, 100))
        app.text_editor.insert('1.0', 'Paint Pro')
        app.commit_text()
        app.show_tab('home')
        app.set_zoom(2)
        app._render()
        if require_native: assert backend_name() == 'C++17'
        with tempfile.TemporaryDirectory() as temp:
            app.doc.save(Path(temp) / 'check.png')
            assert not app.doc.dirty
        return {'status': 'ok', 'version': '0.5.0', 'backend': backend_name(), 'tools': len(app.tool_buttons)}
    finally:
        app.destroy()


if __name__ == "__main__":
    import sys
    if '--smoke-test' in sys.argv:
        import json
        import traceback
        from pathlib import Path
        status = 0
        try:
            report = smoke_test('--require-native' in sys.argv)
        except Exception:
            status = 1
            report = {'status': 'error', 'details': traceback.format_exc()}
        if '--report' in sys.argv:
            Path(sys.argv[sys.argv.index('--report')+1]).write_text(json.dumps(report, indent=2), encoding='utf-8')
        sys.exit(status)
    else:
        PaintPro().mainloop()
