# pip install selenium
# pip install webdriver-manager
# pip install BeautifulSoup4

from selenium import webdriver # Importa o módulo do Selenium de automação de navegador.
from webdriver_manager.chrome import ChromeDriverManager # Importa o gerenciador de driver para o Chrome.
from selenium.webdriver.chrome.service import Service # Importa o serviço do driver do Chrome.
import time # Função de tempo. Utilizo o módulo sleep para pausar o código temporariamente.
from bs4 import BeautifulSoup # Importa o Beautiful Soup para analisar HTML.
servico = Service(ChromeDriverManager().install()) # Configura o serviço do driver do Chrome.
import re # Importa o módulo re para expressões regulares.
import os # Importa o módulo os para funcionalidades relacionadas ao sistema operacional.

URL_OPEN_STREET_MAP_TRACES = 'https://www.openstreetmap.org/traces' # URL principal onde será feita a raspagem dos dados com o intuito de listar todas as rotas para download.
PREFIX_URL_DOWNLOAD = 'https://www.openstreetmap.org' # URL que será usada como prefixo para montar as URLs das páginas de download.
DOWNLOADS = '/home/thiago/Downloads/' # Caminho para a pasta de downloads.
PRE_PROCESSING = '/home/thiago/tcc_ufrj/PRE_PROCESSING' # Caminho para a pasta de pré-processamento dos dados.

#######################################
### LISTANDO AS ROTAS PARA DOWNLOAD ###
#######################################
navegador = webdriver.Chrome(service=servico) # Inicializa o navegador Chrome usando o serviço configurado. 
navegador.get(URL_OPEN_STREET_MAP_TRACES) # Acessa a página URL_OPEN_STREET_MAP_TRACES usando o navegador.

page_content = navegador.page_source # Obtém o conteúdo HTML da página.
site = BeautifulSoup(page_content, 'html.parser') # Cria um objeto BeautifulSoup a fim de analisar o conteúdo HTML obtido da página acima.
routes = site.findAll('tr') # Encontra na página todas as linhas das tabelas que possuem dados de rotas. Após essa localização as rotas localizadas são transformadas em uma lista.

list_routes = [] # Inicializa uma lista para armazenar informações de todas as rotas

