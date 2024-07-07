from typing import ClassVar
from PIL import Image
from transformers import pipeline
from zipfile import ZipFile
import numpy as np
from api.s3 import S3Client
class Model:
    class_mapping: ClassVar[dict[int, str]] = {
        i: name
        for i, name in enumerate(
            [
                'Badger',
                'Bear',
                'Bison',
                'Cat',
                'Dog',
                'Fox',
                'Goral',
                'Hare',
                'Lynx',
                'Marten',
                'Moose',
                'Mountain_Goat',
                'Musk_Deer',
                'Racoon_Dog',
                'Red_Deer',
                'Roe_Deer',
                'Snow_Leopard',
                'Squirrel',
                'Tiger',
                'Wolf',
                'Wolverine',
                'Empty'
            ]
        )
    }

    def __init__(
        self,
        class_mapping: dict[int, str] | None = None,
        device: str = "cpu",
        max_seq_len: int = 512,
    ):
        self.model_name = "openai/clip-vit-large-patch14-336"
        self.classifier = pipeline("zero-shot-image-classification", model = self.model_name)
        self.class_mapping = class_mapping or self.class_mapping

        self.s3_write_client = S3Client(bucket_name="results")

    def predict(self,archive_s3_path:ZipFile ,yolo_dict:dict) -> dict:
        labels_for_classification =  ['Badger',
        'Bear',
        'Bison',
        'Cat',
        'Dog',
         'Fox',
        'Goral',
        'Hare',
        'Lynx',
       'Marten',
        'Moose',
        'Mountain_Goat',
        'Musk_Deer',
        'Racoon_Dog',
        'Red_Deer',
        'Roe_Deer',
        'Snow_Leopard',
        'Squirrel',
        'Tiger',
        'Wolf',
        'Wolverine',
        'Empty']
        with archive_s3_path as archive:
            dict_result = {}
            for image in archive.namelist():
                # Открыть изображение
                f = archive.open(image)

                #в info будут поля im_datetime, и data для каждого файла
                info = yolo_dict[image]

                #все боксы для файла
                boxes = info['data']

                #сюда резалт сохраняю
                classification_result = []
                #по все ббоксам
                for bbox in boxes:

                    #координаты бокса
                    x1,y1,x2,y2 = bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']
                    img = Image.open(f)
                    img = np.array(img)
                    #обрезал
                    img_cropped = img[y1:y2, x1:x2]
                    #перевел в PIL, чтобы кинуть в классификатор
                    frame = Image.fromarray(img_cropped)
                    result = self.classifier(frame, candidate_labels = labels_for_classification)[0]
                    #резалт это пара из 'score' и 'label' для наиболее вероятного класса           
                    confidance = result['score']
                    class_name = result['label']
                    classification_result.append({
                        "conf":confidance,
                        "class":class_name
                    })

                    
                dict_result[image]= {
                        "im_datetime": info["im_datetime"],
                        "data": classification_result
                    }
        return dict_result
                
            