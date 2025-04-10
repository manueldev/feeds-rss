import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, UTC
import argparse
import re




def generar_feed_rss(nombre_archivo, url, titulo_feed, descripcion_feed, extractor_func):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')

    fg = FeedGenerator()
    fg.title(titulo_feed)
    fg.link(href=url)
    fg.description(descripcion_feed)

    items = extractor_func(soup)

    for item in items:
        fe = fg.add_entry()
        fe.title(item['title'])
        fe.link(href=item['link'])
        fe.pubDate(item['pub_date'])

    fg.rss_file(nombre_archivo)
    print(f"RSS generado: {nombre_archivo}")

# --------- Extractor para Radioactiva ---------
def extractor_radioactiva(soup):
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

            try:
                pub_date = datetime.strptime(raw_date, '%d %B, %Y').replace(tzinfo=timezone.utc)
            except ValueError:
                pub_date = datetime.now(UTC)

            items.append({
                'title': title,
                'link': link,
                'pub_date': pub_date
            })

    return items

# --------- Extractor para Los40 ---------
def extractor_los40(soup):
    items = []

    # Buscar bloques de <script> que contengan "songTitle" en formato texto plano
    scripts = soup.find_all('script', string=re.compile('songTitle'))

    for script in scripts:
        try:
            # Extraer el texto de cada <script> y buscar las ocurrencias
            data_text = script.string.strip()

            # Buscar todas las ocurrencias de songTitle, artistName y youtubeUrl
            pattern = re.compile(r'"songTitle":"(.*?)".*?"artistName":"(.*?)".*?"youtubeUrl":"(https://www\.youtube\.com/watch\?v=[\w-]+)"')
            matches = pattern.findall(data_text)

            # Para cada coincidencia, agregarla a la lista de items
            for match in matches:
                song_title = match[0].strip()
                artist_name = match[1].strip()
                youtube_url = match[2].strip()

                title = f"{artist_name} – {song_title}"
                link = youtube_url
                pub_date = datetime.now(UTC)

                items.append({
                    'title': title,
                    'link': link,
                    'pub_date': pub_date
                })

        except Exception as e:
            print(f"Error procesando script: {e}")
            continue

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
