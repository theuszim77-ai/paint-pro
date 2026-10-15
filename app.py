"""Paint Pro - an original lightweight desktop drawing application."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk


class PaintPro(ctk.CTk):
    CANVAS_SIZE = (1100, 700)
    PALETTE = ("#111827", "#ef4444", "#f97316", "#facc15", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#ffffff")

    def __init__(self) -> None:
        super().__init__()
        self.title("Paint Pro")
        self.geometry("1280x820")
        self.minsize(920, 620)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.image = Image.new("RGB", self.CANVAS_SIZE, "white")
        self.undo_stack: list[Image.Image] = []
        self.redo_stack: list[Image.Image] = []
        self.tool = "brush"
        self.color = "#111827"
        self.width = tk.IntVar(value=8)
        self.zoom = 1.0
        self.start: tuple[int, int] | None = None
        self.last: tuple[int, int] | None = None
        self.preview_base: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.file_path: str | None = None

        self._build_ui()
        self._bind_shortcuts()
        self._render()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, height=56, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(header, text="Paint Pro", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left", padx=18)
        for text, command in (("Novo", self.new_file), ("Abrir", self.open_file), ("Salvar", self.save_file), ("Desfazer", self.undo), ("Refazer", self.redo)):
            ctk.CTkButton(header, text=text, width=82, command=command).pack(side="left", padx=4, pady=10)

        sidebar = ctk.CTkFrame(self, width=150, corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text="Ferramentas", font=ctk.CTkFont(weight="bold")).pack(pady=(18, 8))
        for label, value in (("Pincel", "brush"), ("Borracha", "eraser"), ("Linha", "line"), ("Retângulo", "rectangle"), ("Elipse", "ellipse")):
            ctk.CTkButton(sidebar, text=label, width=120, command=lambda v=value: self.select_tool(v)).pack(pady=4)

        ctk.CTkLabel(sidebar, text="Espessura").pack(pady=(18, 2))
        ctk.CTkSlider(sidebar, from_=1, to=50, number_of_steps=49, variable=self.width).pack(padx=14)
        ctk.CTkLabel(sidebar, text="Cores").pack(pady=(18, 5))
        palette = ctk.CTkFrame(sidebar, fg_color="transparent")
        palette.pack()
        for index, color in enumerate(self.PALETTE):
            ctk.CTkButton(palette, text="", width=36, height=28, fg_color=color, hover_color=color,
                          border_width=1, border_color="#64748b", command=lambda c=color: self.set_color(c)).grid(row=index // 2, column=index % 2, padx=3, pady=3)
        ctk.CTkButton(sidebar, text="Mais cores", width=120, command=self.choose_color).pack(pady=8)

        workspace = ctk.CTkFrame(self, corner_radius=0, fg_color="#334155")
        workspace.grid(row=1, column=1, sticky="nsew")
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(workspace, bg="#334155", highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        horizontal = tk.Scrollbar(workspace, orient="horizontal", command=self.canvas.xview)
        vertical = tk.Scrollbar(workspace, orient="vertical", command=self.canvas.yview)
        horizontal.grid(row=1, column=0, sticky="ew")
        vertical.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        self.canvas.bind("<ButtonPress-1>", self.pointer_down)
        self.canvas.bind("<B1-Motion>", self.pointer_move)
        self.canvas.bind("<ButtonRelease-1>", self.pointer_up)
        self.canvas.bind("<Configure>", lambda _event: self._render())

        footer = ctk.CTkFrame(self, height=42, corner_radius=0)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status = ctk.CTkLabel(footer, text="Pincel • 100%")
        self.status.pack(side="left", padx=16)
        ctk.CTkButton(footer, text="−", width=38, command=lambda: self.change_zoom(-0.1)).pack(side="right", padx=3, pady=5)
        ctk.CTkButton(footer, text="+", width=38, command=lambda: self.change_zoom(0.1)).pack(side="right", padx=3, pady=5)

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-z>", lambda _e: self.undo())
        self.bind("<Control-y>", lambda _e: self.redo())
        self.bind("<Control-s>", lambda _e: self.save_file())
        self.bind("<Control-o>", lambda _e: self.open_file())
        self.bind("<Control-n>", lambda _e: self.new_file())
        self.bind("<Control-plus>", lambda _e: self.change_zoom(0.1))
        self.bind("<Control-minus>", lambda _e: self.change_zoom(-0.1))

    def _canvas_point(self, event: tk.Event) -> tuple[int, int]:
        shown_w, shown_h = int(self.image.width * self.zoom), int(self.image.height * self.zoom)
        left = max(0, (self.canvas.winfo_width() - shown_w) // 2)
        top = max(0, (self.canvas.winfo_height() - shown_h) // 2)
        x = max(0, min(self.image.width - 1, int((self.canvas.canvasx(event.x) - left) / self.zoom)))
        y = max(0, min(self.image.height - 1, int((self.canvas.canvasy(event.y) - top) / self.zoom)))
        return x, y

    def _snapshot(self) -> None:
        self.undo_stack.append(self.image.copy())
        self.undo_stack = self.undo_stack[-30:]
        self.redo_stack.clear()

    def pointer_down(self, event: tk.Event) -> None:
        self._snapshot()
        self.start = self.last = self._canvas_point(event)
        self.preview_base = self.image.copy()
        if self.tool in ("brush", "eraser"):
            self.pointer_move(event)

    def pointer_move(self, event: tk.Event) -> None:
        if self.last is None:
            return
        point = self._canvas_point(event)
        if self.tool in ("brush", "eraser"):
            color = "white" if self.tool == "eraser" else self.color
            draw = ImageDraw.Draw(self.image)
            draw.line((self.last, point), fill=color, width=self.width.get(), joint="curve")
            radius = self.width.get() // 2
            draw.ellipse((point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius), fill=color)
            self.last = point
        elif self.start and self.preview_base:
            self.image = self.preview_base.copy()
            self._draw_shape(self.start, point)
        self._render()

    def pointer_up(self, event: tk.Event) -> None:
        if self.start and self.tool not in ("brush", "eraser"):
            self.image = self.preview_base.copy() if self.preview_base else self.image
            self._draw_shape(self.start, self._canvas_point(event))
        self.start = self.last = None
        self.preview_base = None
        self._render()

    def _draw_shape(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        draw = ImageDraw.Draw(self.image)
        options = {"fill": self.color, "width": self.width.get()}
        if self.tool == "line":
            draw.line((start, end), **options)
        else:
            box = (min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1]))
            getattr(draw, self.tool)(box, outline=self.color, width=self.width.get())

    def _render(self) -> None:
        size = (max(1, int(self.image.width * self.zoom)), max(1, int(self.image.height * self.zoom)))
        display = self.image.resize(size, Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(display)
        self.canvas.delete("all")
        left = max(0, (self.canvas.winfo_width() - size[0]) // 2)
        top = max(0, (self.canvas.winfo_height() - size[1]) // 2)
        self.canvas.create_image(left, top, image=self.tk_image, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, max(size[0], self.canvas.winfo_width()), max(size[1], self.canvas.winfo_height())))
        self.status.configure(text=f"{self.tool.capitalize()} • {int(self.zoom * 100)}% • {self.image.width}×{self.image.height}")

    def select_tool(self, tool: str) -> None:
        self.tool = tool
        self._render()

    def set_color(self, color: str) -> None:
        self.color = color
        self._render()

    def choose_color(self) -> None:
        color = colorchooser.askcolor(color=self.color, title="Escolha uma cor")[1]
        if color:
            self.set_color(color)

    def change_zoom(self, delta: float) -> None:
        self.zoom = round(max(0.2, min(3.0, self.zoom + delta)), 1)
        self._render()

    def undo(self) -> None:
        if self.undo_stack:
            self.redo_stack.append(self.image.copy())
            self.image = self.undo_stack.pop()
            self._render()

    def redo(self) -> None:
        if self.redo_stack:
            self.undo_stack.append(self.image.copy())
            self.image = self.redo_stack.pop()
            self._render()

    def new_file(self) -> None:
        if messagebox.askyesno("Novo desenho", "Limpar a tela e começar um novo desenho?"):
            self._snapshot()
            self.image = Image.new("RGB", self.CANVAS_SIZE, "white")
            self.file_path = None
            self._render()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=(("Imagens", "*.png *.jpg *.jpeg"), ("Todos os arquivos", "*.*")))
        if path:
            try:
                self._snapshot()
                self.image = Image.open(path).convert("RGB")
                self.file_path = path
                self.zoom = min(1.0, 1000 / self.image.width, 650 / self.image.height)
                self._render()
            except OSError as error:
                messagebox.showerror("Erro", f"Não foi possível abrir a imagem.\n{error}")

    def save_file(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=(("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")))
        if path:
            try:
                self.image.save(path, quality=95)
                self.file_path = path
                messagebox.showinfo("Paint Pro", "Imagem salva com sucesso.")
            except OSError as error:
                messagebox.showerror("Erro", f"Não foi possível salvar a imagem.\n{error}")


if __name__ == "__main__":
    PaintPro().mainloop()
