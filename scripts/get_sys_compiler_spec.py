print(sorted([s['compiler']['spec'] for s in spack.config.get('compilers') if ( '/usr' in s['compiler']['paths']['cc'] ) and (s['compiler']['spec'].split('@')[0] == 'gcc' )])[0])
