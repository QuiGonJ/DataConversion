import getpass
import tkinter as tk
from tkinter import filedialog
# Here, we are creating our class, Window, and inheriting from the Frame
# class. Frame is a class from the tkinter module. (see Lib/tkinter/__init__)

#
# TODO: Add target directory and list, execution log.
#

class Window(tk.Frame):

    # Define settings upon initialization. Here you can specify
    def __init__(self, master=None):
        # parameters that you want to send through the Frame class.
        tk.Frame.__init__(self, master)

        # reference to the master widget, which is the tk window
        self.master = master

        # with that, we want to then run init_window, which doesn't yet exist
        self.init_window()

    # Creation of init_window
    def init_window(self):
        self.user = getpass.getuser()
        # changing the title of our master widget
        self.master.title("Convert to Cougar Mountain")

        # allowing the widget to take the full space of the root window
        self.pack(fill=tk.BOTH, expand=1)

        # creating a menu instance
        menu = tk.Menu(self.master)
        self.master.config(menu=menu)

        # create the file object)
        file = tk.Menu(menu)

        # adds a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        file.add_command(label="Select", command=self.client_exit)
        file.add_command(label="Convert", command=self.client_convert)
        file.add_command(label="Test1", command=self.client_test1)
        file.add_command(label="Test2", command=self.client_test2)
        file.add_command(label="Exit", command=self.client_select)

        # added "file" to our menu
        menu.add_cascade(label="File", menu=file)

        # create the file object)
        edit = tk.Menu(menu)

        # adds a command to the menu option, calling it exit, and the
        # command it runs on event is client_exit
        edit.add_command(label="Undo")

        # added "file" to our menu
        menu.add_cascade(label="Edit", menu=edit)

    def client_exit(self):
        exit()

    def client_select(self):
        exit()

    def client_convert(self):
        exit()

    def client_test1(self):
        # tk.Label(self, text='Hello World!', anchor="w", ).pack(side="top", anchor="w")
        # text = tk.Label(self, text="Hey there good lookin!", anchor="e",).pack()
        S = tk.Scrollbar(root)
        T = tk.Text(root, height=40, width=60)
        S.pack(side=tk.RIGHT, fill=tk.Y)
        T.pack(side=tk.LEFT, fill=tk.Y)
        S.config(command=T.yview)
        T.config(yscrollcommand=S.set)
        quote = """HAMLET: To be, or not to be--that is the question:
        Whether 'tis nobler in the mind to suffer
        The slings and arrows of outrageous fortune
        Or to take arms against a sea of troubles
        And by opposing end them. To die, to sleep--
        No more--and by a sleep to say we end
        The heartache, and the thousand natural shocks
        That flesh is heir to. 'Tis a consummation
        Devoutly to be wished."""
        T.insert(tk.END, quote)

    def client_test2(self):
        text = tk.Label(self, text="Hey there evil lookin!", anchor=tk.E, justify=tk.LEFT).pack(side="top", anchor="w")

# root window created. Here, that would be the only window, but
# you can later have windows within windows.
root = tk.Tk()

root.geometry("500x400")

# creation of an instance
app = Window(root)

# mainloop
root.mainloop()