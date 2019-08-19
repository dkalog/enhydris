from datetime import datetime, timezone
from unittest.mock import patch

from rest_framework.test import APITestCase

from model_mommy import mommy

from enhydris import models

from .test_search import SearchTestCaseBase


def make_timeseries(*, start_date, end_date, **kwargs):
    """Make a test timeseries, setting start_date and end_date.

    This is essentially the same as mommy.make(models.Timeseries, **kwargs), except
    that it also sets start_date and end_date.
    """
    with patch("enhydris.models.Timeseries._set_start_and_end_date"):
        return mommy.make(
            models.Timeseries,
            start_date_utc=start_date.replace(tzinfo=timezone.utc),
            end_date_utc=end_date.replace(tzinfo=timezone.utc),
            **kwargs,
        )


class SearchWithYearExistingInOneStationTest(SearchTestCaseBase, APITestCase):
    search_term = "ts_has_years:2005,2012,2016"
    search_result = "Tharbad"

    def _create_models(self):
        komboti = mommy.make(models.Station, name="Komboti")
        tharbad = mommy.make(models.Station, name="Tharbad")
        self.komboti_temperature = make_timeseries(
            gentity=komboti,
            start_date=datetime(2005, 8, 23, 18, 53),
            end_date=datetime(2010, 8, 23, 22, 53),
            variable__descr="Temperature",
        )
        self.komboti_rain = make_timeseries(
            gentity=komboti,
            start_date=datetime(2011, 8, 23, 18, 53),
            end_date=datetime(2015, 8, 23, 22, 53),
            variable__descr="Rain",
        )
        self.tharbad_temperature = make_timeseries(
            gentity=tharbad,
            start_date=datetime(2005, 8, 23, 18, 53),
            end_date=datetime(2010, 8, 23, 22, 53),
            variable__descr="Temperature",
        )
        self.tharbad_rain = make_timeseries(
            gentity=tharbad,
            start_date=datetime(2009, 8, 23, 18, 53),
            end_date=datetime(2017, 8, 23, 22, 53),
            variable__descr="Rain",
        )


class SearchWithYearsExistingInAllStationsTest(SearchWithYearExistingInOneStationTest):
    search_term = "ts_has_years:2005,2012"
    search_result = {"Komboti", "Tharbad"}
    number_of_results = 2


class SearchWithYearsExistingNowhereTest(SearchWithYearExistingInOneStationTest):
    search_term = "ts_has_years:2005,2012,2018"
    search_result = set()
    number_of_results = 0


class SearchWithGarbageTest(SearchWithYearExistingInOneStationTest):
    search_term = "ts_has_years:hello,world"
    status_code = 404
