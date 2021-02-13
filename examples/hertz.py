#!/usr/bin/env python
# coding: utf-8

# # A finite element analysis of elastic contact problem
# 
# In this example of a deformable ``cylinder 1`` enters in contact with a deformable  ``cylinder 2``. We use here python interface, translate this program for another interface or in C++ is easy (see the previous example).
# 
# ![Kontakt_paralleler_Zylinder](https://upload.wikimedia.org/wikipedia/commons/e/ef/Kontakt_paralleler_Zylinder.jpg)

# ## The problem setting
# 
# Let $\Omega^{1} \subset \mathbb{R}^{2}$ be the reference of a 2D cylinder 1 and $\Omega^{2} \subset \mathbb{R}^{2}$ the reference configuration of a deformable cylinder. We consider small deformation of these two bodies (linearized elasticity) and the contact between them.

# ## Building the program
# 
# Let us begin by loading Getfem and fixing the parameters of the problem


import getfem as gf
import numpy as np
import pyvista as pv

###############################################################################
#

E = 200000.0  # Yong Modulus (MPa)
nu = 0.3  # Poisson ratio
clambda = E * nu / ((1 + nu) * (1 - 2 * nu))  # First Lame coefficient (MPa)
cmu = E / (2 * (1 + nu))  # Second Lame coefficient (MPa)
clambdastar = (
    2 * clambda * cmu / (clambda + 2 * cmu)
)  # Lame coefficient for Plane stress (MPa)

elements_degree = 2  # Degree of the finite element methods

applied_force = 200.0 * 100  # Force at the top boundary (N)

gamma0 = 1.0 / E  # Augmentation parameter for the augmented Lagrangian


###############################################################################
#
# We consider that the radius of the two cylinder is 5mm.
# We load the mesh of the cylinder using the load of a mesh from a GetFEM ascii mesh file (see the documentation of the Mesh object in the python interface).

# In[2]:


# !gmsh hertz.mesh -f msh2 -save -o hertz.msh
mesh = gf.Mesh("import", "gmsh", "hertz.msh")
mesh.translate([0.0, 5.0])
P = mesh.pts()

# cvid1
c1 = P[1, :] >= 0.0
pid1 = np.compress(c1, list(range(0, mesh.nbpts())))
cvid1 = mesh.cvid_from_pid(pid1)

# cvid2
c2 = P[1, :] <= 0.0
pid2 = np.compress(c2, list(range(0, mesh.nbpts())))
cvid2 = mesh.cvid_from_pid(pid2)

# Approximate mesh size
h = 1.0

mesh1 = gf.Mesh("clone", mesh)
mesh1.del_convex(cvid2)
mesh1.export_to_vtk("mesh1.vtk")

mesh2 = gf.Mesh("clone", mesh)
mesh2.del_convex(cvid1)
mesh2.export_to_vtk("mesh2.vtk")


###############################################################################
#
# The result is the following

# In[3]:


m1 = pv.read("mesh1.vtk")
m2 = pv.read("mesh2.vtk")
p = pv.Plotter(shape=(1, 1))
p.subplot(0, 0)
p.add_mesh(m1, show_edges=True)
p.add_mesh(m2, show_edges=True)
p.show_grid()
p.show(screenshot="mesh.png", window_size=[1200, 1400], cpos="xy")


###############################################################################
#
# ## Boundary selection

# We have to select the different parts of the boundary where we will set some boundary conditions, namely the boundary of the rim (in order to apply a force and the fact that the rim is rigid), the contact boundary of the wheel and the bottom boundary of the foundation that we will assume clamped.


fb2 = mesh1.outer_faces_with_direction(
    [0.0, -1.0], np.pi / 2.0
)  # Contact boundary of the wheel
fb3 = mesh2.outer_faces_with_direction(
    [0.0, -1.0], 0.01
)  # Bottom boundary of the foundation
fb4 = mesh1.outer_faces_with_direction([0.0, 1.0], np.pi / 2.0)  # Top boundary
fb5 = mesh2.outer_faces_with_direction(
    [0.0, 1.0], np.pi / 2.0
)  # Contact boundary of the wheel
fb6 = mesh1.outer_faces_with_direction([-1.0, 0], 0.01)  # Left boundary
fb7 = mesh2.outer_faces_with_direction([-1.0, 0], 0.01)  # Left boundary

