from api.s3 import S3Client, s3
from zipfile import ZipFile
from io import BytesIO, BufferedReader 
class FileProcessor:
    def __init__(self) -> None:
        self.s3_read_client = s3

    async def process_file(self, filename: str, file_id: str):
        # Определение типа файла по расширению
        extension = filename.split('.')[-1].lower()
        if extension not in ['rar', 'zip', '7z']:
            raise Exception(f"Unexpected file type: {extension}")
        
        # Скачивание файла
        file_data = await self.s3_read_client.download_file(file_id)

        # Обработка файла в зависимости от расширения
        if extension == 'zip':
            return self.extract_text_from_zip(file_data)
        
    def extract_text_from_zip(self, file_data) -> ZipFile:

        zf = ZipFile(BytesIO(file_data), "r") 
        return zf