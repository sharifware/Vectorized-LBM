# -*- coding: utf-8 -*-
"""Boltzmann_equation.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1hObXiM8-QWhMoiPDe3EC84q5FDWuJNno
"""

import cupy as cp

import math

# Define physical and dimensional information
Rho_ref = 2  # Reference density
U_lid = 0.1  # This is the x-velocity on the moving lid

L = 100  # The length of the entire computational domain
H = L  # The height of the entire computational domain
N_nd_x = 50  # The total number of nodes in x-direction
N_nd_y = N_nd_x  # The total number of nodes in y-direction
dx = L / (N_nd_x - 1)  # The distance between the centroids of two horizontally neighboring CVs
dy = H / (N_nd_y - 1)  # The distance between the centroids of two vertically neighboring CVs

N_cv_x = N_nd_x #- 1  # The total number of CVs in x-direction
N_cv_y = N_nd_y #- 1  # The total number of CVs in y-direction

# Compute the area (volume in 2D)
A = dx * dy
# n1 is the unit outward normal vector on face 1 (facing east)
n1 = cp.array([[1], [0]])
# n2 is the unit outward normal vector on face 2 (facing south)
n2 = cp.array([[0], [-1]])
# n3 is the unit outward normal vector on face 3 (facing west)
n3 = cp.array([[-1], [0]])
# n4 is the unit outward normal vector on face 4 (facing north)
n4 = cp.array([[0], [1]])


# Define Boltzmann-related information
c_s = 1 / cp.sqrt(3)
dt = 0.1
Tau = 0.3

# Velocity directions and weights for the lattice Boltzmann method (LBM)
Ksi = cp.array([[0, 1, 0, -1, 0, 1, -1, -1,  1],
                [0, 0, 1,  0, -1, 1,  1, -1, -1]])

w = cp.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36])

# Initialize the distribution functions and other fields
f = cp.zeros([N_nd_y, N_nd_x, 9])  # Changed to (50, 50, 9)
f_eq = cp.zeros([N_cv_y, N_cv_x, 9])   # Changed to (50, 50, 9)
f_neq = cp.zeros([N_nd_y, N_nd_x, 9])  # Changed to (50, 50, 9)
u = cp.zeros([N_cv_y, N_cv_x])
v = cp.zeros([N_cv_y, N_cv_x])
Rho = cp.ones([N_cv_y, N_cv_x]) * Rho_ref  # Initial density at all CV centroids
Rho = cp.ones([N_nd_y, N_nd_x]) * Rho_ref ## Ensuring it has the same shape as rho ref
# Node-level quantities
f_nd_eq = cp.zeros([N_nd_y, N_nd_x, 9])
f_nd = cp.zeros([N_nd_y, N_nd_x, 9])
f_nd_neq = cp.zeros([N_nd_y, N_nd_x, 9])
u_nd = cp.zeros([N_nd_y, N_nd_x])
v_nd = cp.zeros([N_nd_y, N_nd_x])
Rho_nd = cp.ones([N_nd_y, N_nd_x]) * Rho_ref  # Initial density at all nodes ##

# Precompute constants for vectorized operations
Ksi_dot_U = cp.dot(Ksi.T, cp.array([U_lid, 0]))  # Dot product for U_lid direction
Ksi_dot_U_squared = (Ksi_dot_U**2) / (2 * c_s**4)
U_lid_term = (U_lid**2) / (2 * c_s**2)

# Create grid of local velocities (u and v) across the domain
u_local = cp.expand_dims(u, axis=-1)  # Shape: (N_cv_y, N_cv_x, 1)
v_local = cp.expand_dims(v, axis=-1)  # Shape: (N_cv_y, N_cv_x, 1)

# Concatenate u and v to form a velocity array of shape (N_cv_y, N_cv_x, 2)
U_local = cp.concatenate((u_local, v_local), axis=-1)  # Shape: (N_cv_y, N_cv_x, 2)

# Compute the dot product Ksi . U for all directions (9 velocity directions)
# Use broadcasting: Ksi has shape (2, 9), U_local has shape (N_cv_y, N_cv_x, 2)
Ksi_dot_U_local = cp.tensordot(U_local, Ksi, axes=([2], [0]))  # Shape: (N_cv_y, N_cv_x, 9)

# Compute the equilibrium distribution function f_eq in a vectoried manner

f_eq[..., :] = (w[:] * Rho_ref * (1 + cp.dot(Ksi.T , cp.array([0, 0]))/c_s**2 + cp.dot(Ksi.T, cp.array([0, 0]))**2/(2 * c_s**4))) ## Vectorized Transformation of F_EQ

# Compute Dot Products so we only need to do it once
n1_dot_product = Ksi.T @ n1
n2_dot_product = Ksi.T @ n2
n3_dot_product = Ksi.T @ n3
n4_dot_product = Ksi.T @ n4


u_magnitude_sq = u_local**2 + v_local**2  # Shape: (N_cv_y, N_cv_x, 1)

T = 1  # Total number of time steps

