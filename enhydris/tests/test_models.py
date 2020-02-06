import datetime as dt
import os
from io import StringIO
from unittest.mock import MagicMock, Mock, mock_open, patch

from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import TestCase

import pandas as pd
from htimeseries import HTimeseries
from model_mommy import mommy

from enhydris import models
from enhydris.tests import RandomEnhydrisTimeseriesDataDir


class PersonTestCase(TestCase):
    def test_create(self):
        person = models.Person(last_name="Brown", first_name="Alice", initials="A.")
        person.save()
        self.assertEqual(models.Person.objects.first().last_name, "Brown")

    def test_update(self):
        mommy.make(models.Person)
        person = models.Person.objects.first()
        person.first_name = "Bob"
        person.save()
        self.assertEqual(models.Person.objects.first().first_name, "Bob")

    def test_delete(self):
        mommy.make(models.Person)
        person = models.Person.objects.first()
        person.delete()
        self.assertEqual(models.Person.objects.count(), 0)

    def test_str(self):
        person = mommy.make(
            models.Person, last_name="Brown", first_name="Alice", initials="A."
        )
        self.assertEqual(str(person), "Brown A.")

    def test_ordering_string(self):
        mommy.make(models.Person, last_name="Brown", first_name="Alice", initials="A.")
        person = models.Person.objects.first()
        self.assertEqual(person.ordering_string, "Brown Alice")


class OrganizationTestCase(TestCase):
    def test_create(self):
        organization = models.Organization(name="Crooks Intl", acronym="Crooks")
        organization.save()
        self.assertEqual(models.Organization.objects.first().name, "Crooks Intl")

    def test_update(self):
        mommy.make(models.Organization)
        organization = models.Organization.objects.first()
        organization.acronym = "Crooks"
        organization.save()
        self.assertEqual(models.Organization.objects.first().acronym, "Crooks")

    def test_delete(self):
        mommy.make(models.Organization)
        organization = models.Organization.objects.first()
        organization.delete()
        self.assertEqual(models.Organization.objects.count(), 0)

    def test_str(self):
        org = mommy.make(models.Organization, name="Crooks Intl", acronym="Crooks")
        self.assertEqual(str(org), "Crooks")

    def test_ordering_string(self):
        mommy.make(models.Organization, name="Crooks Intl", acronym="Crooks")
        organization = models.Organization.objects.first()
        self.assertEqual(organization.ordering_string, "Crooks Intl")


class VariableTestCase(TestCase):
    """Test lookups.

    We test Variable as an example of Lookup. We don't test EventType
    because it is a similar trivial Lookup descendant.
    """

    def test_create(self):
        gact = models.Variable(descr="Temperature")
        gact.save()
        self.assertEqual(models.Variable.objects.first().descr, "Temperature")

    def test_update(self):
        mommy.make(models.Variable)
        gact = models.Variable.objects.first()
        gact.descr = "Temperature"
        gact.save()
        self.assertEqual(models.Variable.objects.first().descr, "Temperature")

    def test_delete(self):
        mommy.make(models.Variable)
        gact = models.Variable.objects.first()
        gact.delete()
        self.assertEqual(models.Variable.objects.count(), 0)

    def test_str(self):
        gact = mommy.make(models.Variable, descr="Temperature")
        self.assertEqual(str(gact), "Temperature")


class FileTypeTestCase(TestCase):
    # We don't test functionality inherited from Lookup, as this is tested in
    # VariableTestCase.

    def test_str(self):
        file_type = mommy.make(models.FileType, mime_type="image/png")
        self.assertEqual(str(file_type), "image/png")


class GentityFileTestCase(TestCase):
    def test_create(self):
        station = mommy.make(models.Station)
        file_type = mommy.make(models.FileType)
        gentity_file = models.GentityFile(
            gentity=station, file_type=file_type, descr="North view"
        )
        gentity_file.save()
        self.assertEqual(models.GentityFile.objects.first().descr, "North view")

    def test_update(self):
        mommy.make(models.GentityFile)
        gentity_file = models.GentityFile.objects.first()
        gentity_file.descr = "North view"
        gentity_file.save()
        self.assertEqual(models.GentityFile.objects.first().descr, "North view")

    def test_delete(self):
        mommy.make(models.GentityFile)
        gentity_file = models.GentityFile.objects.first()
        gentity_file.delete()
        self.assertEqual(models.GentityFile.objects.count(), 0)

    def test_str(self):
        gentity_file = mommy.make(models.GentityFile, descr="North view")
        self.assertEqual(str(gentity_file), "North view")

    def test_related_station(self):
        station = mommy.make(models.Station)
        gentity_file = mommy.make(models.GentityFile, gentity=station)
        self.assertEqual(gentity_file.related_station, station)

    def test_related_station_is_empty_when_gentity_is_not_station(self):
        garea = mommy.make(models.Garea)
        gentity_file = mommy.make(models.GentityFile, gentity=garea)
        self.assertIsNone(gentity_file.related_station)


