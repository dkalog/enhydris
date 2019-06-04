import csv
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

_station_list_csv_headers = [
    "id",
    "Name",
    "Short name",
    "Type",
    "Owner",
    "Start date",
    "End date",
    "Abscissa",
    "Ordinate",
    "SRID",
    "Altitude",
    "SRID",
    "Water basin",
    "Water division",
    "Political division",
    "Automatic",
    "Remarks",
    "Last modified",
]


def _station_csv(s):
    return [
        s.id,
        s.name,
        s.short_name,
        "+".join([t.descr for t in s.stype.all()]),
        s.owner,
        s.start_date,
        s.end_date,
        s.original_abscissa(),
        s.original_ordinate(),
        s.original_srid,
        s.altitude,
        s.water_basin.name if s.water_basin else "",
        s.water_division.name if s.water_division else "",
        s.political_division.name if s.political_division else "",
        s.is_automatic,
        s.remarks,
        s.last_modified,
    ]


_instrument_list_csv_headers = [
    "id",
    "Station",
    "Type",
    "Name",
    "Manufacturer",
    "Model",
    "Start date",
    "End date",
    "Remarks",
]


def _instrument_csv(i):
    return [
        i.id,
        i.station.id,
        i.type.descr if i.type else "",
        i.name,
        i.manufacturer,
        i.model,
        i.start_date,
        i.end_date,
        i.remarks,
    ]


_timeseries_list_csv_headers = [
    "id",
    "Station",
    "Instrument",
    "Variable",
    "Unit",
    "Name",
    "Precision",
    "Time zone",
    "Time step",
    "Nom. Offs. Min.",
    "Nom. Offs. Mon.",
    "Act. Offs. Min.",
    "Act. Offs.  Mon.",
    "Remarks",
]


def _timeseries_csv(t):
    return [
        t.id,
        t.gentity.id,
        t.instrument.id if t.instrument else "",
        t.variable.descr if t.variable else "",
        t.unit_of_measurement.symbol,
        t.name,
        t.precision,
        t.time_zone.code,
        t.time_step.descr if t.time_step else "",
        t.timestamp_rounding_minutes,
        t.timestamp_rounding_months,
        t.timestamp_offset_minutes,
        t.timestamp_offset_months,
    ]


def prepare_csv(queryset):
    with BytesIO() as result:
        with ZipFile(result, "w", ZIP_DEFLATED) as zipfile:
            with StringIO() as stations_csv:
                csvwriter = csv.writer(stations_csv)
                csvwriter.writerow(_station_list_csv_headers)
                for station in queryset:
                    csvwriter.writerow(_station_csv(station))
                zipfile.writestr("stations.csv", stations_csv.getvalue())

            with StringIO() as instruments_csv:
                csvwriter = csv.writer(instruments_csv)
                csvwriter.writerow(_instrument_list_csv_headers)
                for station in queryset:
                    for instrument in station.instrument_set.all():
                        csvwriter.writerow(_instrument_csv(instrument))
                zipfile.writestr("instruments.csv", instruments_csv.getvalue())

            with StringIO() as timeseries_csv:
                csvwriter = csv.writer(timeseries_csv)
                csvwriter.writerow(_timeseries_list_csv_headers)
                for station in queryset:
                    for timeseries in station.timeseries.order_by("instrument__id"):
                        csvwriter.writerow(_timeseries_csv(timeseries))
                zipfile.writestr("timeseries.csv", timeseries_csv.getvalue())

        return result.getvalue()
