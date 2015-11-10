from ..general_imports import *
import math

from .. import util
from .martensite import Martensite
from ..crystallography import MatrixGroup, CUBIC_LAUE_GROUP


class TwinSystem():
    """
    A TwinSystem is a set of twinning properties between martensite variants.
    """
    def __init__(self, *args):
        """use two parameters Ulist and Laue, or an Martensite object"""
        if len(args) == 1:
            if isinstance(args[0], Martensite):
                self.__Ulist = args[0].getvariants()
            else:
                try:
                    self.__Ulist = np.array(args[0])
                except:
                    raise ValueError("illegal construction parameters")
            # self.__Laue = CUBIC_LAUE_GROUP.matrices()
            self.__Laue = CUBIC_LAUE_GROUP

        elif len(args) >= 2:
            try:
                self.__Ulist = np.array(args[0])
            except:
                raise ValueError("illegal construction parameters")
            if isinstance(args[1], MatrixGroup):
                self.__Laue = args[1]
        self.__N = len(self.__Ulist)    # Number of variants
        self.__twintable = None
        self.__twinpairs = None

    def Ulist(self):
        """
        :return: the list of U's
        :rtype: :py:class:`numpy.ndarray`
        """
        U = np.empty_like(self.__Ulist)
        U[:] = self.__Ulist
        return U

    def Laue(self):
        """

        :return: the Laue group
        :rtype: :py:class:`pystructrans.MatrixGroup`
        """
        return self.__Laue

    def TwinTable(self):
        """
        get all twinnable variant pairs, in terms of indices in ``Ulist``
        """
        if self.__twintable is None:
            self.__twintable = []
            self.__twinpairs = []
            for i in xrange(self.__N - 1):
                for j in xrange(i + 1, self.__N):
                    tp = TwinPair(self.__Ulist[i], self.__Ulist[j], skipcheck=True)
                    if tp.istwinnable():
                        self.__twintable.append((i, j))
                        self.__twinpairs.append(tp)
        return np.array(self.__twintable)

    def getTwinpairs(self):
        """
        get all twinnable variant pairs, in terms of TwinPair objects
        
        The returned list of TwinPair objects one-to-one correspond
        to the return of :py:meth:`pystructrans.TwinSystem.gettwintable`
        # .. doctest::
        #
        #     >>> ts = TwinSystem(Martensite().setU(0.9, 1.1))
        #     >>> ts.TwinTable()
        #     [(0, 1), (0, 2), (1, 2)]
        #
        #
        #     >>> ts.TwinTable()
        #     [(0, 1), (0, 2), (1, 2)]
        :return: the indices of twinnable variants
        :rtype: a list of indices (i, j) associated with twinnable variants
        """
        if self.__twinpairs is None:
            self.TwinTable()
        return self.__twinpairs

    def getConventional(self):
        """

        :return: the idecies of twintable/twinpairs whose corresponding TwinPair is conventional
        :rtype: :py:class:`list`
        """
        if self.__twinpairs is None:
            self.TwinTable()
        return np.array([i for i in xrange(len(self.__twinpairs))
                if self.__twinpairs[i].isconventional(self.Laue())])

    def getCompound(self):
        """

        :return: the idecies of twintable/twinpairs whose corresponding TwinPair is compound
        :rtype: :py:class:`list`
        """
        if self.__twinpairs is None:
            self.TwinTable()
        return np.array([i for i in xrange(len(self.__twinpairs)) if self.__twinpairs[i].iscompound()])

    def getTypeI(self):
        """

        :return: the idecies of twintable/twinpairs whose corresponding TwinPair is Type I/II
        :rtype: :py:class:`list`
        """
        if self.__twinpairs is None:
            self.TwinTable()
        return np.array([i for i in xrange(len(self.__twinpairs)) if self.__twinpairs[i].istypeI()])

    def getTypeII(self):
        """

        :return: the idecies of twintable/twinpairs whose corresponding TwinPair is Type I/II
        :rtype: :py:class:`list`
        """
        return self.getTypeI()


