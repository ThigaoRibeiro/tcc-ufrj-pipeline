###############################################
#### IMPORTAÇÃO DAS BIBLIOTECAS NECESSÁRIAS ###
###############################################
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np
from minio import Minio
import io
from io import StringIO, BytesIO
import psycopg2
from datetime import datetime
data_hora_atual = datetime.now()
import time
#from time import sleep
from decimal import Decimal


##############################
### DEFINIÇÃO DE VARIÁVEIS ### 
##############################
CLUSTERING = 'clustering'
# ML_RESULTS = 'resultados-ml'
start_time = time.time()


##############################################
### CRIANDO UMA INSTÂNCIA DO CLIENTE MINIO ###
##############################################
minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)


#############################################
### ACESSANDO O BANCO DE DADOS POSTGRESQL ###
#############################################
db_config = {
'host': 'localhost',
'database': 'postgres',
'user': 'postgres',
'password': 'postgres',
}


#################################################################################
### EXCLUINDO QUALQUER ARQUIVO QUE EXISTA PREVIAMENTE NO BUCKET DE CLUSTERING ###
#################################################################################
arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
## Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_clustering in arquivos_clustering:
    # Exclui qualquer arquivo que exista no Bucket de clustering no MINIO
    nome_arquivo = arquivo_clustering.object_name    
    minioclient.remove_object(CLUSTERING, nome_arquivo)


####################################################
### CRIAÇÃO DA VIEW  [vw_distancias_percorridas] ###
####################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

create_vw_distancias_percorridas = '''
create or replace view vw_distancias_percorridas as 
with api as (
select 
	id_unico,
	nome_usuario,
	NULLIF(data_inicio_rota,'nan')::date as data_inicio_rota,
	NULLIF(data_fim_rota,'nan')::date as data_fim_rota,
	NULLIF(inicio_rota,'nan')::time as hora_inicio_rota,
	NULLIF(fim_rota,'nan')::time as hora_fim_rota,
	latitude_inicial,
	longitude_inicial,
	latitude_final,
	longitude_final,
	cidade,
	estado,
	pais,
	distancia_real_km_api	
from tb_distancias_percorridas_api )

select 
	api.id_unico,
	api.nome_usuario,
	api.data_inicio_rota,
	api.data_fim_rota,
	api.hora_inicio_rota,
	api.hora_fim_rota,
case 
	when 
		api.data_inicio_rota = api.data_fim_rota and api.hora_fim_rota > api.hora_inicio_rota then api.hora_fim_rota - api.hora_inicio_rota
	when 
		api.data_inicio_rota = api.data_fim_rota and api.hora_inicio_rota > api.hora_fim_rota then api.hora_inicio_rota - api.hora_fim_rota
	when 
		api.data_inicio_rota < api.data_fim_rota and api.hora_fim_rota > api.hora_inicio_rota then api.hora_fim_rota - api.hora_inicio_rota
	when 
		api.data_inicio_rota < api.data_fim_rota and api.hora_inicio_rota > api.hora_fim_rota then api.hora_inicio_rota - api.hora_fim_rota
end as duracao_viagem,
	api.latitude_inicial,
	api.longitude_inicial,
	api.latitude_final,
	api.longitude_final,
	api.cidade,
	api.estado,
	api.pais,
	api.distancia_real_km_api,
	dist_eucl.dist_euclidiana,
	dist_eucl.dist_manhattan,
	dist_eucl.dist_minkowski,
	dist_eucl.data_carga_banco
from api
inner join  tb_dist_euclidian_manhattan_minkowski as dist_eucl
on concat(dist_eucl.id_rota,'__',dist_eucl.nome_usuario) = api.id_unico'''
cursor.execute(create_vw_distancias_percorridas)
conn.commit()
conn.close()


############################################################
### CRIAÇÃO DA VIEW  [vw_valores_combustivel_por_viagem] ###
############################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

