from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from time import sleep
from bs4 import BeautifulSoup
servico = Service(ChromeDriverManager().install())


URL_OPEN_STREET_MAP_TRACES = 'https://www.openstreetmap.org/traces' #--> Página do OpenstreetMap onde estão localizadas as rotas para download.
PREFIX_URL_DOWNLOAD = 'https://www.openstreetmap.org' #--> Página do principal do OpenstreetMap. Esta variável será utilizada para montar a URL das páginas de download.


navegador = webdriver.Chrome(service=servico)
navegador.get(URL_OPEN_STREET_MAP_TRACES)


page_content = navegador.page_source
site = BeautifulSoup(page_content, 'html.parser')
routes = site.findAll('tr')


list_pending_routes = []
list_finished_routes = []
list_routes = []


for route in routes:
    if route.find('span', attrs={'class': 'text-danger'}):
        pending_routes = route.find('span', attrs={'class': 'text-danger'})    
        pending_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+pending_link_routes['href']])
        # list_pending_routes.append([PREFIX_URL_DOWNLOAD+pending_link_routes['href']])
        print (f"{pending_routes.text}: {PREFIX_URL_DOWNLOAD+pending_link_routes['href']}")

    else:         
        finished_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+finished_link_routes['href']])
        # list_finished_routes.append([PREFIX_URL_DOWNLOAD+finished_link_routes['href']])
        print(f"FINISHED: {PREFIX_URL_DOWNLOAD+finished_link_routes['href']}")


## Quando usa [requests.get] estamos usando o BeautifulSoup - e quando usamos só o [.get] estamos usando o selenium
for list_route in list_routes:
    sleep(5)
    url = list_route[0]
    navegador.get(url)  #--> Exemplo onde usamos o Selenium somente com o [.get]
    navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click()
navegador.close()