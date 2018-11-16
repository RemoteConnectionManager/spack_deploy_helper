import os
import errno

##############################################################################
# Copyright (c) 2013-2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This s taken from Spack.
##############################################################################

def mkdirp(*paths):
    """Creates a directory, as well as parent directories if needed."""
    for path in paths:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno != errno.EEXIST or not os.path.isdir(path):
                    raise e
        elif not os.path.isdir(path):
            raise OSError(errno.EEXIST, "File already exists", path)


def traverse_tree(source_root, dest_root, rel_path='', **kwargs):
    """Traverse two filesystem trees simultaneously.

    Walks the LinkTree directory in pre or post order.  Yields each
    file in the source directory with a matching path from the dest
    directory, along with whether the file is a directory.
    e.g., for this tree::

        root/
          a/
            file1
            file2
          b/
            file3

    When called on dest, this yields::

        ('root',         'dest')
        ('root/a',       'dest/a')
        ('root/a/file1', 'dest/a/file1')
        ('root/a/file2', 'dest/a/file2')
        ('root/b',       'dest/b')
        ('root/b/file3', 'dest/b/file3')

    Keyword Arguments:
        order (str): Whether to do pre- or post-order traversal. Accepted
            values are 'pre' and 'post'
        ignore (str): Predicate indicating which files to ignore
        follow_nonexisting (bool): Whether to descend into directories in
            ``src`` that do not exit in ``dest``. Default is True
        follow_links (bool): Whether to descend into symlinks in ``src``
    """
    follow_nonexisting = kwargs.get('follow_nonexisting', True)
    follow_links = kwargs.get('follow_link', False)

    # Yield in pre or post order?
    order = kwargs.get('order', 'pre')
    if order not in ('pre', 'post'):
        raise ValueError("Order must be 'pre' or 'post'.")

    # List of relative paths to ignore under the src root.
    ignore = kwargs.get('ignore', lambda filename: False)

    # Don't descend into ignored directories
    if ignore(rel_path):
        return

    source_path = os.path.join(source_root, rel_path)
    dest_path = os.path.join(dest_root, rel_path)

    # preorder yields directories before children
    if order == 'pre':
        yield (source_path, dest_path)

    for f in os.listdir(source_path):
        source_child = os.path.join(source_path, f)
        dest_child = os.path.join(dest_path, f)
        rel_child = os.path.join(rel_path, f)

        # Treat as a directory
        if os.path.isdir(source_child) and (
                follow_links or not os.path.islink(source_child)):

            # When follow_nonexisting isn't set, don't descend into dirs
            # in source that do not exist in dest
            if follow_nonexisting or os.path.exists(dest_child):
                tuples = traverse_tree(
                    source_root, dest_root, rel_child, **kwargs)
                for t in tuples:
                    yield t

        # Treat as a file.
        elif not ignore(os.path.join(rel_path, f)):
            yield (source_child, dest_child)

    if order == 'post':
        yield (source_path, dest_path)


class LinkTree(object):
    """Class to create trees of symbolic links from a source directory.

    LinkTree objects are constructed with a source root.  Their
    methods allow you to create and delete trees of symbolic links
    back to the source tree in specific destination directories.
    Trees comprise symlinks only to files; directries are never
    symlinked to, to prevent the source directory from ever being
    modified.

    """

    def __init__(self, source_root, maxdepth=1000):
        if not os.path.exists(source_root):
            raise IOError("No such file or directory: '%s'", source_root)

        self._root = source_root
        self._maxdepth=maxdepth
        self._linklist=[]

    def find_conflict(self, dest_root, **kwargs):
        """Returns the first file in dest that conflicts with src"""
        kwargs['follow_nonexisting'] = False
        for src, dest in traverse_tree(self._root, dest_root, **kwargs):
            if os.path.isdir(src):
                if os.path.exists(dest) and not os.path.isdir(dest):
                    return dest
            elif os.path.exists(dest):
                return dest
        return None

    def toodepth(self,path):
        listpath = os.path.normpath(path).lstrip(os.path.sep).split(os.path.sep)
        #print("aaaaaaa:",listpath,listpath.__len__())
        r = (self._maxdepth < listpath.__len__())
        if r  : self._linklist.append(path)
        self._link= (self._maxdepth == listpath.__len__())
        return (r)

    def merge(self, dest_root, link=os.symlink, **kwargs):
        """Link all files in src into dest, creating directories
           if necessary.
           If ignore_conflicts is True, do not break when the target exists but
           rather return a list of files that could not be linked.
           Note that files blocking directories will still cause an error.
        """
        kwargs['order'] = 'pre'
        kwargs['ignore'] = self.toodepth
        ignore_conflicts = kwargs.get("ignore_conflicts", False)
        existing = []
        for src, dest in traverse_tree(self._root, dest_root, **kwargs):
            if os.path.isdir(src):
                if not os.path.exists(dest):
                    if self._link:
                        print("link:",src)
                        link(src, dest)
                    else:
                        mkdirp(dest)
                    continue

                if not os.path.isdir(dest):
                    raise ValueError("File blocks directory: %s" % dest)

                # mark empty directories so they aren't removed on unmerge.
                #no_unmerge#if not os.listdir(dest):
                    #no_unmerge#    marker = os.path.join(dest, empty_file_name)
                    #no_unmerge#    touch(marker)

            else:
                if os.path.exists(dest):
                    if ignore_conflicts:
                        existing.append(src)
                    else:
                        raise AssertionError("File already exists: %s" % dest)
                else:
                    link(src, dest)
        if ignore_conflicts:
            return existing


#################
if __name__ == '__main__':
    print("__file__:" + os.path.realpath(__file__))
    root=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),'cache')
    print("root:" + root)
    l = LinkTree(root,maxdepth=2)
    l.merge('/tmp/cache')