create_view_vw_valores_combustivel_por_viagem = '''
create or replace view vw_valores_combustivel_por_viagem as
with 
cons as (
	select 
		marca,
		modelo,
		tipo_combustivel,
		avg(media_consumo_km_l) as media_consumo_km_l
	from(
		select 
			distinct 
			make as marca,						
			split_part(model,' ', 1) as modelo,
			fuel_type as tipo_combustivel,		
			avg((city_km_l::numeric + highway_km_l::numeric) / 2) as media_consumo_km_l
		from tb_consumo_veiculos
		group by 
			make,model,fuel_type ) as tabela
	group by
		marca,modelo,tipo_combustivel),
	
val_combus as (
	select 	
		estado,	
		case 
			when split_part(produto,' ', 1) = 'GASOLINA' then 'gas' else split_part(produto,' ', 1) end as produto,
		AVG(preco_medio_revenda::numeric) as preco_medio_revenda 
	from preco_combustivel_semanal
	where estado = 'RIO DE JANEIRO'
	group by 
		estado, split_part(produto,' ', 1)),

tb_consumo as (
	select 
		dist_perco.id_unico,
		dist_perco.nome_usuario, 
		cons.tipo_combustivel,
		dist_perco.data_inicio_rota,
		dist_perco.hora_inicio_rota,	
		dist_perco.hora_fim_rota,	
		cons.media_consumo_km_l,
		dist_perco.dist_euclidiana,
		dist_perco.dist_euclidiana::numeric / cons.media_consumo_km_l::numeric as cons_por_km,
		val_combus.preco_medio_revenda,
		(dist_perco.dist_euclidiana::numeric / cons.media_consumo_km_l::numeric) * val_combus.preco_medio_revenda::numeric as custo_trajeto  
	from vw_distancias_percorridas as dist_perco	
	left join cons on split_part(LOWER(dist_perco.nome_usuario),'_',1) = cons.marca and split_part(LOWER(dist_perco.nome_usuario),'_',2) = cons.modelo
	left join val_combus on cons.tipo_combustivel = val_combus.produto
	where dist_perco.data_inicio_rota is not null)

select 
	distinct 
	tb_consumo.id_unico as id_unico,
	tb_consumo.nome_usuario as nome_usuario,
	tb_consumo.tipo_combustivel as tipo_combustivel,	
	tb_consumo.data_inicio_rota as data_rota,	
	tb_consumo.hora_inicio_rota as inicio_viagem, 	
	tb_consumo.hora_fim_rota as fim_viagem,	
	tb_consumo.media_consumo_km_l as media_consumo_km_l,
	tb_consumo.dist_euclidiana as dist_km,
	tb_consumo.cons_por_km as cons_por_km,
	tb_consumo.preco_medio_revenda as preco_medio_revenda,
	tb_consumo.custo_trajeto as custo_trajeto
from tb_consumo
where media_consumo_km_l is not null
order by dist_km desc
'''
cursor.execute(create_view_vw_valores_combustivel_por_viagem)
conn.commit()
conn.close()


##################################################
### CRIAÇÃO DA TABELA [veiculos_clusterizados] ###
##################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

create_veiculos_clusterizados = '''
CREATE TABLE IF NOT EXISTS public.veiculos_clusterizados (
	nome_usuario text NULL,
	dist_km text NULL,
	media_consumo_km_l text NULL,
	cluster_consumo text NULL,
	data_execucao text NULL);
    '''
cursor.execute(create_veiculos_clusterizados)
conn.commit()
conn.close()


#############################################
### CRIAÇÃO DA TABELA [cluster_simulacao] ###
#############################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

create_cluster_simulacao = '''
CREATE TABLE IF NOT EXISTS public.cluster_simulacao (
	nome_usuario_original text NULL,
	media_consumo_km_original text NULL,
	nome_usuario_simulado text NULL,
	media_consumo_km_l_simulado text NULL,
	dist_km_original text NULL,
	custo_viagem_original text NULL,
	custo_viagem_simulado text NULL);
    '''
cursor.execute(create_cluster_simulacao)
conn.commit()
conn.close()


##########################################################################
### CRIAÇÃO DO DATAFRAME PARA FILTRAGEM DOS DADOS PARA USO COM K-MEANS ###
##########################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

sql_query = """
select	
	nome_usuario,
	case when tipo_combustivel = 'gas' then 1 end as tipo_combustivel, 	
	dist_km,
	media_consumo_km_l, 
	case when custo_trajeto = null then avg(custo_trajeto::numeric) else custo_trajeto end as custo_trajeto  	
from vw_valores_combustivel_por_viagem
where tipo_combustivel = 'gas'
group by
	nome_usuario,
	tipo_combustivel, 	
	dist_km,
	media_consumo_km_l,
	custo_trajeto 
"""

