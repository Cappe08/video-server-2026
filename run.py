from fastapi import FastAPI, HTTPException, Request, Form, Cookie
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from fastapi.templating import Jinja2Templates
import logging
import base64
from urllib.parse import unquote
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

# Inizializzazione Config e Logging
level = config.LEVEL
logger = setup_logging(level)
env_vars = load_env()

# Inizializzazione App e CORS
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

# Configurazione Proxy
Global_Proxy = config.Global_Proxy
if Global_Proxy == "1":
    PROXY_CREDENTIALS = env_vars.get('PROXY_CREDENTIALS')
    proxies = {"http": PROXY_CREDENTIALS, "https": PROXY_CREDENTIALS}
else:
    proxies = {}

# Variabili Globali
SC = config.SC
AW = config.AW
CB = config.CB
GS = config.GS
GHD = config.GHD
ES = config.ES
GF = config.GF
GO = config.GO
RT = config.RT
TI = config.TI
HOST = config.HOST
PORT = int(env_vars.get('PORT_ENV')) if env_vars.get('PORT_ENV') else int(config.PORT)
Icon = config.Icon
Name = config.Name

MANIFEST = {
    "id": "org.stremio.mammamia.personale",
    "version": "2.1.0",
    "name": Name,
    "description": "Addon MammaMia Personale - Streaming IT",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png",
    "resources": ["stream", "catalog", "meta"],
    "types": ["movie", "series", "tv"],
    "id_prefixes": ["tt", "tmdb", "kitsu", "tv", "realtime"],
    "catalogs": [
        {"type": "tv", "id": "tv_channels", "name": "MammaMia TV"},
        {"id": "realtime", "type": "series", "name": "MammaMia Realtime", "extra": [{"name": "search", "isRequired": True}]}
    ],
    "behaviorHints": {"configurable": True, "configurationRequired": False}
}

