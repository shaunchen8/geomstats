"""Numpy based linear algebra backend."""

import numpy as np
import scipy.linalg
from numpy.linalg import (
    cholesky,
    det,
    eig,
    eigh,
    eigvalsh,
    inv,
    norm,
    solve,
    svd,
)  # NOQA

from .common import to_ndarray


def _is_symmetric(x, tol=1e-12):
    new_x = to_ndarray(x, to_ndim=3)
    return (np.abs(new_x - np.transpose(new_x, axes=(0, 2, 1))) < tol).all()


def expm(x):
    return np.vectorize(scipy.linalg.expm, signature="(n,m)->(n,m)")(x)


def logm(x):
    ndim = x.ndim
    new_x = to_ndarray(x, to_ndim=3)
    if _is_symmetric(new_x):
        eigvals, eigvecs = np.linalg.eigh(new_x)
        if (eigvals > 0).all():
            eigvals = np.log(eigvals)
            eigvals = np.vectorize(np.diag, signature="(n)->(n,n)")(eigvals)
            transp_eigvecs = np.transpose(eigvecs, axes=(0, 2, 1))
            result = np.matmul(eigvecs, eigvals)
            result = np.matmul(result, transp_eigvecs)
        else:
            result = np.vectorize(scipy.linalg.logm, signature="(n,m)->(n,m)")(new_x)
    else:
        result = np.vectorize(scipy.linalg.logm, signature="(n,m)->(n,m)")(new_x)

    if ndim == 2:
        return result[0]
    return result


def solve_sylvester(a, b, q):
    if a.shape == b.shape:
        axes = (0, 2, 1) if a.ndim == 3 else (1, 0)
        if np.all(a == b) and np.all(np.abs(a - np.transpose(a, axes)) < 1e-12):
            eigvals, eigvecs = eigh(a)
            if np.all(eigvals >= 1e-12):
                tilde_q = np.transpose(eigvecs, axes) @ q @ eigvecs
                tilde_x = tilde_q / (eigvals[..., :, None] + eigvals[..., None, :])
                return eigvecs @ tilde_x @ np.transpose(eigvecs, axes)

    return np.vectorize(
        scipy.linalg.solve_sylvester, signature="(m,m),(n,n),(m,n)->(m,n)"
    )(a, b, q)


def sqrtm(x):
    return np.vectorize(scipy.linalg.sqrtm, signature="(n,m)->(n,m)")(x)


def qr(*args, **kwargs):
    return np.vectorize(
        np.linalg.qr, signature="(n,m)->(n,k),(k,m)", excluded=["mode"]
    )(*args, **kwargs)


def _is_single_matrix_pd(mat):
    """Check if a two dimensional square matrix is
    positive definite
    """
    try:
        ch = np.linalg.cholesky(mat)
        return True
    except np.linalg.LinAlgError as e:
        if e.args[0] == "Matrix is not positive definite":
            return False
        else:
            raise e


def is_pd(mat):
    """Check if matrix is positive definite matrix
    (doesn't check if its symmetric)
    """
    if mat.ndim == 2 and mat.shape[0] == mat.shape[1]:
        return _is_single_matrix_pd(mat)
    elif mat.ndim == 2 and mat.shape[0] != mat.shape[1]:
        return False
    elif mat.ndim == 3 and mat.shape[1] == mat.shape[2]:
        return [_is_single_matrix_pd(m) for m in mat]
    elif mat.ndim == 3 and mat.shape[1] != mat.shape[2]:
        return [False] * mat.shape[0]