class TwinPair():
    """
    A TwinPair object is constructed by two symmetry-related
    martensite variants U_i and U_j.
    """
    
    def __init__(self, Ui, Uj, tolerance=1e-5, skipcheck=False):

        if not skipcheck and (not util.utils.pos_def_sym(Ui) or not util.utils.pos_def_sym(Uj)):
            raise ValueError("Ui or Uj is not a 3 x 3 positive definite symmetric matrix")

        self.__Ui = Ui
        self.__Uj = Uj
        self.__tol = tolerance

        Uiinv = la.inv(Ui)
        self.__C = np.dot(Uiinv.dot(Uj), Uj.dot(Uiinv))
        self.__e, self.__v = util.utils.sort_eig(self.__C)

        self.__twinnable = self.istwinnable()
        self.__conventional = None
        self.__ax = None
        self.__XI = None
        self.__XII = None
        self.__twinparam = None
        self.__fI = None
        self.__fII = None

    def Ui(self):
        """

        :return: return U_i
        """
        U = np.empty_like(self.__Ui)
        U[:] = self.__Ui
        return U

    def Uj(self):
        """

        :return: return U_j
        """
        U = np.empty_like(self.__Uj)
        U[:] = self.__Uj
        return U

    def istwinnable(self):
        """
        twinnable means that
        there exists a Q in SO(3) s.t. Ui and Uj are rank1 connected.
        :return: if the twin pair is in fact twinnable
        """
        if np.isclose(np.max(np.abs(self.__Ui - self.__Uj)), 0.0):
            return False
        return abs(self.__e[1] - 1) < self.__tol

    def isconventional(self, *lauegroup):
        """
        lauegroup is a MatrixGroup.
        :return:  if the twin pair is conventionally twinned
        """
        if self.__conventional is None:
            if not self.__twinnable:
                return False
            twofold = CUBIC_LAUE_GROUP.matrices()[1:10] if len(lauegroup) == 0 else lauegroup[0].matrices()
            conventional = False
            for Q in twofold:
                if np.isclose(np.max(np.abs(Q.dot(self.__Ui).dot(Q.T) - self.__Uj)), 0.0):
                    conventional = True
                    break
            self.__conventional = conventional
        return self.__conventional

    def ax(self):
        """

        :return: axes of possible 180 degree rotations relating two variants
        noticed that the length of self.__ax varies and depends on the types of twin system.
        len(self.__ax) = 1 for the type I/II twins
        len(self.__ax) = 2 for the compound twin
        """
        if self.__ax is None:
            if not self.istwinnable():
                raise AttributeError("only twinnable twin pairs have 180 rotation axes")
            As = self.__Ui.dot(self.__Ui)
            A_11 = np.dot(self.__v[0], As.dot(self.__v[0]))
            A_23 = np.dot(self.__v[1], As.dot(self.__v[2]))
            A_13 = np.dot(self.__v[2], As.dot(self.__v[0]))
            A_21 = np.dot(self.__v[1], As.dot(self.__v[0]))
            ehat = []
            for s in [-1, 1]:
                if abs(s * np.sqrt(self.__e[2]) * A_23 + A_21) <= 0.0005:
                    del1 = math.sqrt(2*(A_11 + s * math.sqrt(self.__e[2])*A_13))
                    del3 = s * math.sqrt(self.__e[2]) * del1
                    e = del1 * self.__Ui.dot(self.__v[0]) + del3 * self.__Ui.dot(self.__v[2])
                    ehat.append(e/la.norm(e))
            self.__ax = ehat
        return self.__ax


    def iscompound(self):
        """

        :return: if the twin pair is a compound twin
        """
        return len(self.ax()) > 1

    def istypeI(self):
        """

        :return: if the twin pair is a Type I/II twin
        """
        return not self.iscompound()

    def istypeII(self):
        """

        :return: if the twin pair is a Type I/II twin
        """
        return not self.iscompound()

    def XI(self):
        """

        :return:  cofactor parameter for Type I twin
        """
        if self.iscompound():
            raise AttributeError("parameter X_I is not defined for compound twins")
        if self.__XI is None:
            t_ax = self.ax()[0]
            self.__XI = la.norm(la.inv(self.__Ui).dot(t_ax))
        return self.__XI

    def XII(self):
        """

        :return:  cofactor parameter for Type II twin
        """
        if self.iscompound():
            raise AttributeError("parameter X_I is not defined for compound twins")
        if self.__XII is None:
            t_ax = self.ax()[0]
            self.__XII = la.norm(self.__Ui.dot(t_ax))
        return self.__XII

    def direct_cof(self):
        """

        :return: values of the cofactor conditions directly calculated from
        U.a.cof(U^2-I)n
        :rtype: (XI, XII)
        """
        U = self.Ui()
        (Q1, a1, n1), (Q2, a2, n2) = self.twinparam()
        A = U.dot(U) - np.eye(3)
        cofU = _brute_cof(A)
        return -np.dot(U.dot(a1), cofU.dot(n1)), -np.dot(U.dot(a2), cofU.dot(n2))


    def twinparam(self):
        """

        :return: twin parameters of the twin pair if it is twinnable
        :rtype: (Q1, a1, n1), (Q2, a2, n2)
        """
        if not self.istwinnable():
            raise AttributeError("only twinnable twin pairs have twin parameters")

        if self.__twinparam is None:
            if len(self.ax()) > 0.0:
                t_ax = self.ax()[0]
                self.__twinparam = _solvetwin(self.__Ui, self.__Uj, t_ax, self.__tol)
            else:
                self.__twinparam = _solvetwin(self.__Ui, self.__Uj, None, self.__tol)

        return self.__twinparam




    def volumefrac(self):
        """

        :return: twinning volume fractions for the Austenite/Martensite
        interfaces given by (U, aI, nI)/I and (U, aII, nII)/I where
        (aI, nI) and (aII, nII) are the twinparam()[0][1:] and twinparam()[1][1:]
        """
        if not self.twinparam()[0] == None:
            aI, nI = self.twinparam()[0][1:]
            self.__fI = _solve_f(self.__Ui, aI, nI)
        else:
            self.__fI = None

        if not self.twinparam()[1] == None:
            aII, nII = self.twinparam()[1][1:]
            # print("aII = {}, nII = {}".format(aII, nII))
            self.__fII = _solve_f(self.__Ui, aII, nII)
        else:
            self.__fII = None

        return self.__fI, self.__fII

    def habitplanes(self, twintype="C"):
        """

        :return: habit planes, two for each Type I, II, four for compound
        """
        if twintype not in ["I", "II", "C"]:
            raise ValueError("unknown twin type {:s}", str(twintype))
        if not self.istwinnable():
            raise AttributeError("twin pair is not twinnable!")

        tp = self.twinparam()
        fs = self.volumefrac()
        if not isinstance(fs, tuple):
            fs = (fs, )
        hps = []

        for i, f in enumerate(fs):
            a = tp[i][1]
            n = tp[i][2]
            Uf = [self.__Ui + f * np.outer(a, n),
                  self.__Ui + (1.0 - f) * np.outer(a, n)]
            hps.extend(_solve_am(Uf[0].T.dot(Uf[0]), self.__tol))
            hps.extend(_solve_am(Uf[1].T.dot(Uf[1]), self.__tol))


        # [(R, b, m), (R, b, m), (R, b, m), (R, b, m)]
        return hps