class GentityEventTestCase(TestCase):
    def test_create(self):
        station = mommy.make(models.Station)
        type = mommy.make(models.EventType)
        gentity_event = models.GentityEvent(
            gentity=station,
            type=type,
            date=dt.datetime.now(),
            user="Alice",
            report="Station exploded",
        )
        gentity_event.save()
        self.assertEqual(models.GentityEvent.objects.first().report, "Station exploded")

    def test_update(self):
        mommy.make(models.GentityEvent)
        gentity_event = models.GentityEvent.objects.first()
        gentity_event.report = "Station exploded"
        gentity_event.save()
        self.assertEqual(models.GentityEvent.objects.first().report, "Station exploded")

    def test_delete(self):
        mommy.make(models.GentityEvent)
        gentity_event = models.GentityEvent.objects.first()
        gentity_event.delete()
        self.assertEqual(models.GentityEvent.objects.count(), 0)

    def test_str(self):
        gentity_event = mommy.make(
            models.GentityEvent, date="2018-11-14", type__descr="Explosion"
        )
        self.assertEqual(str(gentity_event), "2018-11-14 Explosion")

    def test_related_station(self):
        station = mommy.make(models.Station)
        gentity_event = mommy.make(models.GentityEvent, gentity=station)
        self.assertEqual(gentity_event.related_station, station)

    def test_related_station_is_empty_when_gentity_is_not_station(self):
        garea = mommy.make(models.Garea)
        gentity_event = mommy.make(models.GentityEvent, gentity=garea)
        self.assertIsNone(gentity_event.related_station)


class GareaTestCase(TestCase):
    def test_create(self):
        category = mommy.make(models.GareaCategory)
        garea = models.Garea(
            name="Esgalduin",
            category=category,
            geom=MultiPolygon(Polygon(((30, 20), (45, 40), (10, 40), (30, 20)))),
        )
        garea.save()
        self.assertEqual(models.Garea.objects.first().name, "Esgalduin")

    def test_update(self):
        mommy.make(models.Garea)
        garea = models.Garea.objects.first()
        garea.name = "Esgalduin"
        garea.save()
        self.assertEqual(models.Garea.objects.first().name, "Esgalduin")

    def test_delete(self):
        mommy.make(models.Garea)
        garea = models.Garea.objects.first()
        garea.delete()
        self.assertEqual(models.Garea.objects.count(), 0)

    def test_str(self):
        garea = mommy.make(models.Garea, name="Esgalduin")
        self.assertEqual(str(garea), "Esgalduin")


class StationTestCase(TestCase):
    def test_create(self):
        person = mommy.make(models.Person)
        station = models.Station(
            owner=person,
            copyright_holder="Bilbo Baggins",
            copyright_years="2018",
            name="Hobbiton",
            geom=Point(x=21.06071, y=39.09518, srid=4326),
        )
        station.save()
        self.assertEqual(models.Station.objects.first().name, "Hobbiton")

    def test_update(self):
        mommy.make(models.Station)
        station = models.Station.objects.first()
        station.name = "Hobbiton"
        station.save()
        self.assertEqual(models.Station.objects.first().name, "Hobbiton")

    def test_delete(self):
        mommy.make(models.Station)
        station = models.Station.objects.first()
        station.delete()
        self.assertEqual(models.Station.objects.count(), 0)

    def test_str(self):
        station = mommy.make(models.Station, name="Hobbiton")
        self.assertEqual(str(station), "Hobbiton")


class StationOriginalCoordinatesTestCase(TestCase):
    def setUp(self):
        mommy.make(
            models.Station,
            name="Komboti",
            geom=Point(x=21.06071, y=39.09518, srid=4326),
            original_srid=2100,
        )
        self.station = models.Station.objects.get(name="Komboti")

    def test_original_abscissa(self):
        self.assertAlmostEqual(self.station.original_abscissa(), 245648.96, places=1)

    def test_original_ordinate(self):
        self.assertAlmostEqual(self.station.original_ordinate(), 4331165.20, places=1)


