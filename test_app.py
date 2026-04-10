import json
import re
import unittest
from datetime import date, timedelta

import app as hotel_app


class HotelAppTests(unittest.TestCase):
    def setUp(self):
        self.client = hotel_app.app.test_client()
        self.bookings_file = hotel_app.BOOKINGS_FILE
        self._backup = self.bookings_file.read_text(encoding="utf-8") if self.bookings_file.exists() else None

    def tearDown(self):
        if self._backup is None:
            self.bookings_file.unlink(missing_ok=True)
        else:
            self.bookings_file.write_text(self._backup, encoding="utf-8")

    def _reset_bookings(self, data):
        self.bookings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _future_dates(self, start_offset_days=3, nights=2):
        check_in = date.today() + timedelta(days=start_offset_days)
        check_out = check_in + timedelta(days=nights)
        return check_in.isoformat(), check_out.isoformat()

    def test_search_valid_dates(self):
        self._reset_bookings([])
        check_in, check_out = self._future_dates()
        response = self.client.post("/search", data={"check_in": check_in, "check_out": check_out})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Availability", response.data)

    def test_search_rejects_same_day_stay(self):
        self._reset_bookings([])
        check_in, _ = self._future_dates()
        response = self.client.post(
            "/search",
            data={"check_in": check_in, "check_out": check_in},
            follow_redirects=True,
        )

        self.assertIn(b"Check-out date must be after check-in date.", response.data)

    def test_booking_success_persists_record(self):
        self._reset_bookings([])
        check_in, check_out = self._future_dates()
        response = self.client.post(
            "/book",
            data={
                "room_type": "Standard",
                "guest_name": "Alice",
                "guest_email": "alice@example.com",
                "check_in": check_in,
                "check_out": check_out,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Booking Confirmed", response.data)

        bookings = json.loads(self.bookings_file.read_text(encoding="utf-8"))
        self.assertEqual(len(bookings), 1)
        booking = bookings[0]
        self.assertRegex(booking["reference"], r"^BK-\d{8}-\d{4}$")
        self.assertEqual(booking["total_price"], booking["nights"] * booking["price_per_night"])

    def test_cancel_existing_booking(self):
        check_in, check_out = self._future_dates()
        self._reset_bookings(
            [
                {
                    "reference": "BK-20990101-1234",
                    "guest_name": "Seed",
                    "guest_email": "seed@example.com",
                    "room_type": "Deluxe",
                    "check_in": check_in,
                    "check_out": check_out,
                    "price_per_night": 180,
                    "nights": 2,
                    "total_price": 360,
                    "created_at": "2099-01-01T12:00:00",
                }
            ]
        )

        response = self.client.post("/cancel", data={"reference": "BK-20990101-1234"})
        self.assertIn(b"Booking Canceled", response.data)

        bookings = json.loads(self.bookings_file.read_text(encoding="utf-8"))
        self.assertEqual(bookings, [])

    def test_inventory_counts_one_overlapping_booking_as_one_room(self):
        check_in, check_out = self._future_dates()
        self._reset_bookings(
            [
                {
                    "reference": "BK-20990101-1111",
                    "guest_name": "Seed",
                    "guest_email": "seed@example.com",
                    "room_type": "Standard",
                    "check_in": check_in,
                    "check_out": check_out,
                    "price_per_night": hotel_app.ROOMS["Standard"]["price"],
                    "nights": 2,
                    "total_price": 240,
                    "created_at": "2099-01-01T00:00:00",
                }
            ]
        )

        response = self.client.post("/search", data={"check_in": check_in, "check_out": check_out})
        html = response.data.decode("utf-8", errors="ignore")
        counts = re.findall(r"\d+ of \d+ rooms available", html)

        self.assertIn("9 of 10 rooms available", counts)


if __name__ == "__main__":
    unittest.main()