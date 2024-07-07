import json
from typing import Dict, Any

from sqlalchemy import select
from worker.models.yolo_detection import Model as YoloModel
from worker.models.clip_classification import Model as ClassModel
from api.db_model import TransactionHistory, get_session, TransactionStatusEnum, UploadedFile
from sqlalchemy.exc import NoResultFound
from worker.models.yolo_detection.utils import FileProcessor
from api.s3 import s3, S3Client
import traceback
from collections import defaultdict
from datetime import datetime, timedelta
import csv

yolo_model = YoloModel()
classification_model = ClassModel()
file_proc = FileProcessor()


async def analyze_uploaded_file(
    ctx: Dict[str, Any],
    uploaded_file_id : str,
    uploaded_file_name: str,
    **kwargs: Any,
):
    async for session in get_session():
        try:
            
            job_id = ctx.get("job_id", None)
            if not job_id:
                raise Exception("Something is wrong. job_id is None")

            transaction = await session.execute(
                select(TransactionHistory).filter_by(job_id=job_id)
            )
            transaction = transaction.scalar()
            
            doc = await session.execute(
                select(UploadedFile).filter_by(id=uploaded_file_id)
            )
            doc = doc.scalar()
            # zip архив
            print(uploaded_file_id)
            data = await file_proc.process_file(uploaded_file_name, uploaded_file_id)
            # Предикт yolo
            result = await yolo_model.predict(data)
            # zip архив
            data = await file_proc.process_file(uploaded_file_name, uploaded_file_id)
            # Предикт классификатора
            result_finally = classification_model.predict(data,result)
            #result = "Test results"
            _ = await json_to_csv(result_finally)
            if not result_finally:
                raise Exception(f"Something is wrong. Try again later: {result}")

            transaction.status = TransactionStatusEnum.SUCCESS

            json_data = json.dumps(result_finally)
            transaction.result = json_data
            await session.commit()
            return result_finally
        except Exception as e:
            transaction.status = TransactionStatusEnum.FAILURE
            transaction.err_reason = str(e)
            doc.verified = False
            doc.cancellation_reason = f"File processing error: {e}"
            await session.commit()
            traceback.print_exc()
            return json.dumps({"data": uploaded_file_id, "result": str(e)})


async def process_json(data):
    
    results = {}

    for image, details in data.items():
        class_prob_sums = defaultdict(float)
        for obj in details["data"]:
            cls = obj["class"]
            prob = obj["conf"]
            class_prob_sums[cls] += prob
        
        most_probable_class = max(class_prob_sums, key=class_prob_sums.get)
        
        # Корректируем все предсказания
        corrected_predictions = [{ "conf": obj["conf"], "class": most_probable_class} for obj in details["data"]]
        
        results[image] = {
            "im_datetime": details["im_datetime"],
            "data": corrected_predictions
        }
    
    return results

async def json_to_csv(json_dict):
    output = await process_json(json_dict)

    timeline_data = {}

    for image, details in output.items():
        folder_name = image.split('/')[0]
        im_datetime = details['im_datetime']
        date_time_obj = datetime.strptime(im_datetime, '%Y:%m:%d %H:%M:%S')
        max_count = len(details['data'])

        for item in details['data']:
            image_class = item['class']
            key = (folder_name, image_class)

            if key not in timeline_data:
                timeline_data[key] = []
            
            if not timeline_data[key] or (date_time_obj - timeline_data[key][-1]['end_date']) > timedelta(minutes=30):
                timeline_data[key].append({
                    'start_date': date_time_obj,
                    'end_date': date_time_obj,
                    'count': max_count
                })
            else:
                timeline_data[key][-1]['end_date'] = date_time_obj
                timeline_data[key][-1]['count'] = max(timeline_data[key][-1]['count'], max_count)
    
    with open('output.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['name_folder', 'class', 'date_registration_start', 'date_registration_end', 'count'])
    
        for (folder_name, image_class), periods in timeline_data.items():
            for period in periods:
                start_date_str = period['start_date'].strftime('%Y-%m-%d %H:%M:%S')
                end_date_str = period['end_date'].strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([folder_name, image_class, start_date_str, end_date_str, period['count']])
    
    with open('output.csv',"rb") as file:
        S3_res = S3Client('result')
        await S3_res.upload_file(file=file,filename='output.csv')       