class StationOriginalCoordinatesWithNullSridTestCase(TestCase):
    def setUp(self):
        mommy.make(
            models.Station,
            name="Komboti",
            geom=Point(x=21.06071, y=39.09518, srid=4326),
            original_srid=None,
        )
        self.station = models.Station.objects.get(name="Komboti")

    def test_original_abscissa(self):
        self.assertAlmostEqual(self.station.original_abscissa(), 21.06071)

    def test_original_ordinate(self):
        self.assertAlmostEqual(self.station.original_ordinate(), 39.09518)


@patch("enhydris.models.Timeseries._set_start_and_end_date")
class StationLastUpdateTestCase(TestCase):
    def setUp(self):
        self.station = mommy.make(models.Station)
        self.time_zone = mommy.make(models.TimeZone, code="EET", utc_offset=120)

    def _create_timeseries(self, ye=None, mo=None, da=None, ho=None, mi=None):
        if ye:
            end_date_utc = dt.datetime(ye, mo, da, ho, mi, tzinfo=dt.timezone.utc)
        else:
            end_date_utc = None
        mommy.make(
            models.Timeseries,
            gentity=self.station,
            time_zone=self.time_zone,
            end_date_utc=end_date_utc,
            precision=2,
        )

    def test_last_update_when_all_timeseries_have_end_date(self, m):
        self._create_timeseries(2019, 7, 24, 11, 26)
        self._create_timeseries(2019, 7, 23, 5, 10)
        self.assertEqual(
            self.station.last_update,
            dt.datetime(2019, 7, 24, 13, 26, tzinfo=self.time_zone.as_tzinfo),
        )

    def test_last_update_when_one_timeseries_has_no_data(self, m):
        self._create_timeseries(2019, 7, 24, 11, 26)
        self._create_timeseries()
        self.assertEqual(
            self.station.last_update,
            dt.datetime(2019, 7, 24, 13, 26, tzinfo=self.time_zone.as_tzinfo),
        )

    def test_last_update_when_all_timeseries_has_no_data(self, m):
        self._create_timeseries()
        self._create_timeseries()
        self.assertIsNone(self.station.last_update)

    def test_last_update_when_no_timeseries(self, m):
        self.assertIsNone(self.station.last_update)


class UnitOfMeasurementTestCase(TestCase):
    # We don't test functionality inherited from Lookup, as this is tested in
    # VariableTestCase.

    def test_str(self):
        unit = mommy.make(models.UnitOfMeasurement, symbol="mm")
        self.assertEqual(str(unit), "mm")

    def test_str_when_symbol_is_empty(self):
        unit = mommy.make(models.UnitOfMeasurement, symbol="")
        self.assertEqual(str(unit), str(unit.id))


class TimeZoneTestCase(TestCase):
    def test_create(self):
        time_zone = models.TimeZone(code="EET", utc_offset=120)
        time_zone.save()
        self.assertEqual(models.TimeZone.objects.first().code, "EET")

    def test_update(self):
        mommy.make(models.TimeZone)
        time_zone = models.TimeZone.objects.first()
        time_zone.code = "EET"
        time_zone.save()
        self.assertEqual(models.TimeZone.objects.first().code, "EET")

    def test_delete(self):
        mommy.make(models.TimeZone)
        time_zone = models.TimeZone.objects.first()
        time_zone.delete()
        self.assertEqual(models.TimeZone.objects.count(), 0)

    def test_str(self):
        time_zone = mommy.make(models.TimeZone, code="EET", utc_offset=120)
        self.assertEqual(str(time_zone), "EET (UTC+0200)")

    def test_as_tzinfo(self):
        time_zone = mommy.make(models.TimeZone, code="EET", utc_offset=120)
        self.assertEqual(time_zone.as_tzinfo, dt.timezone(dt.timedelta(hours=2), "EET"))


