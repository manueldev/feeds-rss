import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, UTC, timezone
import argparse
import re
import urllib.parse



def generar_feed_rss(nombre_archivo, url, titulo_feed, descripcion_feed, extractor_func):
    fg = FeedGenerator()
    fg.title(titulo_feed)
    fg.link(href=url)
    fg.description(descripcion_feed)

    items = extractor_func(url)

    for item in items:
        fe = fg.add_entry()
        fe.title(item['title'])
        fe.link(href=item['link'])
        fe.pubDate(item['pub_date'])

        # Crear un GUID único combinando title y artist (asumido en el title)
        guid_value = item['title']
        fe.guid(guid_value, permalink=False)


    # --- Exportar como string para editar el XML ---
    rss_str = fg.rss_str(pretty=True)  # pretty=True para saltos de línea y sangría

    # --- Eliminar <lastBuildDate> ---
    from xml.etree import ElementTree as ET
    root = ET.fromstring(rss_str)
    channel = root.find('channel')
    if channel is not None:
        last_build = channel.find('lastBuildDate')
        if last_build is not None:
            channel.remove(last_build)

    # --- Escribir archivo con saltos de línea ---
    final_xml = ET.tostring(root, encoding='utf-8', method='xml')

    with open(nombre_archivo, 'wb') as f:
        f.write(final_xml)

    print(f"RSS generado: {nombre_archivo}")





