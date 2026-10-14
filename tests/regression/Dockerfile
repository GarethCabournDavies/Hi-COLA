FROM python:3.11-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ make git libfftw3-dev libfftw3-mpi-dev libgsl-dev liblua5.4-dev \
    openmpi-bin libopenmpi-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/regression-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/regression-requirements.txt
ENV MPLBACKEND=Agg OMP_NUM_THREADS=1 \
    OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
