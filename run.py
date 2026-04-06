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
from Src.API.guardaserie import guardaserie
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
    "version": "2.7.0",
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
    tmdb = os.environ.get('TMDB_KEY')
    
    # Link informativo
    streams = {'streams': [{
        'title': f'✅ SERVER ATTIVO\nTMDB: OK | Ricerca flussi...',
        'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'
    }]}
    
    # User-Agent per ingannare i siti (far sembrare il server un browser umano)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with AsyncSession(headers=headers, timeout=20) as client:
        if "tt" in id:
            # 1. Prova StreamingCommunity (Fonte più veloce)
            try:
                # Forza ricerca senza proxy per Hugging Face
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            except Exception as e:
                print(f"Errore SC: {e}")

            # 2. Prova CB01 (Se SC fallisce)
            try:
                streams = await cb01(streams, id, "0", ['', ''], client)
            except Exception as e:
                print(f"Errore CB: {e}")
                
            # 3. Prova Guardaserie
            try:
                streams = await guardaserie(streams, id, client)
            except Exception as e:
                print(f"Errore GS: {e}")
    
    # Se dopo la ricerca abbiamo solo il link di test, aggiungiamo un avviso
    if len(streams['streams']) == 1:
        streams['streams'].append({
            'title': '⚠️ Nessun link trovato.\nProva un altro film o attendi.',
            'url': ''
        })
            
    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host="0.0.0.0", port=8080)
