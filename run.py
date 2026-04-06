from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
from curl_cffi.requests import AsyncSession

# Import minimi per stabilità
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
from Src.API.cb01 import cb01
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
    "version": "2.2.0",
    "name": "MammaMia Finale",
    "description": "Streaming IT - Server Personale",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream", "catalog"],
    "types": ["movie", "series"],
    "id_prefixes": ["tt"],
    "catalogs": [],
    "behaviorHints": {"configurable": True, "configurationRequired": False}
}

def respond_with(data):
    resp = JSONResponse(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

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
    # Link di test per verificare che l'addon funzioni
    streams = {'streams': [{
        'title': '🚀 MAMMA MIA ONLINE\nServer di Cappe77',
        'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    }]}
    
    async with AsyncSession() as client:
        if "tt" in id:
            # Proviamo a cercare su StreamingCommunity
            try:
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                print(f"Errore ricerca: {e}")
    
    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
