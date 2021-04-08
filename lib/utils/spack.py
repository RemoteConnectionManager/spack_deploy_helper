import os


def is_spack_root(path):
    print("##@@#####is_spack_root---->",path)
    return os.path.exists(os.path.join(path, 'bin', 'spack'))


