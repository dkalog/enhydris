import datetime as dt
from time import sleep
from unittest import skipUnless

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase, override_settings

import django_selenium_clean
from bs4 import BeautifulSoup
from django_selenium_clean import PageElement
from model_mommy import mommy
from selenium.webdriver.common.by import By

from enhydris.models import GentityFile, GentityImage, Organization, Station, Timeseries
from enhydris.tests import TimeseriesDataMixin


class StationListTestCase(TestCase):
    def setUp(self):
        mommy.make(
            User,
            username="admin",
            password=make_password("topsecret"),
            is_active=True,
            is_superuser=True,
            is_staff=True,
        )
        mommy.make(
            Station,
            name="Komboti",
            geom=Point(x=21.06071, y=39.09518, srid=4326),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="Agios Athanasios",
            geom=Point(x=21.60121, y=39.22440, srid=4326),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="Tharbad",
            geom=Point(x=-176.48368, y=0.19377, srid=4326),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="SRID Point, NoSRID Station",
            geom=Point(x=-176.48368, y=0.19377, srid=4326),
            original_srid=None,
        )
        mommy.make(
            Station,
            name="NoSRID Point, SRID Station",
            geom=Point(x=-176.48368, y=0.19377, srid=None),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="NoSRID Point, NoSRID Station",
            geom=Point(x=-176.48368, y=0.19377, srid=None),
            original_srid=None,
        )

    def test_station_list(self):
        response = self.client.get("/?q=t")
        self.assertContains(response, "Search results", html=True)

    @override_settings(ENHYDRIS_STATIONS_PER_PAGE=3)
    def test_two_pages(self):
        response = self.client.get("/?q=t")
        self.assertContains(
            response, '<a class="page-link" href="?page=2&q=t">2</a>', html=True
        )
        self.assertNotContains(
            response, '<a class="page-link" href="?page=3&q=t">3</a>', html=True
        )

    @override_settings(ENHYDRIS_STATIONS_PER_PAGE=2)
    def test_next_page_url(self):
        response = self.client.get("/?q=t")
        soup = BeautifulSoup(response.content, "html.parser")
        next_page_url = soup.find("a", id="next-page").get("href")
        self.assertEqual(next_page_url, "?page=2&q=t")

    @override_settings(ENHYDRIS_STATIONS_PER_PAGE=2)
    def test_previous_page_url(self):
        response = self.client.get("/?q=t&page=2")
        soup = BeautifulSoup(response.content, "html.parser")
        next_page_url = soup.find("a", id="previous-page").get("href")
        self.assertEqual(next_page_url, "?page=1&q=t")

    @override_settings(ENHYDRIS_STATIONS_PER_PAGE=100)
    def test_one_page(self):
        response = self.client.get("/?q=t")
        self.assertNotContains(response, "<a href='?page=2'>2</a>", html=True)

    @override_settings(ENHYDRIS_MAP_DEFAULT_VIEWPORT=(1.1, 2.2, 3.3, 4.4))
    def test_default_map_viewport_when_given_as_a_tuple(self):
        Station.objects.all().delete()
        response = self.client.get("/")
        self.assertContains(response, "enhydris.mapViewport = [1.1, 2.2, 3.3, 4.4]")


class StationDetailTestCase(TestCase, TimeseriesDataMixin):
    def setUp(self):
        self.create_timeseries()

    @override_settings(ENHYDRIS_MAP_MIN_VIEWPORT_SIZE=0.2)
    def test_map_viewport(self):
        response = self.client.get(f"/stations/{self.station.id}/")
        self.assertContains(response, "enhydris.mapViewport = [20.9, 38.9, 21.1, 39.1]")

    def test_timeseries_group_list(self):
        response = self.client.get(f"/stations/{self.station.id}/")
        self.assertContains(
            response,
            f'<a href="/stations/{self.station.id}/timeseriesgroups'
            f'/{self.timeseries_group.id}/">Beauty</a>',
        )


@override_settings(MEDIA_URL="/media/")
class StationDetailImagesTestCase(TestCase):
    def setUp(self):
        self.station = mommy.make(Station)
        self.image1 = self._create_image(descr="a", content="/image1.png")
        self.image2 = self._create_image(descr="b", content="/image2.png")

    def _create_image(self, descr, content):
        return mommy.make(
            GentityImage, gentity=self.station, descr=descr, content=content
        )

    def test_first_image_is_featured_when_no_image_is_marked_as_featured(self):
        response = self.client.get(f"/stations/{self.station.id}/")
        soup = BeautifulSoup(response.content, "html.parser")
        img = soup.find("div", class_="featured-image").a.img
        self.assertEqual(img["src"], "/media/image1.png")

    def test_featured_image_is_featured(self):
        self.image2.featured = True
        self.image2.save()
        response = self.client.get(f"/stations/{self.station.id}/")
        soup = BeautifulSoup(response.content, "html.parser")
        img = soup.find("div", class_="featured-image").a.img
        self.assertEqual(img["src"], "/media/image2.png")

    def test_first_non_featured_image_when_one_is_featured(self):
        self.image2.featured = True
        self.image2.save()
        response = self.client.get(f"/stations/{self.station.id}/")
        soup = BeautifulSoup(response.content, "html.parser")
        img = soup.find("div", class_="swiper-wrapper").a.img
        self.assertEqual(img["src"], "/media/image1.png")


