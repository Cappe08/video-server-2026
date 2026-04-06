from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
from curl_cffi.requests import AsyncSession

# Import dai tuoi file
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
from Src.API.cb01 import cb01
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
    "version": "2.6.0",
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
def config_page(request: Request):
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
    # Controllo chiave TMDB nei log
    tmdb = os.environ.get('TMDB_KEY')
    if not tmdb:
        print("⚠️ ERRORE: Chiave TMDB_KEY non trovata nei Secrets!")
    else:
        print(f"✅ TMDB_KEY caricata correttamente: {tmdb[:5]}***")

    streams = {'streams': [{
        'title': f'✅ SERVER ATTIVO\nTMDB: {"OK" if tmdb else "MANCANTE"}',
        'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    }]}
    
    async with AsyncSession() as client:
        if "tt" in id:
            print(f"🔍 Ricerca film ID: {id}...")
            try:
                # Prova StreamingCommunity
                streams = await streaming_community(streams, id, client, "0", ['', ''])
                print(f"📊 Risultati correnti: {len(streams['streams'])} link")
            except Exception as e:
                print(f"❌ Errore ricerca SC: {e}")
            
            try:
                # Prova CB01
                streams = await cb01(streams, id, "0", ['', ''], client)
                print(f"📊 Risultati totali: {len(streams['streams'])} link")
            except Exception as e:
                print(f"❌ Errore ricerca CB: {e}")
    
    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