# --------- Extractor para Radioactiva ---------
def extractor_radioactiva(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    articles = soup.select('article')
    items = []

    for article in articles:
        title_tag = article.select_one('h1.fjalla')
        link_tag = title_tag.find_parent('a') if title_tag else None
        date_tag = article.select_one('small.date-post')


        if title_tag and link_tag and date_tag:
            title = title_tag.text.strip()
            link = link_tag['href']
            raw_date = date_tag.text.strip()

            MONTHS_ES = {
                'enero': 'January',
                'febrero': 'February',
                'marzo': 'March',
                'abril': 'April',
                'mayo': 'May',
                'junio': 'June',
                'julio': 'July',
                'agosto': 'August',
                'septiembre': 'September',
                'octubre': 'October',
                'noviembre': 'November',
                'diciembre': 'December'
            }

            # Reemplazar el mes en español por inglés
            for es, en in MONTHS_ES.items():
                if es in raw_date.lower():
                    raw_date = raw_date.lower().replace(es, en)
                    break

            pub_date = datetime.strptime(raw_date, '%d %B, %Y').replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


            items.append({
                'title': title,
                'link': link,
                'pub_date': pub_date
            })

    return items



# --------- Extractor para Los40 ---------
def extractor_los40(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    items = []

    # Buscar bloques de <script> que contengan "songTitle" en formato texto plano
    scripts = soup.find_all('script', string=re.compile('songTitle'))

    for script in scripts:
        try:
            # Extraer el texto de cada <script> y buscar las ocurrencias
            data_text = script.string.strip()

            # Buscar todas las ocurrencias de songTitle, artistName, youtubeUrl y createdAt
            pattern = re.compile(r'"songTitle":"(.*?)".*?"artistName":"(.*?)".*?"youtubeUrl":"(https://www\.youtube\.com/watch\?v=[\w-]+)".*?"createdAt":"(.*?)"')
            matches = pattern.findall(data_text)

            # Para cada coincidencia, agregarla a la lista de items
            for match in matches:
                song_title = match[0].strip()
                artist_name = match[1].strip()
                youtube_url = match[2].strip()
                created_at_str = match[3].strip()  # Extraemos la fecha 'createdAt'
                print(created_at_str)

                # Convertir 'createdAt' a objeto datetime usando fromisoformat
                try:
                    pub_date = datetime.fromisoformat(created_at_str)  # La fecha ya puede tener una zona horaria
                except ValueError:
                    # Si la fecha no es válida, intentar sin zona horaria
                    pub_date = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ')  # Si no tiene zona horaria

                # Crear el título del item combinando artista y título
                title = f"{artist_name} – {song_title}"
                link = youtube_url

                # Agregar el item a la lista
                items.append({
                    'title': title,  # Título combinado
                    'link': link,    # Enlace al video de YouTube
                    'pub_date': pub_date  # Fecha de publicación con zona horaria
                })

        except Exception as e:
            print(f"Error procesando script: {e}")
            continue

    return items




def extractor_djcity_most(url):
    # Hacemos la solicitud a la API de DJcity
    response = requests.get(url)
    data = response.json()  # Suponiendo que la respuesta es JSON

    items = []
    for song in data['data']:  # Recorremos cada canción en la lista "data"
        artist = song.get('artist', 'Unknown Artist')  # Extraemos el nombre del artista
        title = song.get('title', 'No Title')  # Extraemos el título de la canción
        release_date_str = song.get('releasedate', '')  # Extraemos la fecha de lanzamiento

        # Convertir la fecha de lanzamiento a formato datetime
        try:
            pub_date = datetime.strptime(release_date_str, '%Y-%m-%dT%H:%M:%S.%fZ')  # Formato ISO 8601
        except ValueError:
            pub_date = datetime.strptime(release_date_str, '%Y-%m-%dT%H:%M:%SZ')  # Para el formato sin milisegundos
        
        # Añadir la zona horaria UTC a la fecha
        pub_date = pub_date.replace(tzinfo=timezone.utc)

        # Creamos la URL de búsqueda en Google usando el artista y el título
        query = f"{artist} {title}"
        link = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

        # Combinamos el artista y el título para formar el título del item RSS
        item_title = f"{artist} - {title}"

        # Aquí agregamos cada canción a la lista de items
        items.append({
            'title': item_title,  # El título combinado de artista y título
            'link': link,  # Añadimos el link a la entrada
            'pub_date': pub_date  # Añadimos la fecha de publicación con la zona horaria
        })
    return items


from urllib.parse import quote

# --------- Extractor para MonitorLatino ---------
def extractor_monitorlatino(url):
    # Hacemos la solicitud a la API de Monitor Latino
    response = requests.get(url)
    data = response.json()  # Suponiendo que la respuesta es JSON
    items = []
    
    # La fecha fija para pub_date
    pub_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Recorremos cada canción en la lista "data"
    for song in data['data']:
        title = song.get('title', 'No Title')  # Extraemos el título de la canción
        artist = song.get('artists', 'Unknown Artist')  # Extraemos el nombre del artista
        
        # Creamos el título del item RSS combinando el artista y el título
        item_title = f"{artist} – {title}"
        
        # Creamos una búsqueda en Google con "artista - título"
        search_query = quote(f"{artist} - {title}")
        link = f"https://www.google.com/search?q={search_query}"

        # Aquí agregamos cada canción a la lista de items
        items.append({
            'title': item_title,  # El título combinado de artista y título
            'link': link,         # Enlace de búsqueda en Google
            'pub_date': pub_date  # Fecha fija de publicación
        })
    
    return items




# Diccionario de feeds configurables
FEEDS = {
    'radioactiva': {
        'nombre_archivo': 'estrenos_radioactivos.xml',
        'url': 'https://www.radioactiva.cl/?s=Estrenos+RadioActivos',
        'titulo_feed': 'Estrenos RadioActivos',
        'descripcion_feed': 'Últimos estrenos musicales publicados en RadioActiva',
        'extractor_func': extractor_radioactiva
    },
    'los40': {
        'nombre_archivo': 'lista40.xml',
        'url': 'https://los40.cl/lista40/',
        'titulo_feed': 'Lista Los40 Chile',
        'descripcion_feed': 'Ranking musical semanal de Los40 Chile',
        'extractor_func': extractor_los40
    },
    'djcity_most_dance': {
        'nombre_archivo': 'djcity_most_dance.xml',
        'url': 'https://api.djcity.com/v1/songs/hotbox?locale=en-US&tags=102&types=&ctypes=2&bpmlt=200&remixers=&keys=&type=1W&page=1&pageSize=15&pageCount=1&sortBy=9',
        'titulo_feed': 'DJcity Most Popular - Dance',
        'descripcion_feed': 'Explore the Most Popular Music & Songs on DJcity - Dance',
        'extractor_func': extractor_djcity_most
    },
    'djcity_most_latin': {
        'nombre_archivo': 'djcity_most_latin.xml',
        'url': 'https://api.djcity.com/v1/songs/hotbox?locale=en-US&tags=3&types=&ctypes=2&bpmlt=200&remixers=&keys=&type=1W&page=1&pageSize=15&pageCount=1&sortBy=9',
        'titulo_feed': 'DJcity Most Popular - Latin',
        'descripcion_feed': 'Explore the Most Popular Music & Songs on DJcity - Latin',
        'extractor_func': extractor_djcity_most
    },
    'djcity_most_pop': {
        'nombre_archivo': 'djcity_most_pop.xml',
        'url': 'https://api.djcity.com/v1/songs/hotbox?locale=en-US&tags=4&types=&ctypes=2&bpmlt=200&remixers=&keys=&type=1W&page=1&pageSize=15&pageCount=1&sortBy=9',
        'titulo_feed': 'DJcity Most Popular - Pop',
        'descripcion_feed': 'Explore the Most Popular Music & Songs on DJcity - Pop',
        'extractor_func': extractor_djcity_most
    },
    'monitorlatino_chile': {
        'nombre_archivo': 'monitorlatino_chile.xml',
        'url': 'http://us.monitorlatino.com/chart_top10_v2.aspx?format=json&c=Chile',
        'titulo_feed': 'MonitorLatino Chile Top 10',
        'descripcion_feed': 'Top 10 canciones en Chile según MonitorLatino',
        'extractor_func': extractor_monitorlatino
    }





}

def main():
    parser = argparse.ArgumentParser(description="Generador de feeds RSS")
    parser.add_argument("feed", nargs="?", help="Nombre del feed a generar (opcional)")
    args = parser.parse_args()

    if args.feed:
        feed_name = args.feed.lower()
        if feed_name in FEEDS:
            config = FEEDS[feed_name]
            generar_feed_rss(**config)
        else:
            print(f"Feed desconocido: {feed_name}. Opciones válidas: {', '.join(FEEDS.keys())}")
    else:
        for name, config in FEEDS.items():
            print(f"Generando feed: {name}")
            generar_feed_rss(**config)

if __name__ == "__main__":
    main()
