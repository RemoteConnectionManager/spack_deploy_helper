import sys
import string
import logging
import os
import inspect

sys.path.append(os.path.dirname(os.path.abspath(inspect.getfile(lambda: None))))

import select_spec

if __name__ == '__main__':
    import argparse
    import os
    import inspect

    logging.basicConfig(format='%(message)s')
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    #parser.add_argument("spec", help="input partial spec")

    parser.add_argument("--compiler", help="installed spec for compiler", default='gcc')
    parser.add_argument("-o", "--outdir", help="output config dir", default='')
    parser.add_argument("-l", "--lockfile", help="lockfile file to parse for installed specs", default='')
    parser.add_argument( "--loglevel", help="log level", default='warning')
    args = parser.parse_args()

    log.setLevel(getattr(logging, args.loglevel.upper()))



    if args.lockfile:
        preferred_spec_tuples = select_spec.installed_root_specs(args.lockfile)
    else:
        preferred_spec_tuples = []
    for h in preferred_spec_tuples:
        p=preferred_spec_tuples[h]
        log.debug(p[0] + " --- " + p[1])
    compiler_prefix=''
    compiler_spec_tuple = select_spec.select_spec(args.compiler)
    if compiler_spec_tuple:
        for h in preferred_spec_tuples:
            spec_tuple = preferred_spec_tuples[h]
            if spec_tuple[0] == compiler_spec_tuple[0]:
                compiler_prefix = spec_tuple[1]
 
    log.info("Using compiler prefix: -->" + compiler_prefix + "<--")
    if compiler_prefix:
        search_prefixes = [compiler_prefix]
    else:
        search_prefixes = []

    
    compilers_config = select_spec.find_new_compiler_config(prefixes=search_prefixes)

    if args.outdir:
        if args.outdir[0] == '/':
            outdir = args.outdir
        else:
           outdir = os.path.normpath(os.path.join(os. getcwd(),args.outdir))

        select_spec.makedirs(outdir, mode = 0o755)
        configscope = spack.config.ConfigScope('private',outdir)
        outfile = configscope.get_section_filename('compilers')
        configscope.sections['compilers'] = {'compilers': compilers_config}
        data = configscope.get_section('compilers')
        
        configscope._write_section('compilers') 
    else:
        spack.config.set('compilers', compilers_config, scope='site')
