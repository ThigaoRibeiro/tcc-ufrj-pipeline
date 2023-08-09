import os
import shutil


DATALAKE_STAGE = 'DATALAKE_STAGE'  # Substitua pelo caminho do diretório de destino
DOWNLOADS = '/home/thiago/Downloads/'


files_to_rename = [arquivo for arquivo in os.listdir(DOWNLOADS) if arquivo.endswith(".crdownload")]
for file_name in files_to_rename:
        new_name = file_name.replace(".crdownload", "")
        os.rename(os.path.join(DOWNLOADS, file_name), os.path.join(DOWNLOADS, new_name))


files_to_move = [files for files in os.listdir(DOWNLOADS) if files.endswith(".gpx")]
for name_files in files_to_move:
    origin_path = os.path.join(DOWNLOADS, name_files)
    destiny_path = os.path.join(DATALAKE_STAGE, name_files)
    os.rename(origin_path, destiny_path)
    print(f"Arquivo {name_files} movido para {destiny_path}")