### Hello, and welcome to my simple weather (wx) api

Get started by creating a virtual environment (I used "venv") and installing the dependencies.
`pip install -r requirements.txt`


Start the microservice with `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`

Open a browser and visit `http://127.0.0.1:8000/66211` to check the weather in Leawood, KS. The endpoint should return the forecast for the next two forecast periods.

Visit `http://127.0.0.1:8000/requests` to see a history/log of recent requests.

Press CTRL+C to quit