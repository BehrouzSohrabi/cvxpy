"""
Copyright 2013 Steven Diamond

This file is part of CVXPY.

CVXPY is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CVXPY is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with CVXPY.  If not, see <http://www.gnu.org/licenses/>.
"""

from cvxpy import settings as s
from cvxpy.expressions.leaf import Leaf
import cvxpy.lin_ops.lin_utils as lu
from cvxpy.constraints.psd import PSD
import scipy.sparse as sp


def upper_tri_to_full(n):
    """Returns a coefficient matrix to create a symmetric matrix.

    Parameters
    ----------
    n : int
        The width/height of the matrix.

    Returns
    -------
    SciPy CSC matrix
        The coefficient matrix.
    """
    entries = n*(n+1)//2

    val_arr = []
    row_arr = []
    col_arr = []
    count = 0
    for i in range(n):
        for j in range(i, n):
            # Index in the original matrix.
            col_arr.append(count)
            # Index in the filled matrix.
            row_arr.append(j*n + i)
            val_arr.append(1.0)
            if i != j:
                # Index in the original matrix.
                col_arr.append(count)
                # Index in the filled matrix.
                row_arr.append(i*n + j)
                val_arr.append(1.0)
            count += 1

    return sp.coo_matrix((val_arr, (row_arr, col_arr)),
                         (n*n, entries)).tocsc()


class Variable(Leaf):
    """ The base variable class """

    def __init__(self, shape=(), name=None, var_id=None, **kwargs):
        if var_id is None:
            self.id = lu.get_id()
        else:
            self.id = var_id
        if name is None:
            self._name = "%s%d" % (s.VAR_PREFIX, self.id)
        else:
            self._name = name
        self.primal_value = None

        super(Variable, self).__init__(shape, **kwargs)


    def name(self):
        return self._name

    def save_value(self, value):
        """Save the value of the primal variable.
        """
        # # HACK change vector into symmetric matrix.
        # if value is not None and any([self.attributes[key] for key in ['symmetric', 'PSD', 'NSD']]):
        #     n = self.shape[0]
        #     shape = (n*(n+1)//2, 1)
        #     value = upper_tri_to_full(n)*value.flatten('F')[:shape[0]]
        #     value = np.reshape(value, (n, n), 'F')

        self.primal_value = value

    @property
    def value(self):
        return self.primal_value

    @value.setter
    def value(self, val):
        """Assign a value to the variable.
        """
        val = self._validate_value(val)
        self.save_value(val)

    @property
    def grad(self):
        """Gives the (sub/super)gradient of the expression w.r.t. each variable.

        Matrix expressions are vectorized, so the gradient is a matrix.

        Returns:
            A map of variable to SciPy CSC sparse matrix or None.
        """
        return {self: sp.eye(self.shape[0]*self.shape[1]).tocsc()}

    def variables(self):
        """Returns itself as a variable.
        """
        return [self]

    def canonicalize(self):
        """Returns the graph implementation of the object.

        Returns:
            A tuple of (affine expression, [constraints]).
        """
        if self.is_symmetric():
            n = self.shape[0]
            shape = (n*(n+1)//2, 1)
            obj = lu.create_var(shape, self.id)
            mat = lu.create_const(upper_tri_to_full(n), (n*n, shape[0]), sparse=True)
            obj = lu.mul_expr(mat, obj, (n*n, 1))
            obj = lu.reshape(obj, (n, n))
        else:
            obj = lu.create_var(self.shape, self.id)

        constr = []
        if self.is_nonneg():
            constr.append(lu.create_geq(obj))
        elif self.is_nonpos():
            constr.append(lu.create_leq(obj))
        elif self.attributes['PSD']:
            constr.append(PSD(obj))
        elif self.attributes['NSD']:
            constr.append(PSD(lu.neg(obj)))
        return (obj, constr)

    def __repr__(self):
        """String to recreate the object.
        """
        return "Variable(%s)" % (self.shape,)
