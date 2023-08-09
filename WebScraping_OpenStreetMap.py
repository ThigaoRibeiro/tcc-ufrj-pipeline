from selenium import webdriver # Importa o módulo do Selenium de automação de navegador.
from webdriver_manager.chrome import ChromeDriverManager # Importa o gerenciador de driver para o Chrome.
from selenium.webdriver.chrome.service import Service # Importa o serviço do driver do Chrome.
from time import sleep # Importa a função sleep para pausar o código temporariamente.
from bs4 import BeautifulSoup # Importa o Beautiful Soup para analisar HTML.
servico = Service(ChromeDriverManager().install()) # Configura o serviço do driver do Chrome.


URL_OPEN_STREET_MAP_TRACES = 'https://www.openstreetmap.org/traces' # [URL_OPEN_STREET_MAP_TRACES] = URL principal onde será feita a raspagem dos dados com o intuito de listar todas as rotas para download.
PREFIX_URL_DOWNLOAD = 'https://www.openstreetmap.org' # [PREFIX_URL_DOWNLOAD] = URL que será usada como prefixo para montar as URLs das páginas de download.

navegador = webdriver.Chrome(service=servico) # Inicializa o navegador Chrome usando o serviço configurado. 
navegador.get(URL_OPEN_STREET_MAP_TRACES) # Acessa a página URL_OPEN_STREET_MAP_TRACES usando o navegador.


page_content = navegador.page_source # Obtém o conteúdo HTML da página.
site = BeautifulSoup(page_content, 'html.parser') # Cria um objeto BeautifulSoup a fim de analisar o conteúdo HTML obtido da página acima.
routes = site.findAll('tr') # Encontra na na página todas as linhas das tabelas que possuem dados de rotas. Após essa localização as rotas localizadas são transformadas em uma lista.

# list_pending_routes = [] # Inicializa uma lista para armazenar informações somente das rotas pendentes (Não utilizada por enquanto).
# list_finished_routes = [] # Inicializa uma lista para armazenar informações somente das rotas finalizadas (Não utilizada por enquanto).
list_routes = [] # Inicializa uma lista para armazenar informações de todas as rotas

for route in routes: # Itera pela lista das rotas localizadas através das linhas das tabelas da página.    
    if route.find('span', attrs={'class': 'text-danger'}): # Se a rota estiver pendente, o link é localizado e adicionado à lista de rotas.
        pending_routes = route.find('span', attrs={'class': 'text-danger'})    
        pending_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+pending_link_routes['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
        # list_pending_routes.append([PREFIX_URL_DOWNLOAD+pending_link_routes['href']]) # Esse trecho constrói a URL para download apenas das rotas pendentes.
    
    else: # Se a rota estiver finalizada, encontrar o link e adicioná-lo à lista de rotas    
        finished_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+finished_link_routes['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
        # list_finished_routes.append([PREFIX_URL_DOWNLOAD+finished_link_routes['href']]) # Esse trecho constrói a URL para download apenas das rotas finalizadas.

## Obs.: Quando usamos [requests.get] estamos usando o BeautifulSoup - e quando usamos o [.get] estamos usando o Selenium.

for list_route in list_routes: # Itera pelas rotas na lista de rotas obtidas no for acima.
    sleep(3) # Pausar por 3 segundos para que dê tempo do navegador renderizar a tela, a fim de se obter o link e o Selenium efetuar o clique, fazendo o download do arquivo.
    url = list_route[0] # Obter a URL da página onde o link de download do arquivo está.
    navegador.get(url)  # Acessa a URL com o Selenium #--> Exemplo onde usamos o Selenium somente com o [.get]
    
    # Exemplo onde usamos o Selenium para clicar em um elemento específico na página
    navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click() # Capturamos o 'xpath' do elemento que possui o link para download e efetuamos efetivamente o clique. O download do arquivo.gpx com o conteúdo da rota é feito na pasta Download.
navegador.close() # Fecha o navegador após a conclusão das operações.




