##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install selenium
# pip install webdriver-manager
# pip install BeautifulSoup4
# pip install openpyxl
##############################################
import time
import os
import pandas as pd
from minio import Minio #--> O módulo minio é usado para interagir com um servidor MinIO
from minio.error import S3Error #--> O módulo S3Error é uma exceção específica do MinIO para exibição de forma semelhante ao Amazon S3
from io import StringIO, BytesIO
import psycopg2
import io
import time
start_time = time.time()
import requests


####################################
### DEFINIÇÃO DA CAMADA NO MINIO ###
####################################
DADOS_COMBUSTIVEL = '/home/thiago/tcc_ufrj/DADOS_COMBUSTIVEL/'
BUCKET_DADOS_COMBUSTIVEL = 'dados-combustivel'


##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000', #--> O cliente é configurado para se conectar a um servidor MinIO local usando as credenciais fornecidas
    access_key='minioadmin', #--> A chave de acesso = usuário
    secret_key='minioadmin', #--> A chave secreta = Senha 
    secure=False) #--> Sem usar conexão segura (HTTPS).


#############################################
### ACESSANDO O BANCO DE DADOS POSTGRESQL ###
#############################################
db_config = {
'host': 'localhost',
'database': 'postgres',
'user': 'postgres',
'password': 'postgres',
}


############################################################################################################
### CRIAÇÃO DAS TABELAS [preco_combustivel_semanal] - [tb_consumo_veiculos] NO BANCO DE DADOS POSTGRESQL ###
############################################################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

create_preco_combustivel_semanal = '''
CREATE TABLE IF NOT EXISTS public.preco_combustivel_semanal (
	data_inicial text NULL,
	data_final text NULL,
	estado text NULL,
	municipio text NULL,
	produto text NULL,
	numero_de_postos_pesquisados text NULL,
	unidade_de_medida text NULL,
	preco_medio_revenda text NULL,
	desvio_padrao_revenda text NULL,
	preco_minimo_revenda text NULL,
	preco_maximo_revenda text NULL,
	coef_de_variacao_revenda text NULL
);'''
cursor.execute(create_preco_combustivel_semanal)
conn.commit()

create_tb_consumo_veiculos = '''
CREATE TABLE IF NOT EXISTS public.tb_consumo_veiculos (
	classe text NULL,
	cylinders text NULL,
	displacement text NULL,
	drive text NULL,
	fuel_type text NULL,
	make text NULL,
	model text NULL,
	transmission text NULL,
	"year" text NULL,
	city_km_l text NULL,
	highway_km_l text NULL
);'''

cursor.execute(create_tb_consumo_veiculos)
conn.commit()

conn.close()


