FROM public.ecr.aws/sam/build-python3.14:latest-arm64
COPY requirements.txt .
RUN pip install --only-binary :all: -r requirements.txt -t /opt/python