HOLE_BOUND = 1
CONTACT_BOUND = 2
BOTTOM_BOUND = 3
TOP_BOUND = 4
LEFT_BOUND = 5

mesh1.set_region(CONTACT_BOUND, fb2)
mesh2.set_region(BOTTOM_BOUND, fb3)
mesh1.set_region(TOP_BOUND, fb4)
mesh2.set_region(CONTACT_BOUND, fb5)
mesh1.set_region(LEFT_BOUND, fb6)
mesh2.set_region(LEFT_BOUND, fb7)


###############################################################################
#
# Note that the command `mesh1.outer_faces_with_direction([0., -1.0], np.pi/6)` allows to select all the faces having a unit outward normal having an angle less or equal to `np.pi/6` with the vector `[0., -1.0]`.

# ## Definition of finite elements methods and integration method
# We define mfu1, mfu2 two finite element methods which will approximate the displacements in the `cylinder1` and `cylinder2`.
# `mflambda` is finite element method to approximate a multiplier to take into account the rigidity of the rim, `mflambda_C` is to approximate the contact multiplier (contact pressure) and `mfvm1`, `mfvm2` will be used to interpolate the Von Mises stresses of the wheel and the foundation for post-processing.
# `mim1`, `mim2` are two integration methods on the `cylinder1` and the `cylinder2`.


mfu1 = gf.MeshFem(mesh1, 2)
mfu1.set_classical_fem(elements_degree)
mfd1 = gf.MeshFem(mesh1, 1)
mfd1.set_classical_fem(elements_degree)
mflambda = gf.MeshFem(mesh1, 2)
mflambda.set_classical_fem(elements_degree - 1)
mflambda_C = gf.MeshFem(mesh1, 1)
mflambda_C.set_classical_fem(elements_degree - 1)
mfu2 = gf.MeshFem(mesh2, 2)
mfu2.set_classical_fem(elements_degree)
mfd2 = gf.MeshFem(mesh2, 1)
mfd2.set_classical_fem(elements_degree)
mfvm1 = gf.MeshFem(mesh1, 1)
mfvm1.set_classical_discontinuous_fem(elements_degree)
mfvm2 = gf.MeshFem(mesh2, 1)
mfvm2.set_classical_discontinuous_fem(elements_degree)
mim1 = gf.MeshIm(mesh1, pow(elements_degree, 2))
mim2 = gf.MeshIm(mesh2, pow(elements_degree, 2))


###############################################################################
#
# ## Model definition
# 
# We use a real model and declare the two variables which will represent the displacements:

# In[6]:


md = gf.Model("real")
md.add_fem_variable("u1", mfu1)
md.add_fem_variable("u2", mfu2)

###############################################################################
#
# ## Linearized elasticity bricks
# 
# We add the Lamé coefficients as data of the model and add a linearized elasticity brick for the wheel and the foundation:

md.add_initialized_data("cmu", [cmu])
md.add_initialized_data("clambdastar", [clambdastar])
md.add_isotropic_linearized_elasticity_brick(mim1, "u1", "clambdastar", "cmu")
md.add_isotropic_linearized_elasticity_brick(mim2, "u2", "clambdastar", "cmu")

###############################################################################
#
# ## Clamped condition at the bottom boundary
# 
# We prescribed the displacement at bottom face of the foundation to vanish, for instance with a multiplier with the add of the following brick:

md.add_initialized_data("r0", [0, -0.1])
md.add_initialized_data("r1", [0, 0])
md.add_initialized_data("r2", [0, 0])
md.add_initialized_data("r3", [0, 0])
md.add_initialized_data("H0", [[0, 0], [0, 1]])
md.add_initialized_data("H1", [[1, 0], [0, 0]])
md.add_initialized_data("H2", [[1, 0], [0, 0]])
md.add_initialized_data("H3", [[0, 0], [0, 1]])


