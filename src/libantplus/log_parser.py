"""Parsing tools for messages logs in csv format."""
import ast
import csv
import json


def parse(filename):
    """Parse message log file."""
    with open(filename, encoding="UTF-8") as file, open(
        filename + "-parsed", "w", encoding="UTF-8"
    ) as out_file:
        fieldnames = ["channel", "Id", "info", "extended_data", "parsed_extended_data"]
        reader = csv.DictReader(
            file,
            fieldnames=fieldnames,
        )
        out_fieldnames = fieldnames + [
            "page_number",
            "channel_id",
            "device_number",
            "device_type_id",
            "transmission_type",
            "timestamp",
        ]
        out_fieldnames.remove("extended_data")
        out_fieldnames.remove("parsed_extended_data")
        writer = csv.DictWriter(
            out_file, fieldnames=out_fieldnames, extrasaction="ignore", restval=""
        )

        for r in reader:
            string = r["parsed_extended_data"].replace("'", '"')
            out_row = r
            if r["Id"] in ["Id.BroadcastData", "Id.AcknowledgedData"]:
                out_row["page_number"] = ast.literal_eval(r["info"])[1]
            if string:
                string_dict = json.loads(string)
                out_row["channel_id"] = string_dict["channel_id"]
                out_row["device_number"] = string_dict["channel_id"]["device_number"]
                out_row["device_type_id"] = string_dict["channel_id"]["device_type_id"]
                out_row["transmission_type"] = string_dict["channel_id"][
                    "transmission_type"
                ]
                out_row["timestamp"] = string_dict["timestamp"]

            writer.writerow(out_row)


def filter_by_channel_id(filename):
    """Filter parsed log by channel id."""
    with open(filename, encoding="UTF-8") as file:
        fieldnames = [
            "channel",
            "Id",
            "info",
            "page_number",
            "channel_id",
            "device_number",
            "device_type_id",
            "transmission_type",
            "timestamp",
            "interval",
        ]
        reader = csv.DictReader(
            file,
            fieldnames=fieldnames,
        )

        channel_ids = []
        files = []
        writers = []
        last_timestamps = []
        i = 0

        for r in reader:
            if r["channel_id"] not in channel_ids:
                channel_ids.append(r["channel_id"])
                file = open(  # noqa PLR732
                    filename + "-filtered-" + str(i), "w", encoding="UTF-8"
                )
                writer = csv.DictWriter(
                    file, fieldnames=fieldnames, extrasaction="ignore", restval=""
                )
                i += 1
                files.append(file)
                writers.append(writer)
                last_timestamps.append(None)
                writer.writeheader()

            writer = writers[channel_ids.index(r["channel_id"])]
            try:
                if last_timestamps[channel_ids.index(r["channel_id"])] is not None:
                    interval = int(r["timestamp"]) - int(
                        last_timestamps[channel_ids.index(r["channel_id"])]
                    )
                    if interval < 0:
                        interval += 2**16
                    r["interval"] = interval
                last_timestamps[channel_ids.index(r["channel_id"])] = r["timestamp"]
            except ValueError:
                pass
            writer.writerow(r)
        for file in files:
            file.close()


def view_page_number(
    filename, page_number, start=0, end=9, to_int=False, signed=False, byteorder="big"
):
    """Print rows with specific page number to stdout."""
    with open(filename, encoding="UTF-8") as file:
        fieldnames = [
            "channel",
            "Id",
            "info",
            "page_number",
            "channel_id",
            "device_number",
            "device_type_id",
            "transmission_type",
            "timestamp",
            "interval",
        ]
        reader = csv.DictReader(
            file,
            fieldnames=fieldnames,
        )
        for r in reader:
            if r["page_number"] == str(page_number):
                out = ast.literal_eval(r["info"])[start:end]
                if to_int:
                    out = int.from_bytes(out, signed=signed, byteorder=byteorder)
                print(out)
