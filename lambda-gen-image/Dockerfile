FROM amazon/aws-lambda-python:3.12

WORKDIR /var/task

COPY requirements.txt .
RUN /var/lang/bin/python3 -m pip install -r requirements.txt

COPY . .

CMD ["lambda_function.lambda_handler"]