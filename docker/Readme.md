
# start the containers
docker-compose -f ./docker-compose.yml up

# start the postgres container
docker-compose -f ./docker-compose.yml up postgres

# start the container in detached mode
docker-compose -f ./docker-compose.yml up -d

# bring the containers down
docker-compose -f ./docker-compose.yml down

# list the running containers
docker container ls

# once the containers are running, enter into postgres container
docker exec -it phenomedb-dev_postgres_1 /bin/bash