cursor.execute(sql_query)
resultados_agrup_veiculos = cursor.fetchall()
conn.close()
df_agrup_veiculos = pd.DataFrame(resultados_agrup_veiculos, columns=[desc[0] for desc in cursor.description])


##########################################################################################################
### APLICAÇÃO DO ALGORITMO K-MEANS PARA A SEGMENTAÇÃO DOS VEÍCULOS CONFORME SUA PERFORMANCE ENERGÉTICA ###
##########################################################################################################
# Selecionando colunas relevantes
X = df_agrup_veiculos[['dist_km', 'media_consumo_km_l']]

# Normalizando os dados
scaler = StandardScaler()
X_normalized = scaler.fit_transform(X)

# Especificando o número de clusters
num_clusters = 3  

# Aplicando o K-means
kmeans = KMeans(n_clusters=num_clusters, random_state=0)
df_agrup_veiculos['cluster_consumo'] = kmeans.fit_predict(X_normalized)

# Criando um novo DataFrame com os resultados do agrupamento
df_veiculos_clusterizados = df_agrup_veiculos[['nome_usuario', 'dist_km', 'media_consumo_km_l', 'cluster_consumo']].copy()

# Adicionando informações adicionais conforme necessário
# df_resultado['informacao_adicional'] = ...

# Salvando o DataFrame resultante em um arquivo CSV ou inserindo no banco de dados
#df_veiculos_clusterizados.to_csv('resultado_agrupamento.csv', index=False)


##############################################################################
### INSERINDO O RESULTADO DO K-MEANS EM NA TABELA [veiculos_clusterizados] ###
##############################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

for i in range(len(df_veiculos_clusterizados)):
    nome_usuario = df_veiculos_clusterizados['nome_usuario'].iloc[i]
    dist_km = df_veiculos_clusterizados['dist_km'].iloc[i]
    media_consumo_km_l = df_veiculos_clusterizados['media_consumo_km_l'].iloc[i]
    cluster_consumo = df_veiculos_clusterizados['cluster_consumo'].iloc[i]

    insert_veiculos_clusterizados = f'''
    insert into veiculos_clusterizados (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo, data_execucao )
        values(
        	'{nome_usuario}',
        	'{dist_km}',
        	'{media_consumo_km_l}',
        	'{cluster_consumo}',
        	now())
    '''
    cursor.execute(insert_veiculos_clusterizados)
    conn.commit()

conn.close() 


########################################
### 1ª PARTE DE CÓDIGO NÃO UTILIZADA ###
########################################
##--------------------------------------------------------------------------------------------------##
##--------------------------------------------------------------------------------------------------##

## Calculando a média do consumo de combustível para cada cluster
#media_consumo_por_cluster = df_agrup_veiculos.groupby('cluster_consumo')['media_consumo_km_l'].mean()
## Exibindo os resultados
#for cluster, media_consumo in media_consumo_por_cluster.items():
#    print(f"\nCluster {cluster} - Média de Consumo: {media_consumo}")
#    veiculos_cluster = df_agrup_veiculos[df_agrup_veiculos['cluster_consumo'] == cluster]
#    print(veiculos_cluster[['nome_usuario', 'media_consumo_km_l']])

##--------------------------------------------------------------------------------------------------##
##--------------------------------------------------------------------------------------------------##


######################################################################
### ENVIANDO O RESULTADO DA CLUSTERIZAÇÃO PARA O BUCKET CLUSTERING ###
######################################################################
nome_arquivo = f'clustering_{data_hora_atual}.csv' #--> # Define o nome do arquivo, usando a variável 'data_hora_atual' para incluir a data e hora no nome
csv_veiculos_clusterizados_buffer = io.BytesIO() #--> # Cria um buffer de bytes usando io.BytesIO(), que permite manipular dados em memória
df_veiculos_clusterizados.to_csv(csv_veiculos_clusterizados_buffer, index=False, sep=';', encoding='utf-8') #--> # Escreve o DataFrame 'df_veiculos_clusterizados' no buffer de bytes no formato CSV
csv_veiculos_clusterizados_buffer.seek(0) #--> # Reposiciona o cursor no início do buffer de bytes ( reposiciona o cursor do buffer de bytes para o início, garantindo que os dados possam ser lidos a partir do início do buffer.)
csv_veiculos_clusterizados_bytes = csv_veiculos_clusterizados_buffer.getvalue() #--> # Obtém os bytes do buffer de bytes (Aqui, os bytes são lidos do buffer de bytes usando getvalue() e armazenados na variável csv_veiculos_clusterizados_bytes.)

