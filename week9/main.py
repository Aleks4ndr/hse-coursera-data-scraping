from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from math import sqrt
import numpy as np


import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/main")
async def main(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.post("/plot")
async def show_plot(request: Request, a: int = Form(...), b: int = Form(...), c: int = Form(...)):
    roots = find_roots(a, b, c)
    legend=f'${a}x^2 {b:+d}x {c:+d}$'
    if len(roots) == 2:
        start = roots[0] - 10
        end = roots[1] + 10
    elif len(roots) == 1:
        start = roots[0] - 10
        end = roots[0] + 10
    else:
        start = -10
        end = 10

    x = np.linspace(start, end, 1000, True)
    f = np.vectorize(lambda x: get_value(a,b,c,x))
    fig = plt.figure()
    plt.plot(x, f(x))
    plt.plot(roots, f(roots), "ro")
    plt.xlabel('x')
    plt.ylabel(legend)
    plt.title(legend)
    plt.grid(True)

    pngImage = io.BytesIO()
    fig.savefig(pngImage)
    pngImageB64 = base64.b64encode(pngImage.getvalue())

    return templates.TemplateResponse("plot.html", {"request": request, "roots": roots, "picture": pngImageB64.decode('ascii')})

@app.get("/solve")
async def solve(a: int, b: int, c: int):
    roots = find_roots(a, b, c)

    return {"roots": roots}

def find_roots(a, b, c):
    roots = []
    if a == 0:
        if b != 0:
            roots.append(-c/b)
    else:
        d = b ** 2 -4 * a * c
        if d > 0:
            roots.append((-b - sqrt(d)) / (2 * a))
            roots.append((-b + sqrt(d)) / (2 * a))
        elif d == 0:
            roots.append(-b / (2 * a))
    return roots

def get_value(a, b, c, x):
    return a * x ** 2 + b * x * c
