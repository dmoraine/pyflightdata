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

"""Offline unit tests.

Unlike the other ``test_*`` modules in this package, nothing here touches the
network. Every test exercises pure parsing/filtering/state logic, so the suite
runs deterministically in CI where flightradar24 is unreachable (Cloudflare
blocks GitHub-hosted runners). Anything that would make an HTTP request is
either fed canned input or monkeypatched.
"""

import time
from datetime import datetime

from bs4 import BeautifulSoup

from . import conftest
from .common import ProcessorMixin
from .common_fr24 import FR24
from .flightdata import FlightData
from .json_helper import fltr
from .utils import nowtimestamp_millis, totimestamp


# ---------------------------------------------------------------------------
# json_helper.fltr
# ---------------------------------------------------------------------------

class TestFltr(object):

    def test_removes_top_level_and_nested_keys(self):
        node = {'id': 1, 'name': 'AI101', 'nested': {'hex': 'abc', 'keep': 'v'}}
        out = fltr(node, ['id', 'hex'])
        assert 'id' not in out
        assert out['name'] == 'AI101'
        assert 'hex' not in out['nested']
        assert out['nested']['keep'] == 'v'

    def test_non_string_scalars_are_preserved(self):
        out = fltr({'count': 3, 'ratio': 1.5}, [])
        assert out['count'] == 3
        assert out['ratio'] == 1.5

    def test_bool_is_kept_as_bool(self):
        # isinstance(True, int) is True in Python, so bools take the int branch
        # and are returned unchanged rather than stringified.
        assert fltr({'flag': True}, [])['flag'] is True

    def test_timestamp_keys_are_expanded(self):
        out = fltr({'updated': 1609459200}, [])
        assert out['updated'] == 1609459200
        assert out['updated_millis'] == 1609459200 * 1000
        # date/time strings are local-tz dependent; assert shape not value
        assert len(out['updated_date']) == 8 and out['updated_date'].isdigit()
        assert len(out['updated_time']) == 4 and out['updated_time'].isdigit()

    def test_non_timestamp_int_is_not_expanded(self):
        out = fltr({'seats': 180}, [])
        assert out['seats'] == 180
        assert 'seats_millis' not in out

    def test_empty_dict_returns_none(self):
        assert fltr({}, []) is None

    def test_dict_reduced_to_empty_returns_none(self):
        assert fltr({'id': 1}, ['id']) is None

    def test_empty_list_returns_none(self):
        assert fltr([], []) is None

    def test_list_drops_entries_that_reduce_to_empty(self):
        out = fltr([{'id': 1}, {'name': 'x'}], ['id'])
        assert out == [{'name': 'x'}]


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------

class TestUtils(object):

    def test_totimestamp_epoch_is_zero(self):
        assert totimestamp(datetime(1970, 1, 1)) == 0

    def test_totimestamp_known_value(self):
        # 2021-01-01T00:00:00 == 1609459200 seconds since the epoch
        assert totimestamp(datetime(2021, 1, 1)) == 1609459200

    def test_nowtimestamp_is_int_seconds(self):
        v = nowtimestamp_millis()
        assert isinstance(v, int)
        # within a few seconds of the real epoch-seconds clock
        assert abs(v - int(time.time())) < 5


# ---------------------------------------------------------------------------
# common.ProcessorMixin
# ---------------------------------------------------------------------------

class TestProcessorMixin(object):

    p = ProcessorMixin()

    def test_json_loads_byteified_from_bytes(self):
        out = self.p.json_loads_byteified(b'{"a": "b", "n": 1}')
        assert out['a'] == 'b'
        assert out['n'] == 1

    def test_json_loads_byteified_from_str(self):
        out = self.p.json_loads_byteified('{"nested": {"k": "v"}}')
        assert out['nested']['k'] == 'v'

    def test_encode_and_get_plain_string(self):
        assert self.p.encode_and_get('hello') == 'hello'

    def test_encode_and_get_replaces_nbsp_with_space(self):
        # a non-breaking space (\xa0) should come back as a regular space
        assert self.p.encode_and_get('a\xa0b') == 'a b'

    def test_get_soup_or_none_on_bad_input(self):
        # BeautifulSoup happily parses None-ish content only when given bytes/str;
        # None triggers the guarded except and yields None
        assert self.p.get_soup_or_none(None) is None


# ---------------------------------------------------------------------------
# common_fr24.FR24 - pure logic, no network
# ---------------------------------------------------------------------------

