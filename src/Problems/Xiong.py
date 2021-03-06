import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

from Problems.Benchmark import Benchmark


#-------------------------------------#
#-------------class Xiong-------------#
#-------------------------------------#
class Xiong(Benchmark):
    """Class for 1D mono-objective Xiong problem."""

    
    #-----------------------------------------#
    #-------------special methods-------------#
    #-----------------------------------------#

    #-------------__init__-------------#    
    def __init__(self):
        Benchmark.__init__(self, 1, 1)

    #-------------__del__-------------#
    def __del__(self):
        Benchmark.__del__(self)

    #-------------__str__-------------#
    def __str__(self):
        return "Xiong problem "+str(self.n_dvar)+" decision variable"


    #----------------------------------------#
    #-------------object methods-------------#
    #----------------------------------------#
    
    #-------------perform_real_evaluation-------------#
    def perform_real_evaluation(self, candidates):
        """Fitness function.

        :param candidates: candidate decision vectors
        :type candidates: np.ndarray
        :return: costs (i.e. objective values)
        :rtype: np.ndarray
        """

        assert self.is_feasible(candidates)
        if candidates.ndim==1:
            candidates = np.array([candidates])
        costs = -(np.multiply(np.sin(40*np.power((candidates-0.85),4)), np.cos(2.5*(candidates-0.95)))+(candidates-0.9)/2+1)/2
        return costs.flatten()

    #-------------get_bounds-------------#
    def get_bounds(self):
        """Returns search space bounds.

        :returns: search space bounds
        :rtype: np.ndarray
        """

        res=np.ones((2,self.n_dvar))
        res[0,:]*=0
        res[1,:]*=1
        return res

    #-------------is_feasible-------------#
    def is_feasible(self, candidates):
        """Check feasibility of candidates.

        :param candidates: candidate decision vectors
        :type candidates: np.ndarray
        :returns: boolean indicating whether candidates are feasible
        :rtype: bool
        """

        res=False
        if Benchmark.is_feasible(self, candidates)==True:
            lower_bounds=self.get_bounds()[0,:]
            upper_bounds=self.get_bounds()[1,:]
            res=(lower_bounds<=candidates).all() and (candidates<=upper_bounds).all()
        return res

    #-------------plot-------------#
    def plot(self):
        """Plot the 1D Xiong fitness function."""
        
        x = np.linspace(self.get_bounds()[0], self.get_bounds()[1], 100)
        y = self.perform_real_evaluation(x)

        plt.plot(x, y, 'r')
        plt.title("Xiong-1D")
        plt.show()
