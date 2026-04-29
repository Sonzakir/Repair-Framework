[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/vSMsQZ9k)

# Repair Framework

This is an empty repository serving as workspace for your repair framework implementation.

## To run in a container

```bash
docker compose up
docker compose run apr-framework
```

## Currently supported commands

```bash
python -m apr_framework list-benchmarks
python -m apr_framework bugsinpy list-projects
python -m apr_framework bugsinpy list-bugs pandas
python -m apr_framework bugsinpy setup
python -m apr_framework bugsinpy checkout pandas 1
python -m apr_framework bugsinpy test pandas 1
```
