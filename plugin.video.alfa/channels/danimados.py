# -*- coding: utf-8 -*-

import re
import base64
from bs4 import BeautifulSoup
from channelselector import get_thumb
from core import httptools
from core import scrapertools
from core import servertools
from core import tmdb
from core.item import Item
from platformcode import config, logger
from channels import autoplay
from channels import filtertools

host = "https://www.danimados.com/"

list_servers = [
                'okru',
                'rapidvideo'
                ]
list_quality = ['default']
list_idiomas = ['LAT']


def mainlist(item):
    logger.info()
    thumb_series = get_thumb("channels_tvshow.png")
    autoplay.init(item.channel, list_servers, list_quality)
    itemlist = list()
    itemlist.append(Item(channel=item.channel, action="lista", title="Series Clásicas", url=host+"genero/series-clasicas/",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="lista", title="Series Actuales", url=host+"genero/series-actuales/",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="lista", title="Anime Clásico", url=host+"genero/anime-clasico/",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="lista", title="Anime Moderno", url=host+"genero/anime-moderno/",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="lista", title="Live Action", url=host+"genero/live-action/",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="lista", title="Peliculas Animadas", url=host+"peliculas/", extra="Peliculas Animadas",
                         thumbnail=thumb_series))
    itemlist.append(Item(channel=item.channel, action="search", title="Buscar", url=host + "?s=",
                         thumbnail=thumb_series))
    autoplay.show_option(item.channel, itemlist)
    return itemlist


def search(item, texto):
    logger.info()
    texto = texto.replace(" ","+")
    item.url = host + "?s=" + texto
    if texto!='':
       return sub_search(item)


def sub_search(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    patron  = '(?s)class="thumbnail animation-.*?href=([^>]+).*?'
    patron += 'src=(.*?(?:jpg|jpeg)).*?'
    patron += 'alt=(?:"|)(.*?)(?:"|>).*?'
    patron += 'class=year>(.*?)<'
    matches = scrapertools.find_multiple_matches(data, patron)
    for scrapedurl, scrapedthumbnail, scrapedtitle, scrapedyear in matches:
        scrapedyear = scrapertools.find_single_match(scrapedyear, 'class="year">(\d{4})')
        item.action = "findvideos"
        item.contentTitle = scrapedtitle
        item.contentSerieName = ""
        if "serie" in scrapedurl:
           item.action = "temporadas"
           item.contentTitle = ""
           item.contentSerieName = scrapedtitle
        title = scrapedtitle
        if scrapedyear:
            item.infoLabels['year'] = int(scrapedyear)
            title += " (%s)" %item.infoLabels['year']
        itemlist.append(item.clone(thumbnail = scrapedthumbnail,
                                   title = title,
                                   url = scrapedurl
                                  ))
    tmdb.set_infoLabels(itemlist)
    return itemlist


def mainpage(item):
    logger.info()
    itemlist = []
    data1 = httptools.downloadpage(item.url).data
    data1 = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data1)
    patron_sec='<divclass=head-main-nav>(.+?)peliculas\/>'
    patron='<ahref=([^"]+)>([^"]+)<\/a>'#scrapedurl, #scrapedtitle
    data = scrapertools.find_single_match(data1, patron_sec)
    matches = scrapertools.find_multiple_matches(data, patron)
    if item.title=="Géneros" or item.title=="Categorías":
        for scrapedurl, scrapedtitle in matches:
            if "Películas Animadas"!=scrapedtitle:
                itemlist.append(
                    Item(channel=item.channel, title=scrapedtitle, url=scrapedurl, action="lista"))
        return itemlist
    else:
        for scraped1, scraped2, scrapedtitle in matches:
            scrapedthumbnail=scraped1
            scrapedurl=scraped2
            itemlist.append(
                    Item(channel=item.channel, title=scrapedtitle, url=scrapedurl, thumbnail=scrapedthumbnail, action="episodiosxtemporada",
                         show=scrapedtitle))
        tmdb.set_infoLabels(itemlist)
        return itemlist
    return itemlist


