#!/usr/bin/env bash
spack spec -I curl
spack install curl
spack spec -I nasm
spack install nasm
spack spec -I cmake
spack install cmake
spack install --verbose py-flake8
spack install perl
