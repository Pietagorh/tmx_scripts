"""
Checks for all UId clashes on tmnf-x
"""
import json
from os.path import exists
import requests


UID_TABLE_FILE = "./uid_table.json"
ONLY_PRINT_UNFINISHED = True


type UIdTable = dict[str, list[int]]
type ResponseJson = {"More": bool, "Results": list[{"TrackId": int, "UId": str}]}


def open_uid_table() -> (UIdTable, int | None):
    """
    Opens potential existing table
    """
    if not exists(UID_TABLE_FILE):
        return {}, None

    with open(UID_TABLE_FILE, "r", encoding="utf-8") as f:
        res = json.loads(f.read())

    return res["Table"], res["LastTrackId"]


def save_uid_table(table: UIdTable, last_track_id: int):
    """
    Saves table
    """
    with open(UID_TABLE_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps({"Table": table, "LastTrackId": last_track_id}, indent=4))


def request_new_tracks(after: int | None) -> ResponseJson:
    """
    Performs a track search for new track ids, uids, and upload date, sorted by asc upload date
    Based on https://api2.mania.exchange/Method/Index/43
    """
    url = "https://tmnf.exchange/api/tracks?fields=TrackId,UId,UploadedAt&order1=1&count=10000"
    if after is not None:
        url += f"&after={after}"

    return requests.get(url, timeout=None).json()


def get_upload_date(track_id: int) -> str:
    """
    Get upload date of a track
    """
    url = f"https://tmnf.exchange/api/tracks?fields=UploadedAt&count=1&id={track_id}"
    return requests.get(url, timeout=None).json()["Results"][0]["UploadedAt"]


def in_hasrecord(track_id: int) -> bool:
    """
    Checks if a map has no records
    """
    url = f"https://tmnf.exchange/api/tracks?fields=TrackId&count=1&inhasrecord=1&id={track_id}"
    return len(requests.get(url, timeout=None).json()["Results"]) != 0


def populate_table(uid_table: UIdTable, last_track_id: int | None) -> None:
    """
    Populates the table with new tracks
    """
    more = True
    while more:
        tracks = request_new_tracks(last_track_id)
        more = tracks["More"]
        results = tracks["Results"]

        if not results:
            break

        for result in results:
            u_id = result["UId"]
            last_track_id = track_id = result["TrackId"]

            if u_id in uid_table:
                uid_table[u_id].append(track_id)
            else:
                uid_table[u_id] = [track_id]

        save_uid_table(uid_table, last_track_id)
        print(f"Checked until {results[-1]['UploadedAt']}")


def find_duplicates(table: UIdTable) -> list[list[int]]:
    """
    Finds duplicates in the full table
    """
    return [sorted(track_ids) for _, track_ids in table.items() if len(track_ids) != 1]


def main():
    """
    Requests all new tracks to tmnf-x and checks for duplicates
    """
    uid_table, last_track_id = open_uid_table()

    print(f"Starting search from {get_upload_date(last_track_id)}")
    populate_table(uid_table, last_track_id)
    print("UId table now up to date")

    for duplicates in find_duplicates(uid_table):
        # all replays go to the greatest track id
        redirect = duplicates[-1]
        unreachable = duplicates[:-1]

        if ONLY_PRINT_UNFINISHED:
            for track_id in unreachable:
                if not in_hasrecord(track_id):
                    print(f"{track_id} -> {redirect}")
        else:
            print(f"{', '.join(str(d) for d in duplicates[:-1])} -> {duplicates[-1]}")


if __name__ == "__main__":
    main()