def respond_with(data):
    resp = JSONResponse(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.get('/configure', response_class=HTMLResponse)
def config_page(request: Request):
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = forwarded_proto if forwarded_proto else request.url.scheme
    instance_url = f"{scheme}://{request.url.netloc}"
    return CONFIGURE.replace("{instance_url}", instance_url)

@app.get('/{config:path}/manifest.json')
def addon_manifest(config: str): 
    manifest_copy = MANIFEST.copy() 
    try:
        decoded_config = base64.b64decode(config).decode('utf-8')
    except:
        decoded_config = ""
    
    if "LIVETV" not in decoded_config:
        manifest_copy['catalogs'] = [c for c in manifest_copy['catalogs'] if c['id'] != 'tv_channels']
    
    if 'RT' not in decoded_config or RT == '0':
        manifest_copy['catalogs'] = [c for c in manifest_copy['catalogs'] if c['id'] != 'realtime']
        
    if not manifest_copy['catalogs']:
        if "catalog" in manifest_copy["resources"]:
            manifest_copy["resources"].remove('catalog')
            
    return respond_with(manifest_copy)

@app.get('/manifest.json')
def manifest_default():
    return RedirectResponse(url="/|SC|LC|/manifest.json")

@app.get('/', response_class=HTMLResponse)
def root(request: Request):
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = forwarded_proto if forwarded_proto else request.url.scheme
    instance_url = f"{scheme}://{request.url.netloc}"
    return HTML.replace("{instance_url}", instance_url)

async def addon_catalog(type: str, id: str, genre: str = None):
    if type != "tv": raise HTTPException(status_code=404)
    catalogs = {"metas": []}
    for channel in STREAM["channels"]:
        if genre and genre not in channel.get("genres", []): continue 
        catalogs["metas"].append({
            "id": channel["id"], "type": "tv", "name": channel["title"],
            "poster": channel["poster"], "description": f'Watch {channel["title"]}',
            "genres": channel.get("genres", [])
        })
    return catalogs

@app.get('/{config:path}/catalog/{type}/{id}.json')
@limiter.limit("5/second")
async def first_catalog(request: Request, type: str, id: str, genre: str = None):
    return respond_with(await addon_catalog(type, id, genre))

@app.get('/{config:path}/catalog/{type}/{id}/search={query}.json')
async def realtime_catalog(type: str, id: str, query: str = None):
    if type != 'series': raise HTTPException(status_code=404)
    catalogs = {"query": query, 'cacheMaxAge': 86400, "metas": []}
    async with AsyncSession(proxies=proxies) as client:
        catalogs = await realtime(query, catalogs, client)
    return respond_with(catalogs)

@app.get('/{config:path}/meta/{type}/{id}.json')
async def addon_meta(type: str, id: str):
    if type == "tv":
        channel = next((ch for ch in STREAM['channels'] if ch['id'] == id), None)
        if not channel: raise HTTPException(status_code=404)
        async with AsyncSession(proxies=proxies) as client:
            if id in convert_bho_1 or id in convert_bho_2 or id in convert_bho_3:
                description, title = await epg_guide(id, client)
            elif id in tivu:
                description = await tivu_get(id, client)
                title = ""
            else:
                description, title = f'Watch {channel["title"]}', ""
        return respond_with({'meta': {
            'id': id, 'type': 'tv', 'name': channel['name'], 'poster': channel['poster'],
            'posterShape': 'landscape', 'description': title + "\n" + description,
            'background': channel['poster'], 'logo': channel['poster'], 'genres': channel.get('genres', [])
        }})
    elif type == "series" and 'realtime' in id:
        meta = {'meta': {'videos': [], 'status': 'Continuing', 'type': 'series', 'id': id}}
        async with AsyncSession(proxies=proxies) as client:
            meta = await meta_catalog_realtime(id, meta, client)
        return respond_with(meta)
    raise HTTPException(status_code=404)

@app.get('/{config:path}/stream/{type}/{id}.json')
@limiter.limit("5/second")
async def addon_stream(request: Request, config: str, type: str, id: str):
    if type not in MANIFEST['types']: raise HTTPException(status_code=404)
    streams = {'streams': []}
    try:
        config_clean = config.replace("%7C", "|").replace(" ", "")
        decoded_config = base64.b64decode(config_clean).decode('utf-8')
    except:
        decoded_config = "|SC|CB|GS|GHD|ES|GF|GO|RT|TI|"

    config_providers = decoded_config.split('|')
    provider_maps = {name: "0" for name in provider_map.values()}
    for p in config_providers:
        if p in provider_map: provider_maps[provider_map[p]] = "1"

    MFP, MFP_CREDENTIALS = "0", ['', '']
    if "MFP[" in decoded_config:
        try:
            mfp_data = decoded_config.split("MFP[")[1].split("]")[0]
            u, p = mfp_data.split(",")
            MFP_CREDENTIALS = [u[:-1] if u.endswith('/') else u, p]
            MFP = "1"
        except: pass

    async with AsyncSession(proxies=proxies) as client:
        if type == "tv":
            for channel in STREAM["channels"]:
                if channel["id"] == id:
                    if 'url' in channel: streams['streams'].append({'title': f"{Icon} Server 1 - {channel['name']}", 'url': channel['url']})
                    if id in extra_sources:
                        for idx, item in enumerate(extra_sources[id], 2):
                            streams['streams'].append({'title': f"{Icon} Server {idx}", 'url': item})
        elif "realtime" in id and RT == '1':
            streams = await streams_realtime(streams, id, client)
        elif any(x in id for x in ["tt", "tmdb", "kitsu"]):
            if "kitsu" in id and provider_maps.get('ANIMEWORLD') == "1" and AW == "1":
                streams = await animeworld(streams, id, client)
            else:
                if provider_maps.get('STREAMINGCOMMUNITY') == "1" and SC == "1":
                    streams = await streaming_community(streams, id, client, "1" if provider_maps.get('SC_MFP') != "0" else "0", MFP_CREDENTIALS)
                if provider_maps.get('CB01') == "1" and CB == "1": streams = await cb01(streams, id, MFP, MFP_CREDENTIALS, client)
                if provider_maps.get('GUARDASERIE') == "1" and GS == "1": streams = await guardaserie(streams, id, client)
                if provider_maps.get('GUARDAHD') == "1" and GHD == "1": streams = await guardahd(streams, id, client)
                if provider_maps.get('EUROSTREAMING') == "1" and ES == "1": streams = await eurostreaming(streams, id, client, MFP, MFP_CREDENTIALS)
                if provider_maps.get('GUARDAFLIX') == "1" and GF == "1": streams = await guardaflix(streams, id, client, MFP, MFP_CREDENTIALS)
                if provider_maps.get('GUARDOSERIE') == "1" and GO == "1": streams = await guardoserie(streams, id, client, MFP, MFP_CREDENTIALS)
                if provider_maps.get('TOONITALIA') == "1" and TI == "1": streams = await toonitalia(streams, id, client, MFP, MFP_CREDENTIALS)
    
    if not streams['streams']: raise HTTPException(status_code=404)
    return respond_with(streams)

@app.get('/uprot')
async def uprot_get(request: Request):
    async with AsyncSession(proxies=proxies) as client:
        image, cookies = await get_uprot_numbers(client)
    resp = static.TemplateResponse('uprot.html', {'request': request, "image_url": image})
    if cookies: resp.set_cookie(key='PHPSESSID', value=cookies.get('PHPSESSID'), httponly=True)
    return resp

@app.post("/uprot")
async def uprot_post(request: Request, user_input=Form(...), PHPSESSID: str = Cookie(None)):
    async with AsyncSession(proxies=proxies) as client:
        status = await generate_uprot_txt(user_input, {'PHPSESSID': PHPSESSID}, client)
    img = 'https://tinyurl.com/doneokdone' if status else 'https://tinyurl.com/tryagaindumb'
    return static.TemplateResponse('uprot.html', {'request': request, "image_url": img})

@app.get('/update')
async def update_sites():
    async with AsyncSession(proxies=proxies) as client:
        return JSONResponse(content={"message": "200" if await update_all_sites(client) else "Failed"})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host=HOST, port=PORT, log_level=level)
