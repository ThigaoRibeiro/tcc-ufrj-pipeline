#from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta
from airflow.models import DAG
from airflow.operators.bash import BashOperator

default_args={
     'owner': 'thiago',     
     'retries': 5,
     'retry_delay': timedelta(minutes=5)
}


with DAG (
    dag_id='exec-web-scraping',
    default_args= default_args,
    description='DAG Responsável por executar modelos de Machine Learning nos dados do banco de dados.',
    start_date=datetime(2023,9,18),
    #schedule_interval='@daily',
    schedule_interval='*/10 * * * *',
    catchup=False
) as dag:
      

# 1ª Tarefa
    regressao_linear = BashOperator(
        task_id='regressao_linear',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/7_regressao_linear.py',        
        dag=dag,
    )

# 2ª Tarefa
    clustering = BashOperator(
        task_id='clustering',
        bash_command='python3 /home/thiago/tcc_ufrj/scripts_finalizados/8_clustering.py',
        dag=dag,
    )

# Definindo a ordem das tarefas
regressao_linear >> clustering