def _rows_from_html(html):
    return BeautifulSoup(html, 'html5lib').find_all('tr')


class TestFR24State(object):

    def test_check_last_key_resets_timestamp_on_new_key(self):
        fr = FR24()
        fr.timestamp = '999'
        fr.last_key = 'AI101'
        fr.check_last_key('AI202')
        assert fr.timestamp == ''
        assert fr.last_key == 'AI202'

    def test_check_last_key_keeps_timestamp_for_same_key(self):
        fr = FR24()
        fr.timestamp = '999'
        fr.last_key = 'AI101'
        fr.check_last_key('AI101')
        assert fr.timestamp == '999'

    def test_filter_and_get_data_handles_empty(self):
        fr = FR24()
        assert fr.filter_and_get_data(None) == []
        assert fr.filter_and_get_data([]) == []

    def test_filter_and_get_data_filters_noise_keys(self):
        fr = FR24()
        out = fr.filter_and_get_data([{'id': 1, 'callsign': 'SIA', 'logo': 'x'}])
        assert 'id' not in out
        assert 'logo' not in out
        assert out['callsign'] == 'SIA'

    def test_process_raw_flight_data_captures_last_timestamp(self):
        fr = FR24()
        data = [
            {'time': {'other': {'updated': 111}}},
            {'time': {'other': {'updated': 222}}},
        ]
        result = fr.process_raw_flight_data(data)
        assert result is data
        assert fr.timestamp == 222

    def test_process_raw_flight_data_empty_clears_timestamp(self):
        fr = FR24()
        fr.timestamp = 'stale'
        fr.process_raw_flight_data([])
        assert fr.timestamp == ''


class TestFR24FleetParsing(object):

    FLEET_HTML = (
        '<table><tbody>'
        '<tr><td><a>9V-ABC</a></td><td>A359</td><td>1234</td><td>5.6</td></tr>'
        '</tbody></table>'
    )

    def test_unauthenticated_masks_msn_and_age(self):
        fr = FR24()
        out = fr.process_raw_airline_fleet_data(_rows_from_html(self.FLEET_HTML), False)
        assert out[0]['reg'] == '9V-ABC'
        assert out[0]['type'] == 'A359'
        assert out[0]['msn'] == 'requires user login'
        assert out[0]['age'] == 'requires user login'

    def test_authenticated_exposes_msn_and_age(self):
        fr = FR24()
        out = fr.process_raw_airline_fleet_data(_rows_from_html(self.FLEET_HTML), True)
        assert out[0]['msn'] == '1234'
        assert out[0]['age'] == '5.6'

    def test_row_without_anchor_is_skipped(self):
        fr = FR24()
        html = '<table><tbody><tr><td>x</td><td>y</td></tr></tbody></table>'
        out = fr.process_raw_airline_fleet_data(_rows_from_html(html), False)
        assert out == []

    def test_short_row_is_skipped(self):
        fr = FR24()
        html = '<table><tbody><tr><td>only-one-cell</td></tr></tbody></table>'
        out = fr.process_raw_airline_fleet_data(_rows_from_html(html), False)
        assert out == []

    def test_authenticated_short_row_falls_back_to_masked(self):
        # authenticated but the site only returned reg + type columns
        fr = FR24()
        html = '<table><tbody><tr><td><a>9V-XYZ</a></td><td>B789</td></tr></tbody></table>'
        out = fr.process_raw_airline_fleet_data(_rows_from_html(html), True)
        assert out[0]['reg'] == '9V-XYZ'
        assert out[0]['msn'] == 'requires user login'


# ---------------------------------------------------------------------------
# flightdata.FlightData - offline behaviour and monkeypatched I/O
# ---------------------------------------------------------------------------

class TestFlightDataState(object):

    def test_logout_resets_authentication(self):
        f = FlightData()
        f.AUTH_TOKEN = 'tok'
        assert f.is_authenticated() is True
        f.logout()
        assert f.is_authenticated() is False

    def test_fresh_instance_is_not_authenticated(self):
        assert FlightData().is_authenticated() is False

    def test_clear_last_request_resets_fr24_state(self):
        f = FlightData()
        f._fr24.timestamp = 'x'
        f._fr24.last_key = 'y'
        f.clear_last_request()
        assert f._fr24.timestamp == ''
        assert f._fr24.last_key == ''


