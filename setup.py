# coding: utf-8
import os, re
from setuptools import setup, find_packages, find_namespace_packages

with open(os.path.join("mmgui", "__init__.py"), encoding="utf8") as f:
  version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
  name='mmgui',
  version=version,
  python_requires='>=3.6',
  description='mmgui',
  url='http://gitlab.testplus.cn/sandin/mmgui',
  author='lds2012',
  author_email='lds2012@gmail.com',
  license='GPLv3',
  include_package_data=True, # 代码以外的文件也包含进来, 这些文件可以通过 __file__ 加相对路径找到
  packages=find_namespace_packages(include=['mmgui.*', "mmgui"]),
  install_requires='''
PyQt5==5.12
PyQt5-sip==4.19.19
PyQtWebEngine==5.12
'''.split('\n'),
  zip_safe=False)
