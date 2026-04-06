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
    "version": "3.0.0",
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
    streams = {'streams': []}
    
    # Proviamo a cercare
    async with AsyncSession(timeout=30) as client:
        if "tt" in id:
            try:
                # Cerchiamo su StreamingCommunity
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                print(f"Errore ricerca: {e}")
    
    # Se la ricerca è vuota, aggiungiamo un messaggio chiaro
    if not streams['streams']:
        streams['streams'].append({
            'title': '❌ Nessun link trovato su StreamingCommunity',
            'url': 'https://vjs.zencdn.net/v/oceans.mp4' # Video di errore
        })
    else:
        # Se ha trovato link reali, assicuriamoci che siano in cima
        print(f"Trovati {len(streams['streams'])} link!")
            
    return JSONResponse(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
