"""Classic ribbon interface, implemented independently with Tk and Pillow."""
import math
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
from document import Document, SHAPES, shape
from native_backend import flood_fill
from clipboard_bridge import read_image, write_image
from editor_dialogs import SizeDialog

PALETTE = ["#000000", "#7f7f7f", "#880015", "#ed1c24", "#ff7f27", "#fff200", "#22b14c", "#00a2e8", "#3f48cc", "#a349a4",
           "#ffffff", "#c3c3c3", "#b97a57", "#ffaec9", "#ffc90e", "#efe4b0", "#b5e61d", "#99d9ea", "#7092be", "#c8bfe7"]
TOOLS = {"pencil": "Lápis", "fill": "Preencher com cor", "text": "Texto", "eraser": "Borracha", "picker": "Selecionador de cores", "magnify": "Lupa", "brush": "Pincel", "select": "Selecionar"}


class PaintPro(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        super().__init__()
        self.geometry(f'{min(1380, self.winfo_screenwidth()-70)}x{min(880, self.winfo_screenheight()-90)}')
        self.minsize(980, 580)
        self.configure(fg_color="#f0f0f0")
        self.doc = Document()
        self.tool = "brush"
        self.color, self.secondary = "#000000", "#ffffff"
        self.active_color = 1
        self.width = tk.IntVar(value=5)
        self.fill_mode = tk.StringVar(value="Sem preenchimento")
        self.outline_mode = tk.StringVar(value="Cor sólida")
        self.brush_mode = tk.StringVar(value="Pincel")
        self.zoom = 1.0
        self.start = self.last = self.preview_base = None
        self.selection = self.clip = self.drag_selection = None
        self.path_points = []
        self.curve_stage = False
        self.curve_ends = None
        self.gesture_history = None
        self.gesture_color = self.color
        self.tk_image = None
        self.text_editor = None
        self.text_point = None
        self.text_family = tk.StringVar(value='Arial')
        self.text_size = tk.StringVar(value='24')
        self.text_bold = tk.BooleanVar(value=False)
        self.text_italic = tk.BooleanVar(value=False)
        self.text_opaque = tk.BooleanVar(value=False)
        self.text_color = self.color
        self.space_down = self.panning = False
        self._chrome_signature = None
        self._dirty_display = False
        self._help_window = None
        self.grid_on = tk.BooleanVar(value=False)
        self.rulers_on = tk.BooleanVar(value=False)
        self.status_on = tk.BooleanVar(value=True)
        self._build_ui()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_idletasks()
        self.fit()
        self.after(300, self.install_icon)

    def install_icon(self):
        from ui_icons import icon
        self.application_icon = ImageTk.PhotoImage(icon('palette', '#2563eb', 64))
        self.iconphoto(True, self.application_icon)

    @property
    def image(self):
        return self.doc.image

    @image.setter
    def image(self, value):
        self.doc.image = value

    def button(self, parent, text, command, width=60, height=28):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
                             fg_color="transparent", text_color="#25354a", hover_color="#eef4ff",
                             corner_radius=6, border_spacing=4, font=("Segoe UI", 12))

    def _build_ui(self):
        from studio_ui import build_ui
        self.tool_names = TOOLS
        build_ui(self)


    def option(self, parent, variable, values, width, command=None):
        return ctk.CTkOptionMenu(parent, values=values, variable=variable, command=command, width=width, height=27, corner_radius=5, font=("Segoe UI", 11), fg_color="#f1f5f9", text_color="#334155", button_color="#e2e8f0", button_hover_color='#d0ddf0', dropdown_fg_color='white', dropdown_text_color='#334155')

    def tooltip(self, widget, text):
        state = {"tip": None, "timer": None}
        def hide(_e=None):
            if state["timer"]:
                widget.after_cancel(state["timer"])
                state["timer"] = None
            if state["tip"]:
                state["tip"].destroy()
                state["tip"] = None
        def show():
            tip = state["tip"] = tk.Toplevel(self)
            tip.overrideredirect(True)
            tip.geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty()+widget.winfo_height()+3}")
            tk.Label(tip, text=text, bg="#fffde7", relief="solid", borderwidth=1, padx=6, pady=3).pack()
        widget.bind("<Enter>", lambda _e: state.update(timer=widget.after(600, show)), add="+")
        widget.bind("<Leave>", hide, add="+")
        widget.bind("<ButtonPress>", hide, add="+")

    def _bind_shortcuts(self):
        for key, action in {"n": self.new_file, "o": self.open_file, "s": self.save_file, "z": self.undo, "y": self.redo, "c": self.copy, "x": self.cut, "v": self.paste, "a": self.select_all}.items():
            self.bind(f"<Control-{key}>", lambda e, f=action, k=key: self.shortcut(e, k, f))
        self.bind("<Control-Shift-S>", lambda _e: self.save_file(True))
        self.bind("<Delete>", lambda e: self.shortcut(e, 'delete', self.delete_selection))
        self.bind("<Escape>", lambda _e: self.escape())
        self.bind("<Return>", lambda e: self.shortcut(e, 'enter', self.finish_polygon))
        self.bind('<Control-Return>', lambda _e: self.commit_text())
        self.bind("<F11>", lambda _e: self.fullscreen())
        self.bind("<Control-plus>", lambda _e: self.change_zoom(.25))
        self.bind("<Control-minus>", lambda _e: self.change_zoom(-.25))
        self.bind('<KeyPress-space>', self.press_space)
        self.bind('<KeyRelease-space>', self.release_space)
        self.bind('<FocusOut>', lambda _e: self.release_space())
        self.canvas.bind('<ButtonPress-2>', self.pan_start)
        self.canvas.bind('<B2-Motion>', self.pan_move)
        self.canvas.bind('<ButtonRelease-2>', self.pan_end)
        for key, dx, dy in [('Left', -1, 0), ('Right', 1, 0), ('Up', 0, -1), ('Down', 0, 1)]:
            self.bind(f'<{key}>', lambda e, x=dx, y=dy: self.nudge_selection(e, x, y))

    def shortcut(self, event, key, action):
        # Keep native editing shortcuts inside text fields and canvas text boxes.
        if isinstance(event.widget, (tk.Text, tk.Entry)) and key in ('a', 'c', 'x', 'v', 'z', 'y', 'delete', 'enter'):
            return
        action()
        return 'break'

    def show_tab(self, tab):
        self.home.pack_forget()
        self.view.pack_forget()
        self.textbar.pack_forget()
        {'home': self.home, 'view': self.view, 'text': self.textbar}[tab].pack(fill='both', expand=True)
        for name, button in getattr(self, 'tab_buttons', {}).items():
            button.configure(fg_color='#e8f0ff' if name == tab else 'transparent', text_color='#2563eb' if name == tab else '#334155')

    def menu(self, entries):
        menu = tk.Menu(self, tearoff=False)
        for label, cmd in entries:
            menu.add_command(label=label, command=cmd)
        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def file_menu(self):
        self.menu((("Novo  Ctrl+N", self.new_file), ("Abrir  Ctrl+O", self.open_file), ("Salvar  Ctrl+S", self.save_file), ("Salvar como", lambda: self.save_file(True)), ('Tamanho da tela', self.resize_canvas), ("Sair", self.close)))

    def rotate_menu(self):
        self.menu((("Girar 90° à direita", lambda: self.transform("right")), ("Girar 90° à esquerda", lambda: self.transform("left")), ("Girar 180°", lambda: self.transform("180")), ("Inverter horizontalmente", lambda: self.transform("horizontal")), ("Inverter verticalmente", lambda: self.transform("vertical"))))

    def _color_buttons(self):
        for n, b, c in ((1, self.primary_button, self.color), (2, self.secondary_button, self.secondary)):
            b.configure(fg_color=c, text_color="white" if sum(bytes.fromhex(c[1:])) < 380 else "black", border_width=2 if self.active_color == n else 0, border_color="#32a8ed")

    def activate_color(self, n):
        self.active_color = n
        self._color_buttons()
        if self.text_editor:
            self.text_color = self.color if self.active_color == 1 else self.secondary
            self.update_text_font()

    def set_color(self, color, slot=None):
        if (slot or self.active_color) == 1:
            self.color = color
        else:
            self.secondary = color
        self._color_buttons()
        if self.text_editor:
            self.text_color = self.color if (slot or self.active_color) == 1 else self.secondary
            self.update_text_font()

    def swap_colors(self):
        self.color, self.secondary = self.secondary, self.color
        self._color_buttons()
        if self.text_editor:
            self.text_color = self.color if self.active_color == 1 else self.secondary
            self.update_text_font()

    def choose_color(self):
        result = colorchooser.askcolor(self.color if self.active_color == 1 else self.secondary, parent=self)[1]
        if result: self.set_color(result)

    def select_tool(self, tool):
        self.commit_text()
        if self.path_points: self.finish_polygon()
        self.cancel()
        self.tool = tool
        for name, button in self.tool_buttons.items():
            button.configure(fg_color='#e8f0ff' if name == tool else 'transparent', text_color='#2563eb' if name == tool else '#334155')
        self.canvas.configure(cursor="xterm" if tool == "text" else "crosshair")
        self._render()
        if tool == 'text': self.show_tab('text')

    @property
    def origin(self):
        return 36 if self.rulers_on.get() else 20

    def _canvas_point(self, event, clamp=True):
        x = math.floor((self.canvas.canvasx(event.x)-self.origin)/self.zoom)
        y = math.floor((self.canvas.canvasy(event.y)-self.origin)/self.zoom)
        if not clamp and not (0 <= x < self.image.width and 0 <= y < self.image.height): return None
        return max(0, min(self.image.width-1, x)), max(0, min(self.image.height-1, y))

    def pointer_down(self, event):
        if self.space_down:
            self.pan_start(event)
            return
        point = self._canvas_point(event, False)
        if point is None: return
        self.commit_text()
        self.canvas.focus_set()
        secondary = getattr(event, "num", 1) == 3
        self.gesture_color = self.secondary if secondary else self.color
        if self.tool == "picker":
            self.set_color("#%02x%02x%02x" % self.image.getpixel(point), 2 if secondary else 1)
            return
        if self.tool == "magnify":
            self.change_zoom(-.5 if secondary else .5)
            return
        if self.tool == "fill":
            if self.image.getpixel(point) == Image.new('RGB', (1, 1), self.gesture_color).getpixel((0, 0)):
                return
            self.doc.snapshot()
            self.image = flood_fill(self.image, point, self.gesture_color)
            self._render()
            return
        if self.tool == "text":
            self.add_text(point)
            return
        if self.tool == "polygon":
            if not self.path_points:
                self.begin_gesture_history()
                self.preview_base = self.image.copy()
            self.path_points.append(point)
            self._render()
            return
        if self.tool == "curve" and self.curve_stage:
            self.start = self.last = point
            self.pointer_move(event)
            return
        self.start = self.last = point
        self.preview_base = self.image.copy()
        self.drag_selection = None
        if self.tool == "select":
            if self.selection and self.selection[0] <= point[0] < self.selection[2] and self.selection[1] <= point[1] < self.selection[3]:
                self.drag_selection = self.selection
                self.begin_gesture_history()
            else: self.selection = None
        else:
            self.selection = None
            self.begin_gesture_history()
        if self.tool in ("brush", "pencil", "eraser"): self.pointer_move(event)

    def pointer_move(self, event):
        if self.panning:
            self.pan_move(event)
            return
        if self.last is None: return
        point = self._canvas_point(event)
        if self.tool in SHAPES and self.tool not in ('curve', 'polygon') and getattr(event, 'state', 0) & 1:
            point = self.constrain_point(self.start, point)
        if self.tool in ("brush", "pencil", "eraser"):
            draw = ImageDraw.Draw(self.image)
            width = 1 if self.tool == "pencil" else self.width.get()
            color = self.secondary if self.tool == "eraser" else self.gesture_color
            if self.tool == "brush" and self.brush_mode.get() == "Caligrafia":
                distance = max(1, int(math.dist(self.last, point)))
                for i in range(distance+1):
                    x = self.last[0]+(point[0]-self.last[0])*i/distance
                    y = self.last[1]+(point[1]-self.last[1])*i/distance
                    draw.line((x-width/2, y+width/2, x+width/2, y-width/2), fill=color, width=2)
            elif self.tool == "brush" and self.brush_mode.get() == "Marcador":
                draw.line((self.last, point), fill=color, width=width*2)
            else:
                draw.line((self.last, point), fill=color, width=width)
                radius = (width-1)/2
                draw.ellipse((point[0]-radius, point[1]-radius, point[0]+radius, point[1]+radius), fill=color)
            self.last = point
        elif self.tool == "select":
            if self.drag_selection:
                box = self.drag_selection
                dx = max(-box[0], min(self.image.width-box[2], point[0]-self.start[0]))
                dy = max(-box[1], min(self.image.height-box[3], point[1]-self.start[1]))
                self.image = self.preview_base.copy()
                ImageDraw.Draw(self.image).rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=self.secondary)
                self.image.paste(self.preview_base.crop(box), (box[0]+dx, box[1]+dy))
                self.selection = (box[0]+dx, box[1]+dy, box[2]+dx, box[3]+dy)
            else:
                self.selection = (min(self.start[0], point[0]), min(self.start[1], point[1]), max(self.start[0], point[0])+1, max(self.start[1], point[1])+1)
        elif self.preview_base:
            self.image = self.preview_base.copy()
            if self.tool == "curve" and self.curve_stage:
                a, b = self.curve_ends
                points = [((1-t)**2*a[0]+2*(1-t)*t*point[0]+t*t*b[0], (1-t)**2*a[1]+2*(1-t)*t*point[1]+t*t*b[1]) for t in (i/80 for i in range(81))]
                ImageDraw.Draw(self.image).line(points, fill=self.gesture_color, width=self.width.get())
            else: self._draw_shape(self.start, point)
        self._render()

    def pointer_up(self, event):
        if self.panning:
            self.pan_end(event)
            return
        if self.start is None: return
        self.pointer_move(event)
        if self.tool == "curve" and not self.curve_stage:
            self.curve_ends = self.start, self._canvas_point(event)
            self.curve_stage = True
            self.start = self.last = None
            self._render()
            return
        self.curve_stage = False
        self.finish_gesture_history()
        self.start = self.last = self.preview_base = self.drag_selection = None
        self._render()

    def _draw_shape(self, start, end):
        shape(self.image, "line" if self.tool == "curve" else self.tool, start, end, self.gesture_color, self.secondary, self.width.get(), self.outline_mode.get() == "Cor sólida", self.fill_mode.get() == "Cor sólida")

    def finish_polygon(self):
        if len(self.path_points) >= 2:
            draw = ImageDraw.Draw(self.image)
            if self.fill_mode.get() == "Cor sólida": draw.polygon(self.path_points, fill=self.secondary)
            if self.outline_mode.get() == "Cor sólida": draw.line(self.path_points+[self.path_points[0]], fill=self.gesture_color, width=self.width.get(), joint="curve")
        self.finish_gesture_history()
        self.path_points = []
        self.preview_base = None
        self._render()

    def pointer_hover(self, event):
        point = self._canvas_point(event, False)
        if hasattr(self, 'position_label'):
            self.position_label.configure(text=f'{point[0]}, {point[1]} px' if point else '')
        if self.path_points:
            self.canvas.delete("polygon_preview")
            coords = [self.origin+c*self.zoom for p in self.path_points+[self._canvas_point(event)] for c in p]
            self.canvas.create_line(*coords, fill=self.gesture_color, width=max(1, self.width.get()*self.zoom), tags="polygon_preview")

    def cancel(self):
        self.cancel_text()
        if self.preview_base and (self.start is not None or self.curve_stage or self.path_points): self.image = self.preview_base.copy()
        if self.gesture_history is not None:
            self.doc.undo_stack, self.doc.redo_stack = self.gesture_history
            self.gesture_history = None
        self.start = self.last = self.preview_base = self.drag_selection = None
        self.path_points = []
        self.curve_stage = False
        self.selection = None
        self._render()

    def begin_gesture_history(self):
        self.gesture_history = (list(self.doc.undo_stack), list(self.doc.redo_stack))
        self.doc.snapshot()

    def finish_gesture_history(self):
        if self.gesture_history is not None:
            if self.preview_base and self.image.tobytes() == self.preview_base.tobytes():
                self.doc.undo_stack, self.doc.redo_stack = self.gesture_history
            self.gesture_history = None

    def escape(self):
        self.attributes("-fullscreen", False)
        self.cancel()
        self.release_space()

    def constrain_point(self, start, end):
        dx, dy = end[0]-start[0], end[1]-start[1]
        if self.tool == 'line':
            angle = round(math.atan2(dy, dx)/(math.pi/4))*math.pi/4
            length = math.hypot(dx, dy)
            return (max(0, min(self.image.width-1, round(start[0]+math.cos(angle)*length))),
                    max(0, min(self.image.height-1, round(start[1]+math.sin(angle)*length))))
        sx, sy = 1 if dx >= 0 else -1, 1 if dy >= 0 else -1
        size = min(max(abs(dx), abs(dy)), self.image.width-1-start[0] if sx > 0 else start[0], self.image.height-1-start[1] if sy > 0 else start[1])
        return start[0]+sx*size, start[1]+sy*size

    def press_space(self, event):
        if isinstance(event.widget, (tk.Text, tk.Entry)): return
        self.space_down = True
        self.canvas.configure(cursor='hand2')
        return 'break'

    def release_space(self, event=None):
        self.space_down = False
        if hasattr(self, 'canvas'):
            self.canvas.configure(cursor='xterm' if self.tool == 'text' else 'crosshair')

    def pan_start(self, event):
        if self.start is not None: return
        self.panning = True
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.configure(cursor='fleur')

    def pan_move(self, event):
        if self.panning:
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            self._render()

    def pan_end(self, event=None):
        self.panning = False
        self.canvas.configure(cursor='hand2' if self.space_down else 'xterm' if self.tool == 'text' else 'crosshair')

    def nudge_selection(self, event, dx, dy):
        if isinstance(event.widget, (tk.Text, tk.Entry)) or not self.selection: return
        step = 10 if getattr(event, 'state', 0) & 1 else 1
        box = self.selection
        dx = max(-box[0], min(self.image.width-box[2], dx*step))
        dy = max(-box[1], min(self.image.height-box[3], dy*step))
        if dx == 0 and dy == 0: return 'break'
        self.doc.snapshot()
        content = self.image.crop(box)
        ImageDraw.Draw(self.image).rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=self.secondary)
        self.image.paste(content, (box[0]+dx, box[1]+dy))
        self.selection = box[0]+dx, box[1]+dy, box[2]+dx, box[3]+dy
        self._render()
        return 'break'

    def show_help(self):
        if self._help_window and self._help_window.winfo_exists():
            self._help_window.lift()
            return
        win = self._help_window = ctk.CTkToplevel(self)
        win.title('Atalhos — Paint Pro')
        win.geometry('540x460')
        win.transient(self)
        ctk.CTkLabel(win, text='Desenhe com mais fluidez', font=('Segoe UI', 22, 'bold')).pack(pady=(24, 6))
        ctk.CTkLabel(win, text='Ferramentas à mão. Espaço para criar.', text_color='#65748a').pack()
        text = ctk.CTkTextbox(win, fg_color='#f1f5f9', corner_radius=10, font=('Segoe UI', 13), wrap='word')
        text.pack(fill='both', expand=True, padx=24, pady=18)
        text.insert('1.0', 'Ctrl+N / Ctrl+O       Novo / abrir\nCtrl+S                       Salvar\nCtrl+Shift+S             Salvar como\nCtrl+Z / Ctrl+Y         Desfazer / refazer\nCtrl+A                       Selecionar tudo\nCtrl+C / X / V           Copiar / recortar / colar\nShift + arrastar        Formas regulares e linhas a 45°\nEspaço + arrastar    Mover a tela\nCtrl + roda               Zoom no cursor\nSetas / Shift+setas   Mover seleção em 1 / 10 px\nCtrl+Enter                Aplicar texto\nEnter                          Fechar polígono\nEsc                              Cancelar / sair da tela inteira\nF11                              Tela inteira')
        text.configure(state='disabled')
        ctk.CTkButton(win, text='Voltar a desenhar', command=win.destroy, width=180).pack(pady=(0, 18))

    def add_text(self, point):
        self.text_point = point
        self.text_color = self.gesture_color
        self.text_editor = tk.Text(self.canvas, undo=True, wrap='none', borderwidth=1, relief='solid', highlightthickness=1, highlightbackground='#1477cf', padx=0, pady=0)
        self.text_editor.bind('<Control-Return>', lambda _e: (self.commit_text(), 'break')[1])
        self.text_editor.bind('<Escape>', lambda _e: (self.cancel_text(), 'break')[1])
        self.show_tab('text')
        self.update_text_font()
        self._render()
        self.text_editor.focus_set()

    def text_pixel_size(self):
        try: return max(6, min(300, int(self.text_size.get())))
        except ValueError: return 24

    def update_text_font(self):
        if self.text_editor:
            style = ('bold' if self.text_bold.get() else 'normal') + (' italic' if self.text_italic.get() else '')
            self.text_editor.configure(font=(self.text_family.get(), -max(1, round(self.text_pixel_size()*self.zoom)), style), fg=self.text_color,
                                       bg=self.secondary if self.text_opaque.get() else 'white')

    def text_font(self):
        bold, italic = self.text_bold.get(), self.text_italic.get()
        suffix = 'bi' if bold and italic else 'bd' if bold else 'i' if italic else ''
        names = {
            'Arial': 'arial'+suffix+'.ttf',
            'Segoe UI': 'segoeui'+('z' if bold and italic else 'b' if bold else 'i' if italic else '')+'.ttf',
            'Times New Roman': 'times'+suffix+'.ttf',
            'Courier New': 'cour'+suffix+'.ttf',
        }
        fallback = 'DejaVuSans'+('-BoldOblique' if bold and italic else '-Bold' if bold else '-Oblique' if italic else '')+'.ttf'
        for name in (names[self.text_family.get()], fallback):
            try: return ImageFont.truetype(name, self.text_pixel_size())
            except OSError: pass
        return ImageFont.load_default(size=self.text_pixel_size())

    def commit_text(self):
        if self.text_editor is None: return
        value = self.text_editor.get('1.0', 'end-1c')
        point = self.text_point
        self.text_editor.destroy()
        self.text_editor = self.text_point = None
        if value.strip():
            self.doc.snapshot()
            draw = ImageDraw.Draw(self.image)
            font = self.text_font()
            box = draw.multiline_textbbox((0, 0), value, font=font, spacing=4)
            if self.text_opaque.get():
                draw.rectangle((point[0], point[1], point[0]+box[2]-box[0], point[1]+box[3]-box[1]), fill=self.secondary)
            draw.multiline_text((point[0]-box[0], point[1]-box[1]), value, fill=self.text_color, font=font, spacing=4)
        self._render()

    def cancel_text(self):
        if self.text_editor:
            self.text_editor.destroy()
            self.text_editor = self.text_point = None
            self._render()

    def select_all(self):
        self.select_tool("select")
        self.selection = (0, 0, self.image.width, self.image.height)
        self._render()

    def copy(self):
        if self.selection:
            self.clip = self.image.crop(self.selection)
            write_image(self.clip, self.winfo_id())

    def cut(self):
        self.copy()
        self.delete_selection()

    def delete_selection(self):
        if self.selection:
            self.doc.snapshot()
            x0, y0, x1, y1 = self.selection
            ImageDraw.Draw(self.image).rectangle((x0, y0, x1-1, y1-1), fill=self.secondary)
            self.selection = None
            self._render()

    def paste(self):
        self.commit_text()
        incoming = read_image()
        if incoming is not None: self.clip = incoming
        if self.clip is None:
            messagebox.showinfo("Colar", "Copie uma imagem de outro aplicativo ou uma seleção do Paint Pro.", parent=self)
            return
        self.select_tool("select")
        size = max(self.image.width, self.clip.width), max(self.image.height, self.clip.height)
        if size[0]*size[1] > self.doc.MAX_PIXELS:
            messagebox.showerror('Colar', 'A imagem resultante excede 16 milhões de pixels.', parent=self)
            return
        self.doc.snapshot()
        if size != self.image.size:
            expanded = Image.new('RGB', size, self.secondary)
            expanded.paste(self.image, (0, 0))
            self.image = expanded
        self.image.paste(self.clip, (0, 0))
        self.selection = (0, 0, min(self.clip.width, self.image.width), min(self.clip.height, self.image.height))
        self._render()

    def crop(self):
        if self.selection:
            self.doc.snapshot()
            self.image = self.image.crop(self.selection)
            self.selection = None
            self._render()
        else: messagebox.showinfo("Cortar", "Use Selecionar para marcar a área que deseja manter.", parent=self)

    def transform(self, action):
        self.commit_text()
        self.cancel()
        self.doc.snapshot()
        if action in ("right", "left", "180"):
            self.image = self.image.rotate({"right": -90, "left": 90, "180": 180}[action], expand=True)
        else: self.image = ImageOps.mirror(self.image) if action == "horizontal" else ImageOps.flip(self.image)
        self._render()

    def resize_image(self):
        self.commit_text()
        result = SizeDialog(self, self.image.size).result
        if result is None: return
        try:
            self.cancel()
            self.doc.resize(result[0])
            self._render()
        except ValueError as error: messagebox.showerror("Redimensionar", str(error), parent=self)

    def resize_canvas(self):
        self.commit_text()
        result = SizeDialog(self, self.image.size, canvas=True).result
        if result is None: return
        size, anchor = result
        self.cancel()
        self.doc.snapshot()
        resized = Image.new('RGB', size, self.secondary)
        offset = ((size[0]-self.image.width)//2, (size[1]-self.image.height)//2) if anchor == 'Centro' else (0, 0)
        resized.paste(self.image, offset)
        self.image = resized
        self._render()

    def _render(self):
        if not hasattr(self, "status"): return
        origin = self.origin
        w, h = max(1, round(self.image.width*self.zoom)), max(1, round(self.image.height*self.zoom))
        self.canvas.configure(scrollregion=(0, 0, w+origin+10, h+origin+10))
        self.canvas.delete("all")
        self.canvas.create_rectangle(origin+4, origin+4, origin+w+5, origin+h+5, fill='#c8d3e2', outline='')
        # Render only the viewport, avoiding huge bitmaps at 800% zoom.
        left = max(0, int((self.canvas.canvasx(0)-origin)/self.zoom))
        top = max(0, int((self.canvas.canvasy(0)-origin)/self.zoom))
        right = min(self.image.width, math.ceil((self.canvas.canvasx(self.canvas.winfo_width())-origin)/self.zoom)+1)
        bottom = min(self.image.height, math.ceil((self.canvas.canvasy(self.canvas.winfo_height())-origin)/self.zoom)+1)
        if right > left and bottom > top:
            region = self.image.crop((left, top, right, bottom))
            region = region.resize((max(1, round((right-left)*self.zoom)), max(1, round((bottom-top)*self.zoom))), Image.Resampling.NEAREST if self.zoom >= 1 else Image.Resampling.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(region)
            self.canvas.create_image(origin+left*self.zoom, origin+top*self.zoom, image=self.tk_image, anchor="nw")
            if self.grid_on.get() and self.zoom >= 4:
                for x in range(left, right): self.canvas.create_line(origin+x*self.zoom, origin+top*self.zoom, origin+x*self.zoom, origin+bottom*self.zoom, fill="#d4d4d4")
                for y in range(top, bottom): self.canvas.create_line(origin+left*self.zoom, origin+y*self.zoom, origin+right*self.zoom, origin+y*self.zoom, fill="#d4d4d4")
        self.canvas.create_rectangle(origin-1, origin-1, origin+w, origin+h, outline='#bdc9d9')
        if self.selection:
            coords = tuple(origin+c*self.zoom for c in self.selection)
            self.canvas.create_rectangle(*coords, outline='white', width=2)
            self.canvas.create_rectangle(*coords, outline='#2563eb', dash=(5, 3))
        if self.rulers_on.get():
            for x in range(left//100*100, right, 100): self.canvas.create_text(origin+x*self.zoom, self.canvas.canvasy(10), text=str(x), fill="#535d68", anchor="w", font=("Segoe UI", 8))
            for y in range(top//100*100, bottom, 100): self.canvas.create_text(self.canvas.canvasx(3), origin+y*self.zoom, text=str(y), fill="#535d68", anchor="w", font=("Segoe UI", 8))
        tool = TOOLS.get(self.tool, SHAPES.get(self.tool, self.tool))
        hint = " • clique nos vértices; Enter fecha" if self.tool == "polygon" else " • arraste para curvar" if self.curve_stage else ""
        self.status.configure(text=f"{self.image.width} × {self.image.height} px     |     {tool}{hint}")
        if self.selection:
            box = self.selection
            self.status.configure(text=f'{self.image.width} × {self.image.height} px     |     Seleção {box[2]-box[0]} × {box[3]-box[1]} px')
        self.zoom_label.configure(text=f"{round(self.zoom*100)}%")
        self.zoom_slider.set(self.zoom*100)
        self.undo_button.configure(state='normal' if self.doc.undo_stack else 'disabled')
        self.redo_button.configure(state='normal' if self.doc.redo_stack else 'disabled')
        if self.text_editor:
            x, y = self.text_point
            self.canvas.create_window(origin+x*self.zoom, origin+y*self.zoom, window=self.text_editor, anchor='nw',
                                      width=max(30, min(420, (self.image.width-x)*self.zoom)), height=max(30, min(180, (self.image.height-y)*self.zoom)))
        self.refresh_chrome(tool)

    def refresh_chrome(self, tool):
        active = self.start is not None or self.curve_stage or bool(self.path_points)
        signature = (id(self.image), len(self.doc.undo_stack), len(self.doc.redo_stack), id(self.doc.saved), active)
        if signature != self._chrome_signature:
            self._dirty_display = True if active else self.doc.dirty
            self._chrome_signature = signature
        name = Path(self.doc.path).name if self.doc.path else 'Sem título'
        self.filename_label.configure(text=name if len(name) <= 35 else name[:32]+'…')
        editing = self.text_editor is not None
        self.saved_label.configure(text='Texto em edição' if editing else 'Alterações não salvas' if self._dirty_display else 'Salvo' if self.doc.path else 'Novo desenho',
                                   text_color='#9a6700' if editing or self._dirty_display else '#65748a', fg_color='#fff7df' if editing or self._dirty_display else '#f1f5f9')
        self.tool_label.configure(text=tool)
        for button in self.selection_buttons:
            button.configure(state='normal' if self.selection else 'disabled')
        marker = ' *' if self._dirty_display or editing else ''
        self.title(f'{name}{marker} — Paint Pro 0.5')

    def scroll(self, axis, *args):
        (self.canvas.xview if axis == "x" else self.canvas.yview)(*args)
        self._render()

    def mouse_wheel(self, event):
        if event.state & 4:
            self.zoom_at(self.zoom*(1.2 if event.delta > 0 else 1/1.2), event.x, event.y)
        else: self.scroll("y", "scroll", -1 if event.delta > 0 else 1, "units")
        return "break"

    def set_zoom(self, value):
        self.zoom = max(.1, min(8, value))
        self.update_text_font()
        self._render()

    def change_zoom(self, delta): self.set_zoom(self.zoom+delta)

    def zoom_at(self, value, x, y):
        point_x = (self.canvas.canvasx(x)-self.origin)/self.zoom
        point_y = (self.canvas.canvasy(y)-self.origin)/self.zoom
        self.set_zoom(value)
        extent_x = max(1, round(self.image.width*self.zoom)+self.origin+10)
        extent_y = max(1, round(self.image.height*self.zoom)+self.origin+10)
        self.canvas.xview_moveto((point_x*self.zoom+self.origin-x)/extent_x)
        self.canvas.yview_moveto((point_y*self.zoom+self.origin-y)/extent_y)
        self._render()

    def fit(self):
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.set_zoom(min((self.canvas.winfo_width()-self.origin*2-10)/self.image.width, (self.canvas.winfo_height()-self.origin*2-10)/self.image.height))

    def view_options(self):
        if self.status_on.get(): self.footer.grid()
        else: self.footer.grid_remove()
        self._render()

    def fullscreen(self): self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def undo(self):
        self.commit_text()
        self.cancel()
        self.doc.undo()
        self._render()

    def redo(self):
        self.cancel()
        self.doc.redo()
        self._render()

    def confirm_discard(self):
        self.commit_text()
        if not self.doc.dirty: return True
        result = messagebox.askyesnocancel("Paint Pro", "Deseja salvar as alterações?", parent=self)
        return False if result is None else self.save_file() if result else True

    def new_file(self):
        if self.confirm_discard():
            self.cancel()
            self.doc = Document()
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
            self.set_zoom(1)

    def open_file(self):
        if not self.confirm_discard(): return
        path = filedialog.askopenfilename(parent=self, filetypes=(("Imagens", "*.png *.jpg *.jpeg *.bmp"), ("Todos os arquivos", "*.*")))
        if path:
            try:
                self.cancel()
                self.doc.open(path)
                self.fit()
            except (OSError, ValueError, Image.DecompressionBombError) as error: messagebox.showerror("Abrir", str(error), parent=self)

    def save_file(self, save_as=False):
        self.commit_text()
        path = self.doc.path if not save_as else None
        if not path: path = filedialog.asksaveasfilename(parent=self, defaultextension=".png", filetypes=(("PNG", "*.png"), ("JPEG", "*.jpg"), ("Bitmap", "*.bmp")))
        if not path: return False
        try:
            if self.path_points: self.finish_polygon()
            # Keep the visible line/curve when saving during its second stage.
            self.curve_stage = False
            self.finish_gesture_history()
            self.start = self.last = self.preview_base = None
            self.doc.save(path)
            self._render()
            return True
        except (OSError, ValueError) as error:
            messagebox.showerror("Salvar", str(error), parent=self)
            return False

    def close(self):
        if self.confirm_discard(): self.destroy()
