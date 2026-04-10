from __future__ import annotations

import json
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from secrets import randbelow
from typing import Any

from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-only-secret-key"

BOOKINGS_FILE = Path(__file__).with_name("bookings.json")
ROOM_TYPES: dict[str, dict[str, int]] = {
	"Standard": {"price": 120, "inventory": 10},
	"Deluxe": {"price": 180, "inventory": 6},
	"Suite": {"price": 260, "inventory": 4},
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ensure_bookings_file() -> None:
	if BOOKINGS_FILE.exists():
		return
	BOOKINGS_FILE.write_text("[]\n", encoding="utf-8")


def load_bookings() -> list[dict[str, Any]]:
	ensure_bookings_file()
	try:
		with BOOKINGS_FILE.open("r", encoding="utf-8") as f:
			payload = json.load(f)
	except json.JSONDecodeError as exc:
		raise RuntimeError("bookings.json is corrupted and cannot be read.") from exc

	if not isinstance(payload, list):
		raise RuntimeError("bookings.json must contain a top-level list of bookings.")
	return payload


def save_bookings(bookings: list[dict[str, Any]]) -> None:
	directory = BOOKINGS_FILE.parent
	with tempfile.NamedTemporaryFile(
		mode="w", encoding="utf-8", dir=directory, delete=False
	) as temp_file:
		json.dump(bookings, temp_file, indent=2)
		temp_file.write("\n")
		temp_name = temp_file.name

	Path(temp_name).replace(BOOKINGS_FILE)


def parse_iso_date(raw: str) -> date | None:
	try:
		return datetime.strptime(raw, "%Y-%m-%d").date()
	except ValueError:
		return None


def validate_stay_dates(check_in_raw: str, check_out_raw: str) -> tuple[date, date] | None:
	check_in = parse_iso_date(check_in_raw)
	check_out = parse_iso_date(check_out_raw)
	today = date.today()

	if not check_in or not check_out:
		flash("Please provide valid check-in and check-out dates.", "error")
		return None
	if check_in < today or check_out < today:
		flash("Dates in the past are not allowed.", "error")
		return None
	if check_out <= check_in:
		flash("Check-out must be after check-in.", "error")
		return None

	return check_in, check_out


def stays_overlap(
	existing_check_in: date,
	existing_check_out: date,
	new_check_in: date,
	new_check_out: date,
) -> bool:
	return not (existing_check_out <= new_check_in or existing_check_in >= new_check_out)


def count_booked_rooms(
	room_type: str,
	check_in: date,
	check_out: date,
	bookings: list[dict[str, Any]],
) -> int:
	count = 0
	for booking in bookings:
		if booking.get("room_type") != room_type:
			continue

		existing_check_in = parse_iso_date(str(booking.get("check_in", "")))
		existing_check_out = parse_iso_date(str(booking.get("check_out", "")))
		if not existing_check_in or not existing_check_out:
			continue

		if stays_overlap(existing_check_in, existing_check_out, check_in, check_out):
			count += 1
	return count


def availability_for_dates(
	check_in: date,
	check_out: date,
	bookings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
	availability: list[dict[str, Any]] = []
	for room_type, config in ROOM_TYPES.items():
		booked = count_booked_rooms(room_type, check_in, check_out, bookings)
		remaining = max(config["inventory"] - booked, 0)
		availability.append(
			{
				"room_type": room_type,
				"price": config["price"],
				"inventory": config["inventory"],
				"available": remaining,
			}
		)
	return availability


def generate_reference(existing_refs: set[str]) -> str:
	prefix = date.today().strftime("BK-%Y%m%d-")
	for _ in range(10000):
		suffix = f"{randbelow(10000):04d}"
		candidate = f"{prefix}{suffix}"
		if candidate not in existing_refs:
			return candidate
	raise RuntimeError("Unable to generate a unique booking reference.")


@app.get("/")
def index() -> str:
	return render_template("index.html")


@app.post("/search")
def search() -> str:
	check_in_raw = request.form.get("check_in", "").strip()
	check_out_raw = request.form.get("check_out", "").strip()

	validated_dates = validate_stay_dates(check_in_raw, check_out_raw)
	if not validated_dates:
		return redirect(url_for("index"))

	check_in, check_out = validated_dates
	try:
		bookings = load_bookings()
	except RuntimeError as exc:
		flash(str(exc), "error")
		return redirect(url_for("index"))

	availability = availability_for_dates(check_in, check_out, bookings)
	return render_template(
		"results.html",
		check_in=check_in.isoformat(),
		check_out=check_out.isoformat(),
		availability=availability,
	)


@app.post("/book")
def book() -> str:
	check_in_raw = request.form.get("check_in", "").strip()
	check_out_raw = request.form.get("check_out", "").strip()
	room_type = request.form.get("room_type", "").strip()
	guest_name = request.form.get("guest_name", "").strip()
	guest_email = request.form.get("guest_email", "").strip()

	validated_dates = validate_stay_dates(check_in_raw, check_out_raw)
	if not validated_dates:
		return redirect(url_for("index"))

	if room_type not in ROOM_TYPES:
		flash("Selected room type is invalid.", "error")
		return redirect(url_for("index"))
	if not guest_name:
		flash("Guest name is required.", "error")
		return redirect(url_for("index"))
	if not guest_email or not EMAIL_PATTERN.match(guest_email):
		flash("Please provide a valid email address.", "error")
		return redirect(url_for("index"))

	check_in, check_out = validated_dates

	try:
		bookings = load_bookings()
	except RuntimeError as exc:
		flash(str(exc), "error")
		return redirect(url_for("index"))

	availability = availability_for_dates(check_in, check_out, bookings)
	selected_room = next(item for item in availability if item["room_type"] == room_type)
	if selected_room["available"] < 1:
		flash(f"No {room_type} rooms are available for those dates.", "error")
		return redirect(url_for("index"))

	existing_refs = {str(item.get("reference", "")) for item in bookings}
	reference = generate_reference(existing_refs)
	nights = (check_out - check_in).days
	price_per_night = ROOM_TYPES[room_type]["price"]
	total_price = nights * price_per_night

	booking = {
		"reference": reference,
		"guest_name": guest_name,
		"guest_email": guest_email,
		"room_type": room_type,
		"check_in": check_in.isoformat(),
		"check_out": check_out.isoformat(),
		"price_per_night": price_per_night,
		"nights": nights,
		"total_price": total_price,
		"created_at": datetime.now().isoformat(timespec="seconds"),
	}
	bookings.append(booking)
	save_bookings(bookings)

	return render_template("confirmation.html", booking=booking, action="booked")


@app.post("/cancel")
def cancel() -> str:
	reference = request.form.get("reference", "").strip().upper()
	if not reference:
		flash("Please enter a booking reference to cancel.", "error")
		return redirect(url_for("index"))

	try:
		bookings = load_bookings()
	except RuntimeError as exc:
		flash(str(exc), "error")
		return redirect(url_for("index"))

	remaining = [item for item in bookings if str(item.get("reference", "")).upper() != reference]
	if len(remaining) == len(bookings):
		flash("Booking reference not found.", "error")
		return redirect(url_for("index"))

	save_bookings(remaining)
	return render_template("confirmation.html", booking={"reference": reference}, action="canceled")


if __name__ == "__main__":
	app.run(debug=True)