for route in routes: # Itera pela lista das rotas localizadas através das linhas das tabelas da página.    
    if route.find('span', attrs={'class': 'text-danger'}): # Se a rota estiver pendente, o link é localizado e adicionado à lista de rotas.   
        pending_routes = route.find('span', attrs={'class': 'text-danger'})    
        pending_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+pending_link_routes['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
    else:         
        finished_link_routes = route.find('a')        
        list_routes.append([PREFIX_URL_DOWNLOAD+finished_link_routes['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
time.sleep(3) # Adicionado um time de 3 segundos antes de fechar o navegador.
navegador.close() # Fechando o navegador.

####################################
### FAZENDO O DOWNLOAD DAS ROTAS ###
####################################
navegador = webdriver.Chrome(service=servico) # Aqui abrimos novamente o navegador para fazer o download dos arquivos com as rotas.
users = [] # Criando uma lista para capturar o nome dos usuários que fizeram as rotas
for list_route in list_routes: # Itera pelas rotas na lista de rotas obtidas no for acima.
    time.sleep(3) # Pausa de 3 segundos para que dê tempo do navegador renderizar a tela, a fim de se obter o link e o Selenium efetuar o clique, fazendo o download do arquivo.
    url = list_route[0] # Obter a URL da página onde o link de download do arquivo está.
    navegador.get(url) # Acessa a URL com o Selenium #--> Exemplo onde usamos o Selenium somente com o [.get]

    user_page_content = navegador.page_source # Obtendo o conteúdo HTML da página de download.
    site_user = BeautifulSoup(user_page_content, 'html.parser') # Criando um objeto BeautifulSoup a fim de analisar o conteúdo HTML obtido da página acima.

    if any(td.find('span', attrs={'class': 'text-danger'}) for td in site_user): # Em caso de rodas pendentes o xpath com o nome do usuário muda de posição. Por isso essa abordagem.
        tb_user_name = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[4]/td') # Encontrando o nome do usuário quando a rota ainda está pendente.
        user_name = tb_user_name.text
        user_name = re.sub(r'\s|\.|\(|\)','_',user_name) # Usando Regex para ajustar o nome do usuário de modo que fique de facil entendimento ao renomear o arquivo
        navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click() # Capturando o 'xpath' do elemento que possui o link para download e efetuamos efetivamente o clique. O download do arquivo.gpx com o conteúdo da rota é feito na pasta Download.
        users.append(user_name) # Adicionando o nome do usuário em uma na lista

    else: # Encontrando o nome do usuário quando a rota está finalizada.
        tb_user_name = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[6]/td') # Encontrando o nome do usuário quando a rota está finalizada.
        user_name = tb_user_name.text
        user_name = re.sub(r'\s|\.|\(|\)','_',user_name) # Usando Regex para ajustar o nome do usuário de modo que fique de facil entendimento ao renomear o arquivo
        navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click() # Capturando o 'xpath' do elemento que possui o link para download e efetuamos efetivamente o clique. O download do arquivo.gpx com o conteúdo da rota é feito na pasta Download.
        users.append(user_name) # Adicionando o nome do usuário em uma na lista
time.sleep(3) # Adicionado um time de 3 segundos antes de fechar o navegador. Dessa forma garantimos que qualquer download finalize com sucesso.
navegador.close() # Fechando o navegador.

#########################################################################
### RENOMEANDO OS ARQUIVOS BAIXADOS ACRESCENTANDO O NOME DOS USUÁRIOS ###
#########################################################################
files_to_rename = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")] # Listando arquivos com extensão incorreta [.crdownload] na pasta de download.
for file_name in files_to_rename: # Iterando sobre os resultados encontrados.
        new_name = file_name.replace(".crdownload", "") # Removendo a extensão incorreta do nome do arquivo.
        os.rename(os.path.join(DOWNLOADS, file_name), os.path.join(DOWNLOADS, new_name)) # Substituindo os arquivos com a extensão incorreta pelos arquivos corrigidos.

files_to_rename_gpx = sorted([arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")], reverse=True) # Listando arquivos com extensão [.gpx] na pasta de download.
for user, file_to_rename_gpx in zip(users, files_to_rename_gpx): # Iterando sobre a lista de arquivos na pasta download e sobre a lista com o nome dos usuários.     
    old_path = os.path.join(DOWNLOADS, file_to_rename_gpx) # Montando o caminho absoluto da pasta download + arquivo
    new_name = f"{file_to_rename_gpx.replace('.gpx', '')}__{user}.gpx" # Montando o novo nome do arquivo
    new_path = os.path.join(DOWNLOADS,new_name) # Montando o novo caminho absoluto da pasta download + arquivo renomeado
    os.rename(old_path, new_path) # Efetivando a renomeação do arquivo antigo pelo novo
time.sleep(3) # Adicionando uma pausa de 3 segundos.

##########################################################################################
### MOVENDO OS ARQUIVOS RENOMEADOS DA PASTA DOWNLOAD PARA A PASTA DE PRÉ PROCESSAMENTO ###
##########################################################################################
files_to_move_pre_processing = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")] # Listando arquivos com extensão [.gpx] (agora renomeados) na pasta de download.
for file_to_move_pre_processing in files_to_move_pre_processing: # Iterando sobre a lista de arquivos na pasta download que serão movidos para a pasta de pré-processamento.
    src_path = os.path.join(DOWNLOADS, file_to_move_pre_processing) # Montando o caminho absoluto da pasta de origem dos arquivos (download + arquivo)
    dest_path = os.path.join(PRE_PROCESSING, file_to_move_pre_processing) # Montando o caminho absoluto da pasta de destino dos arquivos (PRE_PROCESSING + arquivo)
    try: # Adicionado tratamento de erro para caso não seja possivel a transferencia
        os.rename(src_path,dest_path) # Efetivando a transferencia do arquivo da pasta de download para a pasta PRE_PROCESSING
    except Exception as e:
        print(f"Erro ao mover o arquivo: '{file_to_move_pre_processing}': {e}.")