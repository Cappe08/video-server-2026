from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
import random
from curl_cffi.requests import AsyncSession

# Import minimi
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
import Src.Utilities.config as config

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "org.stremio.mammamia.cappe77",
    "version": "4.0.0",
    "name": "MammaMia Finale",
    "description": "Server Render di Cappe77",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "id_prefixes": ["tt"]
}

@app.get('/configure', response_class=HTMLResponse)
@app.get('/{config_str}/configure', response_class=HTMLResponse)
def config_page(request: Request, config_str: str = None):
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
    
    # Check TMDB Key
    tmdb_key = os.environ.get('TMDB_KEY')
    tmdb_status = "OK" if tmdb_key else "MANCANTE (Controlla Environment su Render!)"
    
    async with AsyncSession(impersonate="chrome110", timeout=25) as client:
        if "tt" in id:
            try:
                # Tentativo di ricerca
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                # Scrive l'errore nel titolo del link su Stremio
                error_msg = str(e)[:30]
                streams['streams'].append({
                    'title': f'❌ Errore ricerca: {error_msg}\nSito bloccato o down.',
                    'url': 'https://vjs.zencdn.net/v/oceans.mp4'
                })

    if not streams['streams'] or (len(streams['streams']) == 1 and "Errore" not in streams['streams'][0]['title']):
        streams['streams'].append({
            'title': f'⚠️ Nessun link trovato.\nChiave TMDB: {tmdb_status}',
            'url': 'https://vjs.zencdn.net/v/oceans.mp4'
        })
            
    return JSONResponse(streams)

if __name__ == '__main__':
    import uvicorn
    # Render assegna la porta automaticamente tramite la variabile PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("run:app", host="0.0.0.0", port=port)
