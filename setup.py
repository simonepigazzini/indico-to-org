import setuptools

with open('README.org', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='indico2org-simonepigazzini', # Replace with your own username
    version='0.0.1',
    author='Simone Pigazzini',
    author_email='simone.pigazzini@cern.ch',
    description='A simple package to fetch data from CERN indico and convert it into emacs org-mode',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/simonepigazzini/indico-to-org',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
        'Operating System :: Linux',
    ],
    scripts=[
        'bin/indico-to-org.py'
    ],
    python_requires='>=3.6',
)
