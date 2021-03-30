from __future__ import absolute_importfrom Shadow import __version__from Shadow import *
def load_ipython_extension(ip):
    from Build.IpythonMagic import CythonMagics
    ip.register_magics(CythonMagics)
