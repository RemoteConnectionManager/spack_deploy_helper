import os
import logging


def is_spack_root(path):
    logging.getLogger(__name__).debug("##@@#####is_spack_root---->" + path)
    return os.path.exists(os.path.join(path, 'bin', 'spack'))


