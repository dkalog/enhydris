import mimetypes
import os
from io import StringIO
from wsgiref.util import FileWrapper

from django.db import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

import iso8601
import pandas as pd
from htimeseries import HTimeseries

from enhydris import models
from enhydris.views_common import StationListViewMixin

from . import permissions, serializers
from .csv import prepare_csv


class StationViewSet(StationListViewMixin, ModelViewSet):
    serializer_class = serializers.StationSerializer

    def get_permissions(self):
        if self.action == "create":
            pc = [permissions.CanCreateStation]
        else:
            pc = [permissions.CanEditOrReadOnly]
        return [x() for x in pc]

    def list(self, request):
        response = super().list(request)
        response.data["bounding_box"] = self._get_bounding_box()
        return response

    @action(detail=False, methods=["get"])
    def csv(self, request):
        data = prepare_csv(self.get_queryset())
        response = HttpResponse(data, content_type="application/zip")
        response["Content-Disposition"] = "attachment; filename=data.zip"
        response["Content-Length"] = len(data)
        return response


class WaterDivisionViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.WaterDivisionSerializer
    queryset = models.WaterDivision.objects.all()


class GentityAltCodeTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.GentityAltCodeTypeSerializer
    queryset = models.GentityAltCodeType.objects.all()


class OrganizationViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.OrganizationSerializer
    queryset = models.Organization.objects.all()


class PersonViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.PersonSerializer
    queryset = models.Person.objects.all()


class StationTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.StationTypeSerializer
    queryset = models.StationType.objects.all()


class TimeZoneViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.TimeZoneSerializer
    queryset = models.TimeZone.objects.all()


class PoliticalDivisionViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.PoliticalDivisionSerializer
    queryset = models.PoliticalDivision.objects.all()


class IntervalTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.IntervalTypeSerializer
    queryset = models.IntervalType.objects.all()


class FileTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.FileTypeSerializer
    queryset = models.FileType.objects.all()


class EventTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.EventTypeSerializer
    queryset = models.EventType.objects.all()


class InstrumentTypeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.InstrumentTypeSerializer
    queryset = models.InstrumentType.objects.all()


class WaterBasinViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.WaterBasinSerializer
    queryset = models.WaterBasin.objects.all()


class TimeStepViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.TimeStepSerializer
    queryset = models.TimeStep.objects.all()


class VariableViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.VariableSerializer
    queryset = models.Variable.objects.all()


class UnitOfMeasurementViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.UnitOfMeasurementSerializer
    queryset = models.UnitOfMeasurement.objects.all()


class GentityAltCodeViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.GentityAltCodeSerializer

    def get_queryset(self):
        return models.GentityAltCode.objects.filter(
            gentity_id=self.kwargs["station_id"]
        )


class GentityEventViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.GentityEventSerializer

    def get_queryset(self):
        return models.GentityEvent.objects.filter(gentity_id=self.kwargs["station_id"])


class OverseerViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.OverseerSerializer

    def get_queryset(self):
        return models.Overseer.objects.filter(station_id=self.kwargs["station_id"])


class InstrumentViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.InstrumentSerializer

    def get_queryset(self):
        return models.Instrument.objects.filter(station_id=self.kwargs["station_id"])


class GentityFileViewSet(ReadOnlyModelViewSet):
    serializer_class = serializers.GentityFileSerializer

    def get_permissions(self):
        if self.action == "content":
            pc = [permissions.CanAccessGentityFileContent]
        else:
            pc = [permissions.CanEditOrReadOnly]
        return [x() for x in pc]

    def get_queryset(self):
        return models.GentityFile.objects.filter(gentity_id=self.kwargs["station_id"])

    @action(detail=True, methods=["get"])
    def content(self, request, pk=None, *, station_id):
        gfile = self.get_object()
        self.check_object_permissions(request, gfile)
        try:
            gfile_content_file = gfile.content.file
            filename = gfile_content_file.name
            wrapper = FileWrapper(open(filename, "rb"))
        except (ValueError, IOError):
            raise Http404
        download_name = gfile.content.name.split("/")[-1]
        content_type = mimetypes.guess_type(filename)[0]
        response = HttpResponse(content_type=content_type)
        response["Content-Length"] = os.path.getsize(filename)
        response["Content-Disposition"] = "attachment; filename=" + download_name

        for chunk in wrapper:
            response.write(chunk)

        return response


