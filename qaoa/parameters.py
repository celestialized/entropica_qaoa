"""Different parametrizations of QAOA circuits.

This module holds an abstract class to store QAOA parameters in and (so far)
four derived classes that allow for more or less degrees of freedom in the QAOA
Ansätze

Todo
----
 - Better default values for ``time`` if ``None`` is passed
 - Better default parameters for ``fourier`` timesteps
 - implement AbstractQAOAParameters.linear_ramp_from_hamiltonian() and then super() from it
"""

from typing import Iterable, Union, List, Tuple, Any, Type
import warnings
from custom_inherit import DocInheritMeta

# from custom_inherit import DocInheritMeta
import matplotlib.pyplot as plt
import numpy as np

from pyquil.paulis import PauliSum


def _is_list_empty(in_list):
    if isinstance(in_list, list):    # Is a list
        return all(map(_is_list_empty, in_list))
    return False    # Not a list


class AbstractQAOAParameters(metaclass=DocInheritMeta(style="numpy")):
    """
    An abstract class to hold the parameters of a QAOA
    run and compute the angles from them.

    Parameters
    ----------
    hyperparameters : Tuple
        The hyperparameters containing the hamiltonian, the number of steps,
        the total annealing time and possibly more.
        ``hyperparametesr = (hamiltonian, timesteps, time, ...)``
    parameters : Tuple
        The QAOA parameters, that can be optimized. E.g. the gammas and betas or
        the annealing timesteps.
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self,
                 hyperparameters: Tuple,
                 parameters: Tuple = None):
        """
        Extracts the qubits the reference and mixer hamiltonian act on and
        sets them.
        """
        # Note
        # ----
        # ``AbstractQAOAParameters.__init__`` doesn't do anything with the
        # argument ``parameters``. In the child classes we have to super from
        # them and handle them correctly. Additionally we might need to handle
        # extra hyperparameters.

        hamiltonian, self.timesteps = hyperparameters[:2]

        # extract the qubit lists from the hamiltonian
        self.reg = hamiltonian.get_qubits()
        self.qubits_pairs = []
        self.qubits_singles = []

        # and fill qubits_singles and qubits_pairs according to the terms in the hamiltonian
        for term in hamiltonian:
            if len(term) == 1:
                self.qubits_singles.append(term.get_qubits()[0])
            elif len(term) == 2:
                self.qubits_pairs.append(term.get_qubits())
            elif len(term) == 0:
                pass  # could give a notice, that multiples of the identity are
                      # ignored, since unphysical
            else:
                raise NotImplementedError(
                    "As of now we can only handle hamiltonians with at most two-qubit terms")

    def __repr__(self):
        raise NotImplementedError()

    def __len__(self):
        """
        Returns
        -------
        int:
            the length of the data produced by self.raw() and accepted by
            self.update_from_raw()
        """
        raise NotImplementedError()

    def update_variable_parameters(self, variable_parameters: Tuple):
        """
        Deprecated. You can safely remove any call without replacement.
        """
        warnings.warn("self.update_variable_parameters is deprecated."
                      "You can safely remove any call and replace it with nothing",
                      DeprecationWarning)

    def update_from_raw(self, new_values: Union[list, np.array]):
        """
        Updates all the angles based on a 1D array whose shape is specified later.
        The input has the same format as the output of ``self.raw()``.
        This is useful for ``scipy.optimize.minimize`` which only minimizes
        w.r.t a 1D array of parameters

        Parameters
        ----------
        new_values : Union[list, np.array]
            A 1D array with the new parameters. Must have length  ``len(self)``

        """
        raise NotImplementedError()

    def raw(self):
        """
        Returns the angles in a 1D array. This is needed by ``scipy.optimize.minimize``
        which only minimizes w.r.t a 1D array of parameters

        Returns
        -------
        np.array :
            all the tunable parameters in a 1D array. Has the same output
            format as the expected input of ``self.update_from_raw``

        """
        raise NotImplementedError()

    def raw_rotation_angles(self):
        """
        Returns all single rotation angles as needed for the memory map in parametric circuits

        Returns
        -------
        Union[List, np.array] :
            Returns all single rotation angles in the ordering
            ``(x_rotation_angles, gamma_singles, zz_rotation_angles)`` where
            ``x_rotation_angles = (beta_q0_t0, beta_q1_t0, ... , beta_qn_tp)``
            and the same for ``z_rotation_angles`` and ``zz_rotation_angles``

        """
        raw_data = []
        raw_data += [beta for betas in self.x_rotation_angles for beta in betas]
        raw_data += [g for gammas in self.z_rotation_angles for g in gammas]
        raw_data += [g for gammas in self.zz_rotation_angles for g in gammas]
        return raw_data

    @classmethod
    def linear_ramp_from_hamiltonian(cls,
                                     hamiltonian: PauliSum,
                                     timesteps: int,
                                     time: float = None):
        """
        Calculate initial parameters from a hamiltonian corresponding to a
        linear ramp annealing schedule.

        Parameters
        ----------
        hamiltonian : PauliSum
            `hamiltonian` for which to calculate the initial QAOA parameters.
        timesteps : int
            Number of timesteps.
        time : float
            Total annealing time. Defaults to ``0.7*timesteps``.

        Returns
        -------
        Type[AbstractQAOAParameters]
            The initial parameters best for `cost_hamiltonian`.

        """
        raise NotImplementedError()

    # TODO pass kwargs forward to plot() in all implementations  of this.
    def plot(self, ax=None):
        """
        Plots ``self`` in a sensible way to the canvas ``ax``, if provided.

        Parameters
        ----------
        ax : matplotlib.axes._subplots.AxesSubplot
            The canvas to plot itself on

        """
        raise NotImplementedError()


class GeneralQAOAParameters(AbstractQAOAParameters):
    """
    QAOA parameters in their most general form with different angles for each
    operator.

    This means, that at the i-th timestep the evolution hamiltonian is given by

    .. math::

        H(t_i) = \sum_{\textrm{qubits } j} \beta_{ij} X_j
               + \sum_{\textrm{qubits } j} \gamma_{\textrm{single } ij} Z_j
               + \sum_{\textrm{qubit pairs} (jk)} \gamma_{\textrm{pair }, i(jk)} Z_j Z_k

    and the complete circuit is then

    .. math::

        U = e^{-i H(t_p)} \cdots e^{-iH(t_1)}.

    Parameters
    ----------
    hyperparameters : Tuple
        The hyperparameters containing the hamiltonian and the number of steps
        ``hyperparameters = (hamiltonian, timesteps)``
    parameters : Tuple
        Tuple containing ``(betas, gammas_singles, gammas_pairs)`` with dimensions
        ``((timesteps x nqubits), (timesteps x nsingle_terms), (timesteps x npair_terms))``
    """
    def __init__(self,
                 hyperparameters: Tuple[PauliSum, int],
                 parameters: Tuple):
        """
        Extracts the qubits the reference and mixer hamiltonian act on and
        sets them.

        Todo
        ----
        Add checks, that the parameters and hyperparameters work together (same
        number of timesteps and single and pair qubit terms)
        """
        # setup reg, qubits_singles and qubits_pairs
        super().__init__(hyperparameters)
        self.betas, self.gammas_singles, self.gammas_pairs = parameters

    def __repr__(self):
        string = "Hyperparameters:\n"
        string += "\tregister: " + str(self.reg) + "\n"
        string += "\tqubits_singles: " + str(self.qubits_singles) + "\n"
        string += "\tqubits_pairs: " + str(self.qubits_pairs) + "\n"
        string += "Parameters:\n"
        string += "\tbetas: " + str(self.betas) + "\n"
        string += "\tgammas_singles: " + str(self.gammas_singles) + "\n"
        string += "\tgammas_pairs: " + str(self.gammas_pairs) + "\n"
        return string

    def __len__(self):
        return self.timesteps * (len(self.reg) + len(self.qubits_pairs)
                                 + len(self.qubits_singles))

    @property
    def x_rotation_angles(self):
        return self.betas

    @property
    def z_rotation_angles(self):
        return self.gammas_singles

    @property
    def zz_rotation_angles(self):
        return self.gammas_pairs

    def update_from_raw(self, new_values):
        self.betas = [new_values[len(self.reg) * i:len(self.reg) * i + len(self.reg)]
                      for i in range(self.timesteps)]
        new_values = new_values[self.timesteps * len(self.reg):]

        self.gammas_singles =\
            [new_values[len(self.qubits_singles) * i:len(self.qubits_singles) * i
                        + len(self.qubits_singles)] for i in range(self.timesteps)]
        new_values = new_values[self.timesteps * len(self.qubits_singles):]

        self.gammas_pairs =\
            [new_values[len(self.qubits_pairs) * i:len(self.qubits_pairs) * i
                        + len(self.qubits_pairs)] for i in range(self.timesteps)]
        new_values = new_values[self.timesteps * len(self.qubits_pairs):]

        # PEP8 complains, but new_values could be np.array and not list!
        if  not len(new_values) == 0:
            raise RuntimeWarning(
                "list to make new gammas and x_rotation_angles out of didn't have the right length!")

    def raw(self):
        raw_data = []
        raw_data += [beta for betas in self.betas for beta in betas]
        raw_data += [g for gammas in self.gammas_singles for g in gammas]
        raw_data += [g for gammas in self.gammas_pairs for g in gammas]
        return raw_data


    # TODO: Update this classmethod to work correctly with the new constructor
    @classmethod
    def linear_ramp_from_hamiltonian(cls,
                                     hamiltonian: PauliSum,
                                     timesteps: int,
                                     time: float = None):
        """
        Calculate initial parameters from a hamiltonian corresponding to a
        linear ramp annealing schedule.

        Parameters
        ----------
        hamiltonian : PauliSum
            `cost_hamiltonian` for which to calcuate the initial QAOA parameters.
        timesteps : int
            Number of timesteps.
        time : float
            Total annealing time. If none is passed, 0,7 * timesteps is used.

        Returns
        -------
        GeneralQAOAParameters
            The initial parameters best for `cost_hamiltonian`.

        """
        # create evenly spaced timesteps at the centers of #timesteps intervals
        if time is None:
            time = float(0.7 * timesteps)

        dt = time / timesteps
        times = np.linspace(time * (0.5 / timesteps), time
                            * (1 - 0.5 / timesteps), timesteps)

        betas = []
        gammas_pairs = []
        gammas_singles = []

        # fill betas and gammas_singles, gammas_pairs according to the timesteps and
        # coefficients of the terms in the hamiltonian
        for t in times:
            gamma_pairs = []
            gamma_singles = []
            beta = []

            for term in hamiltonian:
                if len(term) == 1:
                    gamma_singles.append(t * term.coefficient.real * dt / time)

                elif len(term) == 2:
                    gamma_pairs.append(t * term.coefficient.real * dt / time)
                elif len(term) == 0:
                    pass  # could give a notice, that multiples of the identity are ignored, since unphysical

                else:
                    raise NotImplementedError(
                        "As of now we can only handle hamiltonians with at most two-qubit terms")

            if gamma_singles:
                gammas_singles.append(gamma_singles)
            if gamma_pairs:
                gammas_pairs.append(gamma_pairs)

            for qubit in hamiltonian.get_qubits():              # not efficient, but following the
                beta.append((1 - t / time) * dt)   # same logic as above
            betas.append(beta)

        # if there are no one qubit terms return a list containing an empty list
        # same for no two qubit terms. This ensures that prepare_qaoa_ansatz
        # works as expected
        if not gammas_singles:
            gammas_singles = [[]]
        if not gammas_pairs:
            gammas_pairs = [[]]

        # wrap it all nicely in a qaoa_parameters object
        params = cls((hamiltonian, timesteps),
                     (betas, gammas_singles, gammas_pairs))
        return params

    def plot(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(self.betas, label="betas", marker="s", ls="")
        if not _is_list_empty(self.gammas_singles):
            ax.plot(self.gammas_singles,
                    label="gammas_singles", marker="^", ls="")
        if not _is_list_empty(self.gammas_pairs):
            ax.plot(self.gammas_pairs, label="gammas_pairs", marker="v", ls="")
        ax.set_xlabel("timestep")
        ax.legend()


class AlternatingOperatorsQAOAParameters(AbstractQAOAParameters):
    """
    QAOA parameters that implement a state preparation circuit with

    .. math::

        e^{-i \\beta_p H_0}
        e^{-i \\gamma_{\\textrm{singles}, p} H_{c, \\textrm{singles}}}
        e^{-i \\gamma_{\\textrm{pairs}, p} H_{c, \\textrm{pairs}}}
        \\cdots
        e^{-i \\beta_0 H_0}
        e^{-i \\gamma_{\\textrm{singles}, 0} H_{c, \\textrm{singles}}}
        e^{-i \\gamma_{\\textrm{pairs}, 0} H_{c, \\textrm{pairs}}}

    where the cost hamiltonian is split into :math:`H_{c, \\textrm{singles}}`
    the bias terms, that act on only one qubit, and
    :math:`H_{c, \\textrm{pairs}}` the coupling terms, that act on two qubits.

    Parameters
    ----------
    hyperparameters : Tuple
        The hyperparameters containing the hamiltonian and the number of steps
        ``hyperparameters = (hamiltonian, timesteps)``
    parameters : Tuple
        Tuple containing ``(betas, gammas_singles, gammas_pairs)`` with dimensions
        ``(p, p, p)``
    """
    def __init__(self,
                 hyperparameters: Tuple[PauliSum, int],
                 parameters: Tuple):
        """
        Extracts the qubits the reference and mixer hamiltonian act on and
        sets them.

        Todo
        ----
        Add checks, that the parameters and hyperparameters work together (same
        number of timesteps and single and pair qubit terms)
        """
        # setup reg, qubits_singles and qubits_pairs
        super().__init__(hyperparameters, parameters)
        hamiltonian = hyperparameters[0]
        self.betas, self.gammas_singles, self.gammas_pairs = parameters
        self.single_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 1]
        self.pair_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 2]


    def __repr__(self):
        string = "Hyperparameters:\n"
        string += "\tregister: " + str(self.reg) + "\n"
        string += "\tqubits_singles: " + str(self.qubits_singles) + "\n"
        string += "\tqubits_pairs: " + str(self.qubits_pairs) + "\n"
        string += "Parameters:\n"
        string += "\tbetas: " + str(self.betas) + "\n"
        string += "\tgammas_singles: " + str(self.gammas_singles) + "\n"
        string += "\tgammas_pairs: " + str(self.gammas_pairs) + "\n"
        return(string)

    def __len__(self):
        return self.timesteps * 3

    @property
    def x_rotation_angles(self):
        return [[b] * len(self.reg) for b in self.betas]

    @property
    def z_rotation_angles(self):
       return [[gamma * coeff for coeff in self.single_qubit_coeffs]
                              for gamma in self.gammas_singles]

    @property
    def zz_rotation_angles(self):
        return [[gamma * coeff for coeff in self.pair_qubit_coeffs]
                               for gamma in self.gammas_pairs]

    def update_from_raw(self, new_values):
        # overwrite self.betas with new ones
        self.betas = list(new_values[0:self.timesteps])
        new_values = new_values[self.timesteps:]    # cut betas from new_values
        self.gammas_singles = list(new_values[0:self.timesteps])
        new_values = new_values[self.timesteps:]
        self.gammas_pairs = list(new_values[0:self.timesteps])
        new_values = new_values[self.timesteps:]

        if not len(new_values) == 0:
            raise RuntimeWarning("list to make new gammas and x_rotation_angles out of"
                                 "didn't have the right length!")
        # self.update_variable_parameters()

    def raw(self):
        raw_data = []
        raw_data += self.betas
        raw_data += self.gammas_singles
        raw_data += self.gammas_pairs
        return raw_data

    @classmethod
    def linear_ramp_from_hamiltonian(cls,
                                     hamiltonian: PauliSum,
                                     timesteps: int,
                                     time: float = None):
        """
        Returns
        -------
        AlternatingOperatorsQAOAParameters
            An `AlternatingOperatorsQAOAParameters` object holding all the
            parameters
        """
        if time is None:
            time = float(0.7 * timesteps)
        # create evenly spaced timesteps at the centers of #timesteps intervals
        dt = time / timesteps
        times = np.linspace(time * (0.5 / timesteps), time
                         * (1 - 0.5 / timesteps), timesteps)

        # fill betas, gammas_singles and gammas_pairs
        betas = [dt * (1 - t / time) for t in times]
        gammas_singles = [dt * t / time for t in times]
        gammas_pairs = [dt * t / time for t in times]

        # wrap it all nicely in a qaoa_parameters object
        params = cls((hamiltonian, timesteps),
                     (betas, gammas_singles, gammas_pairs))
        return params

    def plot(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(self.betas, label="betas", marker="s", ls="")
        if not _is_list_empty(self.gammas_singles):
            ax.plot(self.gammas_singles,
                    label="gammas_singles", marker="^", ls="")
        if not _is_list_empty(self.gammas_pairs):
            ax.plot(self.gammas_pairs, label="gammas_pairs", marker="v", ls="")
        ax.set_xlabel("timestep")
        # ax.grid(linestyle='--')
        ax.legend()


class AdiabaticTimestepsQAOAParameters(AbstractQAOAParameters):
    """
    QAOA parameters that implement a state preparation circuit of the form

    .. math::

        U = e^{-i (T-t_p) H_0} e^{-i t_p H_c} \\cdots e^{-i(T-t_p)H_0} e^{-i t_p H_c}

    where the :math:`t_i` are the variable parameters.

    Parameters
    ----------
    hyperparameters : Tuple
        The hyperparameters containing the hamiltonian, the number of steps
        and the total annealing time ``hyperparameters = (hamiltonian, timesteps, time)``
    parameters : Tuple
        Tuple containing ``(times)`` of length ``timesteps``
    """
    def __init__(self,
                 hyperparameters: Tuple[PauliSum, int, float],
                 parameters: List):
        """
        Extracts the qubits the reference and mixer hamiltonian act on and
        sets them.

        Todo
        ----
        Add checks, that the parameters and hyperparameters work together (same
        number of timesteps and single and pair qubit terms)
        """
        # setup reg, qubits_singles and qubits_pairs
        super().__init__(hyperparameters)
        hamiltonian, self._T = hyperparameters[0], hyperparameters[2]
        self.single_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 1]
        self.pair_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 2]
        self.times = parameters

    def __repr__(self):
        string = "Hyperparameters:\n"
        string += "\tregister: " + str(self.reg) + "\n"
        string += "\tqubits_singles: " + str(self.qubits_singles) + "\n"
        string += "\tqubits_pairs: " + str(self.qubits_pairs) + "\n"
        string = "Parameters:\n"
        string += "\ttimes: " + str(self.times)
        return string

    def __len__(self):   # needs fixing
        return self.timesteps

    @property
    def x_rotation_angles(self):
        dt = self._T / self.timesteps
        return [[(1 - t / self._T) * (dt)] * len(self.reg) for t in self.times]

    @property
    def z_rotation_angles(self):
        dt = self._T / self.timesteps
        return  [[t * dt * coeff / self._T for coeff in self.single_qubit_coeffs]
                 for t in self.times]

    @property
    def zz_rotation_angles(self):
        dt = self._T / self.timesteps
        return [[t * dt * coeff / self._T for coeff in self.pair_qubit_coeffs]
                for t in self.times]

    def update_from_raw(self, new_values):
        if len(new_values) != self.timesteps:
            raise RuntimeWarning(
                "the new times should have length timesteps+1")
        self.times = new_values

    def raw(self):
        """
        Returns
        -------
        Union[List[float], np.array]:
            A list or array of the times `t_i`
        """
        return self.times

    @classmethod
    def linear_ramp_from_hamiltonian(cls,
                                     hamiltonian: PauliSum,
                                     timesteps: int,
                                     time: float = None):
        """
        Returns
        -------
        AdiabaticTimestepsQAOAParameters :
            An `AdiabaticTimestepsQAOAParameters` object holding all the
            parameters
        """
        if time is None:
            time = 0.7 * timesteps

        times = list(np.linspace(time * (0.5 / timesteps),
                                 time * (1 - 0.5 / timesteps), timesteps))

        # wrap it all nicely in a qaoa_parameters object
        params = cls((hamiltonian, timesteps, time), (times))
        return params

    def plot(self, ax=None):
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(self.times, label="times", marker="s", ls="")
        ax.set_xlabel("timestep number")
        ax.legend()


class FourierQAOAParameters(AbstractQAOAParameters):
    """
    The QAOA parameters as the sine/cosine transform of the original gammas
    and x_rotation_angles. See (Quantum Approximate Optimization Algorithm:
    Performance, Mechanism, and Implementation on Near-Term Devices)
    [https://arxiv.org/abs/1812.01041] for a detailed description.

    Parameters
    ----------
    hyperparameters : Tuple
        The hyperparameters containing the hamiltonian, the number of steps
        and the total annealing time ``hyperparameters = (hamiltonian, timesteps, q)``
        ``q`` is the number of fourier coefficients. For ``q == timesteps`` we have
        the full expresivity of ``AlternatingOperatorsQAOAParameters``. More
        are redundant.
    parameters : Tuple
        Tuple containing ``(v, u_singles, u_pairs)`` with dimensions
        ``(q, q, q)``
    """
    def __init__(self,
                 hyperparameters: Tuple[PauliSum, int, float],
                 parameters: Tuple):
        """
        Extracts the qubits the reference and mixer hamiltonian act on and
        sets them.

        Todo
        ----
        Add checks, that the parameters and hyperparameters work together (same
        number of timesteps and single and pair qubit terms)
        """
        # setup reg, qubits_singles and qubits_pairs
        super().__init__(hyperparameters)
        hamiltonian, self.q = hyperparameters[0], hyperparameters[2]
        self.v, self.u_singles, self.u_pairs = parameters
        self.single_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 1]
        self.pair_qubit_coeffs = [
            term.coefficient.real for term in hamiltonian if len(term) == 2]

    def __repr__(self):
        string = "Hyperparameters:\n"
        string += "\tregister: " + str(self.reg) + "\n"
        string += "Parameters:\n"
        string += "\tu_singles: " + str(self.u_singles) + "\n"
        string += "\tu_pairs: " + str(self.u_pairs) + "\n"
        string += "\tv: " + str(self.v) + "\n"
        return(string)

    def __len__(self):
        return 3 * self.q

    @staticmethod
    def _dst(v, p):
        """Compute the discrete sine transform from frequency to timespace."""
        x = np.zeros(p)
        for i in range(p):
            for k in range(len(v)):
                x[i] += v[k] * np.sin((k + 0.5) * (i + 0.5) * np.pi / p)
        return x

    @staticmethod
    def _dct(u, p):
        """Compute the discrete cosine transform from frequency to timespace."""
        x = np.zeros(p)
        for i in range(p):
            for k in range(len(u)):
                x[i] += u[k] * np.cos((k + 0.5) * (i + 0.5) * np.pi / p)
        return x


    @property
    def x_rotation_angles(self):
        betas = self._dct(self.v, self.timesteps)
        return [[b] * len(self.reg) for b in betas]

    @property
    def z_rotation_angles(self):
        gammas_singles = self._dst(self.u_singles, self.timesteps)
        return [[gamma * coeff for coeff in self.single_qubit_coeffs]
                               for gamma in gammas_singles]

    @property
    def zz_rotation_angles(self):
        gammas_pairs = self._dst(self.u_pairs, self.timesteps)
        return [[gamma * coeff for coeff in self.pair_qubit_coeffs]
                               for gamma in gammas_pairs]

    def update_from_raw(self, new_values):
        self.v = list(new_values[0:self.q])   # overwrite x_rotation_angles with new ones
        new_values = new_values[self.q:]    # cut x_rotation_angles from new_values
        self.u_singles = list(new_values[0:self.q])
        new_values = new_values[self.q:]
        self.u_pairs = list(new_values[0:self.q])
        new_values = new_values[self.q:]

        if not len(new_values) == 0:
            raise RuntimeWarning("list to make new u's and v's out of\
            didn't have the right length!")

    def raw(self):
        raw_data = []
        raw_data += self.v
        raw_data += self.u_singles
        raw_data += self.u_pairs
        return raw_data

    @classmethod
    def linear_ramp_from_hamiltonian(cls,
                                     hamiltonian: PauliSum,
                                     timesteps: int,
                                     q: int = 4,
                                     time: float = None):
        """
        Parameters
        ----------
        cost_hamiltonian : PauliSum
            The cost hamiltonian
        timesteps: int
            number of timesteps
        time: Number
            total time. Set to 0.7*timesteps if None is passed.
        fourier: q
            Number of Fourier coeffs. Defaults to 4

        Returns
        -------
        AlternatingOperatorsQAOAParameters:
            A `AlternatingOperatorsQAOAParameters` object holding all the
            parameters

        ToDo
        ----
        Make a more informed choice of the default value for q. Probably
        depending on nqubits
        """
        if time is None:
            time = 0.7 * timesteps

        # fill x_rotation_angles, z_rotation_angles and zz_rotation_angles
        v = [time / timesteps, *[0] * (q - 1)]
        u_singles = [time / timesteps, *[0] * (q - 1)]
        u_pairs = [time / timesteps, *[0] * (q - 1)]

        # wrap it all nicely in a qaoa_parameters object
        params = cls((hamiltonian, timesteps, q), (v, u_singles, u_pairs))
        return params

    def plot(self, ax=None):
        warnings.warn("Plotting the gammas and x_rotation_angles through DCT and DST. If you are "
              "interested in v, u_singles and u_pairs you can access them via "
              "params.v, params.u_singles, params.u_pairs")
        if ax is None:
            fig, ax = plt.subplots()

        ax.plot(self.betas, label="betas", marker="s", ls="")
        if not _is_list_empty(self.gammas_singles):
            ax.plot(self.gammas_singles,
                    label="gammas_singles", marker="^", ls="")
        if not _is_list_empty(self.gammas_pairs):
            ax.plot(self.gammas_pairs, label="gammas_pairs", marker="v", ls="")
        ax.set_xlabel("timestep")
        # ax.grid(linestyle='--')
        ax.legend()


class QAOAParameterIterator:
    """An iterator to sweep one parameter over a range in a QAOAParameter object.

    Example
    -------
    Assume qaoa_params is of type ``AlternatingOperatorsQAOAParameters`` and
    has at least 2 timesteps.

    .. code-block:: python

        the_range = np.arange(0, 1, 0.4)
        the_parameter = "gammas_singles[1]"
        param_iterator = QAOAParameterIterator(qaoa_params, the_parameter, the_range)
        for params in param_iterator:
            # do what ever needs to be done
    """

    def __init__(self, qaoa_params: Type[AbstractQAOAParameters],
                 the_parameter: str,
                 the_range: Iterable):
        """
        Parameters
        ----------
        qaoa_params : Type[AbstractQAOAParameters]
            The inital qaoa_parameters, where one of them is swept over
        the_parameter: String
            A string specifying, which parameter should be varied. It has to be
            of the form ``<attr_name>[i]`` where ``<attr_name>`` is the name of the
            _internal_ list and ``i`` the index, at which it sits. E.g. if
            ``qaoa_params`` is of type ``AdiabaticTimestepsQAOAParameters`` and
            we want to vary over the second timestep, it is
            ``the_parameter = "times[1]"``.
        the_range : Iterable -> float
            The range, that ``the_parameter`` should be varied over

        Todo
        ----
        - Add checks, that the number of indices in ``the_parameter`` matches the
          dimensions of ``the_parameter``
        - Add checks, that the index is not too large
        """
        self.params = qaoa_params
        self.iterator = iter(the_range)
        self.the_parameter, *indices = the_parameter.split("[")
        indices = [i.replace(']', '') for i in indices]
        if len(indices) == 1:
            self.index0 = int(indices[0])
            self.index1 = False
        elif len(indices) == 2:
            self.index0 = int(indices[0])
            self.index1 = int(indices[1])
        else:
            raise ValueError("the_parameter has to many indices")

    def __iter__(self):
        return self

    def __next__(self):
        # get next value from the_range
        value = next(self.iterator)

        # 2d list or 1d list?
        if self.index1 is not False:
            getattr(self.params, self.the_parameter)[self.index0][self.index1] = value
        else:
            getattr(self.params, self.the_parameter)[self.index0] = value

        return self.params