##############################################
### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
##############################################
# pip install minio
# pip install pandas
# pip install numpy

from minio import Minio #--> O módulo minio é usado para interagir com um servidor MinIO
from minio.error import S3Error #--> O módulo S3Error é uma exceção específica do MinIO para exibição de forma semelhante ao Amazon S3
from io import StringIO, BytesIO #--> Classes do módulo io. Usadas para criar fluxos de dados em memória que podem ser tratados como arquivos. StringIO é usado para manipular strings como arquivos, e BytesIO é usado para manipular bytes como arquivos.
import pandas as pd #--> Importação da biblioteca pandas para análise e manipulação de dados
import re #--> Biblioteca padrão de expressões regulares é usada para realizar operações de busca e manipulação de padrões em strings.
import numpy as np #--> Importação da biblioteca numpy para manipulação de dados e trabalhar com arrays

##############################
### DEFINIÇÃO DE VARIÁVEIS ### 
##############################
CAMADA_BRONZE = 'bronze' #--> CAMADA_BRONZE recebe uma string que representa uma camada no servidor MinIO.
CAMADA_SILVER = 'silver' #--> CAMADA_SILVER recebe uma string que representa uma camada no servidor MinIO.
PADRAO_REGEX = r'(.*?)__' #--> Padrão criado para separar o id da rota e o nome do usuário em variáveis.

##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000', #--> O cliente é configurado para se conectar a um servidor MinIO local usando as credenciais fornecidas
    access_key='minioadmin', #--> A chave de acesso = usuário
    secret_key='minioadmin', #--> A chave secreta = Senha 
    secure=False) #--> Sem usar conexão segura (HTTPS).

############################
### PREPARAÇÃO DOS DADOS ###
############################
arquivos_rotas_gpx_csv = [arquivo_gpx for arquivo_gpx in minioclient.list_objects(CAMADA_BRONZE) if arquivo_gpx.object_name.endswith(".csv")] #--> Listando todos os arquivos da camada bronze do datalake com extensão .csv
for arquivo_rotas_gpx_csv in arquivos_rotas_gpx_csv: #--> Iterando sobre a lista encontrada

    ### OBTENDO O ARQUIVO E O CONVERTENDO EM UM DF PANDAS ###
    obj_rota_csv = minioclient.get_object(CAMADA_BRONZE, arquivo_rotas_gpx_csv.object_name) #--> Obtendo o nome do arquivo de dentro da camada bronze
    csv_decod = obj_rota_csv.data.decode('utf-8') #--> Decodificando o arquivo encontrado para utf-8 - Essa conversão transforma os dados obtidos do arquivo no bucket em bytes
    arquivo_csv = StringIO(csv_decod) #--> Convertendo os bytes em string
    df = pd.read_csv(arquivo_csv) #--> Convertendo string para pandas dataframe

    ### SEPARANDO A INFORMAÇÃO DE DATA E HORA EM 2 COLUNAS SEPARADAS ###
    df['time_point'] = pd.to_datetime(df['time_point']) #--> Convertendo a coluna time_point em objetos de data e hora do tipo datetime 
    df['data'] = df['time_point'].dt.date #--> Extraindo apenas a parte da data da coluna time_point e atribuindo à nova coluna data.
    df['hora'] = df['time_point'].dt.strftime('%H:%M:%S') #--> Formatando a parte de hora (horas, minutos e segundos) da coluna time_point e atribuindo à nova coluna hora.
    df = df.drop(columns=['time_point']) #--> Removendo a coluna time_point do DataFrame.

    ### USANDO O REGEX PARA PEGAR O ID DA ROTA E O NOME DO USUÁRIO (DADOS PRESENTES NO NOME DO ARQUIVO) ###
    nome_arquivo = arquivo_rotas_gpx_csv.object_name #--> Pegando o nome do arquivo no bucket e salvando como uma string na variável
    padrao_encontrado = re.findall(PADRAO_REGEX, nome_arquivo) #--> Localizando os padrões definidos (pegue tudo que esteja antes de '__')
    id_rota = padrao_encontrado[0] #--> Pegando a primeira ocorrência do padrão encontrado e atribuindo à variável id_rota
    nome_usuario = padrao_encontrado[-1] #--> Pegando a última ocorrência do padrão encontrado e atribuindo à variável nome_usuario
    num_df = len(df) #--> Obtendo a quantidade de linhas presentes no dataframe
    replic_id_rota = np.tile(id_rota, num_df) #--> Criando uma matriz e repetindo os id_rota várias vezes, de acordo com o valor especificado em num_df. 
    replic_nome_usuario = np.tile(nome_usuario, num_df) #--> #--> Criando uma matriz e repetindo os nome_usuario várias vezes, de acordo com o valor especificado em num_df. 
    df['id_rota'] = replic_id_rota #--> Adicionando uma nova coluna ao dataframe com a informação "repetida" do id_rota
    df['nome_usuario'] = replic_nome_usuario #--> Adicionando uma nova coluna ao dataframe com a informação "repetida" do nome_usuario
    ordenacao_df = ['id_rota', 'nome_usuario', 'latitude', 'longitude', 'elevacao', 'data', 'hora'] #-->  Criando uma lista chamada ordenacao_df contendo os nomes das colunas do dataframe na ordem desejada.
    df = df.reindex(columns=ordenacao_df) #--> Reordenando as colunas de acordo com a ordem especificada em ordenacao_df

    try:
        csv_bytes = df.to_csv(index=False).encode('utf-8')  #--> Convertendo o dataframe(sem o indice) em bytes com a codificação utf-8
        csv_buffer = BytesIO(csv_bytes) #--> Criando um objeto (BytesIO) chamado csv_buffer a partir do comando anterior. Isso cria um buffer em memória que contém os bytes do arquivo CSV.
        minioclient.put_object( #-->Usdndo o metodo do MinIO responsável por adicionar arquivos no Bucket
                            CAMADA_SILVER, #--> Nome da camada de destino do arquivo transformado
                            nome_arquivo, #--> Nome do arquivo a ser adicionado na nova camada
                            data=csv_buffer, #--> Objeto csv_buffer que contém os bytes do arquivo CSV.
                            length=len(csv_bytes), #--> Especificando o comprimento dos bytes do arquivo CSV que você está enviando.
                            content_type='application/csv') #--> Definindo o tipo de conteúdo do arquivo como "application/csv", o que é apropriado para arquivos CSV.
        
        #minioclient.remove_object(CAMADA_BRONZE, nome_arquivo) #--> Removendo o arquivo do bucket

    except S3Error as e: #--> Capturando qualquer erro que porventura ocorra
        print(f"Erro ao enviar o arquivo: {nome_arquivo} para a [camada silver]. Erro: {e}") #--> Exibindo o erro