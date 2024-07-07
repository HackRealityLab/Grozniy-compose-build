


Предварительные настройки:
1) MINIO
```bash
    chown 1001 -R minio-persistence
```
2) Set up docker compose path variables!
Поднять MINIO

3) docker compose up minio

![image](https://github.com/HackRealityLab/Grozniy-compose-build/assets/69810254/31471f08-864c-495e-85ee-ad0d8b37b19c)

авторизоваться в minio
логин пароль
hack
minio123

4) Через веб морду сделать secret и access key

![image](https://github.com/HackRealityLab/Grozniy-compose-build/assets/69810254/803ec4a6-1015-4991-b502-2326d93708cd)


5) Прописать секрет в docker compose


прописать ключи в api/s3.py

![image](https://github.com/HackRealityLab/Grozniy-compose-build/assets/69810254/55c0d086-ba7e-4b83-83d7-9b0f5980d4fc)


6) Запустить docker compose up
```bash
    docker compose up -d
```
7) ссылки

   http://localhost:3000/ - front
   http://localhost:9001/ - minio
   http://localhost:9080/docs - swagger
