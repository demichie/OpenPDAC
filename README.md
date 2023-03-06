# OpenPDAC

OpenPDAC is an offline Eulerian-Lagrangian model for the simulation of volcanic flows. The model solves the conservation equations of mass, momentum and energy for a compressible multiphase gas/fine particles mixture and the lagrangian transport equations for larger particles. The solver is based on the OpenFOAM C++ toolbox for computational fluid dynamics. 



> mkdir -p $WM_PROJECT_USER_DIR

> cd $WM_PROJECT_USER_DIR

> mkdir -p applications/solvers/multiphase

> cd applications/solvers/multiphase

> cp -r GitHub/OpenPDAC-10/applications/OpenPDAC .

> cd OpenPDAC

> ./Allwmake


