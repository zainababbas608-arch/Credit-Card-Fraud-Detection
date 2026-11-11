FROM jupyter/pyspark-notebook:latest

USER root

COPY spark-defaults.conf ${SPARK_HOME}/conf/spark-defaults.conf

RUN pip install pyspark==3.5.0

RUN /opt/conda/bin/python -m venv /opt/venv/fraudui \
 && /opt/venv/fraudui/bin/pip install --no-cache-dir "streamlit==1.66.1" matplotlib kafka-python
 
RUN mkdir -p /home/jovyan/work && chown -R jovyan:users /home/jovyan/work

USER ${NB_UID}