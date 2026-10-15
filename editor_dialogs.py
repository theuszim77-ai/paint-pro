"""Small modal dialogs for image size and canvas size."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk


class SizeDialog(ctk.CTkToplevel):
    def __init__(self, master, size, canvas=False):
        super().__init__(master)
        self.result = None
        self.original = size
        self.title('Tamanho da tela' if canvas else 'Redimensionar imagem')
        self.geometry('400x320')
        self.resizable(False, False)
        self.transient(master)
        self.unit = tk.StringVar(value='Pixels')
        self.width_value = tk.StringVar(value=str(size[0]))
        self.height_value = tk.StringVar(value=str(size[1]))
        self.lock = tk.BooleanVar(value=not canvas)
        self.anchor = tk.StringVar(value='Superior esquerdo')
        self.changing = False
        self.canvas_mode = canvas
        ctk.CTkLabel(self, text='Dimensões', font=('Segoe UI', 18, 'bold')).pack(pady=(16, 8))
        if not canvas:
            ctk.CTkSegmentedButton(self, values=['Pixels', 'Porcentagem'], variable=self.unit, command=self.change_unit).pack(pady=4)
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(pady=8)
        for row, (label, value) in enumerate((('Largura', self.width_value), ('Altura', self.height_value))):
            ctk.CTkLabel(body, text=label).grid(row=row, column=0, padx=8, pady=4)
            ctk.CTkEntry(body, textvariable=value, width=130).grid(row=row, column=1)
        if canvas:
            ctk.CTkOptionMenu(self, values=['Superior esquerdo', 'Centro'], variable=self.anchor).pack(pady=5)
            ctk.CTkLabel(self, text='Expande ou recorta sem esticar o desenho.').pack()
        else:
            ctk.CTkCheckBox(self, text='Manter proporção', variable=self.lock).pack(pady=8)
        self.width_value.trace_add('write', lambda *_: self.sync(True))
        self.height_value.trace_add('write', lambda *_: self.sync(False))
        buttons = ctk.CTkFrame(self, fg_color='transparent')
        buttons.pack(side='bottom', pady=16)
        ctk.CTkButton(buttons, text='Aplicar', command=self.accept, width=100).pack(side='left', padx=5)
        ctk.CTkButton(buttons, text='Cancelar', command=self.destroy, width=100).pack(side='left', padx=5)
        self.bind('<Return>', lambda _e: self.accept())
        self.bind('<Escape>', lambda _e: self.destroy())
        self.wait_visibility()
        self.grab_set()
        self.wait_window()

    def change_unit(self, unit):
        self.changing = True
        self.width_value.set('100' if unit == 'Porcentagem' else str(self.original[0]))
        self.height_value.set('100' if unit == 'Porcentagem' else str(self.original[1]))
        self.changing = False

    def sync(self, from_width):
        if self.changing or not self.lock.get() or self.canvas_mode:
            return
        try:
            value = float(self.width_value.get() if from_width else self.height_value.get())
            ratio = 1 if self.unit.get() == 'Porcentagem' else self.original[1]/self.original[0] if from_width else self.original[0]/self.original[1]
            self.changing = True
            (self.height_value if from_width else self.width_value).set(str(max(1, round(value*ratio))))
        except ValueError:
            pass
        finally:
            self.changing = False

    def accept(self):
        try:
            values = float(self.width_value.get()), float(self.height_value.get())
            if any(not (0 < v <= 16_000_000) for v in values):
                raise ValueError
            size = tuple(max(1, round(v*self.original[i]/100)) if self.unit.get() == 'Porcentagem' else round(v) for i, v in enumerate(values))
            if min(size) < 1 or size[0]*size[1] > 16_000_000:
                raise ValueError
        except (ValueError, OverflowError):
            messagebox.showerror('Dimensões', 'Informe dimensões positivas, até 16 milhões de pixels.', parent=self)
            return
        self.result = size, self.anchor.get()
        self.destroy()
