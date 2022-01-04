import sys
import string
substitutions={
#from spack.compilers        'GCC_VER' : str(sorted([ s.version for s in spack.compilers.all_compiler_specs() if 'gcc' in str(s) ])[0]), 
        'COMPILER_SPEC' : str(sorted([s['compiler']['spec'] for s in spack.config.get('compilers') if ( '/usr' in s['compiler']['paths']['cc'] ) and (s['compiler']['spec'].split('@')[0] == 'gcc' )])[0]),
#from config       'SYS_OPENSSL_VER' : spack.config.get('packages')['openssl']['externals'][0]['spec'].split('@')[1]}
        'SYS_OPENSSL_VER' : str(sorted([s.version for s in spack.store.db.query('openssl') if s.external])[0])}
with open(sys.argv[1], mode='r', encoding='utf-8')  as filein:
    with open(sys.argv[2], mode='w', encoding='utf-8')  as fileout:
        for line in filein :
            fileout.write(string.Template( line).safe_substitute(substitutions))
