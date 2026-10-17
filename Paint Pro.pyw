"""Windows double-click launcher (uses pythonw, without a terminal window)."""
if __name__ == '__main__':
    try:
        from classic import PaintPro
    except ImportError as error:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Paint Pro', 'Falta uma dependência para abrir o editor.\n\nConsulte a seção Instalar e abrir do README.\n\nDetalhes: ' + str(error))
        root.destroy()
    else:
        PaintPro().mainloop()