class TimeseriesTestCase(TestCase):
    def test_create(self):
        station = mommy.make(models.Station)
        variable = mommy.make(models.Variable)
        unit = mommy.make(models.UnitOfMeasurement)
        time_zone = mommy.make(models.TimeZone)
        timeseries = models.Timeseries(
            gentity=station,
            name="Temperature",
            variable=variable,
            unit_of_measurement=unit,
            time_zone=time_zone,
            precision=2,
        )
        timeseries.save()
        self.assertEqual(models.Timeseries.objects.first().name, "Temperature")

    def test_update(self):
        mommy.make(models.Timeseries)
        timeseries = models.Timeseries.objects.first()
        timeseries.name = "Temperature"
        timeseries.save()
        self.assertEqual(models.Timeseries.objects.first().name, "Temperature")

    def test_delete(self):
        mommy.make(models.Timeseries)
        timeseries = models.Timeseries.objects.first()
        timeseries.delete()
        self.assertEqual(models.Timeseries.objects.count(), 0)

    def test_str(self):
        timeseries = mommy.make(models.Timeseries, name="Temperature")
        self.assertEqual(str(timeseries), "Temperature")

    def test_related_station(self):
        station = mommy.make(models.Station)
        timeseries = mommy.make(models.Timeseries, gentity=station)
        self.assertEqual(timeseries.related_station, station)


class TimeseriesDatesTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(
            models.Timeseries, time_zone__utc_offset=120, precision=2
        )

        # We can't have mommy save the following two, because it calls
        # Timeseries.save(), and .save() would overwrite them.
        self.timeseries.start_date_utc = dt.datetime(
            2018, 11, 15, 16, 0, tzinfo=dt.timezone.utc
        )
        self.timeseries.end_date_utc = dt.datetime(
            2018, 11, 17, 23, 0, tzinfo=dt.timezone.utc
        )

    def test_start_date(self):
        self.assertEqual(
            self.timeseries.start_date,
            dt.datetime(
                2018, 11, 15, 18, 0, tzinfo=self.timeseries.time_zone.as_tzinfo
            ),
        )

    def test_end_date(self):
        self.assertEqual(
            self.timeseries.end_date,
            dt.datetime(2018, 11, 18, 1, 0, tzinfo=self.timeseries.time_zone.as_tzinfo),
        )


class TimeseriesSaveDatesTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(
            models.Timeseries, time_zone__utc_offset=120, precision=2
        )

        # Mock self.timeseries.datafile
        self.timeseries.datafile = Mock(size=50)

        # Mock open so that it appears to provide some data
        m = mock_open(read_data="2017-11-23 17:23,1,\n" "2018-11-25 01:00,2,\n")
        patch_open = patch("enhydris.models.open", m)

        # Mock ropen so that it appears to provide the same data in reverse
        m = mock_open(read_data="2018-11-25 01:00,2,\n" "2017-11-23 17:23,1,\n")
        patch_ropen = patch("enhydris.models.ropen", m)

        # Mock django's Model.save(), otherwise when it runs under this mock mess
        # it causes an error
        patch_save = patch("enhydris.models.models.Model.save")

        # Execute Timeseries.save(); then we will verify dates were overwritten
        with patch_open, patch_ropen, patch_save:
            self.timeseries.save()

    def test_start_date(self):
        self.assertEqual(
            self.timeseries.start_date_utc,
            dt.datetime(2017, 11, 23, 15, 23, tzinfo=dt.timezone.utc),
        )

    def test_end_date(self):
        self.assertEqual(
            self.timeseries.end_date_utc,
            dt.datetime(2018, 11, 24, 23, 0, tzinfo=dt.timezone.utc),
        )


@RandomEnhydrisTimeseriesDataDir()
class TimeseriesGetDataTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        station = mommy.make(
            models.Station,
            name="Celduin",
            original_srid=2100,
            geom=Point(x=21.06071, y=39.09518, srid=4326),
            altitude=219,
        )
        cls.timeseries = mommy.make(
            models.Timeseries,
            name="Daily temperature",
            gentity=station,
            time_step="H",
            unit_of_measurement__symbol="mm",
            time_zone__code="IST",
            time_zone__utc_offset=330,
            variable__descr="Temperature",
            precision=1,
            remarks="This timeseries rocks",
        )
        cls.timeseries.datafile.save(
            "filename", ContentFile("2017-11-23 17:23,1,\n2018-11-25 01:00,2,\n")
        )

        cls.data = cls.timeseries.get_data()

    def test_abscissa(self):
        self.assertAlmostEqual(self.data.location["abscissa"], 245648.96, places=2)

    def test_ordinate(self):
        self.assertAlmostEqual(self.data.location["ordinate"], 4331165.20, places=2)

    def test_srid(self):
        self.assertAlmostEqual(self.data.location["srid"], 2100)

    def test_altitude(self):
        self.assertAlmostEqual(self.data.location["altitude"], 219)

    def test_time_step(self):
        self.assertEqual(self.data.time_step, "H")

    def test_unit(self):
        self.assertEqual(self.data.unit, "mm")

    def test_title(self):
        self.assertEqual(self.data.title, "Daily temperature")

    def test_timezone(self):
        self.assertEqual(self.data.timezone, "IST (UTC+0530)")

    def test_negative_timezone(self):
        self.timeseries.time_zone.code = "NST"
        self.timeseries.time_zone.utc_offset = -210
        data = self.timeseries.get_data()
        self.assertEqual(data.timezone, "NST (UTC-0330)")

    def test_variable(self):
        self.assertEqual(self.data.variable, "Temperature")

    def test_precision(self):
        self.assertEqual(self.data.precision, 1)

    def test_comment(self):
        self.assertEqual(self.data.comment, "Celduin\n\nThis timeseries rocks")

    def test_location_is_none(self):
        self.timeseries.gentity.geom = None
        data = self.timeseries.get_data()
        self.assertIsNone(data.location)

    def test_data(self):
        expected_result = pd.DataFrame(
            data={"value": [1.0, 2.0], "flags": ["", ""]},
            columns=["value", "flags"],
            index=[dt.datetime(2017, 11, 23, 17, 23), dt.datetime(2018, 11, 25, 1, 0)],
        )
        expected_result.index.name = "date"
        pd.testing.assert_frame_equal(self.data.data, expected_result)