#     def satisfyCofI(self):
#         if abs(self.XI()-1)<1e-4:
#             return True
#         else:
#             return False
#     def satisfyCofII(self):
#         if abs(self.XII()-1)<1e-4:
#             return True
#         else:
#             return False

#         self._ax = [[1,0,0],[0,1,0],[0,0,1],
#                     [1/sqrt(2), 1/sqrt(2), 0], [1/sqrt(2), -1/sqrt(2), 0],
#                     [1/sqrt(2), 0, 1/sqrt(2)], [1/sqrt(2), 0, -1/sqrt(2)],
#                     [0, 1/sqrt(2), 1/sqrt(2)], [0, 1/sqrt(2), 1/sqrt(2)]]

def _solvetwin(U, Uj, e, tol_twin):
    """
    find the two solutions to the twinning equation
    """
    if not e == None:
        ehat = e/la.norm(e)
        Uinv = la.inv(U)
        R180 = -np.eye(3) + 2*np.outer(ehat, ehat)
        uj = np.dot(R180.dot(U), R180.T)
        if _isvariant(U, Uj):
            # print("This is normal twin")
            n1 = e
            denominator = np.dot(np.dot(Uinv, e), np.dot(Uinv, e))
            a1 = 2 * (Uinv.dot(e)/denominator - U.dot(e))
            rho = la.norm(n1)
            n1 = np.round(n1/rho, 10)
            a1 = np.round(rho * a1, 10)
            Q1 = (U + np.outer(a1, n1)).dot(la.inv(uj))

            n2 = 2 * (e - np.dot(U, U.dot(e))/np.dot(U.dot(e), U.dot(e)))
            a2 = U.dot(e)
            rho = la.norm(n2)
            n2 = np.round(n2/rho, 10)
            a2 = np.round(rho * a2, 10)
            Q2 = (U + np.outer(a2, n2)).dot(la.inv(uj))
            return (Q1, a1, n1), (Q2, a2, n2)
        else:
            cmix = np.dot(la.inv(U).dot(Uj), Uj.dot(la.inv(U)))
            #print("This is abnormal twin!")
            (Q1, hat_a1, hat_n1), (Q2, hat_a2, hat_n2) = _solve_am(cmix, tol_twin)
            rho1 = la.norm(U.T.dot(hat_n1))
            rho2 = la.norm(U.T.dot(hat_n2))
            n1 = U.T.dot(hat_n1)/rho1
            a1 = rho1*hat_a1
            n2 = U.T.dot(hat_n2)/rho2
            a2 = rho2*hat_a2
            return (Q1, a1, n1), (Q2, a2, n2)

    else:
            cmix = np.dot(la.inv(U).dot(Uj), Uj.dot(la.inv(U)))
            #print "This twin is not rank 1 connected!"
            (Q1, hat_a1, hat_n1), (Q2, hat_a2, hat_n2) = _solve_am(cmix, tol_twin)
            # print hat_n1, hat_n2
            rho1 = la.norm(U.T.dot(hat_n1))
            rho2 = la.norm(U.T.dot(hat_n2))
            n1 = U.T.dot(hat_n1)/rho1
            a1 = rho1*hat_a1
            n2 = U.T.dot(hat_n2)/rho2
            a2 = rho2*hat_a2
            return (Q1, a1, n1), (Q2, a2, n2)