def lista(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    if item.extra == "Peliculas Animadas":
        data_lista = scrapertools.find_single_match(data, '(?is)archive-content(.*?)class=pagination')
    else:
        data_lista = scrapertools.find_single_match(data, 'class=items><article(.+?)<\/div><\/article><\/div>')
    patron  = '(?is)src=(.*?(?:jpg|jpeg)).*?'
    patron += 'alt=(?:"|)(.*?)(?:"|>).*?'
    patron += 'href=([^>]+)>.*?'
    patron += 'title.*?<span>([^<]+)<'
    matches = scrapertools.find_multiple_matches(data_lista, patron)
    for scrapedthumbnail, scrapedtitle, scrapedurl, scrapedyear in matches:
        if item.title=="Peliculas Animadas":
            thumbnail = re.sub('p/w\d+','p/original',scrapedthumbnail)
            itemlist.append(
                item.clone(title=scrapedtitle, url=scrapedurl, thumbnail=thumbnail, contentType="movie",
                       action="findvideos", contentTitle=scrapedtitle, infoLabels={'year':scrapedyear}))
        else:    
            itemlist.append(
                item.clone(title=scrapedtitle, url=scrapedurl, thumbnail=scrapedthumbnail, 
                       context=autoplay.context,action="temporadas", contentSerieName=scrapedtitle))
    tmdb.set_infoLabels(itemlist)
    next_page = scrapertools.find_single_match(data, 'rel=next href=([^>]+)>')
    if next_page:
        itemlist.append(item.clone(action="lista", title="Página siguiente>>", url=next_page, extra=item.extra))
    return itemlist

def temporadas(item):
    logger.info()
    itemlist = []

    data = httptools.downloadpage(item.url).data
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', "", data)

    patron = '<spanclass=title>Temporada (\d+) <i>'

    matches = re.compile(patron, re.DOTALL).findall(data)
    infoLabels = item.infoLabels
    for scrapedseason in matches:
        contentSeasonNumber = scrapedseason
        title = 'Temporada %s' % scrapedseason
        infoLabels['season'] = contentSeasonNumber

        itemlist.append(Item(channel=item.channel, action='episodiosxtemporada', url=item.url, title=title,
                             contentSeasonNumber=contentSeasonNumber, infoLabels=infoLabels))
    tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)

    if config.get_videolibrary_support() and len(itemlist) > 0:
        itemlist.append(
            Item(channel=item.channel, title='[COLOR yellow]Añadir esta serie a la videoteca[/COLOR]', url=item.url,
                 action="add_serie_to_library", extra="episodios", contentSerieName=item.contentSerieName, seasons = matches,
                 extra1='library'))

    return itemlist
    
def episodios(item):
    logger.info()
    itemlist = []
    templist = item.seasons
    infoLabels = item.infoLabels
    for contentSeasonNumber in templist:
        infoLabels['season'] = contentSeasonNumber
        itemlist += episodiosxtemporada(item)
    return itemlist

def episodiosxtemporada(item):
    logger.info()
    itemlist = []
    infoLabels = {}
    data = httptools.downloadpage(item.url).data
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)
    patron = '<divid=episodes (.+?)<\/div><\/div><\/div>'
    data_lista = scrapertools.find_single_match(data,patron)
    contentSerieName = item.title
    patron_caps  = '<ahref=(.+?) ><imgalt=".+?" '
    patron_caps += 'src=([^"]+)><\/a>.*?'
    patron_caps += 'numerando>([^<]+).*?'
    patron_caps += 'episodiotitle>.*?>([^<]+)<\/a>'
    matches = scrapertools.find_multiple_matches(data_lista, patron_caps)
    infoLabels = item.infoLabels
    for scrapedurl, scrapedthumbnail, scrapedtempepi, scrapedtitle in matches:
        tempepi=scrapedtempepi.split(" - ")
        if len(tempepi) != 1:
            if tempepi[0]=='Pel':
                tempepi[0]=0
            title="{0}x{1} - {2}".format(tempepi[0], tempepi[1].zfill(2), scrapedtitle)
            #item.infoLabels["season"] = tempepi[0]
            infoLabels["episode"] = tempepi[1]
            if int(infoLabels['season']) == int(tempepi[0]):
                itemlist.append(item.clone(#thumbnail=scrapedthumbnail,
                            action="findvideos", title=title, infoLabels=infoLabels, url=scrapedurl))
    #if config.get_videolibrary_support() and len(itemlist) > 0:
    #    itemlist.append(Item(channel=item.channel, title="[COLOR yellow]Añadir " + contentSerieName + " a la videoteca[/COLOR]", url=item.url,
    #                         action="add_serie_to_library", extra="episodiosxtemporada", contentSerieName=contentSerieName))
    tmdb.set_infoLabels(itemlist, True)
    return itemlist


def create_soup(url, referer=None, unescape=False):
    logger.info()

    if referer:
        data = httptools.downloadpage(url, headers={'Referer':referer}).data
    else:
        data = httptools.downloadpage(url).data

    if unescape:
        data = scrapertools.unescape(data)
    soup = BeautifulSoup(data, "html5lib", from_encoding="utf-8")

    return soup

