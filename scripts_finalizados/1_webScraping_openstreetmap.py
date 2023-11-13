###############################################
#### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
###############################################
## pip install selenium
## pip install webdriver-manager
## pip install BeautifulSoup4
#
from selenium import webdriver # Importa o módulo do Selenium de automação de navegador.
from webdriver_manager.chrome import ChromeDriverManager # Importa o gerenciador de driver para o Chrome.
from selenium.webdriver.chrome.service import Service # Importa o serviço do driver do Chrome.
import time # Função de tempo. Utilizo o módulo sleep para pausar o código temporariamente.
from bs4 import BeautifulSoup # Importa o Beautiful Soup para analisar HTML.
servico = Service(ChromeDriverManager().install()) # Configura o serviço do driver do Chrome.
import re # Importa o módulo re para expressões regulares.
import os # Importa o módulo os para funcionalidades relacionadas ao sistema operacional.

# import time
# start_time = time.time()


URL_OPEN_STREET_MAP_TRACES = 'https://www.openstreetmap.org/traces' # URL principal onde será feita a raspagem dos dados com o intuito de listar todas as rotas para download.
PREFIXO_URL_DOWNLOAD = 'https://www.openstreetmap.org' # URL que será usada como prefixo para montar as URLs das páginas de download.
DOWNLOADS = '/home/thiago/Downloads/' # Caminho para a pasta de downloads.
PRE_PROCESSAMENTO = '/home/thiago/tcc_ufrj/PRE_PROCESSAMENTO' # Caminho para a pasta de pré-processamento dos dados.

#######################################
### LISTANDO AS ROTAS PARA DOWNLOAD ###
#######################################
navegador = webdriver.Chrome(service=servico) # Inicializa o navegador Chrome usando o serviço configurado. 
navegador.get(URL_OPEN_STREET_MAP_TRACES) # Acessa a página URL_OPEN_STREET_MAP_TRACES usando o navegador.

conteudo_da_pagina = navegador.page_source # Obtém o conteúdo HTML da página.
site = BeautifulSoup(conteudo_da_pagina, 'html.parser') # Cria um objeto BeautifulSoup a fim de analisar o conteúdo HTML obtido da página acima.
rotas = site.findAll('tr') # Encontra na página todas as linhas das tabelas que possuem dados de rotas. Após essa localização as rotas localizadas são transformadas em uma lista.

lista_rotas = [] # Inicializa uma lista para armazenar informações de todas as rotas