@override_settings(LANGUAGE_CODE="en-gb", LANGUAGES={"en-gb": "English"})
class StationDetailPeriodOfOperationTestCase(TestCase):
    def setUp(self):
        self.station = mommy.make(
            Station,
            name="Komboti",
            geom=Point(x=21.00000, y=39.00000, srid=4326),
            original_srid=4326,
        )

    def _set_dates(self, start_date, end_date):
        self.station.start_date = start_date
        self.station.end_date = end_date
        self.station.save()

    def _get_response(self):
        return self.client.get(
            "/stations/{}/".format(self.station.id), HTTP_ACCEPT_LANGUAGE="en-gb"
        )

    def test_when_start_date_and_end_date(self):
        self._set_dates(dt.datetime(2019, 7, 26), dt.datetime(2019, 7, 27))
        response = self._get_response()
        self.assertContains(
            response, "<b>Period of operation:</b> 26/07/2019 - 27/07/2019"
        )

    def test_when_only_start_date(self):
        self._set_dates(dt.datetime(2019, 7, 26), None)
        response = self._get_response()
        self.assertContains(response, "<b>Start of operation:</b> 26/07/2019")

    @override_settings(LANGUAGE_CODE="en")
    def test_when_only_end_date(self):
        self._set_dates(None, dt.datetime(2019, 7, 27))
        response = self._get_response()
        self.assertContains(response, "<b>End of operation:</b> 27/07/2019")

    def test_when_no_dates(self):
        self._set_dates(None, None)
        response = self._get_response()
        self.assertNotContains(response, "operation")


class TimeseriesDownloadButtonTestCase(TestCase, TimeseriesDataMixin):
    def setUp(self):
        self.create_timeseries()
        self.download_button = (
            '<button type="submit" class="btn form-btn-download">download</button>'
        )

    def _get_response(self):
        self.response = self.client.get(
            f"/stations/{self.station.id}/timeseriesgroups/{self.timeseries_group.id}/"
        )

    @override_settings(ENHYDRIS_OPEN_CONTENT=True)
    def test_contains_download_button_when_site_content_is_free(self):
        self._get_response()
        self.assertContains(self.response, self.download_button)

    @override_settings(ENHYDRIS_OPEN_CONTENT=False)
    def test_has_no_download_link_when_site_content_is_restricted(self):
        self._get_response()
        self.assertNotContains(self.response, self.download_button)

    @override_settings(ENHYDRIS_OPEN_CONTENT=True)
    def test_has_no_permission_denied_message_when_site_content_is_free(self):
        self._get_response()
        self.assertNotContains(self.response, "You don't have permission to download")

    @override_settings(ENHYDRIS_OPEN_CONTENT=False)
    def test_shows_permission_denied_message_when_site_content_is_restricted(self):
        self._get_response()
        self.assertContains(self.response, "You don't have permission to download")


class GentityFileDownloadLinkTestCase(TestCase):
    def setUp(self):
        self.station = mommy.make(Station, name="Komboti")
        self.gentityfile = mommy.make(GentityFile, gentity=self.station)
        self.link = (
            '<a href="/api/stations/{}/files/{}/content/" aria-label="Download">'
        ).format(self.station.id, self.gentityfile.id)

    @override_settings(ENHYDRIS_OPEN_CONTENT=True)
    def test_contains_download_link_when_site_content_is_free(self):
        response = self.client.get("/stations/{}/".format(self.station.id))
        self.assertContains(response, self.link)

    @override_settings(ENHYDRIS_OPEN_CONTENT=False)
    def test_has_no_download_link_when_site_content_is_restricted(self):
        response = self.client.get("/stations/{}/".format(self.station.id))
        self.assertNotContains(response, self.link)


class StationEditRedirectTestCase(TestCase):
    def setUp(self):
        self.response = self.client.get("/stations/42/edit/")

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 302)

    def test_redirect_target(self):
        self.assertEqual(
            self.response["Location"], "/admin/enhydris/station/42/change/"
        )