def findvideos(item):
    logger.info()
    srv_list = {'OpRu': 'okru', 'NeoPen-O-GD': 'netutv', 'mp4': 'mp4upload', 'CloudVid': 'gounlimited',}
    itemlist = list()
    soup = create_soup(item.url).find("ul", class_="new-servers").find_all("li")    
    infoLabels = item.infoLabels
    for btn in soup:
        opt = btn["data-sv"]
        srv = srv_list.get(opt, 'directo')
        id_opt = btn["id"]
        itemlist.append(Item(channel=item.channel, url=item.url, action='play', server=srv, id_opt=id_opt, language='LAT',
                        title=srv, infoLabels=infoLabels))
    
    # Requerido para FilterTools

    itemlist = filtertools.get_links(itemlist, item, list_idiomas, list_quality)
    itemlist = sorted(itemlist, key=lambda i: i.server)
    # Requerido para AutoPlay

    autoplay.start(itemlist, item)

    return itemlist

def play(item):
    logger.info()
    itemlist = list()

    soup = create_soup(item.url).find("li", class_="dooplay_player_option", id=item.id_opt)
    scrapeduser = scrapertools.find_single_match(str(soup), 'data-user="([^"]+)"')
    headers = {"X-Requested-With":"XMLHttpRequest"}
    data1 = httptools.downloadpage("https://sv.danimados.com/gilberto.php?id=%s&sv=mp4" % scrapeduser).data
    data1 = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data1)
    url = base64.b64decode(scrapertools.find_single_match(data1, '<iframe data-source="([^"]+)"'))
    url1 = devuelve_enlace(url)
    if url1:
        srv = servertools.get_server_from_url(url1)
        itemlist.append(item.clone(url=url1, server=srv))
    
    return itemlist

def devuelve_enlace(url1):
    if 'danimados' in url1:
        url1 = "https:%s" % url1
        new_data = httptools.downloadpage(url1).data
        url1 = scrapertools.find_single_match(new_data, '<iframe src="([^"]+)"')
        if not url1:
            url1 = scrapertools.find_single_match(new_data, 'sources: \[{file: "([^"]+)"')
    return url1
'''
def findvideos(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    patron  = 'player-option-\d+.*?'
    patron += 'data-sv=(\w+).*?'
    patron += 'data-user="([^"]+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    headers = {"X-Requested-With":"XMLHttpRequest"}
    for scrapedserver, scrapeduser in matches:
        data1 = httptools.downloadpage("https://sv.danimados.com/gilberto.php?id=%s&sv=mp4" %scrapeduser).data
        data1 = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data1)
        url = base64.b64decode(scrapertools.find_single_match(data1, '<iframe data-source="([^"]+)"'))
        url1 = devuelve_enlace(url)
        if url1:
            itemlist.append(item.clone(title="Ver en %s",url=url1, action="play"))
    tmdb.set_infoLabels(itemlist)
    itemlist = servertools.get_servers_itemlist(itemlist, lambda i: i.title % i.server.capitalize())
    if config.get_videolibrary_support() and len(itemlist) > 0 and item.contentType=="movie" and item.contentChannel!='videolibrary':
        itemlist.append(
            item.clone(channel=item.channel, title='[COLOR yellow]Añadir esta pelicula a la videoteca[/COLOR]', url=item.url,
                action="add_pelicula_to_library"))
    autoplay.start(itemlist, item)
    return itemlist
'''
'''
def findvideos(item):
    logger.info()
    itemlist = []
    data = httptools.downloadpage(item.url).data
    patron  = 'player-option-\d+.*?'
    patron += 'data-sv=(\w+).*?'
    patron += 'data-user="([^"]+)'
    matches = scrapertools.find_multiple_matches(data, patron)
    headers = {"X-Requested-With":"XMLHttpRequest"}
    for scrapedserver, scrapeduser in matches:
        data1 = httptools.downloadpage("https://sv.danimados.com/gilberto.php?id=%s&sv=mp4" %scrapeduser).data
        data1 = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data1)
        url = base64.b64decode(scrapertools.find_single_match(data1, '<iframe data-source="([^"]+)"'))
        url1 = devuelve_enlace(url)
        if url1:
            itemlist.append(item.clone(title="Ver en %s",url=url1, action="play"))
    tmdb.set_infoLabels(itemlist)
    itemlist = servertools.get_servers_itemlist(itemlist, lambda i: i.title % i.server.capitalize())
    if config.get_videolibrary_support() and len(itemlist) > 0 and item.contentType=="movie" and item.contentChannel!='videolibrary':
        itemlist.append(
            item.clone(channel=item.channel, title='[COLOR yellow]Añadir esta pelicula a la videoteca[/COLOR]', url=item.url,
                action="add_pelicula_to_library"))
    autoplay.start(itemlist, item)
    return itemlist


def play(item):
    item.thumbnail = item.contentThumbnail
    return [item]



'''