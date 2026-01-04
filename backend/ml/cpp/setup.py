"""
Setup script for Eaglearn ML C++ Extension
Build with: pip install -e .
"""

from setuptools import setup, Extension
import sys
import os
import pybind11

# Get OpenCV pkg-config or use default
try:
    import pkgconfig
    if pkgconfig.exists('opencv4'):
        opencv_libs = pkgconfig.parse('opencv4')
        include_dirs = opencv_libs['include_dirs']
        library_dirs = opencv_libs['library_dirs']
        libraries = opencv_libs['libraries']
    else:
        raise pkgconfig.PackageNotFoundError
except:
    # Default OpenCV include/lib paths
    include_dirs = ['/usr/local/include/opencv4', '/usr/include/opencv4', 'C:\\opencv\\build\\include']
    library_dirs = ['/usr/local/lib', '/usr/lib', 'C:\\opencv\\build\\x64\\vc16\\lib']
    libraries = ['opencv_core', 'opencv_imgproc', 'opencv_calib3d']

# Find OpenSSL
try:
    import pkgconfig
    if pkgconfig.exists('openssl'):
        openssl = pkgconfig.parse('openssl')
        include_dirs.extend(openssl['include_dirs'])
        library_dirs.extend(openssl['library_dirs'])
        libraries.extend(openssl['libraries'])
except:
    pass

# Python include directories
python_include = sys.prefix + '/include/python' + str(sys.version_info.major) + str(sys.version_info.minor)

# Extension definition
extra_compile_args = ['/O2', '/std:c++17'] if os.name == 'nt' else ['-O3', '-march=native', '-std=c++17']

eaglearn_ml_extension = Extension(
    'eaglearn_ml',
    sources=['eaglearn_ml.cpp'],
    include_dirs=[
        python_include,
        '.',
        '/usr/local/include',
        '/usr/include',
        pybind11.get_include(),
        pybind11.get_include(user=True),
    ] + include_dirs,
    library_dirs=library_dirs,
    libraries=libraries + ['ssl', 'crypto'],
    extra_compile_args=extra_compile_args,
    extra_link_args=[],
)

setup(
    name='eaglearn_ml',
    version='1.0.0',
    description='Eaglearn ML C++ Extension - High performance ML components',
    author='Eaglearn Team',
    ext_modules=[eaglearn_ml_extension],
    python_requires='>=3.8',
    install_requires=[
        'pybind11>=2.10.0',
        'numpy>=1.20.0',
    ],
)