minioclient.put_object(
        CLUSTERING,
        nome_arquivo,  # Use o mesmo nome de arquivo
        data=csv_veiculos_clusterizados_buffer,
        length=len(csv_veiculos_clusterizados_bytes),
        content_type='application/csv')

# Um buffer de bytes é uma área de memória reservada para armazenar uma sequência de bytes. Ele pode ser usado para manipular dados binários de forma eficiente em Python.
# Em termos simples, você pode pensar em um buffer de bytes como uma caixa na memória onde você pode colocar dados binários temporariamente. O buffer permite que você escreva dados binários nele e depois leia esses dados quando necessário.
# Em Python, a classe io.BytesIO fornece uma forma conveniente de trabalhar com buffers de bytes. Você pode escrever dados em um objeto BytesIO como se estivesse escrevendo em um arquivo, e também pode ler esses dados posteriormente. Isso é útil em situações em que você precisa manipular dados binários em memória, como quando você precisa processar ou transmitir dados sem gravá-los em disco.
# Em resumo, um buffer de bytes é uma estrutura de dados na memória que permite armazenar e manipular dados binários. Ele é frequentemente usado em Python para operações que envolvem dados binários temporários, como operações de entrada/saída em memória.


########################################
### 2ª PARTE DE CÓDIGO NÃO UTILIZADA ###
########################################

# ## Converta o DataFrame enriquecido de volta para CSV
# csv_veiculos_clusterizados = df_veiculos_clusterizados.to_csv(index=False, sep=';')
# csv_veiculos_clusterizados_bytes = csv_veiculos_clusterizados.encode('utf-8')

# ## Crie um buffer de bytes
# csv_veiculos_clusterizados_buffer = BytesIO(csv_veiculos_clusterizados_bytes)
# nome_arquivo = f'clustering_{data_hora_atual}.csv'


# minioclient.put_object(
#         CLUSTERING,
#         nome_arquivo,  # Use o mesmo nome de arquivo
#         data=csv_veiculos_clusterizados_buffer,
#         length=len(csv_veiculos_clusterizados_bytes),
#         content_type='application/csv')

# ## Enviando a regressão Linear para o Banco 
# conn = psycopg2.connect(**db_config)
# cursor = conn.cursor()

# truncate = """ truncate table veiculos_clusterizados_temp; """
# cursor.execute(truncate)

# copy_sql = """
#     COPY veiculos_clusterizados_temp (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo)
#     FROM stdin WITH CSV HEADER DELIMITER as ';'"""

# arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
# ## Itera sobre cada arquivo CSV encontrado no Minio
# for arquivo_clustering in arquivos_clustering:
#     # Obtém o objeto do arquivo CSV do Minio  
#     obj_regr = minioclient.get_object(CLUSTERING, arquivo_clustering.object_name)
#     csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
#     arquivo_csv = StringIO(csv_decod)
#     df = pd.read_csv(arquivo_csv, sep=';')
#     csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
#     csv_buffer = BytesIO(csv_bytes)
#     nome_arquivo = arquivo_clustering.object_name

#     with io.StringIO(csv_decod) as file:
#         cursor.copy_expert(sql=copy_sql, file=file)
# conn.commit()
# conn.close()


# conn = psycopg2.connect(**db_config)
# cursor = conn.cursor()
# insert = """
#         insert into veiculos_clusterizados (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo, data_execucao )
#         select 	
#         	nome_usuario,
#         	dist_km,
#         	media_consumo_km_l,
#         	cluster_consumo,
#         	now() as data_execucao 
#         from veiculos_clusterizados_temp
#     """
# cursor.execute(truncate)
# cursor.execute(insert)
# conn.commit()
# conn.close()

# minioclient.put_object(
#         ML_RESULTS,
#         arquivo_clustering.object_name,  # Use o mesmo nome de arquivo
#         data=csv_buffer,
#         length=len(csv_bytes),
#         content_type='application/csv')

# minioclient.remove_object(CLUSTERING, nome_arquivo)


