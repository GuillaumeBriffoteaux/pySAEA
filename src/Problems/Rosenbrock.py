import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

from Problems.Mono_Objective import Mono_Objective

#------------------------------------------#
#-------------class Rosenbrock-------------#
#------------------------------------------#
class Rosenbrock(Mono_Objective):
    """Class for the mono-objective Rosenbrock problem.

    :param n_dvar: number of decision variable
    :type n_dvar: positive int, not zero
    """

    
    #-----------------------------------------#
    #-------------special methods-------------#
    #-----------------------------------------#

    #-------------__init__-------------#    
    def __init__(self, n_dvar):
        assert n_dvar>1
        Mono_Objective.__init__(self, n_dvar, 1)

    #-------------__del__-------------#
    def __del__(self):
        Mono_Objective.__del__(self)

    #-------------__str__-------------#
    def __str__(self):
        return "Rosenbrock problem "+str(self.n_dvar)+" decision variables "+str(self.n_obj)+" objective"

    
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
        costs = np.sum(100*(candidates[:,0:candidates.shape[1]-1].__pow__(2)-candidates[:,1:]).__pow__(2) + (candidates[:,0:candidates.shape[1]-1]-1).__pow__(2), axis=1)
        return costs

    #-------------get_bounds-------------#
    def get_bounds(self):
        """Returns search space bounds.

        :returns: search space bounds
        :rtype: np.ndarray
        """

        res=np.ones((2,self.n_dvar))
        res[0,:]*=-5.0
        res[1,:]*=10.0
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
        if Mono_Objective.is_feasible(self, candidates)==True:
            lower_bounds=self.get_bounds()[0,:]
            upper_bounds=self.get_bounds()[1,:]
            res=(lower_bounds<=candidates).all() and (candidates<=upper_bounds).all()
        return res

    #-------------plot-------------#
    def plot(self):
        """Plot the 2D Rosenbrock fitness function."""
        
        if self.n_dvar==2:
            fig = plt.figure()

            lower_bounds = self.get_bounds()[0,:]
            upper_bounds = self.get_bounds()[1,:]

            x = np.linspace(-2, 2, 100, dtype=np.float)
            y = np.linspace(-1, 3, 100, dtype=np.float)
            # x = np.linspace(lower_bounds[0], upper_bounds[0], 100)
            # y = np.linspace(lower_bounds[1], upper_bounds[1], 100)
            z = self.perform_real_evaluation( np.array(np.meshgrid(x, y)).T.reshape(-1,2) ).reshape(x.size, y.size)
            x, y = np.meshgrid(x, y)
            
            ax = fig.add_subplot(111, projection='3d')
            surf = ax.plot_surface(x, y, z, rstride=1, cstride=1, cmap=cm.jet, antialiased=False)
            plt.title("Rosenbrock-2D")
            plt.show()

        else:
            print("[Rosenbrock.py] Impossible to plot Rosenbrock with n_dvar="+str(self.n_dvar))
