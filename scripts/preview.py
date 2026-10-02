#!/usr/bin/env python3
"""Native frontend preview: shared C catalog, UI model and pixel renderer."""
import argparse
import ctypes as C
import io
import json
import os
import struct
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
class Game(C.Structure):
    _fields_=[('key',C.c_char*1024),('title',C.c_char*256),('title_id',C.c_char*20),('version',C.c_char*20),('root',C.c_char*1024),('eboot',C.c_char*1024),('cover',C.c_char*1024),('fingerprint',C.c_uint64),('metadata_ok',C.c_uint),('files_ok',C.c_uint)]
class Catalog(C.Structure):
    _fields_=[('games',Game*1024),('count',C.c_uint),('mounts',C.c_uint),('warnings',C.c_uint),('limited',C.c_uint),('generation',C.c_uint64)]
class Ui(C.Structure):
    _fields_=[('selected',C.c_char*1024),('fingerprint',C.c_uint64),('initialized',C.c_uint),('present',C.c_uint),('page',C.c_uint)]
class Intent(C.Structure):
    _fields_=[('key',C.c_char*1024),('fingerprint',C.c_uint64),('valid',C.c_uint)]

def load():
    build=ROOT/'build';build.mkdir(exist_ok=True)
    libpath=build/'libfrontend.so'
    sources=[ROOT/'src'/name for name in ('catalog.c','fs.c','decode_budget.c','ui_model.c','input.c','ui_render.c')]
    dependencies=[*sources,*ROOT.glob('include/*.h'),ROOT/'third_party/stb/stb_image.h']
    if not libpath.exists() or any(p.stat().st_mtime>libpath.stat().st_mtime for p in dependencies):
        subprocess.run([os.environ.get('CC','cc'),'-std=c11','-D_POSIX_C_SOURCE=200809L','-D_XOPEN_SOURCE=700','-O2','-fPIC','-shared','-I',str(ROOT/'include'),*[str(p) for p in sources],'-o',str(libpath),'-lm'],check=True)
    lib=C.CDLL(str(libpath))
    lib.zd_catalog_scan.argtypes=[C.POINTER(Catalog),C.POINTER(C.c_char_p),C.c_size_t]
    lib.zd_ui_refresh.argtypes=[C.POINTER(Ui),C.POINTER(Catalog)]
    lib.zd_ui_move.argtypes=[C.POINTER(Ui),C.POINTER(Catalog),C.c_int]
    lib.zd_ui_pick.argtypes=[C.POINTER(Ui),C.POINTER(Catalog),C.c_float,C.c_float]
    lib.zd_ui_capture.argtypes=[C.POINTER(Ui),C.POINTER(Catalog)];lib.zd_ui_capture.restype=Intent
    lib.zd_ui_validate.argtypes=[C.POINTER(Intent),C.POINTER(Catalog)]
    lib.zd_game_revalidate.argtypes=[C.POINTER(Game)]
    lib.zd_render_init.argtypes=[C.c_char_p]
    lib.zd_render.argtypes=[C.POINTER(C.c_uint32),C.c_uint,C.c_uint,C.POINTER(Ui),C.POINTER(Catalog),C.c_int,C.c_int,C.c_char_p]
    if not lib.zd_render_init(os.fsencode(ROOT/'assets/font.zdf')): raise RuntimeError('Font asset unavailable')
    return lib

