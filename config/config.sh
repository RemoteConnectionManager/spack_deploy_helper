#!/usr/bin/env bash
spack  compiler find --scope site
spack module refresh -y --delete-tree
