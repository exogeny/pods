from setuptools import find_namespace_packages
from setuptools import setup


def _parse_requirements(requirements_txt_path):
  with open(requirements_txt_path) as fp:
    return fp.read().splitlines()


_VERSION = '0.0.1'


setup(
  name='proteomics_datasets',
  version=_VERSION,
  author='Terence Wang',
  author_email='wangteng18@mails.ucas.ac.cn',
  description='Proteomics datasets for tensorflow datasets',
  long_description=open('README.md').read(),
  long_description_content_type='text/markdown',
  url='https://github.com/exogeny/pods',
  license='MIT',
  packages=find_namespace_packages(),
  install_requires=_parse_requirements('requirements.txt'),
  python_requires='>=3.9',
  include_package_data=True,
  zip_safe=False,
  classifiers=[
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python',
    'Topic :: Scientific/Engineering',
    'Topic :: Scientific/Engineering :: Artificial Intelligence',
    'Topic :: Software Development :: Libraries',
    'Topic :: Software Development :: Libraries :: Python Modules',
  ]