class RedirectOldUrlsTestCase(TestCase):
    def test_old_stations_url_redirects(self):
        r = self.client.get("/stations/d/200348/")
        self.assertRedirects(
            r, "/stations/200348/", status_code=301, fetch_redirect_response=False
        )

    def test_old_timeseries_url_redirects(self):
        mommy.make(
            Timeseries,
            id=1169,
            timeseries_group__id=100174,
            timeseries_group__gentity__id=200348,
        )
        r = self.client.get("/timeseries/d/1169/")
        self.assertRedirects(
            r,
            "/stations/200348/timeseriesgroups/100174/",
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_old_timeseries_url_for_nonexistent_timeseries_returns_404(self):
        r = self.client.get("/timeseries/d/1169/")
        self.assertEqual(r.status_code, 404)


class SeleniumTestCase(django_selenium_clean.SeleniumTestCase):
    """A change in SeleniumTestCase so that it succeeds in truncating.

    SeleniumTestCase inherits LiveServerTestCase, which inherits TransactionTestCase.
    In contrast to TestCase, which wraps tests in "atomic", TransactionTestCase
    truncates the database in the end by calling the "flush" management command. In our
    case, this fails with "ERROR: cannot truncate a table referenced in a foreign key
    constraint". The reason is that TimeseriesRecord is unmanaged, so "flush" doesn't
    truncate it, but "flush" truncates Timeseries, and TimeseriesRecord has a foreign
    key to Timeseries.

    To fix this, we override TransactionTestCase's _fixture_teardown(), ensuring it
    executes TRUNCATE with CASCADE.

    The same result might have been achieved by setting
    TransactionTestCase.available_apps, but this is a private API that is subject to
    change without notice, and, well, go figure.
    """

    def _fixture_teardown(self):
        for db_name in self._databases_names(include_mirrors=False):
            call_command(
                "flush",
                verbosity=0,
                interactive=False,
                database=db_name,
                reset_sequences=False,
                allow_cascade=True,
                inhibit_post_migrate=False,
            )


@skipUnless(getattr(settings, "SELENIUM_WEBDRIVERS", False), "Selenium is unconfigured")
class ListStationsVisibleOnMapTestCase(SeleniumTestCase):

    button_limit_to_map = PageElement(By.ID, "limit-to-map")
    komboti = PageElement(By.XPATH, '//h3//a[text()="Komboti"]')
    agios_athanasios = PageElement(By.XPATH, '//h3//a[text()="Agios Athanasios"]')
    tharbad = PageElement(By.XPATH, '//h3//a[text()="Tharbad"]')

    def setUp(self):
        mommy.make(
            Station,
            name="Komboti",
            geom=Point(x=21.06071, y=39.09518, srid=4326),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="Agios Athanasios",
            geom=Point(x=21.60121, y=39.22440, srid=4326),
            original_srid=4326,
        )
        mommy.make(
            Station,
            name="Tharbad",
            geom=Point(x=-176.48368, y=0.19377, srid=4326),
            original_srid=4326,
        )

    def test_list_stations_visible_on_map(self):
        # Visit site, click on button, and wait until three stations are shown
        self.selenium.get(self.live_server_url)
        self.button_limit_to_map.wait_until_is_displayed()
        self.button_limit_to_map.click()
        self.komboti.wait_until_is_displayed()
        self.agios_athanasios.wait_until_is_displayed()
        self.tharbad.wait_until_is_displayed()

        # Zoom station to an area that covers only two of these stations.
        self.selenium.execute_script(
            "enhydris.map.leafletMap.fitBounds([[39.0, 21.0], [40.0, 22.0]]);"
        )

        # Click on "List stations visible on map"
        self.button_limit_to_map.click()

        # Now only two stations should be displayed
        self.komboti.wait_until_is_displayed()
        self.agios_athanasios.wait_until_is_displayed()
        self.assertFalse(self.tharbad.exists())


@skipUnless(getattr(settings, "SELENIUM_WEBDRIVERS", False), "Selenium is unconfigured")
class ShowOnlySearchedForStationsOnMapTestCase(SeleniumTestCase):

    markers = PageElement(By.CSS_SELECTOR, ".leaflet-marker-pane")

    def setUp(self):
        self.organization = mommy.make(Organization, name="Assassination Bureau, Ltd")
        self._make_station("West", 23.0, 38.0)
        self._make_station("Middle", 23.1, 38.0)
        self._make_station("East", 23.2, 38.0)

    def _make_station(self, name, lon, lat):
        mommy.make(
            Station,
            name=name,
            geom=Point(x=lon, y=lat, srid=4326),
            owner=self.organization,
        )

    def test_list_stations_visible_on_map(self):
        # Visit site and wait until three stations are shown
        self.selenium.get(self.live_server_url)
        num_stations_shown = self._get_num_stations_shown()
        self.assertEqual(num_stations_shown, 3)

        # Search so that only two stations will be found in an area that could include
        # all three stations, and verify only two stations are shown
        self.selenium.get(self.live_server_url + "?q=st")
        num_stations_shown = self._get_num_stations_shown()
        self.assertEqual(num_stations_shown, 2)

    def _get_num_stations_shown(self):
        self.markers.wait_until_exists()
        for i in range(6):
            sleep(0.5)
            result = len(self.markers.find_elements_by_tag_name("img"))
            if result:
                return result


@skipUnless(getattr(settings, "SELENIUM_WEBDRIVERS", False), "Selenium is unconfigured")
class ShowStationOnStationDetailMapTestCase(SeleniumTestCase):

    markers = PageElement(By.CSS_SELECTOR, ".leaflet-marker-pane")

    def setUp(self):
        self.organization = mommy.make(Organization, name="Assassination Bureau, Ltd")
        self._make_station("West", 23.0, 38.0)
        self.station = self._make_station("Middle", 23.001, 38.0)
        self._make_station("East", 23.002, 38.0)

    def _make_station(self, name, lon, lat):
        return mommy.make(
            Station,
            name=name,
            geom=Point(x=lon, y=lat, srid=4326),
            owner=self.organization,
        )

    def test_shows_a_single_station_in_station_detail(self):
        self.selenium.get(
            "{}/stations/{}/".format(self.live_server_url, self.station.id)
        )
        num_stations_shown = self._get_num_stations_shown()
        self.assertEqual(num_stations_shown, 1)

    def _get_num_stations_shown(self):
        self.markers.wait_until_exists()
        for i in range(6):
            sleep(0.5)
            result = len(self.markers.find_elements_by_tag_name("img"))
            if result:
                return result
        return 0


@override_settings(ENHYDRIS_OPEN_CONTENT=True)
class TimeseriesGroupDetailTestCase(TestCase, TimeseriesDataMixin):
    def setUp(self):
        self.create_timeseries()
        self.response = self.client.get(
            f"/stations/{self.station.id}/timeseriesgroups/{self.timeseries_group.id}/"
        )

    def test_timeseries_group_without_timeseries(self):
        self.timeseries_group.timeseries_set.all().delete()
        self.response = self.client.get(
            f"/stations/{self.station.id}/timeseriesgroups/{self.timeseries_group.id}/"
        )
        self.assertNotContains(self.response, "form-item-download")
        self.assertContains(self.response, "alert-info")  # "No data" message

    def test_timeseries_group_with_timeseries(self):
        self.assertContains(self.response, "form-item-download")
        self.assertNotContains(self.response, "alert-info")  # "No data" message

    def test_title(self):
        self.assertContains(
            self.response, "<title>Beauty — Komboti — Enhydris</title>", html=True
        )

    def test_heading(self):
        self.assertContains(
            self.response, "<h2>Beauty <span>(beauton)</span></h2>", html=True
        )

    def test_download_form(self):
        self.assertContains(
            self.response, '<label for="id_timeseries_id_0">Initial</label>', html=True
        )


class DownloadDataTestCase(TestCase, TimeseriesDataMixin):
    def setUp(self):
        self.create_timeseries()

    def _make_request(self, station_id, timeseries_group_id, timeseries_id):
        self.response = self.client.get(
            f"/downloaddata/?station_id={station_id}"
            f"&timeseries_group_id={timeseries_group_id}"
            f"&timeseries_id={timeseries_id}&format=csv"
        )

    def test_redirects(self):
        self._make_request(
            self.station.id, self.timeseries_group.id, self.timeseries.id
        )
        self.assertRedirects(
            self.response,
            expected_url=(
                f"/api/stations/{self.station.id}/timeseriesgroups"
                f"/{self.timeseries_group.id}/timeseries/{self.timeseries.id}"
                "/data/?fmt=csv"
            ),
            fetch_redirect_response=False,
        )

    def test_returns_404_on_total_garbage(self):
        self.response = self.client.get("/downloaddata/?hello=world")
        self.assertEqual(self.response.status_code, 404)

    def test_returns_404_on_garbage_timeseries_group(self):
        self.response = self.client.get(
            "/downloaddata/?station_id=hello&timeseries_group_id=world"
            "&timeseries_id=earth&format=CSV"
        )
        self.assertEqual(self.response.status_code, 404)

    def test_returns_404_on_garbage_station(self):
        self.response = self.client.get(
            "/downloaddata/?station_id=hello&timeseries_group_id=50"
            "&timeseries_id=earth&format=CSV"
        )
        self.assertEqual(self.response.status_code, 404)

    def test_returns_404_on_no_data(self):
        self.response = self.client.get("/downloaddata/")
        self.assertEqual(self.response.status_code, 404)
