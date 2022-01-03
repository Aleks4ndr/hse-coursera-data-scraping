
import numpy as np
import matplotlib 
import matplotlib.pyplot as plt

matplotlib.use('Agg')

def plot_polynom(poly, buf=None, format='png'):
    fig = plt.figure() 
    # cartesian cross
    ax = plt.gca()
    ax.spines['top'].set_color('none')
    ax.spines['bottom'].set_position('zero')
    ax.spines['left'].set_position('zero')
    ax.spines['right'].set_color('none')

    roots = poly.real_roots(round=3)
    left, right = -10, 10

    if roots:
        left = min(roots)
        right = max(roots)
        left -= 1
        right += 1 

        for i, root in enumerate(roots):
            plt.plot(root, 0, 'ro', label=str(root))

        plt.legend(title="Roots:")

    x = np.linspace(left, right, num=20)
    plt.plot(x, poly(x))

    if buf:
        fig.savefig(buf, transparent=True)
        buf.seek(0)
        return buf
    else:
        return plt

        
        
        
        