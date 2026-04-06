from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
from curl_cffi.requests import AsyncSession

# Import dai tuoi file
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
from Src.API.cb01 import cb01
from Src.API.guardaserie import guardaserie
from Src.Utilities.dictionaries import STREAM, provider_map
import Src.Utilities.config as config
from Src.Utilities.loadenv import load_env

env_vars = load_env()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MANIFEST = {
    "id": "org.stremio.mammamia.cappe77",
    "version": "2.5.0",
    "name": "MammaMia Finale",
    "description": "Server Personale di Cappe77",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream"],
    "types": ["movie", "series"],
    "id_prefixes": ["tt"],
    "behaviorHints": {"configurable": True, "configurationRequired": False}
}

def respond_with(data):
    return JSONResponse(data, headers={'Access-Control-Allow-Origin': '*'})

@app.get('/configure', response_class=HTMLResponse)
@app.get('/{config_str}/configure', response_class=HTMLResponse)
def config_page(request: Request, config_str: str = None):
    instance_url = f"{request.url.scheme}://{request.url.netloc}"
    return CONFIGURE.replace("{instance_url}", instance_url)

@app.get('/manifest.json')
@app.get('/{config_str}/manifest.json')
def addon_manifest(config_str: str = None):
    return respond_with(MANIFEST)

@app.get('/')
def root():
    return RedirectResponse(url="/configure")

@app.get('/{config_str}/stream/{type}/{id}.json')
async def addon_stream(config_str: str, type: str, id: str):
    # Link di test (per conferma che il server risponde)
    streams = {'streams': [{
        'title': '✅ SERVER DI CAPPE77 ATTIVO\nRicerca in corso...',
        'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    }]}
    
    async with AsyncSession() as client:
        if "tt" in id:
            # Ricerca su StreamingCommunity
            try:
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except: pass
            
            # Ricerca su CB01
            try:
                streams = await cb01(streams, id, "0", ['', ''], client)
            except: pass
            
            # Ricerca su Guardaserie
            try:
                streams = await guardaserie(streams, id, client)
            except: pass
            
    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