md.add_generalized_Dirichlet_condition_with_multipliers(
    mim1, "u1", mfu1, TOP_BOUND, "r0", "H0"
)
md.add_generalized_Dirichlet_condition_with_multipliers(
    mim1, "u1", mfu1, LEFT_BOUND, "r1", "H1"
)
md.add_generalized_Dirichlet_condition_with_multipliers(
    mim2, "u2", mfu2, LEFT_BOUND, "r2", "H2"
)
md.add_generalized_Dirichlet_condition_with_multipliers(
    mim2, "u2", mfu2, BOTTOM_BOUND, "r3", "H3"
)

###############################################################################
#

# ## Contact condition (use of interpolate transformations)

# Now, let us see how to prescribed the contact condition between the two structures.
# It is possible to use predefined bricks (see [Small sliding contact with friction bricks](https://getfem.readthedocs.io/en/latest/userdoc/model_contact_friction.html#ud-model-contact-friction) for small deformation/small sliding contact and [Large sliding/large deformation contact with friction bricks](https://getfem.readthedocs.io/en/latest/userdoc/model_contact_friction_large_sliding.html#ud-model-contact-friction-large) for large deformation/large sliding contact).
# However, we will see here how to directly prescribe a contact condition using an augmented Lagrangian formulation and the interpolate transformations.
# 
# For small deformation contact, the correspondence between points of one contact surface to the other have to be described on the reference configuration and is not evolving, which is of course simpler but is an approximation.
# 
# We consider that the contact boundary of the wheel is the slave one and we have to describe the transformation from the contact boundary of the wheel to the contact boundary of the foundation.
# This is quite simple here, since the contact boundary of the foundation corresponds to a vanishing vertical coordinate.
# So we define the transformation
# 
# $$
# X \longmapsto (X(1), -X(2))
# $$
# 
# where $X$ is the vector of coordinates of the point. We add this transformation to the model with the command

md.add_interpolate_transformation_from_expression("Proj1", mesh1, mesh2, "[X(1);-X(2)]")

###############################################################################
#

# As a consequence, it will be possible to use this transformation, from the mesh of the wheel to the mesh of the foundation, into GWFL expressions.
# Notes that this is here a very simple constant expression.
# More complex expressions depending on the data or even the variables of the model can be used.
# If the expression of a transformation depends on the variable of the model, the tangent linear system will automatically takes into account this dependence (see [Interpolate transformations](https://getfem.readthedocs.io/en/latest/userdoc/gasm_high.html#ud-gasm-high-transf) for more details). 
# Note also that transformation corresponding to a large sliding contact and automatically searching for the correspondence between contact boundaries exist in GetFEM (see [Integral contact brick with raytrace](https://getfem.readthedocs.io/en/latest/userdoc/model_contact_friction_large_sliding.html#ud-model-contact-friction-large-hlgav)).
# 
# Using the defined transformation, we can write an integral contact condition using an augmented Lagrangian formulation (see [Small sliding contact with friction bricks](https://getfem.readthedocs.io/en/latest/userdoc/model_contact_friction.html#ud-model-contact-friction) for more details).
# The corresponding term (to be added to the rest of the weak formulation) reads:
# 
# $$
#   \cdots +  \int_{\Gamma_c} \lambda_N(X) (\delta_{u^1}(X)-\delta_{u^2}(\Pi(X)))\cdot n d\Gamma \\
#   -   \int_{\Gamma_c} \left(\lambda_N(X) + \left(\lambda_N(X) + \dfrac{1}{h_T\gamma_0}((X + u^1(X))\cdot n - (\Pi(X) - u^2(\Pi(X)))\cdot n\right)_-\right)\delta_{\lambda_N}(X) d\Gamma = 0 ~~~~ \forall \delta_{\lambda_N}, \forall \delta_{u^1}, \forall \delta_{u^2},
# $$
# 
# where $\Gamma_c$ is the slave contact boundary, $\lambda_N$ is the contact multiplier (contact pressure), $h_T$ is the radius of the element, $\Pi$ is the transformation, $n$ is the outward normal vector to the master contact boundary (here $n = (0,1)$), $\gamma_0$ is an augmentation parameter, $(\cdot)_-:I\hspace{-0.2em}R\rightarrow I\hspace{-0.2em}R_+$ is the negative part and $\delta_{\lambda_N}, \delta_{u^1}, \delta_{u^2}$ are the test  functions corresponding to $\lambda_N, u^1, u^2$, respectively.
# 
# Using GWFL, the contact condition can be added by:

