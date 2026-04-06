from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
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
    "version": "3.1.0",
    "name": "MammaMia Finale",
    "description": "Server Personale di Cappe77",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "id_prefixes": ["tt"]
}

# Lista di identità per ingannare i blocchi
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

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
    
    # Messaggio di debug che vedrai su Stremio
    debug_msg = "🔍 Ricerca avviata..."
    
    async with AsyncSession(
        headers={"User-Agent": random.choice(USER_AGENTS)},
        timeout=25,
        impersonate="chrome110" # Simula perfettamente Chrome
    ) as client:
        if "tt" in id:
            try:
                # Prova StreamingCommunity
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                debug_msg = f"❌ Errore: {str(e)[:20]}"

    if not streams['streams']:
        streams['streams'].append({
            'title': f'⚠️ Nessun link trovato\n{debug_msg}',
            'url': 'https://vjs.zencdn.net/v/oceans.mp4'
        })
            
    return JSONResponse(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
    
