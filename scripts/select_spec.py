import sys
import string
import logging
import errno
import os
import os.path

exclude_variants=['build_type','languages','patches']

def makedirs(folder, *args, **kwargs):
  try:
    return os.makedirs(folder, exist_ok=True, *args, **kwargs)
  except TypeError: 
    # Unexpected arguments encountered 
    pass

  try:
    # Should work is TypeError was caused by exist_ok, eg., Py2
    return os.makedirs(folder, *args, **kwargs)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

    if os.path.isfile(folder):
      # folder is a file, raise OSError just like os.makedirs() in Py3
      raise

def extended_version(in_spec):
    deps_version = str(in_spec.version)
    for s in in_spec.dependencies():
        deps_version += '^' + s.name + '@' + str(s.version)
    return(deps_version)

def select_compiler(comp_spec, sysinstalled=True):
    configured_compilers = spack.config.get('compilers')
    compiler_name = comp_spec.split('@')[0]
    matched_compilers = [s['compiler']['spec'] for s in configured_compilers if (bool( not sysinstalled) ^ str(s['compiler']['paths']['cc']).startswith('/usr') ) and (s['compiler']['spec'].split('@')[0] == compiler_name )]
    return( sorted(matched_compilers))

def select_spec(in_spec):
    
    logging.basicConfig(format='%(message)s')
    log = logging.getLogger(__name__)
    package_available_versions = spack.repo.get(in_spec).versions.keys()
    installed_specs = spack.store.db.query(in_spec)
    matching_specs=sorted([s for s in installed_specs if not s.external and s.version in package_available_versions], reverse=True, key=lambda spc: extended_version(spc))
    if len(matching_specs) == 0:
        log.error('no matching installed spec to ' + in_spec)
        exit(1)
    if len(matching_specs) > 1:
        log.warning("multiple matching installed spec to " + in_spec)
        log.debug(str(matching_specs))
    out_spec = matching_specs[0]
    out_spec_tuple = (out_spec.name,
                     out_spec.prefix,
                     str(out_spec.version),
                     ' '.join([str(vitem[1]) for vitem in out_spec.variants.items() if not vitem[0] in exclude_variants])
                    )
    return(out_spec_tuple)

def get_external_spec(in_spec):
    log = logging.getLogger(__name__)
    out_spec_tuple=(in_spec,'','','')
    try:
        out_spec = sorted([s for s in spack.store.db.query(in_spec) if s.external], reverse=True, key=lambda spc: spc.version)[0]
        out_spec_tuple = (out_spec.name,
                         out_spec.prefix,
                         str(out_spec.version),
                         ' '.join([str(vitem[1]) for vitem in out_spec.variants.items() if not vitem[0] in exclude_variants])
                        )
    except Exception as exception :
        log.warning("unable to extract " + in_spec + " from external spack.store.db.query due to exeception: " + str(exception))
        try:
            out_spec = sorted([ext for ext in spack.config.get('packages')[in_spec]['externals'] if ext['prefix'].startswith('/usr')], reverse=True, key=lambda spc: spc['spec']) [0]
            out_spec_tuple=(out_spec['spec'].split('@')[0],
                            out_spec['prefix'],
                            ''.join(out_spec['spec'].split('@')[1:]),
                            ''
                           )
        except Exception as exception :
            log.error("unable to extract " + in_spec + " from external in config packages due to exeception: " + str(exception))
            exit(1)
    return(out_spec_tuple)

def spec_subst(spec_tuple, named_subst=False, compiler_spec=''):
    spec = spec_tuple[0]
    if spec_tuple[2]:
        spec += '@' + spec_tuple[2]
    if compiler_spec:
        spec += '%' + compiler_spec
    spec += ' ' + spec_tuple[3]
    if named_subst:
        substitutions={
            spec_tuple[0] + '_PREFIX' : spec_tuple[1],
            spec_tuple[0] + '_VERSION' : spec_tuple[2],
            spec_tuple[0] + '_VARIANTS' : spec_tuple[3],
            spec_tuple[0] + '_SPEC' : spec
        }
    else:
        substitutions={
            'NAME' : spec_tuple[0],
            'PREFIX' : spec_tuple[1],
            'VERSION' : spec_tuple[2],
            'VARIANTS' : spec_tuple[3],
            'SPEC' : spec
        }
    return(substitutions)

