import sys
print(str(sorted([ s.version for s in spack.compilers.all_compiler_specs() if sys.argv[1] in str(s) ])[0])) 
