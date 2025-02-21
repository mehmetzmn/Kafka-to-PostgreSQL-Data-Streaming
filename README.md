# How to run

Run docker compose up within project directory.

```docker
docker compose up -d
```

After all system checked up and running, you can check the logs by

```docker
docker logs -f $(docker compose ps -q python-app)
```

```bash
"Data successfully written to PostgreSQL"
```

Above message indicates the project successfully finished. You can check postgres database using

```bash
bash  query_postgres.sh
```

---

## Unit testing

To run Unit test, use below command

```bash
python -m pytest test_all.py -v
```