#################################################################
### CRIANDO O DATAFRAME COM OS VEÍCULOS COM O PIOR DESEMPENHO ###
#################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
pior_desempenho = """
select 
	nome_usuario,
	round(media_consumo_km_l::numeric,2) as media_consumo_km_l,
	round(sum(dist_km::numeric),2) as dist_km, 
	round(sum((dist_km::numeric / media_consumo_km_l::numeric) * (select AVG(preco_medio_revenda::NUMERIC) from preco_combustivel_semanal where estado = 'RIO DE JANEIRO' and produto like '%GAS%')),2) as custo_viagem 
from veiculos_clusterizados
where cluster_consumo between '0' and '1'
group by nome_usuario,
	media_consumo_km_l
order by media_consumo_km_l::numeric asc
limit 5
"""
cursor.execute(pior_desempenho)
resultados_pior_desempenho = cursor.fetchall()
conn.close()

df_pior_desempenho = pd.DataFrame(resultados_pior_desempenho, columns=[desc[0] for desc in cursor.description])
df_pior_desempenho = df_pior_desempenho.sort_values(by='custo_viagem')


###################################################################
### CRIANDO O DATAFRAME COM OS VEÍCULOS COM O MELHOR DESEMPENHO ###
###################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
melhor_desempenho = """
select 
	nome_usuario,
	round(media_consumo_km_l::numeric, 2) as media_consumo_km_l,
	round(sum(dist_km::numeric),2) as dist_km, 
	round(sum((dist_km::numeric / media_consumo_km_l::numeric) * (select AVG(preco_medio_revenda::NUMERIC) from preco_combustivel_semanal where estado = 'RIO DE JANEIRO' and produto like '%GAS%')),2) as custo_viagem  
from veiculos_clusterizados
where cluster_consumo = '2'
group by nome_usuario,
	media_consumo_km_l	
order by media_consumo_km_l::numeric desc
limit 5
"""
cursor.execute(melhor_desempenho)
resultados_melhor_desempenho = cursor.fetchall()
conn.close()

df_melhor_desempenho = pd.DataFrame(resultados_melhor_desempenho, columns=[desc[0] for desc in cursor.description])
df_melhor_desempenho = df_melhor_desempenho.sort_values(by='custo_viagem')


#########################################
### OBTENDO O VALOR MÉDIO DA GASOLINA ###
#########################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
preco_medio_gasolina = """
select 
	avg(preco_medio_revenda::numeric) as media
from preco_combustivel_semanal
where
	 produto like '%GASOLINA%' and 
     estado = 'RIO DE JANEIRO'
"""
cursor.execute(preco_medio_gasolina)
resultados_preco_medio_gasolina = cursor.fetchall()
conn.close()

df_preco_medio_gasolina = pd.DataFrame(resultados_preco_medio_gasolina, columns=[desc[0] for desc in cursor.description])
valor_medio = Decimal(df_preco_medio_gasolina['media'].iloc[0])


###############################################################################################################################
### CRIAÇÃO DO DATAFRAME COM A SIMULAÇÃO DOS VEÍCULOS COM MELHOR DESEMPENHO FAZENDO A ROTA DOS VEÍCULOS COM PIOR DESEMPENHO ###
###############################################################################################################################
df_simulado = pd.DataFrame({
    'nome_usuario_original': df_pior_desempenho['nome_usuario'],
    'media_consumo_km_original': df_pior_desempenho['media_consumo_km_l'],
    'nome_usuario_simulado': df_melhor_desempenho['nome_usuario'],
    'media_consumo_km_l_simulado': df_melhor_desempenho['media_consumo_km_l'],
    'dist_km_original': df_pior_desempenho['dist_km'],
    'custo_viagem_original': df_pior_desempenho['custo_viagem'],    
    'custo_viagem_simulado': df_pior_desempenho['dist_km'] / df_melhor_desempenho['media_consumo_km_l'] * valor_medio
    })


#########################################################################################################
### LIMPANDO A TABELA [cluster_simulacao] PARA QUE FIQUE SEMPRE COM OS DADOS MAIS ATUALIZADOS DA BASE ###
#########################################################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
truncate = """ truncate table cluster_simulacao; """
cursor.execute(truncate)
conn.commit()
conn.close()


#################################################################
### INSERINDO DADOS ATUALIZADOS NA TABELA [cluster_simulacao] ###
#################################################################
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

