FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

RUN pip install playwright playwright-stealth

RUN playwright install chromium

CMD ["tail", "-f", "/dev/null"]
