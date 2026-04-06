from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
from curl_cffi.requests import AsyncSession

# Import minimi
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
import Src.Utilities.config as config
from Src.Utilities.loadenv import load_env

env_vars = load_env()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "org.stremio.mammamia.cappe77",
    "version": "2.8.0",
    "name": "MammaMia Finale",
    "description": "Server Personale di Cappe77",
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
def root():
    return RedirectResponse(url="/configure")

@app.get('/{config_str}/stream/{type}/{id}.json')
async def addon_stream(config_str: str, type: str, id: str):
    # Iniziamo con una lista vuota
    streams = {'streams': []}
    
    # Questo link serve solo a farti capire che il server sta lavorando
    streams['streams'].append({
        'title': '🍕 RICERCA IN CORSO...\nAttendi qualche secondo',
        'url': 'https://vjs.zencdn.net/v/oceans.mp4'
    })
    
    async with AsyncSession(timeout=30) as client:
        if "tt" in id:
            try:
                # Proviamo SOLO StreamingCommunity che è il più stabile
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                print(f"Errore ricerca: {e}")
    
    # Se ha trovato qualcosa, togliamo il messaggio di attesa
    if len(streams['streams']) > 1:
        streams['streams'].pop(0)
            
    return JSONResponse(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
