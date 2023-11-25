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
from time import sleep
from decimal import Decimal
CLUSTERING = 'clustering'
ML_RESULTS = 'resultados-ml'


minioclient = Minio('localhost:9000',
    access_key='minioadmin',
    secret_key='minioadmin',
    secure=False)


db_config = {
'host': 'localhost',
'database': 'postgres',
'user': 'postgres',
'password': 'postgres',
}


arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
## Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_clustering in arquivos_clustering:
    # Obtém o objeto do arquivo CSV do Minio      
    nome_arquivo = arquivo_clustering.object_name    
    minioclient.remove_object(CLUSTERING, nome_arquivo)


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


conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
cursor.execute(sql_query)
resultados_agrup_veiculos = cursor.fetchall()
conn.close()
df_agrup_veiculos = pd.DataFrame(resultados_agrup_veiculos, columns=[desc[0] for desc in cursor.description])


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
df_veiculos_clusterizados.to_csv('resultado_agrupamento.csv', index=False)


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


## Converta o DataFrame enriquecido de volta para CSV
csv_veiculos_clusterizados = df_veiculos_clusterizados.to_csv(index=False, sep=';')
csv_veiculos_clusterizados_bytes = csv_veiculos_clusterizados.encode('utf-8')

## Crie um buffer de bytes
csv_veiculos_clusterizados_buffer = BytesIO(csv_veiculos_clusterizados_bytes)
nome_arquivo = f'clustering_{data_hora_atual}.csv'


minioclient.put_object(
        CLUSTERING,
        nome_arquivo,  # Use o mesmo nome de arquivo
        data=csv_veiculos_clusterizados_buffer,
        length=len(csv_veiculos_clusterizados_bytes),
        content_type='application/csv')

## Enviando a regressão Linear para o Banco 
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

truncate = """ truncate table veiculos_clusterizados_temp; """
cursor.execute(truncate)

copy_sql = """
    COPY veiculos_clusterizados_temp (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo)
    FROM stdin WITH CSV HEADER DELIMITER as ';'"""

arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
## Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_clustering in arquivos_clustering:
    # Obtém o objeto do arquivo CSV do Minio  
    obj_regr = minioclient.get_object(CLUSTERING, arquivo_clustering.object_name)
    csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv, sep=';')
    csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    nome_arquivo = arquivo_clustering.object_name

    with io.StringIO(csv_decod) as file:
        cursor.copy_expert(sql=copy_sql, file=file)
conn.commit()
conn.close()


conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
insert = """
        insert into veiculos_clusterizados (nome_usuario, dist_km, media_consumo_km_l, cluster_consumo, data_execucao )
        select 	
        	nome_usuario,
        	dist_km,
        	media_consumo_km_l,
        	cluster_consumo,
        	now() as data_execucao 
        from veiculos_clusterizados_temp
    """
cursor.execute(truncate)
cursor.execute(insert)
conn.commit()
conn.close()

minioclient.put_object(
        ML_RESULTS,
        arquivo_clustering.object_name,  # Use o mesmo nome de arquivo
        data=csv_buffer,
        length=len(csv_bytes),
        content_type='application/csv')

minioclient.remove_object(CLUSTERING, nome_arquivo)


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


df_simulado = pd.DataFrame({
    'nome_usuario_original': df_pior_desempenho['nome_usuario'],
    'media_consumo_km_original': df_pior_desempenho['media_consumo_km_l'],
    'nome_usuario_simulado': df_melhor_desempenho['nome_usuario'],
    'media_consumo_km_l_simulado': df_melhor_desempenho['media_consumo_km_l'],
    'dist_km_original': df_pior_desempenho['dist_km'],
    'custo_viagem_original': df_pior_desempenho['custo_viagem'],    
    'custo_viagem_simulado': df_pior_desempenho['dist_km'] / df_melhor_desempenho['media_consumo_km_l'] * valor_medio
    })


## Converta o DataFrame enriquecido de volta para CSV
csv_simulado = df_simulado.to_csv(index=False, sep=';')
csv_simulado_bytes = csv_simulado.encode('utf-8')

## Crie um buffer de bytes
csv_simulado_buffer = BytesIO(csv_simulado_bytes)
nome_arquivo = f'simulacao_rota_veiculos_{data_hora_atual}.csv'

minioclient.put_object(
        CLUSTERING,
        nome_arquivo,  # Use o mesmo nome de arquivo
        data=csv_simulado_buffer,
        length=len(csv_simulado_bytes),
        content_type='application/csv')

## Enviando a simulação para o Banco 
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

truncate = """ truncate table cluster_simulacao; """
cursor.execute(truncate)

copy_sql = """
    COPY cluster_simulacao (nome_usuario_original,media_consumo_km_original,nome_usuario_simulado,media_consumo_km_l_simulado,dist_km_original,custo_viagem_original,custo_viagem_simulado)
    FROM stdin WITH CSV HEADER DELIMITER as ';'
    """

arquivos_clustering = [arquivo for arquivo in minioclient.list_objects(CLUSTERING) if arquivo.object_name.endswith(".csv")]
## Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_clustering in arquivos_clustering:
    # Obtém o objeto do arquivo CSV do Minio  
    obj_regr = minioclient.get_object(CLUSTERING, arquivo_clustering.object_name)
    csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv, sep=';')
    csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    nome_arquivo = arquivo_clustering.object_name

    with io.StringIO(csv_decod) as file:
        cursor.copy_expert(sql=copy_sql, file=file)
conn.commit()
conn.close()

minioclient.put_object(
        ML_RESULTS,
        arquivo_clustering.object_name,  # Use o mesmo nome de arquivo
        data=csv_buffer,
        length=len(csv_bytes),
        content_type='application/csv')

minioclient.remove_object(CLUSTERING, nome_arquivo)