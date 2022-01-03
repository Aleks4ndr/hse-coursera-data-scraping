from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import io
import base64
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request, message='Solving Quadratic Equations'):
    return templates.TemplateResponse("index.html",
                        {"request": request,
                        "message": message})


def solve_quadratic(a, b, c):

    dis = b * b - (4 * a * c)
    sqrt_val = (np.sqrt(abs(dis)))

    if dis < 0 or a==0:
        return []

    x = (-b - sqrt_val)/(2 * a)
    y = (-b + sqrt_val)/(2 * a)

    if dis == 0:
        return [x]
    else:
        return [x, y]

@app.get("/solve")
async def solver(a: int, b: int, c: int):
    return {"roots": solve_quadratic(a, b, c)}


@app.get('/plot')
async def plot(request: Request, a: int, b: int, c: int):
    numbers = [a, b, c]
    roots = solve_quadratic(a, b, c)
 
    x = np.linspace(-5, 5, 100)
    y = (a * (x ** 2) + b * x + c)
    x_1 = solve_quadratic(a, b, c)
    y_1 = np.zeros(len(roots))
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1) 
    plt.plot(x, y, 'red', label=f'({a})x^2 +({b})*x +({c})')
    plt.scatter(x_1, y_1, marker='x', c='b', label='roots')
    plt.legend(loc=0)
    #plt.show()
    

    image = io.BytesIO()
    fig.savefig(image)
    image_b64 = base64.b64encode(image.getvalue()).decode('ascii')
    return templates.TemplateResponse('plot.html',
                                    {'request': request,
                                    'numbers': numbers,
                                    'roots': roots,
                                    'picture': image_b64})


