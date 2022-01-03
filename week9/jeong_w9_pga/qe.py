from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
import numpy as np
from decimal import Decimal
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = FastAPI()

templates = Jinja2Templates(directory="templates")

def solve_qe_eq(a, b, c):
    result = []
    if int(b)**2 >= 4*int(a)*int(c):
        x1 = (-Decimal(b)-(Decimal(b)**2-4*Decimal(a)*Decimal(c)).sqrt()) / (Decimal('2') * Decimal(a))
        x2 = (-Decimal(b)+(Decimal(b)**2-4*Decimal(a)*Decimal(c)).sqrt()) / (Decimal('2') * Decimal(a))
        if x1 % 1 == 0:
            x1 = int(x1)
        else:
            x1 = float(x1)
        if x2 % 1 == 0:
            x2 = int(x2)
        else:
            x2 = float(x2)
        if x1 == x2:
            result.append(x1)
        else:
            result=[x1, x2]

    return result

@app.get("/main")
async def root(request: Request, message='Coursera Students'):
    return templates.TemplateResponse("main.html", 
                                {"request": request,
                                'message': message})

@app.get("/solve")
async def solve_qe(a, b, c):
    result = solve_qe_eq(a, b, c)

    return {"roots": result}

@app.post("/main")
async def show_plot(requst: Request,
                    a: str = Form(...),
                    b: str = Form(...),
                    c: str = Form(...)):
    result = solve_qe_eq(a, b, c)

    if len(result) == 2:
        x = np.linspace(result[0]-result[1], result[0]+result[1], 100)
        y = int(a) * x ** 2 + int(b) * x + int(c)
        y0 = x * 0
    elif len(result) == 1:
        x = np.linspace(result[0]-10, result[0]+10, 100)
        y = int(a) * x ** 2 + int(b) * x + int(c)
        y0 = x * 0
    else:
        x = np.linspace(-10, 10, 100)
        y = int(a) * x ** 2 + int(b) * x + int(c)
        y0 = x * 0


    fig = plt.figure() 
    plt.plot(x, y)
    plt.plot(x, y0)
    for l in result:
        plt.text(l, 0, f'({l})', fontsize=12)

    pngImage = io.BytesIO()
    fig.savefig(pngImage)
    pngImageB64String = base64.b64encode(pngImage.getvalue()).decode('ascii')
    return templates.TemplateResponse("plot.html",
                                {"request": requst,
                                "a": a,
                                "b": b,
                                "c": c,
                                "picture": pngImageB64String})
