import sys
import string
if len(sys.argv) < 3:
    print("arguments: spec template outfile [out_compiler_spec]")
    exit(1)
out_compiler_spec=''
if len(sys.argv) >= 4:
    out_compiler_spec='%'+sys.argv[3]

matching_specs=sorted([s for s in spack.store.db.query(sys.argv[1]) if not s.external], key=lambda spc: spc.version)
if len(matching_specs) == 0:
    print("no matching installed spec to " + sys.argv[1])
    exit(1)
if len(matching_specs) > 1:
    print("multiple matching installed spec to " + sys.argv[1])
    print(str(matching_specs))
    print("continue taking first")
matching_spec=matching_specs[0]
template_string="""
packages:
  ${EXTERNAL_NAME}:
    externals:
    - spec: ${NEW_SPEC}
      prefix: ${EXTERNAL_PREFIX}
"""
substitutions={
        'EXTERNAL_NAME' : str(matching_spec.name),
        'EXTERNAL_PREFIX' : str(matching_spec.prefix),
        'NEW_SPEC' : str(matching_spec.name) + '@' + str(matching_spec.version) + out_compiler_spec}
with open(sys.argv[2], mode='w', encoding='utf-8')  as fileout:
    fileout.write(string.Template( template_string).safe_substitute(substitutions))
