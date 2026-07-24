# MIT License
#
# Copyright (c) 2020 Hari Allamraju
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Shared pytest fixtures.

The authenticated online tests need real flightradar24 credentials. They are
read, in order of precedence, from:

1. the ``FR24_EMAIL`` / ``FR24_PASSWORD`` environment variables (use these in
   CI secrets), or
2. a local ``.env`` file at the repository root with ``email=`` / ``password=``
   lines (gitignored, handy for local runs).

When no credentials are available the ``credentials`` fixture skips the test, so
the suite stays green on CI runners that have no secret configured.
"""

import os

import pytest


def _read_env_file(path):
    values = {}
    try:
        with open(path) as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                values[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return values


def load_credentials():
    """Return ``(email, password)`` or ``(None, None)`` if not configured."""
    email = os.environ.get('FR24_EMAIL')
    password = os.environ.get('FR24_PASSWORD')
    if email and password:
        return email, password
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    values = _read_env_file(env_path)
    email = email or values.get('FR24_EMAIL') or values.get('email')
    password = password or values.get('FR24_PASSWORD') or values.get('password')
    if email and password:
        return email, password
    return None, None


@pytest.fixture(scope='session')
def credentials():
    email, password = load_credentials()
    if not (email and password):
        pytest.skip(
            'no flightradar24 credentials; set FR24_EMAIL/FR24_PASSWORD or a '
            'local .env with email=/password=')
    return email, password
