"""==============================
Branded IPython Notebook Launcher
=================================

Executing this module will create an overlay over ipython notebooks own static
files and templates and overrides static files and templates and copies over all
example notebooks into a temporary folder and launches the ipython notebook server.

You can use this to offer an interactive tutorial for your library/framework/...


License
-------

Copyright (c) 2011, Timo Paulssen
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * The name of the author may not be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL TIMO PAULSSEN BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


Revision History
----------------

   1.0 2011-12-10
        First release.
"""

import os
import shutil
import tempfile
from itertools import izip

try:
    from IPython.frontend.html.notebook import notebookapp
except ImportError:
    print "You don't seem to have IPython installed, or the dependencies of "
    print "ipython notebook are not met."

    raise

BASE_PATH = os.path.dirname(__file__)
TEMPLATE_PATH = os.path.join(BASE_PATH, "templates")
STATIC_PATH = os.path.join(BASE_PATH, "static")
EXAMPLES_PATH = os.path.join(BASE_PATH, "notebooks")

NOTEBOOK_BASE_PATH = os.path.dirname(notebookapp.__file__)
NOTEBOOK_TEMPLATE_PATH = os.path.join(NOTEBOOK_BASE_PATH, "templates")
NOTEBOOK_STATIC_PATH = os.path.join(NOTEBOOK_BASE_PATH, "static")

def create_overlay():
    """This method copies all files from the source to the target and then
    links all missing files from IPython itself to the target.

    Templates that are overrided will be linked to orig_{filename}, so that
    changes to templates can just use tornadowebs own template extension scheme."""

    def merge_dirs(base, overlay, target, preserve_originals=False):
        def replace_prefix(prefix, path, new_prefix):
            assert path.startswith(prefix)
            if path.startswith("/"):
                path = path[1:]
            return os.path.join(new_prefix, path[len(prefix):])

        base_w = os.walk(base, followlinks=True)
        overlay_w = os.walk(overlay, followlinks=True)

        from_base_dirs = []
        from_over_dirs = []
        from_base_files = []
        from_over_files = []
        preserved_originals = []

        # walk the base and overlay trees in parallel
        for (base_t, over_t) in izip(base_w, overlay_w):
            (base_path, base_dirs, base_files) = base_t
            (over_path, over_dirs, over_files) = over_t

            # don't recurse into dirs that are only in base or only in overlay.
            # instead, just symlink them.
            # this keeps both walkers in sync.
            for subdir in set(base_dirs[:] + over_dirs[:]):
                if subdir not in over_dirs:
                    base_dirs.remove(subdir)
                    from_base_dirs.append(os.path.join(base_path, subdir))
                elif subdir not in base_dirs:
                    over_dirs.remove(subdir)
                    from_over_dirs.append(os.path.join(base_path, subdir))

            for fn in set(base_files[:] + over_files[:]):
                if fn in over_files and fn in base_files and preserve_originals:
                    preserved_originals.append(os.path.join(base_path, fn))
                if fn not in over_files:
                    from_base_files.append(os.path.join(base_path, fn))
                else:
                    from_over_files.append(os.path.join(over_path, fn))

        # link full directories over
        for source, dirlist in ((base, from_base_dirs), (overlay, from_over_dirs)):
            for dir_link in dirlist:
                os.symlink(dir_link, replace_prefix(source, dir_link, target))

        # link files over.
        for source, filelist in ((base, from_base_files),
                                 (overlay, from_over_files),
                                 (base, preserved_originals)):
            for file_link in filelist:
                target_file = replace_prefix(source, file_link, target)

                # preserved originals get an original_ prefix
                if filelist is preserved_originals:
                    tfp, tfn = os.path.dirname(target_file), os.path.basename(target_file)
                    target_file = os.path.join(tfp, "original_" + tfn)

                parent_dir = os.path.dirname(target_file)
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                os.symlink(file_link, target_file)


    # create the temporary folder where overlay and base are merged
    path = tempfile.mkdtemp(prefix="zasim_tutorial")

    template_path = os.path.join(path, "templates")
    static_path = os.path.join(path, "static")
    os.mkdir(template_path)
    os.mkdir(static_path)

    merge_dirs(NOTEBOOK_TEMPLATE_PATH, TEMPLATE_PATH, template_path, True)
    merge_dirs(NOTEBOOK_STATIC_PATH, STATIC_PATH, static_path)

    return path, {'template_path': template_path, 'static_path': static_path}

def copy_example_notebooks(target_path):
    shutil.copytree(EXAMPLES_PATH, target_path)

def launch_notebook_server():
    base_path, settings = create_overlay()
    copy_example_notebooks(base_path)
    print "running notebook overlay from", base_path
    os.system('''ipython notebook '''
              '''--NotebookApp.webapp_settings="%s" '''
              '''--notebook_dir="%s"''' % (
                    settings, os.path.join(base_path, "notebooks")))
    shutil.rmtree(base_path)

if __name__ == "__main__":
    launch_notebook_server()

