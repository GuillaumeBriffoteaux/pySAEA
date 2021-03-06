#!/usr/bin/python3.7
"""Script running a synchronous parallel efficient global optimization algorithm.

To run sequentially: ``./par_sync_EGO.py``

To run in parallel (in 4 computational units): ``mpiexec -n 4 python3.7 par_sync_EGO.py``

To run in parallel (in 4 computational units) specifying the units in `./hosts.txt`: ``mpiexec --machinefile ./host.txt -n 4 python3.7 par_sync_EGO.py``

Only the simulations (i.e. real evaluations) are executed in parallel.
"""


import sys
sys.path.append('../src')
import os
import time
import numpy as np
from mpi4py import MPI

from Problems.Schwefel import Schwefel
from Problems.Ackley import Ackley
from Problems.Xiong import Xiong
from Problems.Rastrigin import Rastrigin
from Problems.Rosenbrock import Rosenbrock
from Problems.CEC2013 import CEC2013
from Problems.DoE import DoE

from Evolution.Population import Population
from Evolution.Tournament_Position import Tournament_Position
from Evolution.SBX import SBX
from Evolution.Polynomial import Polynomial
from Evolution.Custom_Elitism import Custom_Elitism

from Surrogates.BNN_MCD import BNN_MCD
from Surrogates.BNN_BLR import BNN_BLR
from Surrogates.KRG import KRG
from Surrogates.GP_SMK import GP_SMK
from Surrogates.GP_Matern import GP_Matern
from Surrogates.RF import RF

from Evolution_Controls.Pareto_Tian2018_EC import Pareto_Tian2018_EC
from Evolution_Controls.Probability_Improvement_EC import Probability_Improvement_EC
from Evolution_Controls.Expected_Improvement_EC import Expected_Improvement_EC
from Evolution_Controls.Lower_Confident_Bound_EC import Lower_Confident_Bound_EC
from Evolution_Controls.Variance_EC import Variance_EC
from Evolution_Controls.Distance_EC import Distance_EC
from Evolution_Controls.Best_Predicted_EC import Best_Predicted_EC
from Evolution_Controls.Random_EC import Random_EC
from Evolution_Controls.Committee_EC import Committee_EC
from Evolution_Controls.Dynamic_EC import Dynamic_EC
from Evolution_Controls.Adaptive_EC import Adaptive_EC
from Evolution_Controls.Pareto_EC import Pareto_EC
from Evolution_Controls.Adaptive_Wang2020_EC import Adaptive_Wang2020_EC

from Global_Var import *