# Solver
for t in range(T):
    # Vectorized boundary conditions

    # Top boundary (j == 0)
    f_nd_neq[0, :, :] = f[0, :, :] - f_eq[0, :, :]  # Ensure the shapes align
    Rho_nd[0, :] = Rho[0, :]  # Update density
    f_nd_eq[0, :, :] = w[None, None, :] * Rho_nd[0, :, None] * (1 + Ksi_dot_U / c_s**2 + Ksi_dot_U_squared - U_lid_term)
    f_nd[0, :, :] = f_nd_eq[0, :, :] + f_nd_neq[0, :, :]

    # Bottom boundary (j == N_nd_y - 1)
    f_nd_neq[-1, :, :] = f[-1, :, :] - f_eq[-1, :, :]
    Rho_nd[-1, :] = Rho[-1, :]
    f_nd_eq[-1, :, :] = w[None, None, :] * Rho_nd[-1, :, None] * (1 + Ksi_dot_U / c_s**2 + Ksi_dot_U_squared - U_lid_term)
    f_nd[-1, :, :] = f_nd_eq[-1, :, :] + f_nd_neq[-1, :, :]

    # Left boundary (i == 0)
    f_nd_neq[:, 0, :] = f[:, 0, :] - f_eq[:, 0, :]
    Rho_nd[:, 0] = Rho[:, 0]
    f_nd_eq[:, 0, :] = w[None, None, :] * Rho_nd[:, 0, None] * (1 + Ksi_dot_U / c_s**2 + Ksi_dot_U_squared - U_lid_term)
    f_nd[:, 0, :] = f_nd_eq[:, 0, :] + f_nd_neq[:, 0, :]

    # Right boundary (i == N_nd_x - 1)
    f_nd_neq[:, -1, :] = f[:, -1, :] - f_eq[:, -1, :]
    Rho_nd[:, -1] = Rho[:, -1]
    f_nd_eq[:, -1, :] = w[None, None, :] * Rho_nd[:, -1, None] * (1 + Ksi_dot_U / c_s**2 + Ksi_dot_U_squared - U_lid_term)
    f_nd[:, -1, :] = f_nd_eq[:, -1, :] + f_nd_neq[:, -1, :]

# Output for each time step (for verification) ##end of first portion / loop (line 200)
    print(f"Time step: {t}")
    F1 = cp.zeros((9,1))
    j, i = 0, 0  # Change these values as needed

    fu = f[j, i, :].reshape(9, 1)  # Upwind
    fd = f[j, i + 1, :].reshape(9, 1)  #Downwind
    print("FU shape:", fu.shape)


    n1_mask = n1_dot_product <= 0
    n1_mask = n1_mask.flatten()
    fu_temp = cp.copy(fu[n1_mask, :])  # Copy only the values to be swapped
    fu[n1_mask, :] = fd[n1_mask, :]
    fd[n1_mask, :] = fu_temp

    fc1 = fu  # This will reflect the modified upwind values
    F1 = fc1[:, 0] * n1_dot_product.flatten() * dy  # Element-wise multiplication
    F1 = F1.reshape(-1, 1)  # Reshape to (9, 1)

    F2 = cp.zeros((9,1))

    n2_mask = n2_dot_product <= 0
    n2_mask = n2_mask.flatten()
    fu_temp = cp.copy(fu[n2_mask, :])  # Copy only the values to be swapped
    fu[n2_mask, :] = fd[n2_mask, :]
    fd[n2_mask, :] = fu_temp        # Assign the original fu values to f

    fc2 = fu
    F2 = fc2[:, 0] * n2_dot_product.flatten() * dx # Face 2
    F2 = F2.reshape(-1, 1)  # Reshape to make it a 2D array with one column

    F3 = cp.zeros((9,1))

    fu = f[j, i, :].reshape(9, 1)  # Upwind
    num_nodes = f_nd.shape[0]
    f_nd_center=((f_nd[j,1,:])+(f_nd[j+1,1,:]))/2
    fd = 2 * f_nd_center - fu
    print("shape is ", f_nd_center.shape)

    # If statement in line 253
    n3_mask = n3_dot_product <= 0
    n3_mask = n3_mask.flatten()
    fu_temp = cp.copy(fu[n3_mask, :])  # Copy only the values to be swapped
    print(fd.shape)
    fu[:, 0] = fd[:, 0]
    fd[n3_mask, :] = fu_temp        # Assign the original fu values to f

    fc3 = fu;
    F3 = fc3[:, 0] * n3_dot_product.flatten() * dy # Face 3
    F3 = F3.reshape(-1, 1)  # Reshape to make it a 2D array with one column

#Flux face 4
    F4 = cp.zeros((9,1))
    fu = f[j, i, :].reshape(9, 1)  # Upwind
    num_nodes = f_nd.shape[0]
    f_nd_center=((f_nd[j,1,:])+(f_nd[j+1,1,:]))/2
    fd = 2 * f_nd_center - fu

    # If statement in line 253
    n4_mask = n4_dot_product <= 0
    n4_mask = n4_mask.flatten()
    fu_temp = cp.copy(fu[n4_mask, :])  # Copy only the values to be swapped
    fu[:, 0] = fd[:, 0]
    fd[n4_mask, :] = fu_temp        # Assign the original fu values to f

    fc4 = fu;
    F4 = fc4[:, 0] * n4_dot_product.flatten() * dy # Face 4
    F4 = F4.reshape(-1, 1)  # Reshape to make it a 2D array with one column


    print("F1 shape:", F1.shape)
    #print("F2 shape:", F2.shape)
    #print("F3 shape:", F3.shape)
    #print("F4 shape:", F4.shape)
    F = (F1+F2+F3+F4)/A;
    print(F.shape)
    print(F4)





    #for CVs touching the top boundary ensure proper