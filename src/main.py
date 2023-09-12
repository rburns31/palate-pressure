import json
import sys
import time
import uuid
from math import sqrt
from typing import Any, Dict, List

import requests


class SearchSquare:
    center_latitude: float
    center_longitude: float
    side_len_in_miles: float

    def __init__(
            self,
            center_latitude: float,
            center_longitude: float,
            side_len_in_miles: float,
    ):
        self.center_latitude = center_latitude
        self.center_longitude = center_longitude
        self.side_len_in_miles = side_len_in_miles

    def stringify_coords(self) -> str:
        return f"{self.center_latitude},{self.center_longitude}"

    def get_radius_of_circle_in_meters(self) -> float:
        return self.side_len_in_miles / 2 * sqrt(2) * one_mile_in_km * 1000


file_delimiter: str = "^^^"
southwest_starting_square: SearchSquare = SearchSquare(
    center_latitude=37.512296,
    center_longitude=-77.694100,
    side_len_in_miles=1,
)
northeast_starting_square: SearchSquare = SearchSquare(
    center_latitude=37.667687,
    center_longitude=-77.390260,
    side_len_in_miles=1,
)
latitude_degrees_per_mile: float = 0.014472
longitude_degrees_per_mile: float = 0.018519
one_mile_in_km: float = 1.60934


def pull_for_square(this_square: SearchSquare) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    first_page: bool = True
    next_page_token: str = ""
    params: Dict[str, str] = {
        "location": this_square.stringify_coords(),
        "radius": str(this_square.get_radius_of_circle_in_meters()),
        "keyword": "restaurant",
    }

    while next_page_token or first_page:
        first_page = False

        response: requests.Response = requests.get(
            url="https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "key": "AIzaSyChXlTwUVJNbe4fA2jLgTP2SZOqB_hqkHs",
                **params,
            },
        )
        response_body: Dict[str, Any] = response.json()
        next_page_token = response_body.get("next_page_token", "")
        params = {"pagetoken": next_page_token}

        for place in response_body["results"]:
            results[place["place_id"]] = place

        # Have to inject an artificial wait because Google API's pagination is bad
        if next_page_token:
            time.sleep(3)  # seconds

    print(f"Found {len(results)} places in square {this_square.stringify_coords()}")
    if len(results) < 60:
        return results
    else:
        print("Square had too many places, split it into quadrants and re-process")
        for quadrant in _split_square_into_quadrants(square=this_square):
            results.update(pull_for_square(this_square=quadrant))
        return results


def read_file_and_write_to_google_sheets():
    print("noop todo")


# This function doesn't yet handle if you pass a starting area smaller than one square in either dimension
def _create_starting_search_squares() -> List[SearchSquare]:
    squares: List[SearchSquare] = []

    current_square: SearchSquare = southwest_starting_square
    while current_square.center_latitude <= northeast_starting_square.center_latitude + (
            current_square.side_len_in_miles / 2 * latitude_degrees_per_mile
    ):
        while current_square.center_longitude <= northeast_starting_square.center_longitude + (
                current_square.side_len_in_miles / 2 * longitude_degrees_per_mile
        ):
            squares.append(current_square)
            current_square = _go_one_east(start=current_square)
        current_square = _go_one_north_and_reset_west(start=current_square)

    return squares


def _go_one_east(start: SearchSquare) -> SearchSquare:
    return SearchSquare(
        center_latitude=start.center_latitude,
        center_longitude=start.center_longitude + (start.side_len_in_miles * longitude_degrees_per_mile),
        side_len_in_miles=start.side_len_in_miles,
    )


def _go_one_north_and_reset_west(start: SearchSquare) -> SearchSquare:
    return SearchSquare(
        center_latitude=start.center_latitude + (start.side_len_in_miles * latitude_degrees_per_mile),
        center_longitude=southwest_starting_square.center_longitude,
        side_len_in_miles=start.side_len_in_miles,
    )


def _split_square_into_quadrants(square: SearchSquare) -> List[SearchSquare]:
    latitude_offset: float = square.side_len_in_miles / 4 * latitude_degrees_per_mile
    longitude_offset: float = square.side_len_in_miles / 4 * longitude_degrees_per_mile
    return [
        SearchSquare(
            center_latitude=square.center_latitude - latitude_offset,
            center_longitude=square.center_longitude - longitude_offset,
            side_len_in_miles=square.side_len_in_miles / 2,
        ),
        SearchSquare(
            center_latitude=square.center_latitude + latitude_offset,
            center_longitude=square.center_longitude - longitude_offset,
            side_len_in_miles=square.side_len_in_miles / 2,
        ),
        SearchSquare(
            center_latitude=square.center_latitude - latitude_offset,
            center_longitude=square.center_longitude + longitude_offset,
            side_len_in_miles=square.side_len_in_miles / 2,
        ),
        SearchSquare(
            center_latitude=square.center_latitude + latitude_offset,
            center_longitude=square.center_longitude + longitude_offset,
            side_len_in_miles=square.side_len_in_miles / 2,
        ),
    ]


if __name__ == "__main__":
    # Split up the input area
    starting_squares: List[SearchSquare] = _create_starting_search_squares()

    # For each section, make the api calls with an up-sized circle
    combined_results: Dict[str, Dict[str, Any]] = {}
    square_results: Dict[str, Dict[str, Any]] = {}
    for starting_square in starting_squares:
        square_results = pull_for_square(this_square=starting_square)
        combined_results.update(square_results)

    print(f"Found {len(combined_results)} unique total places in {len(starting_squares)} squares")

    # Write to file
    # for restaurant in response_body["results"]:
    #     rating: int = restaurant["rating"]
    #     num_ratings: int = restaurant["user_ratings_total"]
    #     if rating >= min_rating and num_ratings >= min_num_ratings:
    #         file_contents.append(
    #             f'{restaurant["name"]}{file_delimiter}{rating}{file_delimiter}{num_ratings}\n',
    #         )
    file = open(file=f"output-{uuid.uuid4()}.txt", mode="w")
    file.write(json.dumps(combined_results))
    file.close()
    # return file.name

    # run_args: List[str] = sys.argv
    # if "fresh_pull" == run_args[1]:
    #     file_name: str = pull_and_write_to_file(
    #         min_rating=4.5,
    #         min_num_ratings=200,
    #     )
    #     print(file_name)
    read_file_and_write_to_google_sheets()