def main():
    
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    nprocs = comm.Get_size()

    # Problem
    N_DV = 6
    p = Schwefel(N_DV)
    # p = Ackley(N_DV)
    # N_DV = 1
    # p = Xiong()
    # p = Rastrigin(N_DV)
    # p = Rosenbrock(N_DV)
    # N_DV = 5
    # p = CEC2013(1, N_DV)


    #--------------------------------#
    #-------------MASTER-------------#
    #--------------------------------#
    if rank==0:

        # Argument of the search
        N_CYCLES=2
        INIT_DB_SIZE=48
        q=48 # number of simulated solutions per Cycle (could be less for the last Cycle according to time budget)
        TIME_BUDGET=0 # in seconds (int), DoE excluded (if 0 the search stops after N_CYCLES cycles, that corresponds to N_CYCLES*q simulations)
        SIM_TIME=1 # in seconds, duration of 1 simulation on 1 core
        if TIME_BUDGET>0:
            assert TIME_BUDGET>SIM_TIME
            N_CYCLES=1000000000000
        POP_SIZE=100
        assert q<=POP_SIZE
        N_GEN=5
        N_CHLD=100

        # Files
        DIR_STORAGE="./outputs"
        F_SIM_ARCHIVE=DIR_STORAGE+"/sim_archive.csv"
        F_BEST_PROFILE=DIR_STORAGE+"/best_profile.csv"
        F_INIT_DB=DIR_STORAGE+"/init_pop.csv"
        F_TRAIN_LOG=DIR_STORAGE+"/training_log.csv"
        F_TRAINED_MODEL=DIR_STORAGE+"/trained_model"
        os.system("rm -rf "+DIR_STORAGE+"/*")

        # Database initialization / Parallel DoE
        d = DoE(p)
        db = Population(p.n_dvar)
        db.dvec = d.latin_hypercube_sampling(INIT_DB_SIZE)
        nb_sim_per_proc = (INIT_DB_SIZE//nprocs)*np.ones((nprocs,), dtype=int) # number of simulations per proc
        for i in range(INIT_DB_SIZE%nprocs):
            nb_sim_per_proc[i+1]+=1
        for i in range(1,nprocs): # sending to workers
            comm.send(nb_sim_per_proc[i], dest=i, tag=10)
            comm.send(db.dvec[np.sum(nb_sim_per_proc[:i]):np.sum(nb_sim_per_proc[:i+1])], dest=i, tag=11)
        db.costs = np.zeros((db.dvec.shape[0],))
        db.costs[0:nb_sim_per_proc[0]] = p.perform_real_evaluation(db.dvec[0:nb_sim_per_proc[0]])
        for i in range(1,nprocs): # receiving from workers
            db.costs[np.sum(nb_sim_per_proc[:i]):np.sum(nb_sim_per_proc[:i+1])] = comm.recv(source=i, tag=12)
        db.fitness_modes = True*np.ones(db.costs.shape, dtype=bool)
        db.save_to_csv_file(F_INIT_DB, p)
        db.save_sim_archive(F_SIM_ARCHIVE)
        db.update_best_sim(F_BEST_PROFILE)

        # # Database initialization / Loading from a file
        # db = Population(p.n_dvar)
        # db.load_from_csv_file(F_INIT_DB, p)
        # db.save_sim_archive(F_SIM_ARCHIVE)
        # db.update_best_sim(F_BEST_PROFILE)

        # Number of simulations per proc
        nb_sim_per_proc = (q//nprocs)*np.ones((nprocs,), dtype=int)
        for i in range(q%nprocs):
            nb_sim_per_proc[i+1]+=1
            
        if TIME_BUDGET>0:
            t_start = time.time()

        # Surrogate
        surrogate = BNN_MCD(F_SIM_ARCHIVE, p, INIT_DB_SIZE, F_TRAIN_LOG, F_TRAINED_MODEL)
        # surrogate = BNN_BLR(F_SIM_ARCHIVE, p, INIT_DB_SIZE, F_TRAIN_LOG, F_TRAINED_MODEL)
        # surrogate = KRG(F_SIM_ARCHIVE, p, 16, F_TRAIN_LOG, F_TRAINED_MODEL)
        # surrogate = GP_SMK(F_SIM_ARCHIVE, p, 16, F_TRAIN_LOG, F_TRAINED_MODEL)
        # surrogate = GP_Matern(F_SIM_ARCHIVE, p, 16, F_TRAIN_LOG, F_TRAINED_MODEL)
        # surrogate = RF(F_SIM_ARCHIVE, p, INIT_DB_SIZE, F_TRAIN_LOG, F_TRAINED_MODEL)
        surrogate.perform_training()

        # Evolution Control
        ec_base_f = Best_Predicted_EC(surrogate)
        ec_base_s = Variance_EC(surrogate)
        ec_base_d = Distance_EC(surrogate)
        ec_base_md = Pareto_EC([1, 1], 'rand', ec_base_f, ec_base_d) # min pred cost, max distance
        ec_base_ms = Pareto_EC([1, 1], 'rand', ec_base_f, ec_base_s) # min pred cost, max variance
    
        # ec_op = Random_EC()
        # ec_op = ec_base_f
        # ec_op = ec_base_s
        # ec_op = ec_base_d
    
        # ec_op = Lower_Confident_Bound_EC(surrogate)
        # ec_op = Expected_Improvement_EC(surrogate)
        # ec_op = Probability_Improvement_EC(surrogate)

        # ec_op = Pareto_Tian2018_EC([1, -1], ec_base_f, ec_base_s) # min pred cost, min variance
        ec_op = ec_base_md
        # ec_op = ec_base_ms

        # if TIME_BUDGET>0:
        #     ec_op = Adaptive_Wang2020_EC(surrogate, TIME_BUDGET, "min")
        # else:
        #     ec_op = Adaptive_Wang2020_EC(surrogate, N_CYCLES, "min")
        # if TIME_BUDGET>0:
        #     ec_op = Adaptive_Wang2020_EC(surrogate, TIME_BUDGET, "max")
        # else:
        #     ec_op = Adaptive_Wang2020_EC(surrogate, N_CYCLES, "max")

        # if TIME_BUDGET>0:
        #     ec_op = Dynamic_EC(TIME_BUDGET, [0.25, 0.5, 0.25], ec_base_d, ec_base_md, ec_base_f)
        # else:
        #     ec_op = Dynamic_EC(N_CYCLES, [0.25, 0.5, 0.25], ec_base_d, ec_base_md, ec_base_f)

        # pred_costs = surrogate.perform_prediction(db.dvec)[0]
        # ec_op = Adaptive_EC("tanh", db.costs, pred_costs, ec_base_f, ec_base_s)

        # ec_op = Committee_EC(POP_SIZE, ec_base_s, ec_base_ms, ec_base_f)
        
        # Operators
        select_op = Tournament_Position(2)
        crossover_op = SBX(0.9, 10)
        mutation_op = Polynomial(0.1, 50)
        replace_op = Custom_Elitism(ec_op)

        # Population initialization
        del db


        #----------------------Loop over Cycles----------------------#    
        for curr_cycle in range(N_CYCLES):
            print("cycle "+str(curr_cycle))

            # Update Adaptive_Wang2020_EC (cycle level)
            if isinstance(ec_op, Adaptive_Wang2020_EC):
                if TIME_BUDGET>0:
                    t_now = time.time()
                    elapsed_time = int(t_now-t_start)
                    ec_op.update_EC(elapsed_time)
                else:
                    ec_op.update_EC(curr_cycle)

            # Update active EC in Dynamic_EC (cycle level)
            if isinstance(ec_op, Dynamic_EC):
                if TIME_BUDGET>0:
                    t_now = time.time()
                    elapsed_time = int(t_now-t_start)
                    ec_op.update_active(elapsed_time)
                else:
                    ec_op.update_active(curr_cycle)

            # Population initialization
            pop = Population(p.n_dvar)
            pop.dvec = d.latin_hypercube_sampling(POP_SIZE)
            pop.dvec = pop.dvec[ec_op.get_sorted_indexes(pop)]
            if isinstance(ec_op, Adaptive_EC):
                ec_op.to_be_updated=False

            #----------------------Evolution loop----------------------#
            for curr_gen in range(N_GEN):

                # Acquisition Process
                parents = select_op.perform_selection(pop, N_CHLD)
                children = crossover_op.perform_crossover(parents, p.get_bounds())
                children = mutation_op.perform_mutation(children, p.get_bounds())
                assert p.is_feasible(children.dvec)

                # Replacement
                replace_op.perform_replacement(pop, children)
                assert p.is_feasible(pop.dvec)
                del children
            #----------------------End evolution loop----------------------#

            # Computing number of affordable simulations
            if TIME_BUDGET>0:
                t_now = time.time()
                remaining_time = TIME_BUDGET-(t_now-t_start)
                if remaining_time<SIM_TIME:
                    break
                sim_afford = int(remaining_time//SIM_TIME)
                if np.max(nb_sim_per_proc)>sim_afford: # setting nb_sim_per_proc according to the remaining simulation budget
                    nb_sim_per_proc=sim_afford*np.ones((nprocs,), dtype=int)
                    
            # q(=np.sum(np_sim_per_proc)) best candidates from the population are simulated in parallel
            for i in range(1,nprocs): # sending to workers
                comm.send(nb_sim_per_proc[i], dest=i, tag=10)
                comm.send(pop.dvec[np.sum(nb_sim_per_proc[:i]):np.sum(nb_sim_per_proc[:i+1])], dest=i, tag=11)
            pop.costs = np.zeros((pop.dvec.shape[0],))
            pop.costs[0:nb_sim_per_proc[0]] = p.perform_real_evaluation(pop.dvec[0:nb_sim_per_proc[0]])
            for i in range(1,nprocs): # receiving from workers
                pop.costs[np.sum(nb_sim_per_proc[:i]):np.sum(nb_sim_per_proc[:i+1])] = comm.recv(source=i, tag=12)
            pop.fitness_modes = False*np.ones(pop.costs.shape, dtype=bool)
            pop.fitness_modes[:np.sum(nb_sim_per_proc)] = True

            # New simulations added to database
            pop.save_sim_archive(F_SIM_ARCHIVE)
            pop.update_best_sim(F_BEST_PROFILE)

            # Exit loop over cycles if budget time exhausted
            if TIME_BUDGET>0:
                t_now = time.time()
                if TIME_BUDGET-(t_now-t_start)<SIM_TIME:
                    break

            # Update active EC in Adaptive_EC
            if isinstance(ec_op, Adaptive_EC):
                pred_costs = surrogate.perform_prediction(pop.dvec[:np.sum(nb_sim_per_proc)])[0]
                ec_op.update_active(pop.costs[:np.sum(nb_sim_per_proc)], pred_costs)
            
            # Surrogate update
            surrogate.perform_training()

            del pop

        #----------------------End loop over Cycles----------------------#

        # Stop workers
        for i in range(1,nprocs):
            comm.send(-1, dest=i, tag=10)


    #---------------------------------#
    #-------------WORKERS-------------#
    #---------------------------------#
    else:
        nsim = comm.recv(source=0, tag=10)
        while nsim!=-1:
            candidates = np.empty((nsim, N_DV))
            candidates = comm.recv(source=0, tag=11)
            costs = p.perform_real_evaluation(candidates)
            comm.send(costs, dest=0, tag=12)
            nsim = comm.recv(source=0, tag=10)

if __name__ == "__main__":
    main()
            
