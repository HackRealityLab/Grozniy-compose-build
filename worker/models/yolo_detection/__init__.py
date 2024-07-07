from ultralytics import YOLO
from typing import ClassVar
from zipfile import ZipFile
from api.s3 import S3Client
from PIL import Image, ExifTags
import cv2
from io import BytesIO, BufferedReader 
class Model:
    class_mapping: ClassVar[dict[int, str]] = {
        i: name
        for i, name in enumerate(
            [
                'animal',
                'person',
                'vehicle'
            ]
        )
    }

    def __init__(
        self,
        class_mapping: dict[int, str] | None = None,
        device: str = "cpu"
    ):
        self.model = YOLO("./worker/models/yolo_detection/deepfaune-yolov8s_960.pt")
        self.device = device
        self.model.to(device)
        self.class_mapping = class_mapping or self.class_mapping

        self.s3_write_client = S3Client(bucket_name="results")
        
    async def predict(self, archive_s3_path:ZipFile) -> dict:
        result_dict = {}
        with archive_s3_path as archive:
            for image in archive.namelist():
                result = []
                # Открыть изображение
                f = archive.open(image)
                # Конвертация изображения
                img = Image.open(f)
                # Сбор метаданных
                exif = { ExifTags.TAGS[k]: v for k, v in img._getexif().items() if k in ExifTags.TAGS }
                # Предикт
                res = self.model.predict(source=img)
                # Формирование ответа
                for i in res[0].boxes.data.cpu().tolist():
                    res_dict = {
                        'x1':int(i[0]),
                        'y1':int(i[1]),
                        'x2':int(i[2]),
                        'y2':int(i[3]), 
                        'conf': i[4],
                        'class': self.class_mapping[int(i[5])]
                    }
                    
                    result.append(res_dict)
                if result != []:
                    result_dict[image] = {"im_datetime":exif['DateTime'] ,'data':result}
                else:
                    result_dict[image] = {"im_datetime":exif['DateTime'] ,'data':[{
                        'x1':0,
                        'y1':0,
                        'x2':5,
                        'y2':5
                    }]}
                # Плотинг ббокса
                _, buffer = cv2.imencode('.jpg', res[0].plot())
                #Перевод в iobf
                iobf = BufferedReader(BytesIO(buffer.tobytes()))
                # Сохранение в s3
                await self.s3_write_client.upload_file(iobf,image)
        return result_dict