@RandomEnhydrisTimeseriesDataDir()
class TimeseriesSetDataTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )

    def test_call_with_file_object(self):
        returned_length = self.timeseries.set_data(
            StringIO("2017-11-23 17:23,1,\n" "2018-11-25 01:00,2,\n")
        )
        self.assertEqual(returned_length, 2)
        self.assertEqual(self.timeseries.datafile.name, "0000000042")
        self._assert_file_contents()

    def test_call_with_dataframe(self):
        returned_length = self.timeseries.set_data(self._get_dataframe())
        self.assertEqual(returned_length, 2)
        self.assertEqual(self.timeseries.datafile.name, "0000000042")
        self._assert_file_contents()

    def test_call_with_htimeseries(self):
        returned_length = self.timeseries.set_data(HTimeseries(self._get_dataframe()))
        self.assertEqual(returned_length, 2)
        self.assertEqual(self.timeseries.datafile.name, "0000000042")
        self._assert_file_contents()

    def _get_dataframe(self):
        result = pd.DataFrame(
            data={"value": [1.0, 2.0], "flags": ["", ""]},
            columns=["value", "flags"],
            index=[dt.datetime(2017, 11, 23, 17, 23), dt.datetime(2018, 11, 25, 1, 0)],
        )
        result.index.name = "date"
        return result

    def _assert_file_contents(self):
        self.assertEqual(
            open(
                os.path.join(settings.ENHYDRIS_TIMESERIES_DATA_DIR, "0000000042"), "rb"
            ).read(),
            (
                b"2017-11-23 17:23,1.000000000000000,\r\n"
                b"2018-11-25 01:00,2.000000000000000,\r\n"
            ),
        )


@RandomEnhydrisTimeseriesDataDir()
class TimeseriesAppendDataTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )
        self.timeseries.set_data(StringIO("2016-01-01 00:00,42,\n"))

    def test_call_with_file_object(self):
        returned_length = self.timeseries.append_data(
            StringIO("2017-11-23 17:23,1,\n" "2018-11-25 01:00,2,\n")
        )
        self.assertEqual(returned_length, 2)
        self._assert_wrote_data()

    def test_call_with_dataframe(self):
        returned_length = self.timeseries.append_data(self._get_dataframe())
        self.assertEqual(returned_length, 2)
        self._assert_wrote_data()

    def test_call_with_htimeseries(self):
        returned_length = self.timeseries.append_data(
            HTimeseries(self._get_dataframe())
        )
        self.assertEqual(returned_length, 2)
        self._assert_wrote_data()

    def _get_dataframe(self):
        result = pd.DataFrame(
            data={"value": [1.0, 2.0], "flags": ["", ""]},
            columns=["value", "flags"],
            index=[dt.datetime(2017, 11, 23, 17, 23), dt.datetime(2018, 11, 25, 1, 0)],
        )
        result.index.name = "date"
        return result

    def _assert_wrote_data(self):
        self.assertEqual(
            open(self.timeseries.datafile.path, "rb").read(),
            (
                b"2016-01-01 00:00,42.000000000000000,\r\n"
                b"2017-11-23 17:23,1.000000000000000,\r\n"
                b"2018-11-25 01:00,2.000000000000000,\r\n"
            ),
        )


