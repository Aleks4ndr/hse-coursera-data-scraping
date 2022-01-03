#!/usr/bin/env python3
"""
Demo FastAPI app. Quadratic equations solver.
"""
import io

from typing import Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

import solver

app = FastAPI()
app.mount("/static", StaticFiles(directory="static/"), name="static")
templates = Jinja2Templates(directory='templates')

formula_params = ['a', 'b', 'c']  # could be ['a₁', 'a₂', 'a₃'] , for example
default_value = 0.0

#
# Frontend
#

@app.get("/")
async def main(request: Request):
    custom_status = status.HTTP_200_OK
    query = request.query_params

    params = {}  # formula parameters
    errorlines = {}  # error messagess

    # Read query params, allow empty strings
    
    for p in formula_params:
        params[p] = default_value
        if p in query:
            val = query[p]
            try:
                params[p] = float(val)
            except ValueError:
                errorlines[p] = f"Numeric value expected."

    vars = {"request": request, 'params': params, 'errorlines': errorlines}

    # Primitive routing
    if 'action' in query:
        action = query['action']

        if action == 'solve':
            # Imitate API requests 
            # (parallel API requests won't work on the debug server)
            try:
                vars['solution'] = solve(**params)
            except Exception as e:
                vars['errorlines']['exception'] = str(e)
                custom_status = status.HTTP_422_UNPROCESSABLE_ENTITY

            return templates.TemplateResponse("solve.html", vars, status_code=custom_status)

        elif action == 'plot':
            vars['plot_url'] = request.url_for('plot')  # ('plot', **params)  # - not working
            vars['plot_url'] += "?" + '&'.join([f"{k}={v}" for k,v in params.items()])  # FIX: bug in fastapi
            return templates.TemplateResponse("plot.html", vars)
    
    # default action
    return templates.TemplateResponse("index.html", vars)

# NB: Not using POST in the form since python-multipart is not built-in python library
#     (which is a requirement of the task).

# Backend (API)
@app.get("/solve")
def solve(a: float = 0, b: float = 0, c: float = 0):
    pol = solver.Polynom(a, b, c)
    roots = pol.real_roots(round=4)
    return {'roots': list(roots)}


@app.get("/plot")
def plot(a: float = 0, b: float = 0, c: float = 0):
    pol = solver.Polynom(a, b, c)
    buf = io.BytesIO()
    solver.plot_polynom(pol, buf, format="png")
    return StreamingResponse(buf, media_type="image/png")


# Run for debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
