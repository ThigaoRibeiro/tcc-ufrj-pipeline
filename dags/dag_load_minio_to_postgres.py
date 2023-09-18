'''

from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.bash import BashOperator

default_args={
     'owner': 'thiago',     
     'retries': 5,
     'retry_delay': timedelta(minutes=5)
}


with DAG (
    dag_id='load_minio_to_postgres',
    default_args= default_args,
    description='DAG Responsável por verificar a existência de arquivos na camada "gold". Caso existam arquivos, estes serão carregados na tabela "tb_gpx_full" no Postgres. Após a carga estes arquivos são movidos para o bucket "files-in-table".',
    start_date=datetime(2023,9,18),            
    schedule_interval='*/10 * * * *',
    catchup=False
) as dag:
      

# Tarefa para executar o script WebScraping_OpenStreetMap_v2.py
    exec_minio_to_postgres_sync = BashOperator(
        task_id='load_minio_to_bucket',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/5_minio_to_postgresql.py',
        dag=dag,
    )

# Defina a ordem das tarefas
exec_minio_to_postgres_sync


'''