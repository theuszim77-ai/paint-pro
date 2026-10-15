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
        self.geometry("1320x850")
        self.minsize(1160, 620)
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
        self.grid_on = tk.BooleanVar(value=False)
        self.rulers_on = tk.BooleanVar(value=False)
        self.status_on = tk.BooleanVar(value=True)
        self._build_ui()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self._render)

    @property
    def image(self):
        return self.doc.image

    @image.setter
    def image(self, value):
        self.doc.image = value

    def button(self, parent, text, command, width=60, height=28):
        return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
                             fg_color="transparent", text_color="#202020", hover_color="#d9eafa",
                             corner_radius=2, border_spacing=3, font=("Segoe UI", 12))

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        quick = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#f5f6f7")
        quick.grid(row=0, column=0, sticky="ew")
        for label, command in (("Salvar", self.save_file), ("↶", self.undo), ("↷", self.redo)):
            button = self.button(quick, label, command, 46, 25)
            button.pack(side="left", padx=2)
            if label == '↶': self.undo_button = button
            elif label == '↷': self.redo_button = button
        ctk.CTkLabel(quick, text="Paint Pro", font=("Segoe UI", 12)).pack(side="left", padx=14)
        tabs = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#fafafa")
        tabs.grid(row=1, column=0, sticky="ew")
        ctk.CTkButton(tabs, text="Arquivo", command=self.file_menu, width=65, height=28, corner_radius=0, fg_color="#1979c4").pack(side="left")
        self.button(tabs, "Início", lambda: self.show_tab("home"), 65).pack(side="left")
        self.button(tabs, "Exibir", lambda: self.show_tab("view"), 65).pack(side="left")
        self.button(tabs, 'Texto', lambda: self.select_tool('text'), 65).pack(side='left')
        self.ribbon = ctk.CTkFrame(self, corner_radius=0, fg_color="#f5f6f7", height=142)
        self.ribbon.grid(row=2, column=0, sticky="ew")
        self.ribbon.pack_propagate(False)
        self.home = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.view = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.textbar = ctk.CTkFrame(self.ribbon, fg_color='transparent')
        self.home.pack(fill="both", expand=True)

        def group(title):
            frame = ctk.CTkFrame(self.home, fg_color="transparent", corner_radius=0, border_width=1, border_color="#dce0e5")
            frame.pack(side="left", fill="y", padx=(0, 1))
            body = ctk.CTkFrame(frame, fg_color="transparent")
            body.pack(fill="both", expand=True, padx=5, pady=(5, 0))
            ctk.CTkLabel(frame, text=title, height=19, font=("Segoe UI", 11), text_color="#666666").pack(side="bottom")
            return body

        clipboard = group("Área de Transferência")
        self.button(clipboard, "▣\nColar", self.paste, 45, 64).grid(row=0, column=0, rowspan=2)
        self.button(clipboard, "Recortar", self.cut, 60).grid(row=0, column=1)
        self.button(clipboard, "Copiar", self.copy, 60).grid(row=1, column=1)
        images = group("Imagem")
        for i, (label, cmd) in enumerate((("Selecionar", lambda: self.select_tool("select")), ("Cortar", self.crop), ("Redimensionar", self.resize_image), ("Girar ▾", self.rotate_menu))):
            self.button(images, label, cmd, 88, 26).grid(row=i//2, column=i%2, pady=4)
        tools = group("Ferramentas")
        self.tool_buttons = {}
        for i, (tool, symbol) in enumerate(zip(("pencil", "fill", "text", "eraser", "picker", "magnify"), ("✎", "▨", "A", "▰", "⌖", "⊕"))):
            button = self.button(tools, symbol, lambda t=tool: self.select_tool(t), 28, 28)
            button.grid(row=i//3, column=i%3, padx=1, pady=2)
            self.tooltip(button, TOOLS[tool])
            self.tool_buttons[tool] = button
        brush = group("Pincéis")
        self.tool_buttons["brush"] = self.button(brush, "╱\nPincel", lambda: self.select_tool("brush"), 63, 52)
        self.tool_buttons["brush"].pack()
        self.option(brush, self.brush_mode, ["Pincel", "Caligrafia", "Marcador"], 92, lambda _v: self.select_tool("brush")).pack()
        shapes = group("Formas")
        gallery = ctk.CTkFrame(shapes, fg_color="white", corner_radius=0)
        gallery.grid(row=0, column=0, rowspan=4)
        self.icons = []
        for i, tool in enumerate(SHAPES):
            # Generate icons from the same original geometry; no external icon assets.
            icon = Image.new("RGB", (22, 22), "white")
            shape(icon, "line" if tool in ("curve", "polygon") else tool, (3, 3), (18, 18), "#243345", "white", 1)
            image = ctk.CTkImage(icon, size=(18, 18))
            self.icons.append(image)
            b = self.button(gallery, "", lambda t=tool: self.select_tool(t), 23, 23)
            b.configure(image=image)
            b.grid(row=i//8, column=i%8)
            self.tooltip(b, SHAPES[tool])
            self.tool_buttons[tool] = b
        for i, (label, variable, values) in enumerate((("Contorno", self.outline_mode, ["Cor sólida", "Sem contorno"]), ("Preenchimento", self.fill_mode, ["Sem preenchimento", "Cor sólida"]))):
            ctk.CTkLabel(shapes, text=label, height=17, font=("Segoe UI", 10)).grid(row=i*2, column=1, padx=3)
            self.option(shapes, variable, values, 111).grid(row=i*2+1, column=1)
        size = group("Tamanho")
        for val in (1, 3, 5, 8):
            self.button(size, "━━ " + str(val), lambda v=val: self.width.set(v), 54, 20).pack()
        colors = group("Cores")
        self.primary_button = self.button(colors, "Cor 1", lambda: self.activate_color(1), 44, 30)
        self.primary_button.grid(row=0, column=0)
        self.secondary_button = self.button(colors, "Cor 2", lambda: self.activate_color(2), 44, 30)
        self.secondary_button.grid(row=1, column=0)
        for i, color in enumerate(PALETTE):
            b = ctk.CTkButton(colors, text="", width=16, height=20, fg_color=color, hover_color=color, corner_radius=0, border_width=1, border_color="#aaaaaa", command=lambda c=color: self.set_color(c))
            b.grid(row=i//10, column=1+i%10, padx=1, pady=1)
            b.bind("<Button-3>", lambda _e, c=color: self.set_color(c, 2))
        self.button(colors, "Editar cores", self.choose_color, 80, 24).grid(row=2, column=1, columnspan=5)
        self.button(colors, "⇄", self.swap_colors, 35, 24).grid(row=2, column=0)
        self._color_buttons()
        text_fields = ctk.CTkFrame(self.textbar, fg_color='transparent')
        text_fields.pack(side='left', padx=20, pady=20)
        ctk.CTkLabel(text_fields, text='Fonte').grid(row=0, column=0, sticky='w')
        ctk.CTkOptionMenu(text_fields, variable=self.text_family, values=['Arial', 'Segoe UI', 'Times New Roman', 'Courier New'], command=lambda _v: self.update_text_font(), width=170).grid(row=1, column=0, padx=(0, 12))
        ctk.CTkLabel(text_fields, text='Tamanho (px)').grid(row=0, column=1, sticky='w')
        ctk.CTkComboBox(text_fields, variable=self.text_size, values=['12', '16', '20', '24', '32', '48', '72'], width=85, command=lambda _v: self.update_text_font()).grid(row=1, column=1)
        self.text_size.trace_add('write', lambda *_: self.update_text_font())
        for label, var in (('Negrito', self.text_bold), ('Itálico', self.text_italic), ('Fundo com Cor 2', self.text_opaque)):
            ctk.CTkCheckBox(self.textbar, text=label, variable=var, command=self.update_text_font, width=100).pack(side='left', padx=10)
        self.button(self.textbar, 'Aplicar texto', self.commit_text, 100, 36).pack(side='left', padx=12)
        self.button(self.textbar, 'Cancelar', self.cancel_text, 80, 36).pack(side='left')
        for label, cmd in (("Ampliar", lambda: self.change_zoom(.25)), ("Reduzir", lambda: self.change_zoom(-.25)), ("100%", lambda: self.set_zoom(1)), ("Ajustar à janela", self.fit), ("Tela inteira", self.fullscreen)):
            self.button(self.view, label, cmd, 110, 56).pack(side="left", padx=6, pady=15)
        for label, var in (("Linhas de grade", self.grid_on), ("Réguas", self.rulers_on), ("Barra de status", self.status_on)):
            ctk.CTkCheckBox(self.view, text=label, variable=var, command=self.view_options, width=110, font=("Segoe UI", 12)).pack(side="left", padx=8)
        workspace = ctk.CTkFrame(self, fg_color="#cdd7e4", corner_radius=0)
        workspace.grid(row=3, column=0, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(workspace, bg="#cdd7e4", highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.hscroll = tk.Scrollbar(workspace, orient="horizontal", command=lambda *args: self.scroll("x", *args))
        self.vscroll = tk.Scrollbar(workspace, command=lambda *args: self.scroll("y", *args))
        self.hscroll.grid(row=1, column=0, sticky="ew")
        self.vscroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=self.hscroll.set, yscrollcommand=self.vscroll.set)
        self.canvas.bind("<Configure>", lambda _e: self._render())
        for num in (1, 3):
            self.canvas.bind(f"<ButtonPress-{num}>", self.pointer_down)
            self.canvas.bind(f"<B{num}-Motion>", self.pointer_move)
            self.canvas.bind(f"<ButtonRelease-{num}>", self.pointer_up)
        self.canvas.bind("<Motion>", self.pointer_hover)
        self.canvas.bind("<Double-Button-1>", lambda _e: self.finish_polygon())
        self.canvas.bind("<MouseWheel>", self.mouse_wheel)
        self.footer = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#f4f5f6")
        self.footer.grid(row=4, column=0, sticky="ew")
        self.status = ctk.CTkLabel(self.footer, text="", font=("Segoe UI", 11), height=26)
        self.status.pack(side="left", padx=12)
        self.zoom_label = ctk.CTkLabel(self.footer, text="100%", width=50, height=24)
        self.zoom_slider = ctk.CTkSlider(self.footer, from_=10, to=800, width=140, command=lambda v: self.set_zoom(float(v)/100))
        self.button(self.footer, "+", lambda: self.change_zoom(.25), 24, 24).pack(side="right")
        self.zoom_slider.pack(side="right", padx=5)
        self.button(self.footer, "−", lambda: self.change_zoom(-.25), 24, 24).pack(side="right")
        self.zoom_label.pack(side="right", padx=8)

    def option(self, parent, variable, values, width, command=None):
        return ctk.CTkOptionMenu(parent, values=values, variable=variable, command=command, width=width, height=22, font=("Segoe UI", 10), fg_color="#e4e8ed", text_color="#222222", button_color="#ccd5df")

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
            button.configure(fg_color="#c9e5f9" if name == tool else "transparent")
        self.canvas.configure(cursor="xterm" if tool == "text" else "crosshair")
        self._render()
        if tool == 'text': self.show_tab('text')

    @property
    def origin(self):
        return 25 if self.rulers_on.get() else 6

    def _canvas_point(self, event, clamp=True):
        x = math.floor((self.canvas.canvasx(event.x)-self.origin)/self.zoom)
        y = math.floor((self.canvas.canvasy(event.y)-self.origin)/self.zoom)
        if not clamp and not (0 <= x < self.image.width and 0 <= y < self.image.height): return None
        return max(0, min(self.image.width-1, x)), max(0, min(self.image.height-1, y))

    def pointer_down(self, event):
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
        if self.last is None: return
        point = self._canvas_point(event)
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
        self.canvas.create_rectangle(origin-1, origin-1, origin+w, origin+h, outline="#919aa5")
        if self.selection: self.canvas.create_rectangle(*(origin+c*self.zoom for c in self.selection), outline="#1477cf", dash=(4, 3))
        if self.rulers_on.get():
            for x in range(left//100*100, right, 100): self.canvas.create_text(origin+x*self.zoom, self.canvas.canvasy(10), text=str(x), fill="#535d68", anchor="w", font=("Segoe UI", 8))
            for y in range(top//100*100, bottom, 100): self.canvas.create_text(self.canvas.canvasx(3), origin+y*self.zoom, text=str(y), fill="#535d68", anchor="w", font=("Segoe UI", 8))
        tool = TOOLS.get(self.tool, SHAPES.get(self.tool, self.tool))
        hint = " • clique nos vértices; Enter fecha" if self.tool == "polygon" else " • arraste para curvar" if self.curve_stage else ""
        self.status.configure(text=f"{self.image.width} × {self.image.height} px     |     {tool}{hint}")
        self.zoom_label.configure(text=f"{round(self.zoom*100)}%")
        self.zoom_slider.set(self.zoom*100)
        self.undo_button.configure(state='normal' if self.doc.undo_stack else 'disabled')
        self.redo_button.configure(state='normal' if self.doc.redo_stack else 'disabled')
        if self.text_editor:
            x, y = self.text_point
            self.canvas.create_window(origin+x*self.zoom, origin+y*self.zoom, window=self.text_editor, anchor='nw',
                                      width=max(30, min(420, (self.image.width-x)*self.zoom)), height=max(30, min(180, (self.image.height-y)*self.zoom)))
        self.title(f"{Path(self.doc.path).name if self.doc.path else 'Sem título'} — Paint Pro")

    def scroll(self, axis, *args):
        (self.canvas.xview if axis == "x" else self.canvas.yview)(*args)
        self._render()

    def mouse_wheel(self, event):
        if event.state & 4: self.change_zoom(.25 if event.delta > 0 else -.25)
        else: self.scroll("y", "scroll", -1 if event.delta > 0 else 1, "units")
        return "break"

    def set_zoom(self, value):
        self.zoom = max(.1, min(8, value))
        self.update_text_font()
        self._render()

    def change_zoom(self, delta): self.set_zoom(self.zoom+delta)

    def fit(self):
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.set_zoom(min((self.canvas.winfo_width()-40)/self.image.width, (self.canvas.winfo_height()-40)/self.image.height))

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
