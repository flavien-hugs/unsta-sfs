# UNSTA: Simple files storage (SFS) system using s3 and fastapi

SFS is a simple file storage system that uses MongoDB for data management and MinIO for file storage.

MongoDB acts as a database, centralizing and indexing all descriptive information on multimedia files and baskets,
enabling efficient queries and structured organization of metadata.

At the same time, MinIO handles the physical storage of files, offering a high-performance, adaptable approach
to multimedia content processing.

### Fonctionnalities

SFS is a RESTful API that allows users to upload, download, and delete files, as well as create, read, update,
and delete. It also allows users to create, read, update, and delete baskets.

### Pre-requisites

* [Dockerfile](https://docs.docker.com/get-docker): Docker and docker-compose
* [MinIO](https://min.io): MinIO server
* [MongoDB](https://www.mongodb.com): MongoDB server
* [Python](https://www.python.org): Python 3.8 or higher
* [FastAPI](https://fastapi.tiangolo.com): FastAPI
* [Beanie-odm](https://beanie-odm.dev): Beanie-odm
* [Poetry](https://python-poetry.org): Poetry

### Clone the repository
```shell
   git clone https://github.com/flavien-hugs/unsta-sfs.git
   cd unsta-sfs
```

### Set up the environment
```shell
   cp .env.example .env
```

### Excution
```shell
   docker compose up -d or make run (if you have make installed)
```

### API Documentation
```shell
   http://localhost:9995/sfs/docs
```