def _solve_f(U, a, n):
    """
    the volume fraction for the nonlinear equation 
    (U + f n \otimes a)(U + f a \otimes n) = (I + m \otimes b)(I + b \otimes m)
    """
    A = U.dot(U) - np.eye(3)
    cofU = _brute_cof(A)
    minus_alpha = 2 * np.dot(U.dot(a), cofU.dot(n))
    beta = la.det(U.dot(U)-np.eye(3)) + minus_alpha / 4.0
    if np.abs(minus_alpha) < 0.0:
        return 0.0
    elif beta/minus_alpha > 0.0:
        f = 0.5 + math.sqrt(beta / minus_alpha)
        if abs(1 - f) < 1E-6:
            return 1
        elif abs(f) < 1E-6:
            return 0
        elif f > 0.0 and f < 1.0:
            return f
        else:
            return None
    else:
        return None

def _solve_am(C, tol_interface):
    """
    solve austenite/twinned martensite equation
    :param C: 3x3 matrix, det A > 0, A = A^T
    :param B: 3x3 matrix, det B > 0, B = B^T
    :param tol_var: real numbers
    :return: (R1, b1, m1), (R2, b2, m2)
    """
    # C = np.dot(la.inv(B).dot(A), A.dot(la.inv(B)))

    if not util.utils.pos_def_sym(C):
        raise TypeError('The input should be a positive symmetric matrix! {:s}'.format(str(C)))

    eval, evec = util.utils.sort_eig(C)
    c = math.sqrt(eval[2] - eval[0])
    c1 = math.sqrt(abs(1 - eval[0]))
    c3 = math.sqrt(abs(eval[2] - 1))
    kappa = 1

    if np.isclose(c, 0.0):
        # TODO: solution is b = e, m = - 2 e where |e| = 1.
        print('solution is b = e, m = - 2 e where |e| = 1.')
        return
    else:
        # if _iscompatible(C, tol_interface):
        if True:
            m1 = ((math.sqrt(eval[2]) - math.sqrt(eval[0])) / c) * (-c1 * evec[0] + kappa * c3 * evec[2])
            m2 = ((math.sqrt(eval[2]) - math.sqrt(eval[0])) / c) * (-c1 * evec[0] - kappa * c3 * evec[2])
            rho1 = la.norm(m1)
            rho2 = la.norm(m2)
            m1 /= rho1
            m2 /= rho2
            b1 = rho1 * ((math.sqrt(eval[2]) * c1 / c) * evec[0] + kappa*(math.sqrt(eval[0]) * c3 / c) * evec[2])
            b2 = rho2 * ((math.sqrt(eval[2]) * c1 / c) * evec[0] - kappa*(math.sqrt(eval[0]) * c3 / c) * evec[2])
            ec, vc = la.eig(C)
            ec = np.sqrt(ec)
            Csqrt = np.dot(vc.dot(np.diag(ec)), la.inv(vc))
            # print(la.norm((Csqrt.dot(Csqrt) - C).reshape(9))<1e-4)
            R1 = (np.eye(3) + np.outer(b1, m1)).dot(la.inv(Csqrt))
            R2 = (np.eye(3) + np.outer(b2, m2)).dot(la.inv(Csqrt))
            # print m1, m2
            return (R1, b1, m1), (R2, b2, m2)
        else:
            return None, None

