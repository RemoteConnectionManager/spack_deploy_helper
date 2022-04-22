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

    parser.add_argument("--maincompiler", help="installed spec for main compiler", default='intel-oneapi-compilers')
    parser.add_argument("--auxcompiler", help="installed spec for auxiliary compiler", default='none')
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
    prefixes = {}
    for p in ['maincompiler','auxcompiler']:
        in_spec = vars(args)[p]
        selected_spec_tuple = select_spec.select_spec(in_spec)
        if selected_spec_tuple:
            prefixes[p] = selected_spec_tuple[1]
            for h in preferred_spec_tuples:
                spec_tuple = preferred_spec_tuples[h]
                if spec_tuple[0] == selected_spec_tuple[0]:
                    prefixes[p] = spec_tuple[1]
    log.info(prefixes)

    
    intel_compilers_config = select_spec.map_intel_compilers(prefixes['maincompiler'], prefixes.get('auxcompiler', ''))
    log.debug("######## intel_compilers_config #############")
    log.debug(str(intel_compilers_config))
    compiler_config = spack.compilers.get_compiler_config('site')
    if compiler_config == {}:
       compiler_config= []
    log.debug("######## compiler_config #############")
    log.debug(str(compiler_config))
    for i in intel_compilers_config:
        compiler_config.append(i)

    if args.outdir:
        if args.outdir[0] == '/':
            outdir = args.outdir
        else:
           outdir = os.path.normpath(os.path.join(os. getcwd(),args.outdir))

        select_spec.makedirs(outdir, mode = 0o755)
        configscope = spack.config.ConfigScope('private',outdir)
        outfile = configscope.get_section_filename('compilers')
        configscope.sections['compilers'] = {'compilers': compiler_config}
        data = configscope.get_section('compilers')
        
        configscope._write_section('compilers') 
    else:
        spack.config.set('compilers', compiler_config, scope='site')
