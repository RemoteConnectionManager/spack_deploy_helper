import sys
import string
substitutions={'COMPILER_SPEC' : 'gcc', 'OPENSSL_SPEC' : 'openssl'}
#from spack.compilers        'GCC_VER' : str(sorted([ s.version for s in spack.compilers.all_compiler_specs() if 'gcc' in str(s) ])[0]), 
try:
    substitutions['COMPILER_SPEC'] =  str(sorted([s['compiler']['spec'] for s in spack.config.get('compilers') if ( '/usr' in s['compiler']['paths']['cc'] ) and (s['compiler']['spec'].split('@')[0] == substitutions['COMPILER_SPEC'] )])[0])
except Exception as exception :
    print("unable to set compiler spec for exeception: " + str(esception) + " using " + substitutions['COMPILER_SPEC'] + " for COMPILER_SPEC")
#from config       'SYS_OPENSSL_VER' : spack.config.get('packages')['openssl']['externals'][0]['spec'].split('@')[1]}
try:
    substitutions['OPENSSL_SPEC'] = substitutions['OPENSSL_SPEC'] + '@' + str(sorted([s.version for s in spack.store.db.query(substitutions['OPENSSL_SPEC']) if s.external])[0])
except Exception as exception :
    print("unable to extract OPENSSL_SPEC from external spack.store.db.query due to exeception: " + str(esception))
    try:
        substitutions['OPENSSL_SPEC'] = str(sorted([ext['spec'] for ext in spack.config.get('packages')[substitutions['OPENSSL_SPEC']]['externals'] if '/usr' in ext['prefix']])[0])
    except Exception as exception :
        print("unable to extract OPENSSL_SPEC from external in config packages due to exeception: " + str(esception))
with open(sys.argv[1], mode='r', encoding='utf-8')  as filein:
    with open(sys.argv[2], mode='w', encoding='utf-8')  as fileout:
        for line in filein :
            fileout.write(string.Template( line).safe_substitute(substitutions))
