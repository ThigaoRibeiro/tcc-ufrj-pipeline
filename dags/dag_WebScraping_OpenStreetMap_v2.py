'''
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import os

# Define a zona de fuso horário (substitua 'America/Sao_Paulo' pelo seu fuso horário)
tz = 'America/Sao_Paulo'

# Defina os caminhos para a pasta de downloads e pré-processamento
DOWNLOADS = '/home/thiago/Downloads/'
PRE_PROCESSAMENTO = '/home/thiago/tcc_ufrj/PRE_PROCESSAMENTO'

# Função para executar o script
def execute_script(**kwargs):
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    import time
    from bs4 import BeautifulSoup
    import re

    servico = Service(ChromeDriverManager().install())

    URL_OPEN_STREET_MAP_TRACES = 'https://www.openstreetmap.org/traces'
    PREFIXO_URL_DOWNLOAD = 'https://www.openstreetmap.org'

    navegador = webdriver.Chrome(service=servico)
    navegador.get(URL_OPEN_STREET_MAP_TRACES)
    conteudo_da_pagina = navegador.page_source
    site = BeautifulSoup(conteudo_da_pagina, 'html.parser')
    rotas = site.findAll('tr')

    lista_rotas = []

    for rota in rotas:
        if rota.find('span', attrs={'class': 'text-danger'}):
            rotas_pendentes = rota.find('span', attrs={'class': 'text-danger'})
            link_rotas_pendentes = rota.find('a')
            lista_rotas.append([PREFIXO_URL_DOWNLOAD + link_rotas_pendentes['href']])
        else:
            link_rotas_finalizadas = rota.find('a')
            lista_rotas.append([PREFIXO_URL_DOWNLOAD + link_rotas_finalizadas['href']])
    time.sleep(3)
    navegador.close()

    navegador = webdriver.Chrome(service=servico)
    usuarios = []
    for lista_rota in lista_rotas:
        time.sleep(3)
        url = lista_rota[0]
        navegador.get(url)
        conteudo_pagina_download = navegador.page_source
        pagina_usuario = BeautifulSoup(conteudo_pagina_download, 'html.parser')

        if any(td.find('span', attrs={'class': 'text-danger'}) for td in pagina_usuario):
            tb_nome_usuario = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[4]/td')
            nome_usuario = tb_nome_usuario.text
            nome_usuario = re.sub(r'\s|\.|\(|\)', '_', nome_usuario)
            navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click()
            usuarios.append(nome_usuario)
        else:
            tb_nome_usuario = navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[6]/td')
            nome_usuario = tb_nome_usuario.text
            nome_usuario = re.sub(r'\s|\.|\(|\)', '_', nome_usuario)
            navegador.find_element('xpath', '//*[@id="content"]/div[2]/div/table/tbody/tr[1]/td/a').click()
            usuarios.append(nome_usuario)
    time.sleep(5)
    navegador.close()

    arquivos_para_renomear = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")]
    for arquivo_para_renomear in arquivos_para_renomear:
        novo_nome = arquivo_para_renomear.replace(".crdownload", "")
        os.rename(os.path.join(DOWNLOADS, arquivo_para_renomear), os.path.join(DOWNLOADS, novo_nome))

    arquivos_para_renomear_gpx = sorted([arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")], reverse=True)
    for usuario, arquivo_para_renomear_gpx in zip(usuarios, arquivos_para_renomear_gpx):
        caminho_antigo = os.path.join(DOWNLOADS, arquivo_para_renomear_gpx)
        novo_nome = f"{arquivo_para_renomear_gpx.replace('.gpx', '')}__{usuario}.gpx"
        caminho_novo = os.path.join(DOWNLOADS, novo_nome)
        os.rename(caminho_antigo, caminho_novo)
    time.sleep(3)

    arquivos_para_pre_processamento = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".gpx")]
    for arquivo_para_pre_processamento in arquivos_para_pre_processamento:
        caminho_origem = os.path.join(DOWNLOADS, arquivo_para_pre_processamento)
        caminho_destino = os.path.join(PRE_PROCESSAMENTO, arquivo_para_pre_processamento)
        try:
            os.rename(caminho_origem, caminho_destino)
        except Exception as e:
            print(f"Erro ao mover o arquivo: '{arquivo_para_pre_processamento}': {e}.")

# Define a DAG com a expressão cron para executar a cada 5 minutos
dag = DAG(
    'exec-web-scraping',
    default_args={
        'owner': 'thiago',
        'start_date': datetime(2023, 9, 4, tzinfo=pytz.timezone(tz)),  # Adicione tzinfo aqui
        'retries': 1,
    },
    schedule_interval='*/5 * * * *',  # Expressão cron para cada 5 minutos
)

# Crie uma tarefa para executar o script
executar_script_task = PythonOperator(
    task_id='executar_meu_script',
    python_callable=execute_script,
    provide_context=True,
    dag=dag,
)
'''