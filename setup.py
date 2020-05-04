from setuptools import setup, find_packages
import django_wfe


def read_file(path: str):
    with open(path, 'r') as file:
        return file.read()


setup_requires = [
    "wheel",
]

setup(
    name='django-wfe',
    version=django_wfe.__version__,
    url=django_wfe.__url__,
    description=django_wfe.__doc__,
    long_description=read_file('README.rst'),
    author=django_wfe.__author__,
    author_email=django_wfe.__email__,
    license=django_wfe.__license__,
    platforms='any',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_file('requirements.txt').splitlines(),
)
