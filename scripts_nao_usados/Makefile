airflow_start:
	@echo "Iniciando o Apache Airflow..."
	@airflow webserver -D
	@airflow scheduler -D
	@airflow triggerer -D
	@echo "Apache Airflow iniciado com sucesso!"

airflow_stop:
	@echo "Parando o Apache Airflow..."
	@pkill -f "airflow webserver"
	@pkill -f "airflow scheduler"
	@pkill -f "airflow triggerer"
	@echo "Apache Airflow parado com sucesso!"


