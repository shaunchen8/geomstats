"""
The n-dimensional hypersphere
embedded in the (n+1)-dimensional Euclidean space.
"""

import logging
import math

import geomstats.backend as gs
from geomstats.geometry.embedded_manifold import EmbeddedManifold
from geomstats.geometry.euclidean_space import EuclideanMetric
from geomstats.geometry.euclidean_space import EuclideanSpace
from geomstats.geometry.riemannian_metric import RiemannianMetric

TOLERANCE = 1e-6
EPSILON = 1e-8

COS_TAYLOR_COEFFS = [1., 0.,
                     - 1.0 / math.factorial(2), 0.,
                     + 1.0 / math.factorial(4), 0.,
                     - 1.0 / math.factorial(6), 0.,
                     + 1.0 / math.factorial(8), 0.]
INV_SIN_TAYLOR_COEFFS = [0., 1. / 6.,
                         0., 7. / 360.,
                         0., 31. / 15120.,
                         0., 127. / 604800.]
INV_TAN_TAYLOR_COEFFS = [0., - 1. / 3.,
                         0., - 1. / 45.,
                         0., - 2. / 945.,
                         0., -1. / 4725.]


class Hypersphere(EmbeddedManifold):
    """
    Class for the n-dimensional hypersphere
    embedded in the (n+1)-dimensional Euclidean space.

    By default, points are parameterized by their extrinsic (n+1)-coordinates.
    """

    def __init__(self, dimension):
        assert isinstance(dimension, int) and dimension > 0
        super(Hypersphere, self).__init__(
                dimension=dimension,
                embedding_manifold=EuclideanSpace(dimension+1))
        self.embedding_metric = self.embedding_manifold.metric
        self.metric = HypersphereMetric(dimension)

    def belongs(self, point, tolerance=TOLERANCE):
        """
        Evaluate if a point belongs to the Hypersphere,
        i.e. evaluate if its squared norm in the Euclidean space is 1.

        Parameters
        ----------
        point : array-like, shape=[n_samples, dimension + 1]
                Input points.
        tolerance : float, optional

        Returns
        -------
        belongs : array-like, shape=[n_samples, 1]
        """
        point = gs.asarray(point)
        point_dim = point.shape[-1]
        if point_dim != self.dimension + 1:
            if point_dim is self.dimension:
                logging.warning(
                    'Use the extrinsic coordinates to '
                    'represent points on the hypersphere.')
            return gs.array([[False]])
        sq_norm = self.embedding_metric.squared_norm(point)
        diff = gs.abs(sq_norm - 1)
        return gs.less_equal(diff, tolerance)

    def regularize(self, point):
        """
        Regularize a point to the canonical representation
        chosen for the Hypersphere, to avoid numerical issues.

        Parameters
        ----------
        point : array-like, shape=[n_samples, dimension + 1]
                Input points.

        Returns
        -------
        projected_point : array-like, shape=[n_samples, dimension + 1]
        """
        assert gs.all(self.belongs(point))

        return self.projection(point)

    def projection(self, point):
        """
        Project a point on the Hypersphere.
        """
        point = gs.to_ndarray(point, to_ndim=2)

        norm = self.embedding_metric.norm(point)
        projected_point = point / norm

        return projected_point

    def projection_to_tangent_space(self, vector, base_point):
        """
        Project a vector in Euclidean space
        on the tangent space of the Hypersphere at a base point.

        Parameters
        ----------
        vector : array-like, shape=[n_samples, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]

        Returns
        -------
        tangent_vec : array-like, shape=[n_samples, dimension + 1]
        """
        vector = gs.to_ndarray(vector, to_ndim=2)
        base_point = gs.to_ndarray(base_point, to_ndim=2)

        sq_norm = self.embedding_metric.squared_norm(base_point)
        inner_prod = self.embedding_metric.inner_product(base_point, vector)
        coef = inner_prod / sq_norm
        tangent_vec = vector - gs.einsum('ni,nj->nj', coef, base_point)

        return tangent_vec

    def spherical_to_extrinsic(self, point_spherical):
        """
        Convert from the spherical coordinates in the Hypersphere
        to the extrinsic coordinates in Euclidean space.
        Only implemented in dimension 2.

        Parameters
        ----------
        point_spherical : array-like, shape=[n_samples, dimension]

        Returns
        -------
        point_extrinsic : array_like, shape=[n_samples, dimension + 1]
        """
        if self.dimension != 2:
            raise NotImplementedError(
                    'The conversion from spherical coordinates'
                    ' to extrinsic coordinates is implemented'
                    ' only in dimension 2.')
        point_spherical = gs.to_ndarray(point_spherical, to_ndim=2)
        theta = point_spherical[:, 0]
        phi = point_spherical[:, 1]
        point_extrinsic = gs.zeros(
                (point_spherical.shape[0], self.dimension+1))
        point_extrinsic[:, 0] = gs.sin(theta) * gs.cos(phi)
        point_extrinsic[:, 1] = gs.sin(theta) * gs.sin(phi)
        point_extrinsic[:, 2] = gs.cos(theta)
        assert self.belongs(point_extrinsic).all()

        return point_extrinsic

    def tangent_spherical_to_extrinsic(self, tangent_vec_spherical,
                                       base_point_spherical):
        """
        Convert from the spherical coordinates in the Hypersphere
        to the extrinsic coordinates in Euclidean space for a tangent
        vector. Only implemented in dimension 2.

        Parameters
        ----------
        tangent_vec_spherical : array-like, shape=[n_samples, dimension]
        base_point_spherical : array-like, shape=[n_samples, dimension]

        Returns
        -------
        tangent_vec_extrinsic : array-like, shape=[n_samples, dimension + 1]
        """
        if self.dimension != 2:
            raise NotImplementedError(
                    'The conversion from spherical coordinates'
                    ' to extrinsic coordinates is implemented'
                    ' only in dimension 2.')
        base_point_spherical = gs.to_ndarray(base_point_spherical, to_ndim=2)
        tangent_vec_spherical = gs.to_ndarray(tangent_vec_spherical, to_ndim=2)
        n_samples = base_point_spherical.shape[0]
        theta = base_point_spherical[:, 0]
        phi = base_point_spherical[:, 1]
        jac = gs.zeros((n_samples, self.dimension + 1, self.dimension))
        jac[:, 0, 0] = gs.cos(theta) * gs.cos(phi)
        jac[:, 0, 1] = - gs.sin(theta) * gs.sin(phi)
        jac[:, 1, 0] = gs.cos(theta) * gs.sin(phi)
        jac[:, 1, 1] = gs.sin(theta) * gs.cos(phi)
        jac[:, 2, 0] = - gs.sin(theta)
        tangent_vec_extrinsic = gs.einsum('nij,nj->ni', jac,
                                          tangent_vec_spherical)

        return tangent_vec_extrinsic

    def intrinsic_to_extrinsic_coords(self, point_intrinsic):
        """
        Convert from the intrinsic coordinates in the Hypersphere,
        to the extrinsic coordinates in Euclidean space.

        Parameters
        ----------
        point_intrinsic : array-like, shape=[n_samples, dimension]

        Returns
        -------
        point_extrinsic : array-like, shape=[n_samples, dimension + 1]
        """
        point_intrinsic = gs.to_ndarray(point_intrinsic, to_ndim=2)

        # FIXME: The next line needs to be guarded against taking the sqrt of
        #        negative numbers.
        coord_0 = gs.sqrt(1. - gs.linalg.norm(point_intrinsic, axis=-1) ** 2)
        coord_0 = gs.to_ndarray(coord_0, to_ndim=2, axis=-1)

        point_extrinsic = gs.concatenate([coord_0, point_intrinsic], axis=-1)

        return point_extrinsic

    def extrinsic_to_intrinsic_coords(self, point_extrinsic):
        """
        Convert from the extrinsic coordinates in Euclidean space,
        to some intrinsic coordinates in Hypersphere.

        Parameters
        ----------
        point_extrinsic : array-like, shape=[n_samples, dimension + 1]

        Returns
        -------
        point_intrinsic : array-like, shape=[n_samples, dimension]
        """
        point_extrinsic = gs.to_ndarray(point_extrinsic, to_ndim=2)

        point_intrinsic = point_extrinsic[:, 1:]

        return point_intrinsic

    def random_uniform(self, n_samples=1):
        """
        Sample in the Hypersphere with the uniform distribution.

        Parameters
        ----------
        n_samples : int, optional

        Returns
        -------
        samples : array-like, shape=[n_samples, dimension + 1]
        """
        size = (n_samples, self.dimension + 1)

        samples = gs.random.normal(size=size)
        while True:
            norms = gs.linalg.norm(samples, axis=1)
            indcs = gs.isclose(norms, 0.0)
            num_bad_samples = gs.sum(indcs)
            if num_bad_samples == 0:
                break
            samples[indcs, :] = gs.random.normal(
                size=(num_bad_samples, self.dimension + 1))

        return gs.einsum('n, ni->ni', 1 / norms, samples)

    def random_von_mises_fisher(self, kappa=10, n_samples=1):
        """
        Sample in the 2-sphere with the von Mises distribution centered in the
        north pole.
        """
        if self.dimension != 2:
            raise NotImplementedError(
                    'Sampling from the von Mises Fisher distribution'
                    'is only implemented in dimension 2.')
        angle = 2. * gs.pi * gs.random.rand(n_samples)
        angle = gs.to_ndarray(angle, to_ndim=2, axis=1)
        unit_vector = gs.hstack((gs.cos(angle), gs.sin(angle)))
        scalar = gs.random.rand(n_samples)

        coord_z = 1. + 1. / kappa * gs.log(
            scalar + (1. - scalar) * gs.exp(gs.array(-2. * kappa)))
        coord_z = gs.to_ndarray(coord_z, to_ndim=2, axis=1)

        coord_xy = gs.sqrt(1. - coord_z**2) * unit_vector

        point = gs.hstack((coord_xy, coord_z))

        return point


