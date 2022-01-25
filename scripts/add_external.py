import sys
import string
if len(sys.argv) < 3:
    print("arguments: spec template outfile [out_compiler_spec]")
    exit(1)
out_compiler_spec=''
if len(sys.argv) >= 4:
    out_compiler_spec='%'+sys.argv[3]
package_available_versions = spack.repo.get(sys.argv[1]).versions.keys()
installed_specs = spack.store.db.query(sys.argv[1])
matching_specs=sorted([s for s in installed_specs if not s.external and s.version in package_available_versions], reverse=True, key=lambda spc: spc.version)
if len(matching_specs) == 0:
    print("no matching installed spec to " + sys.argv[1])
    exit(1)
if len(matching_specs) > 1:
    print("multiple matching installed spec to " + sys.argv[1])
    print(str(matching_specs))
    print("continue taking first")
matching_spec=matching_specs[0]

substitutions={
        'EXTERNAL_NAME' : str(matching_spec.name),
        'EXTERNAL_PREFIX' : str(matching_spec.prefix),
}
exclude_variants = ['build_type']
new_spec += ''.join([str(vitem[1]) for vitem in curr_spec.variants.items() if not vitem[0] in exclude_variants])
substitutions['NEW_SPEC'] =  str(matching_spec.name) + '@' + 
                             str(matching_spec.version) + 
                             out_compiler_spec + 
                             ''.join([str(vitem[1]) for vitem in curr_spec.variants.items() if not vitem[0] in exclude_variants])

template_string="""
packages:
  ${EXTERNAL_NAME}:
    externals:
    - spec: ${NEW_SPEC}
      prefix: ${EXTERNAL_PREFIX}
      buildable: false
"""
with open(sys.argv[2], mode='w', encoding='utf-8')  as fileout:
    fileout.write(string.Template( template_string).safe_substitute(substitutions))