for rota in rotas: # Itera pela lista das rotas localizadas através das linhas das tabelas da página.    
    if rota.find('span', attrs={'class': 'text-danger'}): # Se a rota estiver pendente, o link é localizado e adicionado à lista de rotas.   
        rotas_pendentes = rota.find('span', attrs={'class': 'text-danger'})    
        link_rotas_pendentes = rota.find('a')        
        lista_rotas.append([PREFIXO_URL_DOWNLOAD+link_rotas_pendentes['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
    else:         
        link_rotas_finalizadas = rota.find('a')        
        lista_rotas.append([PREFIXO_URL_DOWNLOAD+link_rotas_finalizadas['href']]) # Aqui é construída a URL final onde será possivel fazer o download do arquivo [.gpx]. Note que a URL de prefix é utilizada e o link é obtido através da tag 'a' e seu atributo 'href'.
time.sleep(3) # Adicionado um time de 3 segundos antes de fechar o navegador.
navegador.close() # Fechando o navegador.

####################################
### FAZENDO O DOWNLOAD DAS ROTAS ###
####################################
navegador = webdriver.Chrome(service=servico) # Aqui abrimos novamente o navegador para fazer o download dos arquivos com as rotas.
usuarios = [] # Criando uma lista para capturar o nome dos usuários que fizeram as rotas
for lista_rota in lista_rotas: # Itera pelas rotas na lista de rotas obtidas no for acima.
    time.sleep(3) # Pausa de 3 segundos para que dê tempo do navegador renderizar a tela, a fim de se obter o link e o Selenium efetuar o clique, fazendo o download do arquivo.
    url = lista_rota[0] # Obter a URL da página onde o link de download do arquivo está.
    navegador.get(url) # Acessa a URL com o Selenium #--> Exemplo onde usamos o Selenium somente com o [.get]

    conteudo_pagina_download = navegador.page_source # Obtendo o conteúdo HTML da página de download.
    pagina_usuario = BeautifulSoup(conteudo_pagina_download, 'html.parser') # Criando um objeto BeautifulSoup a fim de analisar o conteúdo HTML obtido da página acima.

    if any(td.find('span', attrs={'class': 'text-danger'}) for td in pagina_usuario): # Em caso de rodas pendentes o xpath com o nome do usuário muda de posição. Por isso essa abordagem.
        tb_nome_usuario = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[4]/td') # Encontrando o nome do usuário quando a rota ainda está pendente.
        nome_usuario = tb_nome_usuario.text
        nome_usuario = re.sub(r'\s|\.|\(|\)','_',nome_usuario) # Usando Regex para ajustar o nome do usuário de modo que fique de facil entendimento ao renomear o arquivo
        navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click() # Capturando o 'xpath' do elemento que possui o link para download e efetuamos efetivamente o clique. O download do arquivo.gpx com o conteúdo da rota é feito na pasta Download.
        usuarios.append(nome_usuario) # Adicionando o nome do usuário em uma na lista

    else: # Encontrando o nome do usuário quando a rota está finalizada.
        tb_nome_usuario = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[6]/td') # Encontrando o nome do usuário quando a rota está finalizada.
        nome_usuario = tb_nome_usuario.text
        nome_usuario = re.sub(r'\s|\.|\(|\)','_',nome_usuario) # Usando Regex para ajustar o nome do usuário de modo que fique de facil entendimento ao renomear o arquivo
        navegador.find_element('xpath','//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click() # Capturando o 'xpath' do elemento que possui o link para download e efetuamos efetivamente o clique. O download do arquivo.gpx com o conteúdo da rota é feito na pasta Download.
        usuarios.append(nome_usuario) # Adicionando o nome do usuário em uma na lista
time.sleep(5) # Adicionado um time de 5 segundos antes de fechar o navegador. Dessa forma tentamos garantir que os downloads finalizem com sucesso.
navegador.close() # Fechando o navegador.

#########################################################################
### RENOMEANDO OS ARQUIVOS BAIXADOS ACRESCENTANDO O NOME DOS USUÁRIOS ###
#########################################################################
arquivos_para_renomear = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")] # Listando arquivos com extensão incorreta [.crdownload] na pasta de download.
for arquivo_para_renomear in arquivos_para_renomear: # Iterando sobre os resultados encontrados.
        novo_nome = arquivo_para_renomear.replace(".crdownload", "") # Removendo a extensão incorreta do nome do arquivo.
        os.rename(os.path.join(DOWNLOADS, arquivo_para_renomear), os.path.join(DOWNLOADS, novo_nome)) # Substituindo os arquivos com a extensão incorreta pelos arquivos corrigidos.

arquivos_para_renomear_gpx = sorted([arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")], reverse=True) # Listando arquivos com extensão [.gpx] na pasta de download.
for usuario, arquivo_para_renomear_gpx in zip(usuarios, arquivos_para_renomear_gpx): # Iterando sobre a lista de arquivos na pasta download e sobre a lista com o nome dos usuários.         
    caminho_antigo = os.path.join(DOWNLOADS, arquivo_para_renomear_gpx) # Montando o caminho absoluto da pasta download + arquivo
    novo_nome = f"{arquivo_para_renomear_gpx.replace('.gpx', '')}__{usuario}.gpx" # Montando o novo nome do arquivo. Forçando que o nome do usuário esteja sempre entre "__"
    caminho_novo = os.path.join(DOWNLOADS,novo_nome) # Montando o novo caminho absoluto da pasta download + arquivo renomeado
    os.rename(caminho_antigo, caminho_novo) # Efetivando a renomeação do arquivo antigo pelo novo
time.sleep(3) # Adicionando uma pausa de 3 segundos.

##########################################################################################
### MOVENDO OS ARQUIVOS RENOMEADOS DA PASTA DOWNLOAD PARA A PASTA DE PRÉ PROCESSAMENTO ###
##########################################################################################
arquivos_para_pre_processamento = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")] # Listando arquivos com extensão [.gpx] (agora renomeados) na pasta de download.
for arquivo_para_pre_processamento in arquivos_para_pre_processamento: # Iterando sobre a lista de arquivos na pasta download que serão movidos para a pasta de pré-processamento.
    caminho_origem = os.path.join(DOWNLOADS, arquivo_para_pre_processamento) # Montando o caminho absoluto da pasta de origem dos arquivos (download + arquivo)
    caminho_destino = os.path.join(PRE_PROCESSAMENTO, arquivo_para_pre_processamento) # Montando o caminho absoluto da pasta de destino dos arquivos (PRE_PROCESSING + arquivo)
    try: # Adicionado tratamento de erro para caso não seja possivel a transferencia
        os.rename(caminho_origem,caminho_destino) # Efetivando a transferencia do arquivo da pasta de download para a pasta PRE_PROCESSING
    except Exception as e: #--> Capturando qualquer erro que porventura ocorra
        print(f"Erro ao mover o arquivo: '{arquivo_para_pre_processamento}': {e}.") #--> Exibindo o erro



# end_time = time.time()
# execution_time = end_time - start_time
# 
# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)
# 
# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")

