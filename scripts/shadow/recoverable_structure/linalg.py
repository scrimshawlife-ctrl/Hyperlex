"""Tiny stdlib linear algebra. No numpy."""


def zeros(n, m=None):
    if m is None:
        return [0.0] * n
    return [[0.0] * m for _ in range(n)]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def scale(a, s):
    return [x * s for x in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def matvec(A, x):
    return [dot(row, x) for row in A]


def transpose(A):
    return [list(col) for col in zip(*A)]


def matmul(A, B):
    Bt = transpose(B)
    return [[dot(row, col) for col in Bt] for row in A]


def identity(n):
    I = zeros(n, n)
    for i in range(n):
        I[i][i] = 1.0
    return I


def solve(A, b):
    n = len(A)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for i in range(n):
        piv = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[piv] = M[piv], M[i]
        if abs(M[i][i]) < 1e-12:
            raise ZeroDivisionError("singular")
        div = M[i][i]
        for j in range(i, n + 1):
            M[i][j] /= div
        for r in range(n):
            if r == i:
                continue
            f = M[r][i]
            for j in range(i, n + 1):
                M[r][j] -= f * M[i][j]
    return [M[i][n] for i in range(n)]


def lstsq(X, y, ridge=1e-6):
    Xt = transpose(X)
    XtX = matmul(Xt, X)
    p = len(XtX)
    for i in range(p):
        XtX[i][i] += ridge
    Xty = matvec(Xt, y)
    return solve(XtX, Xty)


def mse(pred, target):
    n = len(pred)
    if n == 0:
        return 0.0
    s = 0.0
    for a, b in zip(pred, target):
        if isinstance(a, list):
            s += sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)
        else:
            s += (a - b) ** 2
    return s / n
