from numpy import isreal
from numpy.polynomial import Polynomial
from numbers import Number
from collections.abc import Iterable


def _round_to(vals, n):
    """ Round values to <n> decimal places. 
    """
    if isinstance(vals, Number):
        return round(vals, n)
    elif isinstance(vals, Iterable):
        if all((isinstance(x, Number) for x in vals)):
            return list(round(x, n) for x in vals)
    return vals  # fallback


class Polynom(Polynomial):
    def __init__(self, *args):
        coeff = list(reversed(args))  # a,b,c --> c,b,a
        super().__init__(coeff)

    def real_roots(self, round=None):
        roots = self.roots()
        ret = set(roots)  # unique
        ret = [x for x in ret if isreal(x)]  # real
        if round != None:
            ret = _round_to(ret, round)
        return ret
