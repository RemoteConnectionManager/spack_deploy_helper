import sys
import string
substitutions={
        'COMPILER_SPEC' : str(sorted([s['compiler']['spec'] for s in spack.config.get('compilers') if s['compiler']['spec'].split('@')[0] == 'oneapi' ])[0]),
        'COMPILER_PREFIX' : str(sorted([s for s in spack.store.db.query('intel-oneapi-compilers')], key=lambda spc: spc.version)[0].prefix),
        'COMPILER_OS' : str(spack.platforms.host().operating_system('default_os'))}
with open(sys.argv[1], mode='r', encoding='utf-8')  as filein:
    with open(sys.argv[2], mode='w', encoding='utf-8')  as fileout:
        for line in filein :
            fileout.write(string.Template( line).safe_substitute(substitutions))