@RandomEnhydrisTimeseriesDataDir()
class TimeseriesAppendDataToEmptyTimeseriesTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )

    def test_call_with_dataframe(self):
        returned_length = self.timeseries.append_data(self._get_dataframe())
        self.assertEqual(returned_length, 2)
        self._assert_wrote_data()

    def _get_dataframe(self):
        result = pd.DataFrame(
            data={"value": [1.0, 2.0], "flags": ["", ""]},
            columns=["value", "flags"],
            index=[dt.datetime(2017, 11, 23, 17, 23), dt.datetime(2018, 11, 25, 1, 0)],
        )
        result.index.name = "date"
        return result

    def _assert_wrote_data(self):
        self.assertEqual(
            open(self.timeseries.datafile.path, "rb").read(),
            (
                b"2017-11-23 17:23,1.000000000000000,\r\n"
                b"2018-11-25 01:00,2.000000000000000,\r\n"
            ),
        )


@RandomEnhydrisTimeseriesDataDir()
class TimeseriesAppendErrorTestCase(TestCase):
    def test_does_not_update_if_data_to_append_are_not_later(self):
        self.timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )
        self.timeseries.set_data(StringIO("2018-01-01 00:00,42,\n"))
        with self.assertRaises(IntegrityError):
            self.timeseries.append_data(
                StringIO("2017-11-23 17:23,1,\n2018-11-25 01:00,2,\n")
            )


class TimeseriesGetFirstOrLastLineTestCase(TestCase):
    def test_get_first_line(self):
        timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )

        # Mock self.timeseries.datafile
        timeseries.datafile = MagicMock(size=50)

        # Mock open() so that it supposedly returns some data
        m = mock_open(read_data="2017-11-23 17:23,1,\n" "2018-11-25 01:00,2,\n")
        patch1 = patch("enhydris.models.open", m)

        # Mock Timeseries.save(), otherwise there's chaos
        patch2 = patch("enhydris.models.Timeseries.save")

        with patch1, patch2:
            first_line = timeseries.get_first_line()

        self.assertEqual(first_line, "2017-11-23 17:23,1,\n")

    def test_get_last_line(self):
        timeseries = mommy.make(
            models.Timeseries, id=42, time_zone__utc_offset=0, precision=2
        )

        # Mock self.timeseries.datafile
        timeseries.datafile = MagicMock(size=50)

        # Mock ropen() so that it supposedly returns some data
        m = mock_open(read_data="2018-11-25 01:00,2,\n" "2017-11-23 17:23,1,\n")
        patch1 = patch("enhydris.models.ropen", m)

        # Mock Timeseries.save(), otherwise there's chaos
        patch2 = patch("enhydris.models.Timeseries.save")

        with patch1, patch2:
            first_line = timeseries.get_last_line()

        self.assertEqual(first_line, "2018-11-25 01:00,2,\n")


class TimestepTestCase(TestCase):
    def setUp(self):
        self.timeseries = mommy.make(models.Timeseries)

    def set_time_step(self, time_step):
        self.timeseries.time_step = time_step
        self.timeseries.save()

    def test_min(self):
        self.set_time_step("27min")
        self.assertEqual(models.Timeseries.objects.first().time_step, "27min")

    def test_hour(self):
        self.set_time_step("3H")
        self.assertEqual(models.Timeseries.objects.first().time_step, "3H")

    def test_day(self):
        self.set_time_step("3D")
        self.assertEqual(models.Timeseries.objects.first().time_step, "3D")

    def test_month(self):
        self.set_time_step("3M")
        self.assertEqual(models.Timeseries.objects.first().time_step, "3M")

    def test_3Y(self):
        self.set_time_step("3Y")
        self.assertEqual(models.Timeseries.objects.first().time_step, "3Y")

    def test_Y(self):
        self.set_time_step("Y")
        self.assertEqual(models.Timeseries.objects.first().time_step, "Y")

    def test_garbage(self):
        with self.assertRaisesRegex(ValueError, '"hello" is not a valid time step'):
            self.set_time_step("hello")

    def test_wrong_number(self):
        with self.assertRaisesRegex(ValueError, '"FM" is not a valid time step'):
            self.set_time_step("FM")

    def test_wrong_unit(self):
        with self.assertRaisesRegex(ValueError, '"3B" is not a valid time step'):
            self.set_time_step("3B")
