from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello from Flask on Vercel 🚀"

# Vercel serverless handler
def handler(request, response):
    return app(request.environ, response.start_response)