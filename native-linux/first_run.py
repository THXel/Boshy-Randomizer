"""First launch: user supplies a game folder or ZIP. No game download is performed."""
from pathlib import Path
import queue,threading,tkinter as tk
from tkinter import ttk,filedialog
from ui_i18n import tr,configure_tk,font_family
from game_import import import_game

class Setup:
 def __init__(self,base):
  self.base=Path(base);self.result=False;self.busy=False;self.events=queue.Queue()
  self.root=tk.Tk();configure_tk(self.root);self.root.title('Boshy Randomizer');self.root.geometry('660x440');self.root.minsize(600,420)
  self.root.configure(bg='#101820');style=ttk.Style();style.theme_use('clam');style.configure('Setup.TFrame',background='#101820');style.configure('Setup.TLabel',background='#101820',foreground='#e7edf3',font=(font_family(),11));style.configure('Setup.TButton',font=(font_family(),11),padding=10)
  frame=ttk.Frame(self.root,style='Setup.TFrame',padding=24);frame.pack(fill='both',expand=True)
  ttk.Label(frame,text=tr('Welcome to Boshy Randomizer'),style='Setup.TLabel',font=(font_family(),19,'bold')).pack(anchor='w',pady=(0,18))
  ttk.Label(frame,text=tr('The game is not included. Choose your Boshy folder or the original game ZIP.'),style='Setup.TLabel',wraplength=600).pack(anchor='w',pady=(0,14))
  ttk.Label(frame,text=tr('We create a separate game copy. Your original folder and saves stay unchanged.'),style='Setup.TLabel',wraplength=600).pack(anchor='w',pady=(0,20))
  row=ttk.Frame(frame,style='Setup.TFrame');row.pack(fill='x');self.buttons=[]
  for label,action in [('Choose game folder',self.folder),('Choose game ZIP',self.zip)]:
   button=ttk.Button(row,text=tr(label),command=action,style='Setup.TButton');button.pack(side='left',expand=True,fill='x',padx=4);self.buttons.append(button)
  self.status=tk.StringVar(value=tr('Your randomizer saves will be stored separately.'))
  ttk.Label(frame,textvariable=self.status,style='Setup.TLabel',wraplength=600).pack(anchor='w',pady=20)
  self.bar=ttk.Progressbar(frame,mode='indeterminate');self.bar.pack(fill='x')
  self.root.protocol('WM_DELETE_WINDOW',self.close);self.root.after(100,self.poll)
 def folder(self):
  path=filedialog.askdirectory(parent=self.root,title=tr('Choose game folder'))
  if path:self.start(path)
 def zip(self):
  path=filedialog.askopenfilename(parent=self.root,title=tr('Choose game ZIP'),filetypes=[('ZIP','*.zip'),('All files','*')])
  if path:self.start(path)
 def start(self,path):
  if self.busy:return
  self.busy=True;self.bar.start(15);self.status.set(tr('Checking and copying the game…'))
  for button in self.buttons:button.configure(state='disabled')
  def work():
   try:import_game(path,self.base);self.events.put((True,''))
   except Exception as e:self.events.put((False,str(e)))
  threading.Thread(target=work,daemon=True).start()
 def poll(self):
  try:
   ok,error=self.events.get_nowait();self.busy=False;self.bar.stop()
   if ok:self.result=True;self.root.destroy();return
   self.status.set(tr(error))
   for button in self.buttons:button.configure(state='normal')
  except queue.Empty:pass
  self.root.after(100,self.poll)
 def close(self):
  if not self.busy:self.root.destroy()
 def run(self):self.root.mainloop();return self.result


def prepare_environment(base):
 """Keep setup visible while downloading the pinned runner and creating the prefix."""
 from wine_setup import prepare_wine
 from tkinter import messagebox
 root=tk.Tk();configure_tk(root);root.title('Boshy Randomizer');root.geometry('620x170');root.resizable(False,False)
 status=tk.StringVar(value=tr('Checking Wine Staging 11.2…'));events=queue.Queue();result=[]
 ttk.Label(root,textvariable=status,wraplength=580,font=(font_family(),12)).pack(padx=20,pady=24)
 bar=ttk.Progressbar(root,mode='indeterminate');bar.pack(fill='x',padx=20);bar.start(15)
 root.protocol('WM_DELETE_WINDOW',lambda:None)
 def work():
  try:prepare_wine(Path(base),lambda text:events.put(('status',text)));events.put(('done',None))
  except Exception as e:events.put(('error',str(e)))
 def poll():
  try:
   while True:
    event,value=events.get_nowait()
    if event=='status':status.set(tr(value))
    else:
     if event=='error':messagebox.showerror('Boshy Randomizer',tr(value),parent=root)
     result.append(event=='done');root.destroy();return
  except queue.Empty:pass
  root.after(100,poll)
 threading.Thread(target=work,daemon=True).start();root.after(100,poll);root.mainloop()
 return bool(result and result[0])