class TimeseriesViewSet(ModelViewSet):
    queryset = models.Timeseries.objects.all()
    serializer_class = serializers.TimeseriesSerializer

    def get_permissions(self):
        if self.action in ("data", "bottom"):
            pc = [permissions.CanAccessTimeseriesData]
        else:
            pc = [permissions.CanEditOrReadOnly]
        return [x() for x in pc]

    def get_queryset(self):
        return models.Timeseries.objects.filter(gentity_id=self.kwargs["station_id"])

    def create(self, request, *args, **kwargs):
        """Redefine create, checking permissions and gentity_id.

        Django-rest-framework does not do object-level permission when
        creating a new object, so we have to completely customize the create
        method. In addition, we check that the gentity_id specified in the data
        is the same as the station_id in the URL.
        """
        # Get the data
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check permissions
        try:
            gentity_id = int(serializer.get_initial()["gentity"])
        except ValueError:
            raise Http404
        station = get_object_or_404(models.Station, id=gentity_id)
        if not request.user.is_authenticated:
            return Response("Unauthorized", status=status.HTTP_401_UNAUTHORIZED)
        if not request.user.has_perm("enhydris.change_station", station):
            return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)

        # Check the correctness of gentity_id
        if str(gentity_id) != self.kwargs["station_id"]:
            return Response("Wrong gentity_id", status=status.HTTP_400_BAD_REQUEST)

        # All checks passed, call inherited method to do the actual work.
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=["get", "post"])
    def data(self, request, pk=None, *, station_id):
        if request.method == "GET":
            return self._get_data(request, pk)
        elif request.method == "POST":
            return self._post_data(request, pk)

    @action(detail=True, methods=["get"])
    def bottom(self, request, pk=None, *, station_id):
        ts = get_object_or_404(models.Timeseries, pk=pk)
        self.check_object_permissions(request, ts)
        response = HttpResponse(content_type="text/plain")
        response.write(ts.get_last_line())
        return response

    def _get_data(self, request, pk, format=None):
        timeseries = get_object_or_404(models.Timeseries, pk=int(pk))
        self.check_object_permissions(request, timeseries)

        tz = timeseries.time_zone.as_tzinfo
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        start_date = self._get_date_from_string(start_date, tz)
        end_date = self._get_date_from_string(end_date, tz)

        # The time series data are naive, so we also make start_date and end_date naive.
        if start_date:
            start_date = start_date.replace(tzinfo=None)
        if end_date:
            end_date = end_date.replace(tzinfo=None)

        ahtimeseries = timeseries.get_data(start_date=start_date, end_date=end_date)
        response = HttpResponse(content_type="text/plain; charset=utf-8")
        if request.GET.get("fmt", "").lower() == "hts":
            fmt = HTimeseries.FILE
        else:
            fmt = HTimeseries.TEXT
        ahtimeseries.write(response, format=fmt)
        return response

    def _post_data(self, request, pk, format=None):
        try:
            atimeseries = get_object_or_404(models.Timeseries, pk=int(pk))
            self.check_object_permissions(request, atimeseries)
            atimeseries.append_data(StringIO(request.data["timeseries_records"]))
            return HttpResponse(status=status.HTTP_204_NO_CONTENT)
        except (IntegrityError, iso8601.ParseError) as e:
            return HttpResponse(
                status=status.HTTP_400_BAD_REQUEST,
                content=str(e),
                content_type="text/plain",
            )

    def _get_date_from_string(self, adate, tz):
        if not adate:
            return None
        result = iso8601.parse_date(adate, default_timezone=tz)
        if result.isoformat() < pd.Timestamp.min.isoformat():
            result = pd.Timestamp.min
        if result.isoformat() > pd.Timestamp.max.isoformat():
            result = pd.Timestamp.max
        return result
