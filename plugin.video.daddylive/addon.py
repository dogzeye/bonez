#rewrite daddylive, working favs folder prior to adding schedules in panel
# -*- coding: utf-8 -*-
'''
***********************************************************
*
* @file addon.py
* @package script.module.thecrew
*
* Created on 2024-03-08.
* Copyright 2024 by The Crew. All rights reserved.
*
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''
# pylint: disable-msg=F0401

import re
import os
import sys
import json
import html
from urllib.parse import urlparse
from urllib.parse import urlencode, quote, unquote, parse_qsl, quote_plus, urlparse
from datetime import datetime, timedelta, timezone
import time
import requests
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon
import base64

addon_url = sys.argv[0]
addon_handle = int(sys.argv[1])
params = dict(parse_qsl(sys.argv[2][1:]))
addon = xbmcaddon.Addon(id='plugin.video.daddylive')

mode = addon.getSetting('mode')
main_url = requests.get('https://raw.githubusercontent.com/thecrewwh/dl_url/refs/heads/main/dl.xml').text
baseurl = re.findall('src = "([^"]*)',main_url)[0]
json_url = f'{baseurl}stream/stream-%s.php'
schedule_url = baseurl + 'schedule/schedule-generated.php'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
FANART = addon.getAddonInfo('fanart')
ICON = addon.getAddonInfo('icon')
FAV_FILE = xbmcvfs.translatePath('special://profile/addon_data/plugin.video.daddylive/favorites.json')

def load_favorites():
    if not xbmcvfs.exists(FAV_FILE):
        return []
    try:
        with open(FAV_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to load favorites: {e}")
        return []

def save_favorites(favorites):
    try:
        folder_path = os.path.dirname(FAV_FILE)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        with open(FAV_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2)

    except Exception as e:
        log(f"Failed to save favorites: {e}")

def log(msg):
    LOGPATH = xbmcvfs.translatePath('special://logpath/')
    FILENAME = 'daddylive.log'
    LOG_FILE = os.path.join(LOGPATH, FILENAME)
    try:
        if isinstance(msg, str):
            _msg = f'\n    {msg}'
        else:
            raise TypeError('log() msg not of type str!')
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w', encoding='utf-8'):
                pass
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            line = ('[{} {}]: {}').format(datetime.now().date(), str(datetime.now().time())[:8], _msg)
            f.write(line.rstrip('\r\n') + '\n')
    except (TypeError, Exception) as e:
        try:
            xbmc.log(f'[ Daddylive ] Logging Failure: {e}', 2)
        except:
            pass

def get_local_time(utc_time_str):
    try:
        utc_now = datetime.utcnow()
        event_time_utc = datetime.strptime(utc_time_str, '%H:%M')
        event_time_utc = event_time_utc.replace(year=utc_now.year, month=utc_now.month, day=utc_now.day)
        event_time_utc = event_time_utc.replace(tzinfo=timezone.utc)
        local_time = event_time_utc.astimezone()
        time_format_pref = addon.getSetting('time_format')
        if time_format_pref == '1':
            local_time_str = local_time.strftime('%H:%M')
        else:
            local_time_str = local_time.strftime('%I:%M %p').lstrip('0')
        return local_time_str
    except Exception as e:
        log(f"Failed to convert time: {e}")
        return utc_time_str

def build_url(query):
    return addon_url + '?' + urlencode(query)

def addDir(title, dir_url, is_folder=True):
    li = xbmcgui.ListItem(title)
    labels = {'title': title, 'plot': title, 'mediatype': 'video'}
    kodiversion = getKodiversion()
    if kodiversion < 20:
        li.setInfo("video", labels)
    else:
        infotag = li.getVideoInfoTag()
        infotag.setMediaType(labels.get("mediatype", "video"))
        infotag.setTitle(labels.get("title", "Daddylive"))
        infotag.setPlot(labels.get("plot", labels.get("title", "Daddylive")))
    li.setArt({'thumb': '', 'poster': '', 'banner': '', 'icon': ICON, 'fanart': FANART})
    li.setProperty("IsPlayable", 'true' if is_folder else 'true')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=dir_url, listitem=li, isFolder=is_folder)

def closeDir():
    xbmcplugin.endOfDirectory(addon_handle)

def getKodiversion():
    try:
        return int(xbmc.getInfoLabel("System.BuildVersion")[:2])
    except:
        return 18

def Main_Menu():
    menu = [
        ['[B][COLOR gold]LIVE SPORTS[/COLOR][/B]', 'sched'],
        ['[B][COLOR gold]LIVE TV[/COLOR][/B]', 'live_tv'],
        #['[B][COLOR gold]SEARCH EVENTS[/COLOR][/B]', 'search'],
        #['[B][COLOR gold]SEARCH CHANNELS[/COLOR][/B]', 'search_channels'],
        #['[B][COLOR gold]REFRESH CATEGORIES[/COLOR][/B]', 'refresh_sched']
    ]
    for m in menu:
        addDir(m[0], build_url({'mode': 'menu', 'serv_type': m[1]}))

    # Add Favorites directly — not as a 'menu' mode
    addDir('[B][COLOR blue]LIVE TV FAVORITES[/COLOR][/B]', build_url({'mode': 'live_favs'}))

    closeDir()

def getCategTrans():
    hea = {'User-Agent': UA, 'Referer': baseurl, 'Origin': baseurl}
    categs = []
    try:
        schedule = requests.get(schedule_url, headers=hea, timeout=10).json()
        for date_key, events in schedule.items():
            for categ, events_list in events.items():
                categs.append((categ.replace('</span>', ''), json.dumps(events_list)))
    except Exception as e:
        xbmcgui.Dialog().ok("Error", f"Error fetching category data: {e}")
        return []
    return categs

def Menu_Trans():
    categs = getCategTrans()
    if not categs:
        return

    for categ_name, events_list in categs:
        # Build plot/preview for info panel
        try:
            events = json.loads(events_list)
            preview_lines = []
            for item in events[:5]:  # Limit to first 5 items
                time_str = get_local_time(item.get('time', ''))
                event = item.get('event', '')
                if time_str and event:
                    preview_lines.append(f"{time_str} - {event}")
            plot_text = "\n".join(preview_lines) if preview_lines else "No upcoming events."
        except Exception as e:
            log(f"Failed building preview for {categ_name}: {e}")
            plot_text = "No upcoming events."

        li = xbmcgui.ListItem(categ_name)
        li.setInfo("video", {
            'title': categ_name,
            'plot': plot_text,
            'mediatype': 'video'
        })
        li.setArt({'icon': ICON, 'fanart': FANART})
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({'mode': 'showChannels', 'trType': categ_name}),
            listitem=li,
            isFolder=True
        )

    closeDir()

def ShowChannels(categ, channels_list):
    for item in channels_list:
        title = item.get('title')
        addDir(title, build_url({'mode': 'trList', 'trType': categ, 'channels': json.dumps(item.get('channels'))}), True)
    closeDir()

def getTransData(categ):
    trns = []
    categs = getCategTrans()
    for categ_name, events_list_json in categs:
        if categ_name == categ:
            events_list = json.loads(events_list_json)
            for item in events_list:
                event = item.get('event')
                time_str = item.get('time')
                event_time_local = get_local_time(time_str)
                title = f'[COLOR gold]{event_time_local}[/COLOR] {event}'
                channels = item.get('channels')
                if isinstance(channels, list) and all(isinstance(channel, dict) for channel in channels):
                    trns.append({
                        'title': title,
                        'channels': [{'channel_name': channel.get('channel_name'), 'channel_id': channel.get('channel_id')} for channel in channels]
                    })
                else:
                    log(f"Unexpected data structure in 'channels': {channels}")
    return trns

def TransList(categ, channels):
    xbmcplugin.setContent(addon_handle, 'videos')  # Force plugin-style video context
    for channel in channels:
        channel_title = html.unescape(channel.get('channel_name'))
        channel_id = channel.get('channel_id')
        url = f"{baseurl}stream/stream-{channel_id}.php"

        li = xbmcgui.ListItem(channel_title)
        li.setArt({'icon': ICON, 'fanart': FANART})
        li.setProperty("IsPlayable", "true")  # Prevent default Kodi context menus

        # Force custom context menu only
        fav_entry = {'name': channel_title, 'url': url}
        fav_cmd = f"RunPlugin({build_url({'mode': 'toggle_fav', 'fav': json.dumps(fav_entry)})})"
        li.addContextMenuItems([("Toggle Favorite", fav_cmd)], replaceItems=True)

        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({'mode': 'play', 'url': url}),
            listitem=li,
            isFolder=False
        )
    closeDir()

def getSource(trData):
    data = json.loads(unquote(trData))
    channels_data = data.get('channels')
    if channels_data and isinstance(channels_data, list):
        url_stream = f'{baseurl}stream/stream-{channels_data[0]["channel_id"]}.php'
        xbmcplugin.setContent(addon_handle, 'videos')
        PlayStream(url_stream)

def list_gen():
    chData = channels()
    for c in chData:
        url = baseurl + c[0]
        title = c[1]

        # Create the list item
        li = xbmcgui.ListItem(title)
        li.setArt({'icon': ICON, 'fanart': FANART})
        li.setProperty("IsPlayable", "true")

        # Add context menu for adding/removing favorites
        fav_entry = {'name': title, 'url': url}
        fav_cmd = f"RunPlugin({build_url({'mode': 'toggle_fav', 'fav': json.dumps(fav_entry)})})"
        li.addContextMenuItems([("Toggle Favorite", fav_cmd)])

        # Add the item to the Kodi directory
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({'mode': 'play', 'url': url}),
            listitem=li,
            isFolder=False
        )
    closeDir()
  
def toggle_favorite(fav_str):
    fav = json.loads(fav_str)
    favorites = load_favorites()

    exists = any(f['url'] == fav['url'] for f in favorites)
    if exists:
        favorites = [f for f in favorites if f['url'] != fav['url']]
        xbmcgui.Dialog().notification("Daddylive", "Removed from favorites", xbmcgui.NOTIFICATION_INFO, 2000)
    else:
        favorites.append(fav)
        xbmcgui.Dialog().notification("Daddylive", "Added to favorites", xbmcgui.NOTIFICATION_INFO, 2000)

    save_favorites(favorites)
    
def list_favorites():
    favorites = load_favorites()
    if not favorites:
        xbmcgui.Dialog().ok("Favorites", "No favorites saved.")
        return

    for fav in favorites:
        li = xbmcgui.ListItem(fav['name'])
        li.setArt({'icon': ICON, 'fanart': FANART})
        li.setProperty("IsPlayable", "true")

        # Add context menu: remove this favorite
        fav_cmd = f"RunPlugin({build_url({'mode': 'toggle_fav', 'fav': json.dumps(fav)})})"
        li.addContextMenuItems([("Remove from Favorites", fav_cmd)])

        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=build_url({'mode': 'play', 'url': fav['url']}),
            listitem=li,
            isFolder=False
        )
    closeDir()
    
def channels():
    url = baseurl + '/24-7-channels.php'
    do_adult = xbmcaddon.Addon().getSetting('adult_pw')
    hea = {'Referer': baseurl + '/', 'user-agent': UA}
    resp = requests.post(url, headers=hea).text
    ch_block = re.compile('<center><h1(.+?)tab-2', re.MULTILINE | re.DOTALL).findall(str(resp))
    chan_data = re.compile('href=\"(.*)\" target(.*)<strong>(.*)</strong>').findall(ch_block[0])
    channels = []
    for c in chan_data:
        if not "18+" in c[2]:
            channels.append([c[0], c[2]])
        if do_adult == 'lol' and "18+" in c[2]:
            channels.append([c[0], c[2]])
    return channels

def PlayStream(link):
    try:
        headers = {'User-Agent': UA, 'Referer': baseurl + '/', 'Origin': baseurl}
        response = requests.get(link, headers=headers, timeout=10).text

        iframes = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>\s*<button[^>]*>\s*Player\s*2\s*<\/button>', response)
        if not iframes:
            log("No iframe src found")
            return

        url2 = iframes[0]
        url2 = baseurl + url2
        url2 = url2.replace('//cast','/cast')
        headers['Referer'] = headers['Origin'] = url2
        response = requests.get(url2, headers=headers, timeout=10).text
        iframes = re.findall(r'iframe src="([^"]*)', response)
        if not iframes:
            log("No iframe src found")
            return
        url2 = iframes[0]
        response = requests.get(url2, headers=headers, timeout=10).text

        channel_key = re.findall(r'(?s) channelKey = \"([^"]*)', response)[0]
        auth_ts = re.findall(r'(?s)c = atob\("([^"]*)', response)[0]; auth_ts = base64.b64decode(auth_ts).decode('utf-8')
        auth_rnd = re.findall(r'(?s)d = atob\("([^"]*)', response)[0]; auth_rnd = base64.b64decode(auth_rnd).decode('utf-8')
        auth_sig = re.findall(r'(?s)e = atob\("([^"]*)', response)[0]; auth_sig = base64.b64decode(auth_sig).decode('utf-8')
        auth_sig = quote_plus(auth_sig)
        auth_host = re.findall(r'(?s)a = atob\("([^"]*)', response)[0]; auth_host = base64.b64decode(auth_host).decode('utf-8')
        auth_php = re.findall(r'(?s)b = atob\("([^"]*)', response)[0]; auth_php = base64.b64decode(auth_php).decode('utf-8')
        auth_url = f'{auth_host}{auth_php}?channel_id={channel_key}&ts={auth_ts}&rnd={auth_rnd}&sig={auth_sig}'
        auth = requests.get(auth_url, headers=headers, timeout=10).text

        host = re.findall('(?s)m3u8 =.*?:.*?:.*?".*?".*?"([^"]*)', response)[0]
        server_lookup = re.findall('n fetchWithRetry\(\s*\'([^\']*)', response)[0]

        server_lookup_url = f"https://{urlparse(url2).netloc}{server_lookup}{channel_key}"
        response = requests.get(server_lookup_url, headers=headers, timeout=10).json()
        server_key = response['server_key']

        referer_raw = f'https://{urlparse(url2).netloc}'
        referer = quote_plus(referer_raw)
        ua_encoded = quote_plus(UA)

        final_link = (
            f'https://{server_key}{host}{server_key}/{channel_key}/mono.m3u8'
            f'|Referer={referer}/&Origin={referer}&Connection=Keep-Alive&User-Agent={ua_encoded}'
        )

        liz = xbmcgui.ListItem('Daddylive', path=final_link)
        liz.setProperty('inputstream', 'inputstream.ffmpegdirect')
        liz.setMimeType('application/x-mpegURL')
        liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
        liz.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
        liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')

        xbmcplugin.setResolvedUrl(addon_handle, True, liz)

    except Exception as e:
        import traceback
        log(f"Error in PlayStream: {traceback.format_exc()}")

def Search_Events():
    keyboard = xbmcgui.Dialog().input("Enter search term", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard or keyboard.strip() == '':
        return
    term = keyboard.lower()
    results = []
    categs = getCategTrans()
    for categ_name, events_list_json in categs:
        events_list = json.loads(events_list_json)
        for item in events_list:
            event_title = item.get('event', '')
            if term in event_title.lower():
                time_str = item.get('time')
                event_time_local = get_local_time(time_str)
                title = f'[COLOR gold]{event_time_local}[/COLOR] {event_title}'
                channels = item.get('channels', [])
                results.append({'title': title, 'channels': channels})
    if not results:
        xbmcgui.Dialog().ok("Search", "No matching events found.")
        return
    for result in results:
        addDir(result['title'], build_url({'mode': 'trList', 'trType': 'search', 'channels': json.dumps(result['channels'])}), True)
    closeDir()

def Search_Channels():
    keyboard = xbmcgui.Dialog().input("Enter channel name", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard or keyboard.strip() == '':
        return
    term = keyboard.lower()
    results = []
    categs = getCategTrans()
    for categ_name, events_list_json in categs:
        events_list = json.loads(events_list_json)
        for item in events_list:
            for channel in item.get('channels', []):
                name = channel.get('channel_name', '')
                if term in name.lower():
                    title = html.unescape(name)
                    results.append({
                        'title': title,
                        'channel_id': channel.get('channel_id')
                    })
    if not results:
        xbmcgui.Dialog().ok("Search", "No matching channels found.")
        return
    for result in results:
        addDir(result['title'], build_url({
            'mode': 'trLinks',
            'trData': json.dumps({'channels': [{'channel_name': result["title"], 'channel_id': result["channel_id"]}]})
        }), False)
    closeDir()

kodiversion = getKodiversion()
mode = params.get('mode', None)

if not mode:
    Main_Menu()
else:
    if mode == 'menu':
        servType = params.get('serv_type')
        if servType == 'sched':
            Menu_Trans()
        elif servType == 'live_tv':
            list_gen()
        elif servType == 'search':
            Search_Events()
        elif servType == 'search_channels':
            Search_Channels()
        elif servType == 'refresh_sched':
            xbmc.executebuiltin('Container.Refresh')

    elif mode == 'showChannels':
        transType = params.get('trType')
        channels = getTransData(transType)
        ShowChannels(transType, channels)

    elif mode == 'trList':
        transType = params.get('trType')
        channels = json.loads(params.get('channels'))
        TransList(transType, channels)

    elif mode == 'trLinks':
        trData = params.get('trData')
        getSource(trData)

    elif mode == 'play':
        link = params.get('url')
        PlayStream(link)
        
    elif mode == 'live_favs':
        list_favorites()

    elif mode == 'toggle_fav':
        fav = params.get('fav')
        toggle_favorite(fav)
        
    elif mode == 'live_favs':
        list_favorites()
