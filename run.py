from fastapi import FastAPI, HTTPException, Request, Form, Cookie
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from fastapi.templating import Jinja2Templates
import logging
import base64
from curl_cffi.requests import AsyncSession

# Import locali
from static.static import HTML
from static.configure import CONFIGURE
from Src.API.streamingcommunity import streaming_community
from Src.API.cb01 import cb01
from Src.API.guardaserie import guardaserie
from Src.API.guardahd import guardahd
from Src.API.animeworld import animeworld
from Src.API.guardaflix import guardaflix
from Src.API.guardoserie import guardoserie
from Src.API.eurostreaming import eurostreaming
from Src.API.toonitalia import toonitalia
from Src.API.realtime import search_catalog as realtime
from Src.API.realtime import meta_catalog as meta_catalog_realtime
from Src.API.realtime import realtime as streams_realtime
from Src.Utilities.dictionaries import STREAM, extra_sources, provider_map
from Src.Utilities.update_config import update_all_sites
from Src.API.epg import tivu, tivu_get, epg_guide, convert_bho_1, convert_bho_2, convert_bho_3
from Src.API.extractors.uprot import get_uprot_numbers, generate_uprot_txt
import Src.Utilities.config as config
from Src.Utilities.config import setup_logging
from Src.Utilities.loadenv import load_env

# Inizializzazione
level = config.LEVEL
logger = setup_logging(level)
env_vars = load_env()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
static = Jinja2Templates(directory="static")

# Config Proxy
Global_Proxy = config.Global_Proxy
proxies = {"http": env_vars.get('PROXY_CREDENTIALS'), "https": env_vars.get('PROXY_CREDENTIALS')} if Global_Proxy == "1" else {}

# Config Generale
SC, AW, CB, GS, GHD, ES, GF, GO, RT, TI = config.SC, config.AW, config.CB, config.GS, config.GHD, config.ES, config.GF, config.GO, config.RT, config.TI
HOST, PORT = config.HOST, int(env_vars.get('PORT_ENV')) if env_vars.get('PORT_ENV') else int(config.PORT)
Icon, Name = config.Icon, config.Name

MANIFEST = {
    "id": "org.stremio.mammamia.personale",
    "version": "2.1.2",
    "name": Name,
    "description": "Addon MammaMia Personale - Streaming IT",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream", "catalog"], # Tolto "meta" per evitare il 404
    "types": ["movie", "series", "tv"],
    "id_prefixes": ["tt", "tmdb", "kitsu", "tv"],
    "catalogs": [
        {"type": "tv", "id": "tv_channels", "name": "MammaMia TV"},
        {"id": "realtime", "type": "series", "name": "MammaMia Realtime", "extra": [{"name": "search", "isRequired": True}]}
    ],
    "behaviorHints": {"configurable": True, "configurationRequired": False}
}

def respond_with(data):
    resp = JSONResponse(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.get('/configure', response_class=HTMLResponse)
def config_page(request: Request):
    instance_url = f"{request.url.scheme}://{request.url.netloc}"
    return CONFIGURE.replace("{instance_url}", instance_url)

@app.get('/{config:path}/manifest.json')
def addon_manifest(config: str):
    return respond_with(MANIFEST)

@app.get('/manifest.json')
def manifest_default():
    return RedirectResponse(url="/|SC|LC|/manifest.json")

@app.get('/', response_class=HTMLResponse)
def root(request: Request):
    instance_url = f"{request.url.scheme}://{request.url.netloc}"
    return HTML.replace("{instance_url}", instance_url)

@app.get('/{config:path}/catalog/{type}/{id}.json')
async def first_catalog(type: str, id: str, genre: str = None):
    if type != "tv": return respond_with({"metas": []})
    metas = []
    for ch in STREAM["channels"]:
        if genre and genre not in ch.get("genres", []): continue
        metas.append({"id": ch["id"], "type": "tv", "name": ch["title"], "poster": ch["poster"]})
    return respond_with({"metas": metas})

@app.get('/{config:path}/stream/{type}/{id}.json')
async def addon_stream(config_str: str, type: str, id: str):
    streams = {'streams': []}
    try:
        decoded = base64.b64decode(config_str.replace("%3D", "=")).decode('utf-8')
    except:
        decoded = "|SC|CB|GS|GHD|ES|GF|GO|RT|TI|"

    provider_maps = {name: ("1" if name in decoded or "ALL" in decoded else "0") for name in provider_map.values()}
    
    async with AsyncSession(proxies=proxies) as client:
        if type == "tv":
            for ch in STREAM["channels"]:
                if ch["id"] == id and 'url' in ch:
                    streams['streams'].append({'title': f"{Icon} Link TV", 'url': ch['url']})
        elif "tt" in id or "tmdb" in id:
            if provider_maps.get('STREAMINGCOMMUNITY') == "1":
                streams = await streaming_community(streams, id, client, "0", ['', ''])
            if provider_maps.get('CB01') == "1":
                streams = await cb01(streams, id, "0", ['', ''], client)
    
    return respond_with(streams) # Mai più 404, restituisce lista vuota se non trova nulla

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host=HOST, port=PORT, log_level=level)