class TestGetFlightForDate(object):

    def test_keeps_only_flights_matching_the_date(self, monkeypatch):
        f = FlightData()
        match = {'time': {'scheduled': {'arrival_date': '20210101'}}}
        nomatch = {'time': {'scheduled': {'arrival_date': '20991231'}}}
        monkeypatch.setattr(f, 'get_history_by_flight_number',
                            lambda flight_number: [match, nomatch])
        assert f.get_flight_for_date('AI101', '20210101') == [match]

    def test_matches_on_departure_date_too(self, monkeypatch):
        f = FlightData()
        dep = {'time': {'scheduled': {'departure_date': '20210101'}}}
        monkeypatch.setattr(f, 'get_history_by_flight_number',
                            lambda flight_number: [dep])
        assert f.get_flight_for_date('AI101', '20210101') == [dep]

    def test_returns_empty_when_nothing_matches(self, monkeypatch):
        f = FlightData()
        monkeypatch.setattr(f, 'get_history_by_flight_number',
                            lambda flight_number: [
                                {'time': {'scheduled': {'arrival_date': '19990101'}}}])
        assert f.get_flight_for_date('AI101', '20210101') == []


class TestGetAirportWeather(object):

    def test_adds_km_when_visibility_present(self, monkeypatch):
        f = FlightData()
        weather = {'sky': {'visibility': {'mi': '10'}}}
        monkeypatch.setattr(f._fr24, 'get_airport_weather', lambda url: weather)
        out = f.get_airport_weather('SIN')
        assert out['sky']['visibility']['km'] == 10 * 1.6094

    def test_no_km_when_visibility_is_none(self, monkeypatch):
        f = FlightData()
        weather = {'sky': {'visibility': {'mi': 'None'}}}
        monkeypatch.setattr(f._fr24, 'get_airport_weather', lambda url: weather)
        out = f.get_airport_weather('SIN')
        assert 'km' not in out['sky']['visibility']

    def test_missing_weather_structure_is_swallowed(self, monkeypatch):
        f = FlightData()
        monkeypatch.setattr(f._fr24, 'get_airport_weather', lambda url: [])
        # should not raise even though [] has no 'sky' key
        assert f.get_airport_weather('SIN') == []


class TestLogin(object):

    class _Resp(object):
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content

    def test_successful_login_sets_token(self, monkeypatch):
        f = FlightData()
        payload = b'{"userData": {"subscriptionKey": "secret-token"}}'
        monkeypatch.setattr(FlightData.session, 'post',
                            lambda **kw: self._Resp(200, payload))
        assert f.login('a@b.com', 'pw') is True
        assert f.AUTH_TOKEN == 'secret-token'
        f.logout()

    def test_non_200_returns_false(self, monkeypatch):
        f = FlightData()
        monkeypatch.setattr(FlightData.session, 'post',
                            lambda **kw: self._Resp(403, b''))
        assert f.login('a@b.com', 'pw') is False
        assert f.is_authenticated() is False

    def test_unexpected_shape_returns_false(self, monkeypatch):
        f = FlightData()
        monkeypatch.setattr(FlightData.session, 'post',
                            lambda **kw: self._Resp(200, b'{"unexpected": true}'))
        assert f.login('a@b.com', 'pw') is False
        assert f.is_authenticated() is False

    def test_network_error_returns_false(self, monkeypatch):
        f = FlightData()

        def _boom(**kw):
            raise ConnectionError('down')

        monkeypatch.setattr(FlightData.session, 'post', _boom)
        assert f.login('a@b.com', 'pw') is False


# ---------------------------------------------------------------------------
# conftest credential loader (offline)
# ---------------------------------------------------------------------------

class TestCredentialLoader(object):

    def test_env_vars_take_precedence(self, monkeypatch):
        monkeypatch.setenv('FR24_EMAIL', 'env@x.com')
        monkeypatch.setenv('FR24_PASSWORD', 'env-pw')
        assert conftest.load_credentials() == ('env@x.com', 'env-pw')

    def test_reads_key_value_env_file(self, tmp_path):
        env = tmp_path / '.env'
        env.write_text('email=a@b.com\npassword="secret"\n# a comment\n\n')
        values = conftest._read_env_file(str(env))
        assert values['email'] == 'a@b.com'
        assert values['password'] == 'secret'

    def test_missing_env_file_yields_empty(self, tmp_path):
        assert conftest._read_env_file(str(tmp_path / 'absent.env')) == {}
