from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.bash import BashOperator

default_args={
     'owner': 'thiago',     
     'retries': 5,
     'retry_delay': timedelta(minutes=5)
}


with DAG (
    dag_id='dados-combustivel',
    default_args= default_args,
    description='DAG Responsável por alimentar as tabelas referente ao cálculo de combustível e consumo por veículo',
    start_date=datetime(2023,9,18),            
    schedule_interval='0 10 * * 1',
    catchup=False
) as dag:
      

# Tarefa para executar o script WebScraping_OpenStreetMap_v2.py
    exec_dados_combustivel_consumo = BashOperator(
        task_id='load_minio_to_bucket',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/6_info_combustivel_abastecimento.py',
        dag=dag,        
    )

# Defina a ordem das tarefas
exec_dados_combustivel_consumo

