FROM public.ecr.aws/sam/build-python3.12:latest-arm64
COPY requirements.txt .
RUN pip install -r requirements.txt -t /opt/python
