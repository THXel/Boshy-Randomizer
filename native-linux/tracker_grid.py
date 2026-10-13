"""Wrapping, size-aware icon grid with hover labels and queued reward emphasis."""
from ui_i18n import tr, display, font_path, font_family, configure_tk, LANGUAGE, Localized
import math, tkinter as tk
from pathlib import Path
from PIL import Image,ImageTk,ImageEnhance,ImageOps

def layout(rows,width,height):
    groups=[]
    for row in rows:
        group=row.get('group','')
        if not groups or groups[-1][0]!=group:groups.append((group,[]))
        groups[-1][1].append(row)
    def arrange(size):
        cols=max(1,width//size);y=0;cells=[];headers=[]
        for group,entries in groups:
            if group:
                headers.append((y,group,sum(bool(r.get('done')) for r in entries),len(entries)));y+=20
            for i,row in enumerate(entries):cells.append(((i%cols)*size+(width-cols*size)//2,y+(i//cols)*size,row))
            y+=math.ceil(len(entries)/cols)*size
        return cells,headers,y
    size=48
    while size>24 and arrange(size)[2]>height:size-=2
    cells,headers,content=arrange(size)
    return size,cells,headers,content

class IconGrid(tk.Canvas):
    def __init__(self,parent,base):
        super().__init__(parent,bg='#14161a',highlightthickness=0)
        self.base=Path(base);self.rows=[];self.cache={};self.photos=[];self.cells={};self.tip=None;self.hover=None;self.flash=None;self.phase=0;self.generation=0
        self.bind('<Configure>',lambda e:self.draw());self.bind('<Motion>',self.motion);self.bind('<Leave>',lambda e:self.hide_tip())
        self.bind('<Button-4>',lambda e:self.yview_scroll(-1,'units'));self.bind('<Button-5>',lambda e:self.yview_scroll(1,'units'))
        self.icons={p.stem.casefold():p for p in (self.base/'Custom/trophies').glob('*.png')}
    def set_rows(self,rows):self.rows=list(rows);self.draw()
    def draw(self):
        self.delete('all');self.photos=[];self.cells={};width=max(1,self.winfo_width());height=max(1,self.winfo_height());n=len(self.rows)
        size,cells,headers,content=layout(self.rows,width,height)
        self.configure(scrollregion=(0,0,width,max(height,content)))
        if content<=height:self.yview_moveto(0)
        for y,label,done,total in headers:
            self.create_text(5,y+10,text=display(label),anchor='w',fill='#c6d7e5',font=(font_family(),9,'bold'))
            self.create_text(width-6,y+10,text=f'{done}/{total}',anchor='e',fill='#98abba',font=(font_family(),9))
        for i,(x,y,row) in enumerate(cells):
            name=row['name'];done=bool(row.get('done'));tag='cell'+str(i)
            flashing=(row.get('kind'),name)==self.flash or name==self.flash;edge='#ffda68' if flashing and self.phase%2==0 else '#4bb785' if done else '#343c47';bg='#645327' if flashing and self.phase%2==0 else '#19372d' if done else '#1a2029'
            self.create_rectangle(x+2,y+2,x+size-2,y+size-2,fill=bg,outline=edge,width=3 if flashing else 1,tags=tag)
            key=(name,size,done)
            if key not in self.cache:
                p=self.icons.get(name.casefold(),self.base/'Custom/trophies/trophy.png')
                if not p.exists():p=next(iter(self.icons.values()))
                im=Image.open(p).convert('RGBA');im.thumbnail((size-12,size-12),Image.Resampling.NEAREST)
                if not done:
                    alpha=im.getchannel('A');im=ImageOps.grayscale(im).convert('RGBA');im.putalpha(alpha);im=ImageEnhance.Brightness(im).enhance(.65)
                self.cache[key]=ImageTk.PhotoImage(im,master=self)
            photo=self.cache[key];self.photos.append(photo);self.create_image(x+size/2,y+size/2,image=photo,tags=tag)
            if done:self.create_text(x+size-7,y+8,text='✓',fill='#91ffc5',font=(font_family(),9,'bold'),tags=tag)
            if row.get('goal'):self.create_text(x+7,y+8,text='◆',fill='#ffda68',font=(font_family(),8),tags=tag)
            self.cells[tag]=row
        if not n:self.create_text(width/2,35,text=tr('Kein aktiver Lauf'),fill='#9aa0a6')
    def motion(self,event):
        tags=self.gettags('current');key=next((t for t in tags if t in self.cells),None)
        if key==self.hover:return
        self.hide_tip();self.hover=key
        if not key:return
        row=self.cells[key];self.tip=tk.Toplevel(self);self.tip.withdraw();self.tip.overrideredirect(True);self.tip.attributes('-topmost',True)
        tk.Label(self.tip,text=row['name']+(tr(' · Ziel') if row.get('goal') else '')+' · '+(tr('Vorhanden') if row.get('done') else tr('Noch offen')),bg='#303843',fg='white',padx=7,pady=4,font=(font_family(),10)).pack()
        self.tip.geometry(f'+{event.x_root+12}+{event.y_root+18}');self.tip.deiconify()
    def hide_tip(self):
        if self.tip:self.tip.destroy();self.tip=None
        self.hover=None
    def cancel(self):self.generation+=1;self.flash=None;self.draw()
    def animate(self,name,finished):
        self.generation+=1;generation=self.generation;self.flash=name;self.phase=0
        size,cells,headers,content=layout(self.rows,max(1,self.winfo_width()),max(1,self.winfo_height()))
        for x,y,row in cells:
            if (row.get('kind'),row['name'])==name or row['name']==name:
                if content>self.winfo_height():self.yview_moveto(max(0,(y-self.winfo_height()/2)/content))
                break
        def step():
            if generation!=self.generation or not self.winfo_exists():return
            if self.phase>=14:self.flash=None;self.draw();finished();return
            self.draw();self.phase+=1;self.after(max(25,int(getattr(self,'animation_ms',1540)/14)),step)
        # The notebook is selected by the caller before the first animation frame.
        self.after(150,step)
