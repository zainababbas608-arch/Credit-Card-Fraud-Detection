FROM jupyter/pyspark-notebook:latest

USER root

COPY spark-defaults.conf ${SPARK_HOME}/conf/spark-defaults.conf

RUN pip install pyspark==3.5.0

RUN mkdir -p /home/jovyan/work && chown -R jovyan:users /home/jovyan/work

USER ${NB_UID}