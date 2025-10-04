from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return '<h1>Real Estate Listings Portal</h1><p>App running successfully.</p>'