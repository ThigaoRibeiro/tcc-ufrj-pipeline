from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn import metrics
import pandas as pd
from minio import Minio
import io
from io import StringIO, BytesIO
import psycopg2
from datetime import datetime
data_hora_atual = datetime.now()
REGRESSAO_LINEAR = 'regressao-linear'

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

# Fazendo conexão com o banco para selecionar a view "vw_valores_combustivel_por_viagem" com os dados que serão utilizados para a regressão linear.
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

consulta_veiculos = """
select 
	data_rota,	
	nome_usuario,
	tipo_combustivel,	
	dist_km,
	cons_por_km	
from vw_valores_combustivel_por_viagem 
"""

cursor.execute(consulta_veiculos)
resultados_consumo_veiculos = cursor.fetchall()
conn.close()
df_consumo_veiculos = pd.DataFrame(resultados_consumo_veiculos, columns=[desc[0] for desc in cursor.description])


# Definindo variáveis independentes (X) e dependente (Y)
X = df_consumo_veiculos[['dist_km','nome_usuario']]
Y = df_consumo_veiculos['cons_por_km']
X = pd.get_dummies(X, columns=['nome_usuario'], drop_first=True)

# Dividindo os dados em conjuntos de treinamento e teste
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.3, random_state=0)

# Inicializando o modelo de regressão linear
model = LinearRegression()

# Treinando o modelo
model.fit(X_train, Y_train)

# Fazendo previsões no conjunto de teste
Y_pred = model.predict(X_test)

# Avaliando o desempenho do modelo
print('Erro Médio Absoluto:', metrics.mean_absolute_error(Y_test, Y_pred))
print('Erro Quadrático Médio:', metrics.mean_squared_error(Y_test, Y_pred))


coeficientes = model.coef_
coeficientes_df = pd.DataFrame({'Variável': X.columns, 'Coeficiente': coeficientes})
coeficientes_df['Coeficiente_Abs'] = coeficientes_df['Coeficiente'].abs().apply(lambda x: format(x, '.6f'))
coeficientes_df = coeficientes_df.sort_values(by='Coeficiente_Abs', ascending=False)

#valor_formatado = format(5.551115e-17, '.10f')
#valor_formatado
#valor_arredondado = round(5.551115e-17, 10)
#valor_arredondado

# Converta o DataFrame enriquecido de volta para CSV
csv_to_regressao_linear = coeficientes_df.to_csv(index=False, sep=';')
csv_to_regressao_linear_bytes = csv_to_regressao_linear.encode('utf-8')

# Crie um buffer de bytes
csv_to_regressao_linear_buffer = BytesIO(csv_to_regressao_linear_bytes)
nome_arquivo = f'regressao_linear_{data_hora_atual}.csv'

minioclient.put_object(
        REGRESSAO_LINEAR,
        nome_arquivo,  # Use o mesmo nome de arquivo
        data=csv_to_regressao_linear_buffer,
        length=len(csv_to_regressao_linear_bytes),
        content_type='application/csv')

## Enviando a regressão Linear para o Banco 
conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

truncate = """ truncate table regressao_linear_temp; """
cursor.execute(truncate)

copy_sql = """
    COPY regressao_linear_temp (variavel, Coeficiente, Coeficiente_Abs)
    FROM stdin WITH CSV HEADER DELIMITER as ';'"""


arquivos_regressao = [arquivo for arquivo in minioclient.list_objects(REGRESSAO_LINEAR) if arquivo.object_name.endswith(".csv")]
# Itera sobre cada arquivo CSV encontrado no Minio
for arquivo_regressao in arquivos_regressao:
    # Obtém o objeto do arquivo CSV do Minio  
    obj_regr = minioclient.get_object(REGRESSAO_LINEAR, arquivo_regressao.object_name)
    csv_decod = obj_regr.data.decode('utf-8')  # Convertendo bytes para string
    arquivo_csv = StringIO(csv_decod)
    df = pd.read_csv(arquivo_csv, sep=';')
    csv_bytes = df.to_csv(index=False,sep=';').encode('utf-8')
    csv_buffer = BytesIO(csv_bytes)
    nome_arquivo = arquivo_regressao.object_name

    with io.StringIO(csv_decod) as file:
        cursor.copy_expert(sql=copy_sql, file=file)
    conn.commit()

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()
insert = """
insert into regressao_linear (Variavel, Coeficiente, Coeficiente_Abs, data_execucao )
select 	replace (variavel,'nome_usuario_','') as variavel, 
		Coeficiente, 
		Coeficiente_Abs, 
		now() as data_execucao 
from regressao_linear_temp
    """
cursor.execute(insert)
conn.commit()
conn.close()

minioclient.put_object(
        ML_RESULTS,
        arquivo_regressao.object_name,  # Use o mesmo nome de arquivo
        data=csv_buffer,
        length=len(csv_bytes),
        content_type='application/csv')

minioclient.remove_object(REGRESSAO_LINEAR, nome_arquivo)