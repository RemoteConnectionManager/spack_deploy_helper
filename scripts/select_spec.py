import sys
import string
import logging

def select_spec(in_spec, exclude_variants=[]):
    
    logging.basicConfig(format='%(message)s')
    log = logging.getLogger(__name__)
    package_available_versions = spack.repo.get(in_spec).versions.keys()
    installed_specs = spack.store.db.query(in_spec)
    matching_specs=sorted([s for s in installed_specs if not s.external and s.version in package_available_versions], reverse=True, key=lambda spc: spc.version)
    if len(matching_specs) == 0:
        log.error('no matching installed spec to ' + in_spec)
        exit(1)
    if len(matching_specs) > 1:
        log.warning("multiple matching installed spec to " + in_spec)
        log.warning(str(matching_specs))

    return(matching_specs[0])

def spec_subst(in_spec, exclude_variants=['build_type','languages','patches']):
    substitutions={
        'NAME' : str(in_spec.name),
        'PREFIX' : str(in_spec.prefix),
        'VERSION' : str(in_spec.version),
        'VARIANTS' : ''.join([str(vitem[1]) for vitem in in_spec.variants.items() if not vitem[0] in exclude_variants])
    }
    return(substitutions)

if __name__ == '__main__':
    import argparse
    import os
    import inspect
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", help="input partial spec")

    parser.add_argument("-t", "--tplstr", help="template string", default='${NAME}@${VERSION}${VARIANTS}')
    parser.add_argument("-f", "--tplfile", help="template file", default='')
    args = parser.parse_args()


    template=args.tplstr
    if args.tplfile:
        if args.tplfile[0] == '/':
            tplfile = args.tplfile
        else:
            tplfile = os.path.join(os.path.dirname(os.path.abspath(inspect.getfile(lambda: None))),args.tplfile)
        try:
            with open(tplfile) as f:
                template = f.read()
        except Exception: 
            log.warning("unable to read template from:" + tplfile, file=sys.stderr)
    print(string.Template( template).safe_substitute(spec_subst(select_spec(args.spec))))