class HypersphereMetric(RiemannianMetric):

    def __init__(self, dimension):
        super(HypersphereMetric, self).__init__(
                dimension=dimension,
                signature=(dimension, 0, 0))
        self.embedding_metric = EuclideanMetric(dimension + 1)

    def inner_product(self, tangent_vec_a, tangent_vec_b, base_point=None):
        """
        Inner product.

        Parameters
        ----------
        tangent_vec_a : array-like, shape=[n_samples, dimension + 1]
                                    or shape=[1, dimension + 1]
        tangent_vec_b : array-like, shape=[n_samples, dimension + 1]
                                    or shape=[1, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]
                                 or shape=[1, dimension + 1]

        Returns
        -------
        inner_prod : array-like, shape=[n_samples, 1]
                                 or shape=[1, 1]
        """
        inner_prod = self.embedding_metric.inner_product(
                tangent_vec_a, tangent_vec_b, base_point)

        return inner_prod

    def squared_norm(self, vector, base_point=None):
        """
        Squared norm of a vector associated to the inner product
        at the tangent space at a base point.

        Parameters
        ----------
        vector : array-like, shape=[n_samples, dimension + 1]
                             or shape=[1, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]
                                 or shape=[1, dimension + 1]

        Returns
        -------
        sq_norm : array-like, shape=[n_samples, 1]
                              or shape=[1, 1]
        """
        sq_norm = self.embedding_metric.squared_norm(vector)
        return sq_norm

    def exp(self, tangent_vec, base_point):
        """
        Riemannian exponential of a tangent vector wrt to a base point.

        Parameters
        ----------
        tangent_vec : array-like, shape=[n_samples, dimension + 1]
                                  or shape=[1, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]
                                 or shape=[1, dimension + 1]

        Returns
        -------
        exp : array-like, shape=[n_samples, dimension + 1]
                          or shape=[1, dimension + 1]
        """
        tangent_vec = gs.to_ndarray(tangent_vec, to_ndim=2)
        base_point = gs.to_ndarray(base_point, to_ndim=2)

        # TODO(nina): Decide on metric.space or space.metric
        #  for the hypersphere
        # TODO(nina): Raise error when vector is not tangent
        n_base_points, extrinsic_dim = base_point.shape
        n_tangent_vecs, _ = tangent_vec.shape
        n_exps = gs.cast(gs.maximum(n_base_points, n_tangent_vecs), gs.int32)

        hypersphere = Hypersphere(dimension=extrinsic_dim-1)
        proj_tangent_vec = hypersphere.projection_to_tangent_space(
            tangent_vec, base_point)
        norm_tangent_vec = self.embedding_metric.norm(proj_tangent_vec)

        n_tiles_vec = gs.cast(gs.divide(n_exps, n_tangent_vecs), gs.int32)
        norm_tangent_vec = gs.tile(norm_tangent_vec, [n_tiles_vec, 1])
        n_tiles_base_point = gs.cast(
            gs.divide(n_exps, n_base_points), gs.int32)
        base_point = gs.tile(base_point, [n_tiles_base_point, 1])

        mask_0 = gs.isclose(norm_tangent_vec, 0.)
        mask_non0 = ~mask_0

        coef_1 = gs.zeros((n_exps, 1))
        coef_2 = gs.zeros((n_exps, 1))
        norm2 = norm_tangent_vec[mask_0]**2
        norm4 = norm2**2
        norm6 = norm2**3
        coef_1[mask_0] = 1. - norm2/2. + norm4/24. - norm6/720.
        coef_2[mask_0] = 1. - norm2/6. + norm4/120. - norm6/5040.

        coef_1[mask_non0] = gs.cos(norm_tangent_vec[mask_non0])
        coef_2[mask_non0] = gs.sin(norm_tangent_vec[mask_non0]) / \
            norm_tangent_vec[mask_non0]
        exp = (gs.einsum('ni,nj->nj', coef_1, base_point)
               + gs.einsum('ni,nj->nj', coef_2, proj_tangent_vec))

        return exp

    def log(self, point, base_point):
        """
        Riemannian logarithm of a point wrt a base point.

        Parameters
        ----------
        point : array-like, shape=[n_samples, dimension + 1]
                            or shape=[1, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]
                                 or shape=[1, dimension + 1]

        Returns
        -------
        log : array-like, shape=[n_samples, dimension + 1]
                          or shape=[1, dimension + 1]
        """
        point = gs.to_ndarray(point, to_ndim=2)
        base_point = gs.to_ndarray(base_point, to_ndim=2)

        norm_base_point = self.embedding_metric.norm(base_point)
        norm_point = self.embedding_metric.norm(point)
        inner_prod = self.embedding_metric.inner_product(base_point, point)
        cos_angle = inner_prod / (norm_base_point * norm_point)
        cos_angle = gs.clip(cos_angle, -1., 1.)

        angle = gs.arccos(cos_angle)
        angle = gs.to_ndarray(angle, to_ndim=1)
        angle = gs.to_ndarray(angle, to_ndim=2, axis=1)

        mask_0 = gs.isclose(angle, 0.)
        mask_else = gs.equal(mask_0, gs.array(False))

        mask_0_float = gs.cast(mask_0, gs.float32)
        mask_else_float = gs.cast(mask_else, gs.float32)

        coef_1 = gs.zeros_like(angle)
        coef_2 = gs.zeros_like(angle)

        coef_1 += mask_0_float * (
           1. + INV_SIN_TAYLOR_COEFFS[1] * angle ** 2
           + INV_SIN_TAYLOR_COEFFS[3] * angle ** 4
           + INV_SIN_TAYLOR_COEFFS[5] * angle ** 6
           + INV_SIN_TAYLOR_COEFFS[7] * angle ** 8)
        coef_2 += mask_0_float * (
           1. + INV_TAN_TAYLOR_COEFFS[1] * angle ** 2
           + INV_TAN_TAYLOR_COEFFS[3] * angle ** 4
           + INV_TAN_TAYLOR_COEFFS[5] * angle ** 6
           + INV_TAN_TAYLOR_COEFFS[7] * angle ** 8)

        # This avoids division by 0.
        angle += mask_0_float * 1.

        coef_1 += mask_else_float * angle / gs.sin(angle)
        coef_2 += mask_else_float * angle / gs.tan(angle)

        log = (gs.einsum('ni,nj->nj', coef_1, point)
               - gs.einsum('ni,nj->nj', coef_2, base_point))

        mask_same_values = gs.isclose(point, base_point)

        mask_else = gs.equal(mask_same_values, gs.array(False))
        mask_else_float = gs.cast(mask_else, gs.float32)
        mask_else_float = gs.to_ndarray(mask_else_float, to_ndim=1)
        mask_else_float = gs.to_ndarray(mask_else_float, to_ndim=2)
        mask_not_same_points = gs.sum(mask_else_float, axis=1)
        mask_same_points = gs.isclose(mask_not_same_points, 0.)
        mask_same_points = gs.cast(mask_same_points, gs.float32)
        mask_same_points = gs.to_ndarray(mask_same_points, to_ndim=2, axis=1)

        mask_same_points_float = gs.cast(mask_same_points, gs.float32)

        log -= mask_same_points_float * log

        return log

    def dist(self, point_a, point_b):
        """
        Geodesic distance between two points.

        Parameters
        ----------
        point_a : array-like, shape=[n_samples, dimension + 1]
                              or shape=[1, dimension + 1]
        point_b : array-like, shape=[n_samples, dimension + 1]
                              or shape=[1, dimension + 1]

        Returns
        -------
        dist : array-like, shape=[n_samples, 1]
                           or shape=[1, 1]
        """
        norm_a = self.embedding_metric.norm(point_a)
        norm_b = self.embedding_metric.norm(point_b)
        inner_prod = self.embedding_metric.inner_product(point_a, point_b)

        cos_angle = inner_prod / (norm_a * norm_b)
        cos_angle = gs.clip(cos_angle, -1, 1)

        dist = gs.arccos(cos_angle)

        return dist

    def parallel_transport(self, tangent_vec_a, tangent_vec_b, base_point):
        """Parallel transport of a tangent vector.

        Closed-form solution for the parallel transport of a tangent vector a
        along the geodesic defined by :math: `exp_(base_point)(tangent_vec_b)`

        Parameters
        ----------
        tangent_vec_a : array-like, shape=[n_samples, dimension + 1]
        tangent_vec_b : array-like, shape=[n_samples, dimension + 1]
        base_point : array-like, shape=[n_samples, dimension + 1]

        Returns
        -------
        transported_tangent_vec: array-like, shape=[n_samples, dimension + 1]
        """
        tangent_vec_a = gs.to_ndarray(tangent_vec_a, to_ndim=2)
        tangent_vec_b = gs.to_ndarray(tangent_vec_b, to_ndim=2)
        base_point = gs.to_ndarray(base_point, to_ndim=2)
        # TODO @nguigs: work around this condition
        assert len(base_point) == len(tangent_vec_a) == len(tangent_vec_b)
        theta = gs.linalg.norm(tangent_vec_b, axis=1)
        normalized_b = gs.einsum('n, ni->ni', 1 / theta, tangent_vec_b)
        pb = gs.einsum('ni,ni->n', tangent_vec_a, normalized_b)
        p_orth = tangent_vec_a - gs.einsum('n,ni->ni', pb, normalized_b)
        transported = - gs.einsum('n,ni->ni', gs.sin(theta) * pb, base_point)\
            + gs.einsum('n,ni->ni', gs.cos(theta) * pb, normalized_b)\
            + p_orth
        return transported

    def christoffels(self, point, point_type='spherical'):
        """
        Christoffel symbols. Only implemented in dimension 2
        and for spherical coordinates.

        Parameters
        ----------
        point : array-like, shape=[n_samples, dimension]

        point_type: str

        Returns
        -------
        christoffel : array-like, shape=[n_samples,
                                         contravariant index,
                                         first covariant index,
                                         second covariant index]
        """
        if self.dimension != 2 or point_type != 'spherical':
            raise NotImplementedError(
                    'The Christoffel symbols are only implemented'
                    ' for spherical coordinates in the 2-sphere')

        point = gs.to_ndarray(point, to_ndim=2)
        christoffel = []
        for p in point:
            gamma_0 = gs.array(
                [[0, 0], [0, - gs.sin(p[0]) * gs.cos(p[0])]])
            gamma_1 = gs.array([[0, gs.cos(p[0]) / gs.sin(p[0])],
                                [gs.cos(p[0]) / gs.sin(p[0]), 0]])
            christoffel.append(gs.stack([gamma_0, gamma_1]))

        return gs.stack(christoffel)
