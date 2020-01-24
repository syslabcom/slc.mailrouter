from setuptools import setup, find_packages

version = "3.0.0"

setup(
    name="slc.mailrouter",
    version=version,
    description="Framework for handling email in zope",
    long_description=open("README.md").read(),
    # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        "Framework :: Plone",
        "Framework :: Plone :: 5.2",
    ],
    keywords="smtp2zope email mailin zope",
    author="Syslab.com GmbH",
    author_email="info@syslab.com",
    url="https://github.com/syslabcom/slc.mailrouter",
    license="GPL",
    packages=find_packages("src", exclude=["ez_setup"]),
    package_dir={"": "src"},
    namespace_packages=["slc"],
    include_package_data=True,
    package_data={"slc.mailrouter": ["sql/*"]},
    zip_safe=False,
    extras_require={"test": ["mock", "plone.app.testing"]},
    install_requires=["setuptools", "plone.api", "Products.CMFPlone>=5.0"],
    entry_points="""
        [z3c.autoinclude.plugin]
        target = plone
    """,
    setup_requires=[],
    paster_plugins=[],
)
