#
#
#

from json import loads
from os.path import dirname, join
from unittest import TestCase
from unittest.mock import Mock, call

from requests import HTTPError
from requests_mock import ANY
from requests_mock import mock as requests_mock

from octodns.provider.yaml import YamlProvider
from octodns.record import Record
from octodns.zone import Zone

from octodns_gandi import (
    GandiClientBadRequest,
    GandiClientForbidden,
    GandiClientNotFound,
    GandiClientUnauthorized,
    GandiClientUnknownDomainName,
    GandiProvider,
)


class TestGandiProvider(TestCase):
    expected = Zone('unit.tests.', [])
    source = YamlProvider('test', join(dirname(__file__), 'config'))
    source.populate(expected)

    # We remove this record from the test zone as Gandi API reject it
    # (rightfully).
    expected.remove_record(
        Record.new(
            expected,
            'sub',
            {'ttl': 1800, 'type': 'NS', 'values': ['6.2.3.4.', '7.2.3.4.']},
        )
    )

    def test_populate(self):
        provider = GandiProvider('test_id', 'token', per_page=10)

        # 400 - Bad Request.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=400,
                text='{"status": "error", "errors": [{"location": '
                '"body", "name": "items", "description": '
                '"\'6.2.3.4.\': invalid hostname (param: '
                '{\'rrset_type\': u\'NS\', \'rrset_ttl\': 3600, '
                '\'rrset_name\': u\'sub\', \'rrset_values\': '
                '[u\'6.2.3.4.\', u\'7.2.3.4.\']})"}, {"location": '
                '"body", "name": "items", "description": '
                '"\'7.2.3.4.\': invalid hostname (param: '
                '{\'rrset_type\': u\'NS\', \'rrset_ttl\': 3600, '
                '\'rrset_name\': u\'sub\', \'rrset_values\': '
                '[u\'6.2.3.4.\', u\'7.2.3.4.\']})"}]}',
            )

            with self.assertRaises(GandiClientBadRequest) as ctx:
                zone = Zone('unit.tests.', [])
                provider.populate(zone)
            self.assertIn('"status": "error"', str(ctx.exception))

        # 401 - Unauthorized.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=401,
                text='{"code":401,"message":"The server could not verify '
                'that you authorized to access the document you '
                'requested. Either you supplied the wrong '
                'credentials (e.g., bad api key), or your access '
                'token has expired","object":"HTTPUnauthorized",'
                '"cause":"Unauthorized"}',
            )

            with self.assertRaises(GandiClientUnauthorized) as ctx:
                zone = Zone('unit.tests.', [])
                provider.populate(zone)
            self.assertIn('"cause":"Unauthorized"', str(ctx.exception))

        # 403 - Forbidden.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=403,
                text='{"code":403,"message":"Access was denied to this '
                'resource.","object":"HTTPForbidden","cause":'
                '"Forbidden"}',
            )

            with self.assertRaises(GandiClientForbidden) as ctx:
                zone = Zone('unit.tests.', [])
                provider.populate(zone)
            self.assertIn('"cause":"Forbidden"', str(ctx.exception))

        # 404 - Not Found.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=404,
                text='{"code": 404, "message": "The resource could not '
                'be found.", "object": "HTTPNotFound", "cause": '
                '"Not Found"}',
            )

            with self.assertRaises(GandiClientNotFound) as ctx:
                zone = Zone('unit.tests.', [])
                provider._client.zone(zone)
            self.assertIn('"cause": "Not Found"', str(ctx.exception))

        # General error
        with requests_mock() as mock:
            mock.get(ANY, status_code=502, text='Things caught fire')

            with self.assertRaises(HTTPError) as ctx:
                zone = Zone('unit.tests.', [])
                provider.populate(zone)
            self.assertEqual(502, ctx.exception.response.status_code)

        # No diffs == no changes
        with requests_mock() as mock:
            base = (
                'https://api.gandi.net/v5/livedns/domains/unit.tests' '/records'
            )
            with open('tests/fixtures/gandi-no-changes.json') as fh:
                mock.get(base, text=fh.read())

            zone = Zone('unit.tests.', [])
            provider.populate(zone)
            self.assertEqual(17, len(zone.records))
            changes = self.expected.changes(zone, provider)
            self.assertEqual(0, len(changes))

        del provider._zone_records[zone.name]

        # Default Gandi zone file.
        with requests_mock() as mock:
            with open('tests/fixtures/gandi-records-1.json') as fh:
                text_1 = fh.read()
            with open('tests/fixtures/gandi-records-2.json') as fh:
                text_2 = fh.read()

            total_count = len(loads(text_1)) + len(loads(text_2))
            base = 'https://api.gandi.net/v5/livedns/domains/unit.tests/records'
            mock.get(
                f'{base}?page=1&per_page=10',
                text=text_1,
                headers={'total-count': str(total_count)},
            )
            mock.get(
                f'{base}?page=2&per_page=10',
                text=text_2,
                headers={'total-count': str(total_count)},
            )

            zone = Zone('unit.tests.', [])
            provider.populate(zone)
            self.assertEqual(13, len(zone.records))
            changes = self.expected.changes(zone, provider)
            self.assertEqual(25, len(changes))

        # 2nd populate makes no network calls/all from cache
        again = Zone('unit.tests.', [])
        provider.populate(again)
        self.assertEqual(13, len(again.records))

        # bust the cache
        del provider._zone_records[zone.name]

    def test_apply(self):
        provider = GandiProvider('test_id', 'token', strict_supports=False)

        # Zone does not exists but can be created.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=404,
                text='{"code": 404, "message": "The resource could not '
                'be found.", "object": "HTTPNotFound", "cause": '
                '"Not Found"}',
            )
            mock.post(
                ANY, status_code=201, text='{"message": "Domain Created"}'
            )

            plan = provider.plan(self.expected)
            provider.apply(plan)

        # Zone does not exists and can't be created.
        with requests_mock() as mock:
            mock.get(
                ANY,
                status_code=404,
                text='{"code": 404, "message": "The resource could not '
                'be found.", "object": "HTTPNotFound", "cause": '
                '"Not Found"}',
            )
            mock.post(
                ANY,
                status_code=404,
                text='{"code": 404, "message": "The resource could not '
                'be found.", "object": "HTTPNotFound", "cause": '
                '"Not Found"}',
            )

            with self.assertRaises(
                (GandiClientNotFound, GandiClientUnknownDomainName)
            ) as ctx:
                plan = provider.plan(self.expected)
                provider.apply(plan)
            self.assertIn(
                'This domain is not registered at Gandi.', str(ctx.exception)
            )

        resp = Mock()
        resp.json = Mock()
        resp.headers = {'Total-Count': '500'}
        provider._client._request = Mock(return_value=resp)

        with open('tests/fixtures/gandi-zone.json') as fh:
            zone = fh.read()

        # non-existent domain
        resp.json.side_effect = [
            GandiClientNotFound(resp),  # no zone in populate
            GandiClientNotFound(resp),  # no domain during apply
            zone,
        ]
        plan = provider.plan(self.expected)

        # No ignored, no excluded, no LOC
        n = len(self.expected.records) - 5
        self.assertEqual(n, len(plan.changes))
        self.assertEqual(n, provider.apply(plan))
        self.assertFalse(plan.exists)

        provider._client._request.assert_has_calls(
            [
                call(
                    'GET',
                    '/livedns/domains/unit.tests/records',
                    params={'page': 1, 'per_page': 500},
                ),
                call('GET', '/livedns/domains/unit.tests'),
                call(
                    'POST',
                    '/livedns/domains',
                    data={'fqdn': 'unit.tests', 'zone': {}},
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '@',
                        'rrset_ttl': 300,
                        'rrset_type': 'A',
                        'rrset_values': ['1.2.3.4', '1.2.3.5'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '@',
                        'rrset_ttl': 3600,
                        'rrset_type': 'CAA',
                        'rrset_values': ['0 issue "ca.unit.tests"'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '@',
                        'rrset_ttl': 3600,
                        'rrset_type': 'SSHFP',
                        'rrset_values': [
                            '1 1 7491973e5f8b39d5327cd4e08bc81b05f7710b49',
                            '1 1 bf6b6825d2977c511a475bbefb88aad54a92ac73',
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '_25._tcp.mx1',
                        'rrset_ttl': 3600,
                        'rrset_type': 'TLSA',
                        'rrset_values': [
                            '3 1 1 8a9a70596e869bed72c69d97a8895dfa'
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '_25._tcp.mx2',
                        'rrset_ttl': 3600,
                        'rrset_type': 'TLSA',
                        'rrset_values': [
                            '3 1 1 c164b2c3f36d068d42a6138e446152f568615f28c69bd96a73e354cac88ed00c'
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '_imap._tcp',
                        'rrset_ttl': 600,
                        'rrset_type': 'SRV',
                        'rrset_values': ['0 0 0 .'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '_pop3._tcp',
                        'rrset_ttl': 600,
                        'rrset_type': 'SRV',
                        'rrset_values': ['0 0 0 .'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': '_srv._tcp',
                        'rrset_ttl': 600,
                        'rrset_type': 'SRV',
                        'rrset_values': [
                            '10 20 30 foo-1.unit.tests.',
                            '12 20 30 foo-2.unit.tests.',
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'aaaa',
                        'rrset_ttl': 600,
                        'rrset_type': 'AAAA',
                        'rrset_values': [
                            '2601:644:500:e210:62f8:1dff:feb8:947a'
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'cname',
                        'rrset_ttl': 300,
                        'rrset_type': 'CNAME',
                        'rrset_values': ['unit.tests.'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'dname',
                        'rrset_ttl': 300,
                        'rrset_type': 'DNAME',
                        'rrset_values': ['unit.tests.'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'excluded',
                        'rrset_ttl': 3600,
                        'rrset_type': 'CNAME',
                        'rrset_values': ['unit.tests.'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'mx',
                        'rrset_ttl': 300,
                        'rrset_type': 'MX',
                        'rrset_values': [
                            '10 smtp-4.unit.tests.',
                            '20 smtp-2.unit.tests.',
                            '30 smtp-3.unit.tests.',
                            '40 smtp-1.unit.tests.',
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'ptr',
                        'rrset_ttl': 300,
                        'rrset_type': 'PTR',
                        'rrset_values': ['foo.bar.com.'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'txt',
                        'rrset_ttl': 600,
                        'rrset_type': 'TXT',
                        'rrset_values': [
                            'Bah bah black sheep',
                            'have you any wool.',
                            'v=DKIM1;k=rsa;s=email;h=sha256;p=A/kinda+of/long/string'
                            '+with+numb3rs',
                        ],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'www',
                        'rrset_ttl': 300,
                        'rrset_type': 'A',
                        'rrset_values': ['2.2.3.6'],
                    },
                ),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'www.sub',
                        'rrset_ttl': 300,
                        'rrset_type': 'A',
                        'rrset_values': ['2.2.3.6'],
                    },
                ),
            ]
        )
        # expected number of total calls
        self.assertEqual(20, provider._client._request.call_count)

        provider._client._request.reset_mock()

        # delete 1 and update 1
        provider._client.zone_records = Mock(
            return_value=[
                {
                    'rrset_name': 'www',
                    'rrset_ttl': 300,
                    'rrset_type': 'A',
                    'rrset_values': ['1.2.3.4'],
                },
                {
                    'rrset_name': 'www',
                    'rrset_ttl': 300,
                    'rrset_type': 'A',
                    'rrset_values': ['2.2.3.4'],
                },
                {
                    'rrset_name': 'ttl',
                    'rrset_ttl': 600,
                    'rrset_type': 'A',
                    'rrset_values': ['3.2.3.4'],
                },
            ]
        )

        # Domain exists, we don't care about return
        resp.json.side_effect = ['{}']

        wanted = Zone('unit.tests.', [])
        wanted.add_record(
            Record.new(
                wanted, 'ttl', {'ttl': 300, 'type': 'A', 'value': '3.2.3.4'}
            )
        )

        plan = provider.plan(wanted)
        self.assertTrue(plan.exists)
        self.assertEqual(2, len(plan.changes))
        self.assertEqual(2, provider.apply(plan))

        # recreate for update, and deletes for the 2 parts of the other
        provider._client._request.assert_has_calls(
            [
                call('DELETE', '/livedns/domains/unit.tests/records/www/A'),
                call('DELETE', '/livedns/domains/unit.tests/records/ttl/A'),
                call(
                    'POST',
                    '/livedns/domains/unit.tests/records',
                    data={
                        'rrset_name': 'ttl',
                        'rrset_ttl': 300,
                        'rrset_type': 'A',
                        'rrset_values': ['3.2.3.4'],
                    },
                ),
            ],
            any_order=True,
        )
