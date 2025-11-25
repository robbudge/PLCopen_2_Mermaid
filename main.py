import tkinter as tk
from gui import CodesysToMermaidGUI

def main():
    root = tk.Tk()
    app = CodesysToMermaidGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()