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

"""Authenticated online tests against the live flightradar24 site.

These require real credentials (see ``conftest.load_credentials``) and are
skipped automatically when none are configured, so they never break CI. The
premise, per the flightradar24 plans, is that anonymous and paid access differ
mainly in how far back the history goes: a logged-in client should therefore see
*at least* as much history as an anonymous one within the same page budget.
"""

import time

import pytest
from flaky import flaky

from .flightdata import FlightData


def delay_rerun(*args):
    time.sleep(5)
    return True


def _history_depth(client, tail, max_pages=3):
    """Count history rows for ``tail`` across up to ``max_pages`` pages.

    ``FlightData._fr24`` holds pagination state and is shared across every
    ``FlightData`` instance, so callers must never interleave two clients'
    paged reads. We reset that shared state before and after each pass.
    """
    client.clear_last_request()
    total = 0
    for page in range(1, max_pages + 1):
        rows = client.get_history_by_tail_number(tail, page=page)
        total += len(rows)
        if not rows:
            break
        time.sleep(2)
    client.clear_last_request()
    return total


@pytest.mark.online
@pytest.mark.auth
@flaky(max_runs=3, rerun_filter=delay_rerun)
class TestAuthenticatedAccess(object):

    # A busy long-haul aircraft, so there is plenty of history to page through.
    TAIL = '9V-SMC'

    def teardown(self):
        time.sleep(3)

    def test_login_then_logout(self, credentials):
        email, password = credentials
        f = FlightData()
        assert f.is_authenticated() is False
        assert f.login(email, password) is True
        assert f.is_authenticated() is True
        f.logout()
        assert f.is_authenticated() is False

    def test_login_via_constructor(self, credentials):
        email, password = credentials
        f = FlightData(email, password)
        assert f.is_authenticated() is True

    def test_authenticated_returns_history(self, credentials):
        email, password = credentials
        f = FlightData(email, password)
        assert _history_depth(f, self.TAIL) > 0

    def test_authenticated_history_at_least_anonymous(self, credentials):
        email, password = credentials
        # Sequential, never interleaved, because _fr24 pagination state is shared.
        anon_depth = _history_depth(FlightData(), self.TAIL)
        auth_depth = _history_depth(FlightData(email, password), self.TAIL)
        assert auth_depth > 0
        # Paid history reaches at least as far back as anonymous within the same
        # page budget; the only advertised difference between the tiers is depth.
        assert auth_depth >= anon_depth