##################################
### CONVERSÃO DO xlsx para CSV ###
##################################
## Transformando o xlsx em um Pandas DataFrame 
arquivos_combustivel = [arquivo for arquivo in os.listdir(DADOS_COMBUSTIVEL) if arquivo.endswith(".xlsx")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .gpx
for arquivo_combustivel in arquivos_combustivel:
    caminho_arquivo = os.path.join(DADOS_COMBUSTIVEL, arquivo_combustivel) #--> Criando o caminho completo para o arquivo .gpx        
    df = pd.read_excel(caminho_arquivo, sheet_name='CAPITAIS', skiprows=9)
    df.to_csv(f'{DADOS_COMBUSTIVEL}PRECO_NACIONAL.csv', sep=';', encoding='utf8', index=False)


######################################################
### ENVIANDO CSV PARA O BUCKET [DADOS_COMBUSTIVEL] ###
######################################################
time.sleep(5)
arquivos_para_datalake = [arquivo for arquivo in os.listdir(DADOS_COMBUSTIVEL) if arquivo.endswith(".csv")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .csv
for nome_arquivo in arquivos_para_datalake: #--> Iterando sobre cada item da lista
    caminho_pre_proc = os.path.join(DADOS_COMBUSTIVEL, nome_arquivo) #--> Criando o caminho completo para o arquivo .csv    
    if os.path.isfile(caminho_pre_proc): #--> Verificando se o caminho especificado está apontando para um arquivo válido no sistema de arquivos.
        try:
            minioclient.fput_object(BUCKET_DADOS_COMBUSTIVEL, nome_arquivo, caminho_pre_proc) #--> Usando o cliente Minio para enviar o arquivo da pasta de pré processamento para o bucket especificado
            #print(f"Arquivo {nome_arquivo} enviado com sucesso para o bucket.") #--> Exibindo a mensagem de sucesso após o upload dos arquivos para o bucket.
            os.remove(caminho_pre_proc) # --> Após o envio bem sucedido para o bucket o arquivo é excluído da pasta DADOS_COMBUSTIVEL
        except S3Error as e: #--> Capturando qualquer erro que porventura ocorra
            print(f"Erro ao enviar o arquivo: {nome_arquivo} -> Erro: {e}") #--> Exibindo o erro


###########################################################################################################
### CARREGANDO O ARQUIVO CSV DO BUCKET [BUCKET_DADOS_COMBUSTIVEL] NA TABELA [preco_combustivel_semanal] ###
###########################################################################################################
time.sleep(5)
try:
    # Lista todos os arquivos na camada "gold" do Minio que têm extensão .csv
    arquivos_preco_combustivel = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(BUCKET_DADOS_COMBUSTIVEL) if arquivo_gpx.object_name.endswith(".csv")]
    
    # Verifica se há arquivos no bucket antes de continuar
    if not arquivos_preco_combustivel:
        print("Não existem arquivos CSV no bucket. Nenhuma carga de dados será executada.")

    else:
        # Conexão com o banco de dados PostgreSQL
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        truncate = """ truncate table preco_combustivel_semanal; """
        cursor.execute(truncate)
        conn.commit()

        copy_sql = """
            COPY preco_combustivel_semanal (data_inicial,data_final,estado,municipio,produto,numero_de_postos_pesquisados,unidade_de_medida,preco_medio_revenda,desvio_padrao_revenda,preco_minimo_revenda,preco_maximo_revenda,coef_de_variacao_revenda)
            FROM stdin WITH CSV HEADER DELIMITER as ';'
        """

        # Itera sobre cada arquivo CSV encontrado no Minio
        for arquivo_preco_combustivel in arquivos_preco_combustivel:
            # Obtém o objeto do arquivo CSV do Minio  
            obj_preco = minioclient.get_object(BUCKET_DADOS_COMBUSTIVEL, arquivo_preco_combustivel.object_name)            

            # Decodifica os dados do arquivo CSV de bytes para string
            csv_decod = obj_preco.data.decode('utf-8')  # Convertendo bytes para string
            arquivo_csv = StringIO(csv_decod)
            df = pd.read_csv(arquivo_csv, sep=';')
            csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
            csv_buffer = BytesIO(csv_bytes)
            nome_arquivo = arquivo_preco_combustivel.object_name

            # Usa io.StringIO para criar um objeto de arquivo legível a partir da string CSV
            with io.StringIO(csv_decod) as file:        

                # Executa o comando COPY para inserir os dados no banco de dados PostgreSQL
                cursor.copy_expert(sql=copy_sql, file=file)

            ## Commit para salvar as alterações no banco de dados    
            conn.commit()

            # Após a copia para o bucket de segurança os arquivos são eliminados da camada gold
            minioclient.remove_object(BUCKET_DADOS_COMBUSTIVEL, arquivo_preco_combustivel.object_name) 

        # Fecha a conexão com o banco de dados PostgreSQL
        conn.close()

except Exception as e:
    # Em caso de erro, imprime a mensagem de erro
    print(f"Erro: {str(e)}")


######################################################################################################################################################
### CRIANDO UM DATAFRAME USANDO A TABELA [tb_gpx_full] E A API [api.api-ninjas.com/v1/cars] PARA OBTER O MODELO DOS CARROS E SEUS DEVIDOS CONSUMOS ###
######################################################################################################################################################
# Abrindo novamente a conexão com o banco para selecionar da tabela gpx full somente o nome a marca e o modelo dos veículos
time.sleep(5)
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

consulta_usuarios_gpx_full = """
select distinct
split_part(LOWER(nome_usuario),'_',1) as marca,
split_part(LOWER(nome_usuario),'_',2) as modelo
from tb_gpx_full
"""

cursor.execute(consulta_usuarios_gpx_full)
resultados_usuarios_gpx_full = cursor.fetchall()
conn.close()
df_usuarios_full = pd.DataFrame(resultados_usuarios_gpx_full, columns=[desc[0] for desc in cursor.description])
df_marcas = df_usuarios_full['marca'].tolist()
df_modelos = df_usuarios_full['modelo'].tolist()

# Consumindo a API para criar um DF com o consumo em litros por KM dos veículos
df_carros = pd.DataFrame()
api_key = '/DHg+PPb3h7gYITeEup54w==KXt6OHpmw3zMNgfE'
api_url = 'https://api.api-ninjas.com/v1/cars'

for df_marca, df_modelo in  zip(df_marcas, df_modelos):
    params = {'make': df_marca, 'model': df_modelo}
    headers = {'X-Api-Key': api_key}
    response = requests.get(api_url, params=params, headers=headers)
        
    if response.status_code == requests.codes.ok:            
        data = response.json()
        df_car = pd.DataFrame(data)
        df_carros = pd.concat([df_carros, df_car], ignore_index=True)
    else:
        print("Error:", response.status_code, response.text)

# Convertendo Galão por Milha em Litro por KM
df_carros['city_km/l'] = (df_carros['city_mpg'] * 1.609344) / 3.785411784
df_carros['highway_km/l'] = (df_carros['highway_mpg'] * 1.609344) / 3.785411784
df_carros.drop('city_mpg', axis=1, inplace=True)
df_carros.drop('highway_mpg', axis=1, inplace=True)
df_carros.drop('combination_mpg', axis=1, inplace=True)
df_carros.to_csv(f'{DADOS_COMBUSTIVEL}consumo_veiculos.csv', sep=';', encoding='utf8', index=False)


#######################################################################################################################################
### ENVIANDO O CSV GERADO DA UNIÃO DA TABELA [tb_gpx_full] COM A API [api.api-ninjas.com/v1/cars] PARA O BUCKET [DADOS_COMBUSTIVEL] ### 
#######################################################################################################################################
## Enviando CSV para o Datalake
time.sleep(5)
arquivos_para_datalake = [arquivo for arquivo in os.listdir(DADOS_COMBUSTIVEL) if arquivo.endswith(".csv")] #--> Listando todos os arquivos da pasta pré-processamento com extensão .csv
for nome_arquivo in arquivos_para_datalake: #--> Iterando sobre cada item da lista
    caminho_pre_proc = os.path.join(DADOS_COMBUSTIVEL, nome_arquivo) #--> Criando o caminho completo para o arquivo .csv    
    if os.path.isfile(caminho_pre_proc): #--> Verificando se o caminho especificado está apontando para um arquivo válido no sistema de arquivos.
        try:
            minioclient.fput_object(BUCKET_DADOS_COMBUSTIVEL, nome_arquivo, caminho_pre_proc) #--> Usando o cliente Minio para enviar o arquivo da pasta de pré processamento para o bucket especificado (CAMADA_BRONZE)
            os.remove(caminho_pre_proc) # --> Após o envio bem sucedido para o bucket o arquivo é excluído da pasta DADOS_COMBUSTIVEL
        except S3Error as e: #--> Capturando qualquer erro que porventura ocorra
            print(f"Erro ao enviar o arquivo: {nome_arquivo} -> Erro: {e}") #--> Exibindo o erro


###################################################################################################
### ESCREVENDO O CSV FINAL DO BUCKET [BUCKET_DADOS_COMBUSTIVEL] NA TABELA [tb_consumo_veiculos] ###
###################################################################################################
## Conexão e escrita no banco de dados do arquivo CSV obtido do Bucket
time.sleep(5)
try:
    # Lista todos os arquivos na camada "gold" do Minio que têm extensão .csv
    arquivo_consumo_veiculos = [arquivo for arquivo in minioclient.list_objects(BUCKET_DADOS_COMBUSTIVEL) if arquivo.object_name.endswith(".csv")]
    
    # Verifica se há arquivos no bucket antes de continuar
    if not arquivo_consumo_veiculos:
        print("Não existem arquivos CSV no bucket. Nenhuma carga de dados será executada.")

    else:
        # Conexão com o banco de dados PostgreSQL
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        truncate = """ truncate table tb_consumo_veiculos; """
        cursor.execute(truncate)

        # copy_sql = """
        #     COPY tb_consumo_veiculos (classe, cylinders, displacement, drive, fuel_type, make, model, transmission, year, city_km_l, highway_km_l)
        #     FROM stdin WITH CSV HEADER DELIMITER as ';'
        # """

        # Itera sobre cada arquivo CSV encontrado no Minio
        for arquivo_consumo_veiculo in arquivo_consumo_veiculos:
            # Obtém o objeto do arquivo CSV do Minio  
            obj_preco = minioclient.get_object(BUCKET_DADOS_COMBUSTIVEL, arquivo_consumo_veiculo.object_name)            

            # Decodifica os dados do arquivo CSV de bytes para string
            csv_decod = obj_preco.data.decode('utf-8')  # Convertendo bytes para string
            arquivo_csv = StringIO(csv_decod)
            df = pd.read_csv(arquivo_csv, sep=';')
            csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
            csv_buffer = BytesIO(csv_bytes)
            nome_arquivo = arquivo_consumo_veiculo.object_name

            for i in range(len(df)):
                classe = df['class'].iloc[i]
                cylinders = df['cylinders'].iloc[i]
                displacement = df['displacement'].iloc[i]
                drive = df['drive'].iloc[i]
                fuel_type = df['fuel_type'].iloc[i]
                make = df['make'].iloc[i]
                model = df['model'].iloc[i]
                transmission = df['transmission'].iloc[i]
                year = df['year'].iloc[i]
                city_km_l = df['city_km/l'].iloc[i]
                highway_km_l = df['highway_km/l'].iloc[i]

                insert = f'''
                    insert into tb_consumo_veiculos (classe,cylinders,displacement,drive,fuel_type,make,model,transmission,"year",city_km_l,highway_km_l)
                    values (
                    '{classe}',
                    '{cylinders}',
                    '{displacement}',
                    '{drive}',
                    '{fuel_type}',
                    '{make}',
                    '{model}',
                    '{transmission}',
                    '{year}',
                    '{city_km_l}',
                    '{highway_km_l}'
                    )'''
                cursor.execute(insert)

            # Usa io.StringIO para criar um objeto de arquivo legível a partir da string CSV
            # with io.StringIO(csv_decod) as file:        

                # Executa o comando COPY para inserir os dados no banco de dados PostgreSQL
                # cursor.copy_expert(sql=copy_sql, file=file)

            ## Commit para salvar as alterações no banco de dados    
            conn.commit()             

        # Fecha a conexão com o banco de dados PostgreSQL
        conn.close()
        
        # Após a copia para o bucket de segurança os arquivos são eliminados da camada gold
        minioclient.remove_object(BUCKET_DADOS_COMBUSTIVEL, arquivo_consumo_veiculo.object_name)

except Exception as e:
    # Em caso de erro, imprime a mensagem de erro
    print(f"Erro: {str(e)}")


###########################################################
### CALCULANDO O TEMPO DE EXECUÇÃO DO SCRIPT (OPCIONAL) ###
###########################################################
# end_time = time.time()
# execution_time = end_time - start_time

# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)

# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")