for i in range(len(df_simulado)):
    nome_usuario_original = df_simulado['nome_usuario_original'].iloc[i]
    media_consumo_km_original = df_simulado['media_consumo_km_original'].iloc[i]
    nome_usuario_simulado = df_simulado['nome_usuario_simulado'].iloc[i]
    media_consumo_km_l_simulado = df_simulado['media_consumo_km_l_simulado'].iloc[i]
    dist_km_original = df_simulado['dist_km_original'].iloc[i]
    custo_viagem_original = df_simulado['custo_viagem_original'].iloc[i]
    custo_viagem_simulado = df_simulado['custo_viagem_simulado'].iloc[i]

    query_insert_cluster_simulacao = f'''
        insert into cluster_simulacao (nome_usuario_original, media_consumo_km_original, nome_usuario_simulado, media_consumo_km_l_simulado, dist_km_original, custo_viagem_original, custo_viagem_simulado)
        values(
        '{nome_usuario_original}',
        '{media_consumo_km_original}',
        '{nome_usuario_simulado}',
        '{media_consumo_km_l_simulado}',
        '{dist_km_original}',
        '{custo_viagem_original}',
        '{custo_viagem_simulado}')
        '''    
    cursor.execute(query_insert_cluster_simulacao)
    conn.commit()

conn.close()


########################################################
### FORMA ALTERNATIVA DE SE ITERAR SOBRE O DATAFRAME ###
########################################################
# for index, row in df_simulado.iterrows():
#     nome_usuario_original = row['nome_usuario_original']
#     media_consumo_km_original = row['media_consumo_km_original']
#     nome_usuario_simulado = row['nome_usuario_simulado']
#     media_consumo_km_l_simulado = row['media_consumo_km_l_simulado']
#     dist_km_original = row['dist_km_original']
#     custo_viagem_original = row['custo_viagem_original']
#     custo_viagem_simulado = row['custo_viagem_simulado']



########################################
### 3ª PARTE DE CÓDIGO NÃO UTILIZADA ###
########################################
## Converta o DataFrame enriquecido de volta para CSV
# csv_simulado = df_simulado.to_csv(index=False, sep=';')
# csv_simulado_bytes = csv_simulado.encode('utf-8')

## Crie um buffer de bytes
# csv_simulado_buffer = BytesIO(csv_simulado_bytes)
# nome_arquivo = f'simulacao_rota_veiculos_{data_hora_atual}.csv'

# minioclient.put_object(
#         CLUSTERING,
#         nome_arquivo,  # Use o mesmo nome de arquivo
#         data=csv_simulado_buffer,
#         length=len(csv_simulado_bytes),
#         content_type='application/csv')

## Enviando a simulação para o Banco 
# conn = psycopg2.connect(**db_config)
# cursor = conn.cursor()

# truncate = """ truncate table cluster_simulacao; """
# cursor.execute(truncate)

# copy_sql = """
#     COPY cluster_simulacao (nome_usuario_original,media_consumo_km_original,nome_usuario_simulado,media_consumo_km_l_simulado,dist_km_original,custo_viagem_original,custo_viagem_simulado)
#     FROM stdin WITH CSV HEADER DELIMITER as ';'
#     """

# arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
# ## Itera sobre cada arquivo CSV encontrado no Minio
# for arquivo_clustering in arquivos_clustering:
#     # Obtém o objeto do arquivo CSV do Minio  
#     obj_regr = minioclient.get_object(CLUSTERING, arquivo_clustering.object_name)
#     csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
#     arquivo_csv = StringIO(csv_decod)
#     df = pd.read_csv(arquivo_csv, sep=';')
#     csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
#     csv_buffer = BytesIO(csv_bytes)
#     nome_arquivo = arquivo_clustering.object_name

#     with io.StringIO(csv_decod) as file:
#         cursor.copy_expert(sql=copy_sql, file=file)
# conn.commit()
# conn.close()

# minioclient.put_object(
#         ML_RESULTS,
#         arquivo_clustering.object_name,  # Use o mesmo nome de arquivo
#         data=csv_buffer,
#         length=len(csv_bytes),
#         content_type='application/csv')

# minioclient.remove_object(CLUSTERING, nome_arquivo)


###########################################################
### CALCULANDO O TEMPO DE EXECUÇÃO DO SCRIPT (OPCIONAL) ###
###########################################################
# end_time = time.time()
# execution_time = end_time - start_time

# hours, remainder = divmod(execution_time, 3600)
# minutes, remainder = divmod(remainder, 60)
# seconds, milliseconds = divmod(remainder, 1)

# print(f"Tempo de execução: {int(hours)} horas, {int(minutes)} minutos, {int(seconds)} segundos e {int(milliseconds * 1000)} milissegundos")