md.add_initialized_data("gamma0", [gamma0])
md.add_filtered_fem_variable("lambda1", mflambda_C, CONTACT_BOUND)
md.add_nonlinear_term(mim1, "lambda1*(Test_u1.[0;1])-lambda1*(Interpolate(Test_u2,Proj1).[0;1])", CONTACT_BOUND)
md.add_nonlinear_term(mim1, "-(gamma0*element_size)*(lambda1 + neg_part(lambda1+(1/(gamma0*element_size))*((u1-Interpolate(u2,Proj1)+X-Interpolate(X,Proj1)).[0;1])))*Test_lambda1", CONTACT_BOUND)


###############################################################################
#

# ## Prescribing the rigidity of the rim and the vertical force
# We have now to prescribe the rigidity of the rim. This is a non-standard condition, since we do not know a priori what will be the vertical displacement of the rim.
# We can use an additional unknown for that vertical displacement.

# We need a multiplier to prescribe the displacement on the rim boundary:

# ## Model solve
# We can now solve our problem with:

###############################################################################
#


md.solve("max_res", 1e-9, "max_iter", 100, "noisy")

###############################################################################
# Note that in some configuration, it is preferable to use a more basic line search than the default one:
# md.solve(
#     "max_res", 1e-9, "max_iter", 100, "noisy", "lsearch", "simplest", "alpha min", 0.8
# )
# ## Export the solution
# 
# Now the code to export the solution with the VonMises stress:


U1 = md.variable("u1")
U2 = md.variable("u2")
VM1 = md.compute_isotropic_linearized_Von_Mises_or_Tresca("u1", "clambdastar", "cmu", mfvm1)
VM2 = md.compute_isotropic_linearized_Von_Mises_or_Tresca("u2", "clambdastar", "cmu", mfvm2)

mfvm1.export_to_vtk("displacement_with_von_mises1.vtk", mfvm1, VM1, "Von Mises Stresses", mfu1, U1, "Displacements")

mfvm2.export_to_vtk("displacement_with_von_mises2.vtk", mfvm2, VM2, "Von Mises Stresses", mfu2, U2, "Displacements")

###############################################################################
# You can view solutions with pyvista:
#

m1 = pv.read("displacement_with_von_mises1.vtk")
m2 = pv.read("displacement_with_von_mises2.vtk")
c1 = m1.contour(np.linspace(0, 50000, 5))
c2 = m2.contour(np.linspace(0, 50000, 5))
p = pv.Plotter(shape=(1, 2))

p.subplot(0, 0)
p.add_text("Von Mises Stresses")
p.add_mesh(c1, color="black", line_width=2)
p.add_mesh(m1, show_edges=False, clim=[0, 50000], opacity=0.85)
p.add_mesh(c2, color="black", line_width=2)
p.add_mesh(m2, show_edges=False, clim=[0, 50000], opacity=0.85)
p.show_grid()

p.subplot(0, 1)
p.add_text("Displacements")
m1.active_vectors_name = "Displacements"
m2.active_vectors_name = "Displacements"
p.add_mesh(m1.warp_by_vector(), style="surface", show_edges=True, clim=[0, 50000], opacity=1.0, color="white")
p.add_mesh(m2.warp_by_vector(), style="surface", show_edges=True, clim=[0, 50000], opacity=1.0, color="white")
p.show_grid()

p.show(screenshot="von_mises.png", window_size=[1200, 900], cpos="xy")