if __name__ == '__main__':
    import argparse
    import os
    import inspect

    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    #parser.add_argument("spec", help="input partial spec")
    parser.add_argument('specs', metavar='spec', nargs='*', help='input partial specs')

    parser.add_argument("-t", "--tplstr", help="template string", default='${SYS_GCC}')
    parser.add_argument("-f", "--tplfile", help="template file", default='')
    parser.add_argument("-o", "--outfile", help="output file", default='')
    parser.add_argument("-c", "--compiler", help="compiler spec", default='')
    parser.add_argument('-e', "--external", metavar='spec', nargs='+', help='external specs')
    parser.add_argument('--add', action='store_true')
    parser.add_argument( "--header", help="header string", default='')
    parser.add_argument( "--loglevel", help="log level", default='warning')
    args = parser.parse_args()

    log.setLevel(getattr(logging, args.loglevel.upper()))
    
    if args.add:
         log.info("Adding mode:")
    else:
         log.info("Merging mode:")
  
    compilers_subst={}
    sys_gcc_compilers = select_compiler('gcc') 
    if len(sys_gcc_compilers) > 0:
        compilers_subst['SYS_GCC'] = sys_gcc_compilers[0] 
    if args.compiler:
        compspecs = select_compiler(args.compiler, sysinstalled=False)
        if len(compspecs) > 0:
            compilers_subst['COMPILER'] = compspecs[0] 
            compilers_subst['COMPILER_NAME'] = compspecs[0].split('@')[0] 

    template=args.tplstr
    tpldir=''
    if args.tplfile:
        if args.tplfile[0] == '/':
            tplfile = args.tplfile
        else:
            tplfile = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(lambda: None))),args.tplfile)
        try:
            with open(tplfile) as f:
                template = f.read()
                tpldir = os.path.dirname(tpldir)
        except Exception: 
            log.warning("unable to read template from:" + tplfile)
    outstring = ''
    common_subst = compilers_subst.copy()
    if args.external:
        for spec in args.external:
            common_subst.update( spec_subst(get_external_spec(spec), named_subst=True)  )
    
    substitutions = common_subst.copy()
    for spec in args.specs:
        if args.add:
            substitutions = common_subst.copy()
            substitutions.update( spec_subst(select_spec(spec)) )
            log.debug("substitutions:" + str(substitutions))
            outstring += string.Template( template).safe_substitute(substitutions) + '\n'
        else:
            substitutions.update( spec_subst(select_spec(spec), named_subst=True ))

    if not args.add:
        log.debug("substitutions:" + str(substitutions))
        outstring += string.Template( template).safe_substitute(substitutions) + '\n'
        
    if args.header:
        outstring = args.header + "\n" + outstring
    if args.outfile:
        if args.outfile[0] == '/':
            outfile = args.outfile
        else:
            #if not absolute, outfile is relative to template file if template file exists otherwise to scriptfile
            if not tpldir:
                tpldir = os.path.dirname(os.path.abspath(inspect.getfile(lambda: None)))
            try:
                generated_envs_dir = os.path.join(
                                         os.path.dirname(os.path.dirname(os.environ['SPACK_USER_CACHE_PATH'])),
                                         'generated_envs',
                                         os.path.basename(os.environ['SPACK_USER_CACHE_PATH']))
                outfile = os.path.join(generated_envs_dir,args.outfile)
            except Exception as e:
                log.debug("generated_envs failed:" + str(e))
                outfile = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(lambda: None))),args.outfile)
        makedirs(os.path.dirname(outfile), mode = 0o755)
        with open(outfile,'w') as out:
            out.write(outstring)
        print(outfile)
    else:
        print(outstring)
