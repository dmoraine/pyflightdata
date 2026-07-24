pyflightdata2
=============

[![CI](https://github.com/dmoraine/pyflightdata/actions/workflows/ci.yml/badge.svg)](https://github.com/dmoraine/pyflightdata/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pyflightdata2.svg?maxAge=2592000)](https://pypi.org/project/pyflightdata2/)
[![PyPI](https://img.shields.io/pypi/pyversions/pyflightdata2.svg?maxAge=2592000)](https://pypi.org/project/pyflightdata2/)

A simple library to get flight data from flightradar24 from within Python code.

This is a community-maintained continuation of [supercoderz/pyflightdata](https://github.com/supercoderz/pyflightdata),
which has been inactive since 2021. It fixes the Cloudflare 403 errors that broke the
original package (login and data requests were being blocked) and keeps the project
alive with modern packaging and CI. If the original project resumes active maintenance,
please prefer contributing there.

Install
-------

```
pip install pyflightdata2
```

The import name is unchanged, so existing code keeps working:

```python
from pyflightdata import FlightData
```

Licence
-------

The code for pyflightdata is licenced under MIT licence, see [LICENCE.txt](LICENCE.txt).

We dont own or store any underlying data, the API simply invokes the providers interfaces and returns the data.

Reporting issues
----------------

Please raise an issue at https://github.com/dmoraine/pyflightdata/issues if you see a data or code issue.
Pull requests are welcome.

Tools using pyflightdata
------------------------

pyflighdtata was started as a small hobby library, but it has found other users who have built interesting apps of their own.
Here is a list of the apps that we know of, if you have any other apps that you want to be listed here then please get in touch with us.

1. IATA arrivals cli - this is a neat and useful script to get the details of an airport in your command line - https://github.com/E3V3A/iata-arrivals-cli
