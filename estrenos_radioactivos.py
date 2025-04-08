import requests
from bs4 import BeautifulSoup
import datetime
from feedgen.feed import FeedGenerator

url = "https://www.radioactiva.cl/?s=Estrenos+RadioActivos"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

fg = FeedGenerator()
fg.title('Resultados de búsqueda: Estrenos Radioactivos')
fg.link(href=url)
fg.description('Feed generado automáticamente desde los resultados de búsqueda de Radioactiva.')

articles = soup.select('article')

for article in articles:
    title_tag = article.select_one('h2 a')
    if title_tag:
        title = title_tag.text.strip()
        link = title_tag['href']
        pub_date = datetime.datetime.utcnow()
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.pubDate(pub_date)

fg.rss_file('estrenos_radioactivos.xml')
