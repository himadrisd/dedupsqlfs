#!/usr/bin/env python

import sys

from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from distutils import ccompiler


VERSION = (1, 3, 4)
VERSION_STR = ".".join([str(x) for x in VERSION])

# Minor versions
PKG_VERSION = VERSION
PKG_VERSION_STR = ".".join([str(x) for x in PKG_VERSION])

###
# Ugly hacks, I know
#

SUP_LEGACY=0
if "--legacy" in sys.argv:
    # Support legacy output format functions
    SUP_LEGACY=1
    sys.argv.remove("--legacy")

SUP_PYZSTD_LEGACY=0
if "--pyzstd-legacy" in sys.argv:
    # Support ZSTD legacy format
    SUP_PYZSTD_LEGACY=1
    sys.argv.remove("--pyzstd-legacy")

SUP_EXTERNAL=0
ext_libraries=[]
if "--external" in sys.argv:
    # You want use external Zstd library?
    SUP_EXTERNAL=1
    sys.argv.remove("--external")
    # You should add external library by option: --libraries zstd
    # And probably include paths by option: --include-dirs /usr/include/zstd
    # And probably library paths by option: --library-dirs /usr/lib/i386-linux-gnu
    if "--libraries" not in sys.argv:
        # Add something default
        ext_libraries=["zstd"]


EXTRA_OPT=0
if "--extra-optimization" in sys.argv:
    # Support legacy output format functions
    EXTRA_OPT=1
    sys.argv.remove("--extra-optimization")

if ccompiler.get_default_compiler() == "msvc":
    extra_compile_args = ["/Wall"]
    if EXTRA_OPT:
        extra_compile_args.insert(0, "/O2")
    else:
        extra_compile_args.insert(0, "/Ot")
else:
    extra_compile_args = ["-std=c99", "-Wall", "-DFORTIFY_SOURCE=2", "-fstack-protector"]
    if EXTRA_OPT:
        extra_compile_args.insert(0, "-march=native")
        extra_compile_args.insert(0, "-O3")
    else:
        extra_compile_args.insert(0, "-O2")


if not SUP_EXTERNAL:
    if ccompiler.get_default_compiler() == "msvc":
        extra_compile_args.extend([
            '/Izstd\\lib', '/Izstd\\lib\\common', '/Izstd\\lib\\compress', '/Izstd\\lib\\decompress',
            '/DVERSION=\"\\\"%s\\\"\"' % VERSION_STR,
        ])
    else:
        extra_compile_args.extend([
            '-Izstd/lib', '-Izstd/lib/common', '-Izstd/lib/compress', '-Izstd/lib/decompress',
            '-DVERSION="%s"' % VERSION_STR,
        ])

if SUP_LEGACY:
    if ccompiler.get_default_compiler() == "msvc":
        extra_compile_args.extend(['/Izstd\\lib\\legacy', '/DZSTD_LEGACY_SUPPORT=1'])
    else:
        extra_compile_args.extend(['-Izstd/lib/legacy', '-DZSTD_LEGACY_SUPPORT=1'])

if SUP_PYZSTD_LEGACY:
    if ccompiler.get_default_compiler() == "msvc":
        extra_compile_args.extend(['/DPYZSTD_LEGACY=1'])
    else:
        extra_compile_args.extend(['-DPYZSTD_LEGACY=1'])


class ZstdBuildExt( build_ext ):

    def build_extensions(self):
        for e in self.extensions:
            e.extra_compile_args = extra_compile_args
        build_ext.build_extensions(self)

zstdFiles = []

if not SUP_EXTERNAL:

    for f in [
            'compress/zstd_compress.c', 'compress/zstdmt_compress.c',
            'compress/zstd_fast.c', 'compress/zstd_double_fast.c', 'compress/zstd_lazy.c', 'compress/zstd_opt.c', 'compress/zstd_ldm.c',
            'compress/fse_compress.c', 'compress/huf_compress.c',

            'decompress/zstd_decompress.c', 'common/fse_decompress.c', 'decompress/huf_decompress.c',

            'common/entropy_common.c', 'common/zstd_common.c', 'common/xxhash.c', 'common/error_private.c', 'common/pool.c',
        ]:
        zstdFiles.append('zstd/lib/'+f)

    if SUP_LEGACY:
        for f in [
            'legacy/zstd_v01.c', 'legacy/zstd_v02.c', 'legacy/zstd_v03.c', 'legacy/zstd_v04.c', 'legacy/zstd_v05.c', 'legacy/zstd_v06.c', 'legacy/zstd_v07.c'
            ]:
            zstdFiles.append('zstd/lib/'+f)

zstdFiles.append('src/python-zstd.c')

tests="tests"

setup(
    name='zstd',
    version=PKG_VERSION_STR,
    description="ZSTD Bindings for Python",
    long_description=open('README.rst', 'r').read(),
    author='Sergey Dryabzhinsky, Anton Stuk',
    author_email='sergey.dryabzhinsky@gmail.com',
    maintainer='Sergey Dryabzhinsky',
    maintainer_email='sergey.dryabzhinsky@gmail.com',
    url='https://github.com/sergey-dryabzhinsky/python-zstd',
    keywords='zstd, zstandard, compression',
    license='BSD',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    ext_modules=[
        Extension('_zstd', zstdFiles, libraries=ext_libraries)
    ],
    cmdclass = {'build_ext': ZstdBuildExt },
    test_suite=tests,
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6'
    ]
)