def sfo(title,identity):
    keys=bytearray();data=bytearray();entries=[]
    for key,value in [('TITLE',title),('TITLE_ID',identity),('APP_VER",'01.00')]:
        value=value.encode()+b'\0';entries.append(struct.pack('<HHIII',len(keys),0x0204,len(value),len(value),len(data)));keys+=key.encode()+b'\0';data+=value
    ko=20+len(entries)*16
    return struct.pack('<4sIIII',b'\0PSF',0x101,ko,ko+len(keys),len(entries))+b''.join(entries)+keys+data

def demo():
    root=ROOT/'build/demo-usb'
    titles=['Nebula','Orbital','Echoes','Circuit','Lumen','Horizon']
    colors=[(47,107,102),(123,75,118),(164,101,59),(39,110,143),(121,65,87),(102,114,56)]
    for i,(title,color) in enumerate(zip(titles,colors)):
        meta=root/'GAMES'/title/'PS3_GAME';(meta/'USRDIR').mkdir(parents=True,exist_ok=True)
        (meta/'PARAM.SFO').write_bytes(sfo(title,'DEMO%04d'%i))
        (meta/'USRDIR/EBOOT.BIN').write_bytes(b'SCE\0DEMO NOT EXECUTABLE')
        im=Image.new('RGB',(640,360));p=im.load()
        for y in range(360):
            for x in range(640):
                f=.32+.52*x/640+.16*(360-y)/360
                p[x,y]=tuple(int(v*f) for v in color)
        d=ImageDraw.Draw(im)
        for ring in range(4):
            off=ring*24
            d.ellipse((210-off,-55-off,560+off,295+off),outline=tuple(min(255,v+75) for v in color),width=2)
        d.line((0,320,520,20),fill=tuple(min(255,v+100) for v in color),width=4)
        d.polygon([(380,125),(520,255),(215,285)],fill=tuple(int(v*.7) for v in color))
        im.save(meta/'ICON0.PNG')
    return [root]

HTML='''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ZER0DAY / Native frontend preview</title><style>html,body{margin:0;background:#080c0f;min-height:100%;color:#acbfb9;font:13px system-ui}body{display:grid;place-items:center}canvas{width:min(100vw,1600px);height:auto;display:block;outline:0}p{margin:10px 20px;text-align:center;opacity:.75}button{border:1px solid #34473f;background:#1b2a25;color:#c2dfd0;padding:8px 14px;margin:4px;border-radius:8px;cursor:pointer}</style><main><canvas width="1280" height="720" tabindex="0" aria-label="Libreria PS3: usa frecce, Invio, R e PageUp o PageDown"></canvas><p>Anteprima del frontend nativo. Frecce: selezione · Invio: dettagli · R: scansione · PageUp/PageDown: pagine</p><p><button data-move="6">Pagina precedente</button><button data-move="5">Pagina successiva</button><button id="scan">Aggiorna USB</button></p></main><script>const c=document.querySelector('canvas'),ctx=c.getContext('2d');let fetching=false;async function draw(){if(fetching)return;fetching=true;try{const r=await fetch('/frame.png',{cache:'no-store'});const b=await createImageBitmap(await r.blob());ctx.drawImage(b,0,0);b.close()}finally{fetching=false}}async function action(a){await fetch('/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)});await draw()}c.onclick=e=>{let b=c.getBoundingClientRect();action({pick:[(e.clientX-b.left)*1280/b.width,(e.clientY-b.top)*720/b.height]});c.focus()};const keys={ArrowLeft:1,ArrowRight:2,ArrowUp:3,ArrowDown:4,PageDown:5,PageUp:6};document.onkeydown=e=>{if(keys[e.key]){e.preventDefault();action({move:keys[e.key]})}else if(e.key==='Enter')action({confirm:true});else if(e.key.toLowerCase()==='r')action({scan:true})};document.querySelectorAll('[data-move]').forEach(b=>b.onclick=()=>action({move:Number(b.dataset.move)}));document.querySelector@ll('#scan').onclick=()=>action({scan:true});let previous=0;function pad(){let p=navigator.getGamepads?.()[0];if(p){let bits=0;p.buttons.forEach((b,i)=>{if(b.pressed)bits|=1<<i});let newly=bits&~previous;previous=bits;const mapping={14:1,15:2,12:3,13:4,5:5,4:6};for(const [i,m]of Object.entries(mapping))if(newly&(1<<i))action({move:m});if(newly&1)action({confirm:true});if(newly&8)action({scan:true})}else previous=0;requestAnimationFrame(pad)}pad();draw();setInterval(draw,1000);</script></html>'''

class Preview:
    def __init__(self,roots,sample,width=1280,height=720):
        self.lib=load();self.ui=Ui();self.catalog=Catalog();self.roots=roots;self.sample=sample;self.width=width;self.height=height;self.lock=threading.RLock();self.notice=b'';self.notice_until=0;self.scanning=False;self.stop=threading.Event();self.request=threading.Event();self.scan()
    def scan(self):
        with self.lock:self.scanning=True
        result=Catalog();roots=(C.c_char_p*len(self.roots))(*(os.fsencode(Path(r).resolve()) for r in self.roots))
        rc=self.lib.zd_catalog_scan(C.byref(result),roots,len(roots))
        with self.lock:
            if rc==0:self.catalog=result;self.lib.zd_ui_refresh(C.byref(self.ui),C.byref(self.catalog))
            self.scanning=False
    def worker(self):
        while not self.stop.is_set():
            self.request.wait(3);self.request.clear()
            if not self.stop.is_set():self.scan()
    def image(self):
        with self.lock:
            pixels=(C.c_uint32*(self.width*self.height))()
            notice=self.notice if time.monotonic()<self.notice_until else b''
            rc=self.lib.zd_render(pixels,self.width,self.height,C.byref(self.ui),C.byref(self.catalog),self.scanning,self.sample,notice)
            if not rc:raise RuntimeError('Native rendering failed')
            return Image.frombytes('RGBA',(self.width,self.height),bytes(pixels))
    def action(self,data):
        with self.lock:
            if 'move' in data and isinstance(data['move'],int) and 1<=data['move']<=6:self.lib.zd_ui_move(C.byref(self.ui),C.byref(self.catalog),data['move'])
            if 'pick' in data and isinstance(data['pick'],list) and len(data['pick'])==2 and all(isinstance(x,(int,float)) and abs(x)<4096 for x in data['pick']):self.lib.zd_ui_pick(C.byref(self.ui),C.byref(self.catalog),*data['pick'])
            if data.get('scan'):self.request.set()
            if data.get('confirm'):
                intent=self.lib.zd_ui_capture(C.byref(self.ui),C.byref(self.catalog))
                valid=self.lib.zd_ui_validate(C.byref(intent),C.byref(self.catalog))
                game=next((self.catalog.games[i] for i in range(self.catalog.count) if self.catalog.games[i].key==intent.key),None)
                valid=valid and game is not None and self.lib.zd_game_revalidate(C.byref(game))
                self.notice=("Avvio non disponibile: core RPCS3 non collegato." if valid else "Il gioco non è più disponibile. Aggiorna la libreria.").encode();self.notice_until=time.monotonic()+5

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--usb',action='append',type=Path,default=[]);parser.add_argument('--demo',action='store_true');parser.add_argument('--screenshot',type=Path);parser.add_argument('--size',default='1280x720');parser.add_argument('--port',type=int,default=8765);parser.add_argument('--open',action='store_true');args=parser.parse_args()
    sample=args.demo or not args.usb;roots=demo() if sample else args.usb;width,height=map(int,args.size.split('x'))
    if width<640 or width>3840 or height<360 or height>2160 or width*9!=height*16:parser.error('Size must be 16:9 between 640x360 and 3840x2160')
    app=Preview(roots,sample,width,height)
    if args.screenshot:
        args.screenshot.parent.mkdir(parents=True,exist_ok=True);app.image().save(args.screenshot);print(args.screenshot);return
    app.width,app.height=1280,720
    thread=threading.Thread(target=app.worker,daemon=True);thread.start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*unused):pass
        def reply(self,status,ctype,body):
            self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path=='/':self.reply(200,'text/html; charset=utf-8',HTML.encode())
            elif self.path=='/frame.png':
                out=io.BytesIO();app.image().save(out,format='PNG');self.reply(200,'image/png',out.getvalue())
            else:self.reply(404,'text/plain',b'Not found')
        def do_POST(self):
            if self.path!='/action':return self.reply(404,'text/plain',b'Not found')
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://127.0.0.1:{args.port}':return self.reply(403,'text/plain',b'Invalid origin')
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>1024:raise ValueError('Request too large')
                data=json.loads(self.rfile.read(n))
                if not isinstance(data,dict):raise ValueError('Object required')
                app.action(data)
            except (ValueError,TypeError):return self.reply(400,'text/plain',b'Invalid action')
            self.reply(200,'application/json',b'{"ok":true}')
    url=f'http://127.0.0.1:{args.port}';print(url,flush=True)
    if args.open:
        import webbrowser;webbrowser.open(url)
    try:
        with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:app.stop.set();app.request.set();thread.join(timeout=5);app.lib.zd_render_shutdown()

if __name__=='__main__':main()
