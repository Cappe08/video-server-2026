from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64, os, random, asyncio
from curl_cffi.requests import AsyncSession

from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
from Src.API.cb01 import cb01
from Src.API.guardaserie import guardaserie
import Src.Utilities.config as config

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MANIFEST = {
    "id": "org.stremio.mammamia.cappe77",
    "version": "6.0.0",
    "name": "MammaMia Finale",
    "description": "Server Render di Cappe77",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "id_prefixes": ["tt"]
}

@app.get('/configure', response_class=HTMLResponse)
def config_page(request: Request):
    return CONFIGURE.replace("{instance_url}", f"{request.url.scheme}://{request.url.netloc}")

@app.get('/manifest.json')
@app.get('/{config_str}/manifest.json')
def addon_manifest(config_str: str = None):
    return JSONResponse(MANIFEST)

@app.get('/')
def root(): return RedirectResponse(url="/configure")

@app.get('/{config_str}/stream/{type}/{id}.json')
async def addon_stream(config_str: str, type: str, id: str):
    streams = {'streams': []}
    
    # Headers ultra-reali per bypassare Cloudflare
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }

    async with AsyncSession(impersonate="chrome120", headers=headers, timeout=30) as client:
        if "tt" in id:
            # Task 1: StreamingCommunity
            try:
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except: pass
            
            # Task 2: Guardaserie (Molto meno protetto di SC)
            try:
                streams = await guardaserie(streams, id, client)
            except: pass

            # Task 3: CB01
            try:
                streams = await cb01(streams, id, "0", ['', ''], client)
            except: pass

    # Se dopo tutto questo non c'è nulla, diamo un messaggio di errore dinamico
    if not streams['streams']:
        streams['streams'].append({
            'title': f'❌ Nessun link trovato (TMDB: OK)\nProva un film diverso (es: Inside Out 2)',
            'url': 'https://vjs.zencdn.net/v/oceans.mp4'
        })
            
    return JSONResponse(streams)

if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("run:app", host="0.0.0.0", port=port)
