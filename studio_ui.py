"""A consistent light ribbon, original icons, and a quieter drawing workspace."""
import tkinter as tk
import customtkinter as ctk
from document import SHAPES
from ui_icons import icon

INK = '#25354a'
MUTED = '#65748a'
BLUE = '#2563eb'
SURFACE = '#ffffff'
LINE = '#e2e8f0'
PALETTE = ['#172033', '#64748b', '#991b1b', '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#3b82f6', '#8b5cf6',
           '#ffffff', '#cbd5e1', '#a16207', '#fda4af', '#fdba74', '#fef08a', '#bbf7d0', '#a5f3fc', '#bfdbfe', '#ddd6fe']


def build_ui(a):
    a.configure(fg_color='#f1f5f9')
    a.grid_columnconfigure(0, weight=1)
    a.grid_rowconfigure(3, weight=1)
    a.icon_refs = []
    a.tab_buttons = {}
    a.tool_buttons = {}
    a.selection_buttons = []

    def image(name, size=22, color=INK):
        result = ctk.CTkImage(icon(name, color, size), size=(size, size))
        a.icon_refs.append(result)
        return result

    def action(parent, label, command, symbol=None, width=80, height=32, primary=False):
        b = a.button(parent, label, command, width, height)
        b.configure(corner_radius=6, fg_color=BLUE if primary else 'transparent', hover_color='#1d4ed8' if primary else '#eef4ff',
                    text_color='white' if primary else INK, border_spacing=5)
        if symbol: b.configure(image=image(symbol, 19, '#ffffff' if primary else INK))
        return b

    header = ctk.CTkFrame(a, fg_color=SURFACE, corner_radius=0, height=64)
    header.grid(row=0, column=0, sticky='ew')
    header.pack_propagate(False)
    brand = ctk.CTkLabel(header, text='', image=image('palette', 29, BLUE), width=46)
    brand.pack(side='left', padx=(14, 0))
    names = ctk.CTkFrame(header, fg_color='transparent')
    names.pack(side='left', padx=7)
    ctk.CTkLabel(names, text='Paint Pro', font=('Segoe UI', 18, 'bold'), text_color=INK, height=25, anchor='w').pack(anchor='w')
    a.filename_label = ctk.CTkLabel(names, text='Sem título', font=('Segoe UI', 11), text_color=MUTED, height=18, anchor='w')
    a.filename_label.pack(anchor='w')
    a.saved_label = ctk.CTkLabel(header, text='Novo desenho', text_color=MUTED, font=('Segoe UI', 11), fg_color='#f1f5f9', corner_radius=10, height=24)
    a.saved_label.pack(side='left', padx=16)
    action(header, 'Salvar', a.save_file, 'save', 100, 36, True).pack(side='right', padx=(7, 18))
    action(header, 'Abrir', a.open_file, 'open', 84, 36).pack(side='right', padx=2)
    action(header, 'Novo', a.new_file, 'new', 80, 36).pack(side='right', padx=2)
    divider = ctk.CTkFrame(header, width=1, height=28, fg_color=LINE)
    divider.pack(side='right', padx=10)
    a.redo_button = action(header, '', a.redo, 'redo', 34, 34)
    a.redo_button.pack(side='right', padx=2)
    a.tooltip(a.redo_button, 'Refazer · Ctrl+Y')
    a.undo_button = action(header, '', a.undo, 'undo', 34, 34)
    a.undo_button.pack(side='right', padx=2)
    a.tooltip(a.undo_button, 'Desfazer · Ctrl+Z')

    tabs = ctk.CTkFrame(a, fg_color=SURFACE, corner_radius=0, height=39)
    tabs.grid(row=1, column=0, sticky='ew')
    action(tabs, 'Arquivo', a.file_menu, width=78).pack(side='left', padx=(14, 7), pady=3)
    for title, name in [('Início', 'home'), ('Exibir', 'view'), ('Texto', 'text')]:
        b = action(tabs, title, lambda n=name: a.select_tool('text') if n == 'text' else a.show_tab(n), width=80)
        b.pack(side='left', padx=3, pady=3)
        a.tab_buttons[name] = b
    action(tabs, 'Atalhos', a.show_help, width=72).pack(side='right', padx=(5, 16))
    a.tool_label = ctk.CTkLabel(tabs, text='Pincel', font=('Segoe UI', 11), text_color=MUTED)
    a.tool_label.pack(side='right', padx=12)

    a.ribbon = ctk.CTkFrame(a, fg_color=SURFACE, corner_radius=0, height=158)
    a.ribbon.grid(row=2, column=0, sticky='ew')
    a.ribbon.pack_propagate(False)
    a.home = ctk.CTkScrollableFrame(a.ribbon, fg_color=SURFACE, corner_radius=0, orientation='horizontal', scrollbar_button_color='#dbe4f1', scrollbar_button_hover_color='#b9c9df')
    a.home.pack(fill='both', expand=True, padx=8)
    a.view = ctk.CTkFrame(a.ribbon, fg_color=SURFACE, corner_radius=0)
    a.textbar = ctk.CTkFrame(a.ribbon, fg_color=SURFACE, corner_radius=0)

    def group(title):
        outer = ctk.CTkFrame(a.home, fg_color=SURFACE, corner_radius=0)
        outer.pack(side='left', fill='y', padx=(0, 4))
        body = ctk.CTkFrame(outer, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=8, pady=(5, 2))
        ctk.CTkLabel(outer, text=title, font=('Segoe UI', 10), text_color=MUTED, height=19).pack(side='bottom', pady=(0, 2))
        ctk.CTkFrame(a.home, fg_color=LINE, width=1, height=98).pack(side='left', padx=2, pady=10)
        return body

    transfer = group('ÁREA DE TRANSFERÊNCIA')
    action(transfer, 'Colar', a.paste, 'paste', 72, 32).pack()
    for label, cmd, name in [('Copiar', a.copy, 'copy'), ('Recortar', a.cut, 'cut')]:
        b = action(transfer, label, cmd, name, 72, 26)
        b.pack(pady=1)
        a.selection_buttons.append(b)
    images = group('IMAGEM')
    for i, (label, cmd, name) in enumerate([('Selecionar', lambda: a.select_tool('select'), 'select'), ('Cortar', a.crop, 'crop'), ('Tamanho', a.resize_image, 'resize'), ('Girar', a.rotate_menu, 'rotate')]):
        b = action(images, label, cmd, name, 86, 34)
        b.grid(row=i//2, column=i%2, padx=1, pady=4)
        if name == 'select': a.tool_buttons['select'] = b
        if name == 'crop': a.selection_buttons.append(b)

    tools = group('FERRAMENTAS')
    for i, tool in enumerate(['pencil', 'fill', 'text', 'eraser', 'picker', 'magnify']):
        b = action(tools, '', lambda t=tool: a.select_tool(t), tool, 34, 34)
        b.grid(row=i//3, column=i%3, padx=2, pady=4)
        a.tool_buttons[tool] = b
        a.tooltip(b, a.tool_names[tool])
    brushes = group('PINCÉIS')
    a.tool_buttons['brush'] = action(brushes, 'Pincel', lambda: a.select_tool('brush'), 'brush', 92, 42)
    a.tool_buttons['brush'].pack(pady=3)
    a.option(brushes, a.brush_mode, ['Pincel', 'Caligrafia', 'Marcador'], 100, lambda _v: a.select_tool('brush')).pack(pady=4)
    shapes = group('FORMAS')
    for i, tool in enumerate(SHAPES):
        b = action(shapes, '', lambda t=tool: a.select_tool(t), tool, 26, 26)
        b.grid(row=i//8, column=i%8, padx=1, pady=1)
        a.tool_buttons[tool] = b
        a.tooltip(b, SHAPES[tool])
    style = group('ESTILO')
    for title, var, values in [('Contorno', a.outline_mode, ['Cor sólida', 'Sem contorno']), ('Preenchimento', a.fill_mode, ['Sem preenchimento', 'Cor sólida'])]:
        ctk.CTkLabel(style, text=title, font=('Segoe UI', 10), text_color=MUTED, anchor='w', height=17).pack(anchor='w')
        a.option(style, var, values, 115).pack(pady=(0, 3))
    colors = group('CORES')
    a.primary_button = action(colors, '1', lambda: a.activate_color(1), width=32, height=32)
    a.primary_button.grid(row=0, column=0, padx=(0, 5))
    a.secondary_button = action(colors, '2', lambda: a.activate_color(2), width=32, height=32)
    a.secondary_button.grid(row=1, column=0, padx=(0, 5))
    for i, color in enumerate(PALETTE):
        b = ctk.CTkButton(colors, text='', width=18, height=23, corner_radius=5, fg_color=color, hover_color=color, border_width=1, border_color='#d0d8e5', command=lambda c=color: a.set_color(c))
        b.grid(row=i//10, column=1+i%10, padx=2, pady=3)
        b.bind('<Button-3>', lambda _e, c=color: a.set_color(c, 2))
    action(colors, 'Editar cores', a.choose_color, 'palette', 106, 24).grid(row=2, column=1, columnspan=6, sticky='w')
    action(colors, 'Trocar', a.swap_colors, width=56, height=24).grid(row=2, column=7, columnspan=4)
    a._color_buttons()

    viewrow = ctk.CTkFrame(a.view, fg_color='transparent')
    viewrow.pack(side='left', padx=18, pady=20)
    for label, cmd, symbol in [('Ampliar', lambda: a.change_zoom(.25), 'zoom_in'), ('Reduzir', lambda: a.change_zoom(-.25), 'zoom_out'), ('100%', lambda: a.set_zoom(1), 'magnify'), ('Ajustar', a.fit, 'fit')]:
        action(viewrow, label, cmd, symbol, 96, 48).pack(side='left', padx=4)
    viewchecks = ctk.CTkFrame(a.view, fg_color='transparent')
    viewchecks.pack(side='left', padx=18)
    for title, var in [('Grade de pixels', a.grid_on), ('Réguas', a.rulers_on), ('Barra de status', a.status_on)]:
        ctk.CTkCheckBox(viewchecks, text=title, variable=var, command=a.view_options, font=('Segoe UI', 12), checkbox_width=18, checkbox_height=18).pack(anchor='w', pady=5)
    action(a.view, 'Tela inteira · F11', a.fullscreen, 'fit', 150, 40).pack(side='left', padx=18)

    textfields = ctk.CTkFrame(a.textbar, fg_color='transparent')
    textfields.pack(side='left', padx=20, pady=20)
    for col, label in enumerate(['Família da fonte', 'Tamanho (px)']): ctk.CTkLabel(textfields, text=label, font=('Segoe UI', 11), text_color=MUTED).grid(row=0, column=col, sticky='w')
    a.option(textfields, a.text_family, ['Arial', 'Segoe UI', 'Times New Roman', 'Courier New'], 175, lambda _v: a.update_text_font()).grid(row=1, column=0, padx=(0, 12))
    ctk.CTkComboBox(textfields, variable=a.text_size, values=['12', '16', '20', '24', '32', '48', '72'], width=85, command=lambda _v: a.update_text_font()).grid(row=1, column=1)
    a.text_size.trace_add('write', lambda *_: a.update_text_font())
    for label, var in [('Negrito', a.text_bold), ('Itálico', a.text_italic), ('Fundo com Cor 2', a.text_opaque)]:
        ctk.CTkCheckBox(a.textbar, text=label, variable=var, command=a.update_text_font, checkbox_width=18, checkbox_height=18, width=105).pack(side='left', padx=8)
    action(a.textbar, 'Aplicar texto', a.commit_text, width=108, height=36, primary=True).pack(side='left', padx=15)
    action(a.textbar, 'Cancelar', a.cancel_text, width=80, height=36).pack(side='left')

    workspace = ctk.CTkFrame(a, corner_radius=0, fg_color='#e5ebf3')
    workspace.grid(row=3, column=0, sticky='nsew')
    workspace.grid_columnconfigure(0, weight=1)
    workspace.grid_rowconfigure(1, weight=1)
    options = ctk.CTkFrame(workspace, fg_color='#f7f9fc', height=40, corner_radius=0)
    options.grid(row=0, column=0, columnspan=2, sticky='ew')
    ctk.CTkLabel(options, text='Espessura', text_color=MUTED, font=('Segoe UI', 11)).pack(side='left', padx=(22, 10))
    a.width_slider = ctk.CTkSlider(options, from_=1, to=64, number_of_steps=63, variable=a.width, width=135, height=16, progress_color=BLUE)
    a.width_slider.pack(side='left', padx=8)
    a.width_label = ctk.CTkLabel(options, text='5 px', width=46, text_color=INK, font=('Segoe UI', 11))
    a.width_label.pack(side='left', padx=8)
    a.width.trace_add('write', lambda *_: a.width_label.configure(text=f'{a.width.get()} px'))
    ctk.CTkLabel(options, text='Shift: forma regular     •     Espaço + arrastar: mover a tela', text_color=MUTED, font=('Segoe UI', 11)).pack(side='right', padx=20)
    a.canvas = tk.Canvas(workspace, bg='#e5ebf3', highlightthickness=0, cursor='crosshair')
    a.canvas.grid(row=1, column=0, sticky='nsew')
    a.hscroll = ctk.CTkScrollbar(workspace, orientation='horizontal', command=lambda *args: a.scroll('x', *args), height=12, fg_color='#e5ebf3', button_color='#b9c6d8')
    a.vscroll = ctk.CTkScrollbar(workspace, command=lambda *args: a.scroll('y', *args), width=12, fg_color='#e5ebf3', button_color='#b9c6d8')
    a.hscroll.grid(row=2, column=0, sticky='ew')
    a.vscroll.grid(row=1, column=1, sticky='ns')
    a.canvas.configure(xscrollcommand=a.hscroll.set, yscrollcommand=a.vscroll.set)
    a.canvas.bind('<Configure>', lambda _e: a._render())
    for num in [1, 3]:
        a.canvas.bind(f'<ButtonPress-{num}>', a.pointer_down)
        a.canvas.bind(f'<B{num}-Motion>', a.pointer_move)
        a.canvas.bind(f'<ButtonRelease-{num}>', a.pointer_up)
    a.canvas.bind('<Motion>', a.pointer_hover)
    a.canvas.bind('<Double-Button-1>', lambda _e: a.finish_polygon())
    a.canvas.bind('<MouseWheel>', a.mouse_wheel)
    a.canvas.bind('<Button-4>', lambda e: a.mouse_wheel(type('Wheel', (), {'delta': 120, 'state': e.state, 'x': e.x, 'y': e.y})()))
    a.canvas.bind('<Button-5>', lambda e: a.mouse_wheel(type('Wheel', (), {'delta': -120, 'state': e.state, 'x': e.x, 'y': e.y})()))
    a.footer = ctk.CTkFrame(a, height=34, fg_color=SURFACE, corner_radius=0)
    a.footer.grid(row=4, column=0, sticky='ew')
    a.status = ctk.CTkLabel(a.footer, text='', font=('Segoe UI', 11), text_color=MUTED, height=32)
    a.status.pack(side='left', padx=20)
    a.position_label = ctk.CTkLabel(a.footer, text='', font=('Segoe UI', 10), text_color=MUTED, width=100)
    a.position_label.pack(side='left', padx=12)
    a.zoom_label = ctk.CTkLabel(a.footer, text='100%', font=('Segoe UI', 11), text_color=INK, width=52)
    a.zoom_slider = ctk.CTkSlider(a.footer, from_=10, to=800, width=135, command=lambda v: a.set_zoom(float(v)/100), progress_color=BLUE)
    action(a.footer, '+', lambda: a.change_zoom(.25), width=28, height=26).pack(side='right', padx=(0, 12))
    a.zoom_slider.pack(side='right', padx=8)
    action(a.footer, '−', lambda: a.change_zoom(-.25), width=28, height=26).pack(side='right')
    a.zoom_label.pack(side='right', padx=4)
    a.show_tab('home')
    a.tool_buttons['brush'].configure(fg_color='#e8f0ff', text_color=BLUE)