def _brute_cof(A):
    """compute cofactor of M brutely"""
    m,n = A.shape
    minor = []
    if m == n:
        for i in xrange(m):
            for j in xrange(n):
                a = np.delete(A, i, axis=0)
                a = np.delete(a, j, axis=1)
                minor = np.append(minor, (-1)**(i+j)*la.det(a))
        return np.array(minor).reshape(3, 3)
    else:
        raise TypeError('Please input a square matrix.')

def _isvariant(U, V):
    """check if U and V are variants of a Martensite object"""
    ulist = Martensite(U).getvariants()
    flag = 0
    for u in ulist:
        dv = (V - u).reshape(9)
        if abs(la.norm(dv) - 0.0) < 0.0000001:
            flag+=1
    if flag == 0:
        return False
    else:
        return True



def _iscompatible(C, tol_var):
    """
    :param C: 3x3 matrix, det A > 0, A = A^T
    :param B: 3x3 matrix, det B > 0, B = B^T
    :param tol_var: real numbers
    :return: True if there exist a rotation Q s.t. QA - B = rank 1
    """
    # C = np.dot(la.inv(B).dot(A), A.dot(la.inv(B)))
    eval, _ = util.utils.sort_eig(C)
    if np.abs(eval[1] - 1.0) < tol_var:
        return True
    else:
        return False
