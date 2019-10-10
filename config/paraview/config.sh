#!/usr/bin/env bash
spack spec --install-status paraview
#spack install --verbose paraview
spack install -v paraview
spack install -v vtk
