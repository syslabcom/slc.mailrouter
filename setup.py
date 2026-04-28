from setuptools import setup

version = "4.0.0a1"

setup(
    name="slc.mailrouter",
    version=version,
    description="Framework for handling email in zope",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    # Get more strings from https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Framework :: Plone",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: 6.1",
        "Framework :: Plone :: 6.2",
    ],
    keywords="smtp2zope email mail-in zope",
    author="Syslab.com GmbH",
    author_email="info@syslab.com",
    url="https://github.com/syslabcom/slc.mailrouter",
    license="GPL",
    python_requires=">=3.10",
    include_package_data=True,
    package_data={"slc.mailrouter": ["sql/*"]},
    zip_safe=False,
    extras_require={"test": ["plone.app.testing"]},
    install_requires=["setuptools", "plone.api", "Products.CMFPlone>=5.0"],
    entry_points="""
        [z3c.autoinclude.plugin]
        target = plone
    """,
    setup_requires=[],
    paster_plugins=[],
)
