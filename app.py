import json
import random
from datetime import date, datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key"

BOOKINGS_FILE = Path(__file__).parent / "bookings.json"

ROOMS = {
	"Standard": {"price": 120, "inventory": 10},
	"Deluxe": {"price": 180, "inventory": 6},
	"Suite": {"price": 260, "inventory": 4},
}


def load_bookings() -> list[dict]:
	if not BOOKINGS_FILE.exists():
		return []

	try:
		with BOOKINGS_FILE.open("r", encoding="utf-8") as file:
			data = json.load(file)
	except json.JSONDecodeError:
		return []

	if isinstance(data, list):
		return data
	return []


def save_bookings(bookings: list[dict]) -> None:
	with BOOKINGS_FILE.open("w", encoding="utf-8") as file:
		json.dump(bookings, file, indent=2)


def parse_stay_dates(check_in_raw: str, check_out_raw: str) -> tuple[date, date] | tuple[None, None]:
	try:
		check_in = date.fromisoformat(check_in_raw)
		check_out = date.fromisoformat(check_out_raw)
	except (TypeError, ValueError):
		return None, None

	return check_in, check_out


def validate_stay_dates(check_in: date | None, check_out: date | None) -> str | None:
	if check_in is None or check_out is None:
		return "Please enter valid check-in and check-out dates."

	if check_in < date.today():
		return "Check-in date cannot be in the past."

	if check_out <= check_in:
		return "Check-out date must be after check-in date."

	return None


def bookings_overlap(existing: dict, check_in: date, check_out: date) -> bool:
	existing_check_in = date.fromisoformat(existing["check_in"])
	existing_check_out = date.fromisoformat(existing["check_out"])
	return existing_check_in < check_out and existing_check_out > check_in


def get_availability(check_in: date, check_out: date) -> list[dict]:
	bookings = load_bookings()
	availability = []

	for room_type, details in ROOMS.items():
		taken = 0
		for booking in bookings:
			if booking.get("room_type") != room_type:
				continue
			if bookings_overlap(booking, check_in, check_out):
				taken += 1

		available = max(details["inventory"] - taken, 0)
		availability.append(
			{
				"room_type": room_type,
				"price": details["price"],
				"inventory": details["inventory"],
				"available": available,
			}
		)

	return availability


def generate_reference(existing_references: set[str]) -> str:
	prefix = f"BK-{datetime.now().strftime('%Y%m%d')}"
	while True:
		candidate = f"{prefix}-{random.randint(1000, 9999)}"
		if candidate not in existing_references:
			return candidate


@app.get("/")
def index():
	return render_template("index.html")


@app.post("/search")
def search():
	check_in_raw = request.form.get("check_in", "").strip()
	check_out_raw = request.form.get("check_out", "").strip()
	check_in, check_out = parse_stay_dates(check_in_raw, check_out_raw)

	error = validate_stay_dates(check_in, check_out)
	if error:
		flash(error, "error")
		return redirect(url_for("index"))

	availability = get_availability(check_in, check_out)
	return render_template(
		"results.html",
		check_in=check_in.isoformat(),
		check_out=check_out.isoformat(),
		availability=availability,
	)


@app.post("/book")
def book():
	room_type = request.form.get("room_type", "").strip()
	guest_name = request.form.get("guest_name", "").strip()
	guest_email = request.form.get("guest_email", "").strip()
	check_in_raw = request.form.get("check_in", "").strip()
	check_out_raw = request.form.get("check_out", "").strip()

	check_in, check_out = parse_stay_dates(check_in_raw, check_out_raw)
	error = validate_stay_dates(check_in, check_out)
	if error:
		flash(error, "error")
		return redirect(url_for("index"))

	if room_type not in ROOMS:
		flash("Please choose a valid room type.", "error")
		availability = get_availability(check_in, check_out)
		return render_template(
			"results.html",
			check_in=check_in.isoformat(),
			check_out=check_out.isoformat(),
			availability=availability,
		)

	if not guest_name or not guest_email:
		flash("Guest name and email are required.", "error")
		availability = get_availability(check_in, check_out)
		return render_template(
			"results.html",
			check_in=check_in.isoformat(),
			check_out=check_out.isoformat(),
			availability=availability,
		)

	availability = get_availability(check_in, check_out)
	selected = next((room for room in availability if room["room_type"] == room_type), None)
	if not selected or selected["available"] < 1:
		flash("Selected room type is no longer available for these dates.", "error")
		return render_template(
			"results.html",
			check_in=check_in.isoformat(),
			check_out=check_out.isoformat(),
			availability=availability,
		)

	nights = (check_out - check_in).days
	price_per_night = ROOMS[room_type]["price"]
	total_price = nights * price_per_night

	bookings = load_bookings()
	existing_references = {booking.get("reference", "") for booking in bookings}
	reference = generate_reference(existing_references)

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
		"created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
	}

	bookings.append(booking)
	save_bookings(bookings)

	return render_template("confirmation.html", action="booked", booking=booking)


@app.post("/cancel")
def cancel():
	reference = request.form.get("reference", "").strip()
	if not reference:
		flash("Please enter a booking reference.", "error")
		return redirect(url_for("index"))

	bookings = load_bookings()
	booking_to_cancel = next((item for item in bookings if item.get("reference") == reference), None)

	if booking_to_cancel is None:
		flash("Booking reference not found.", "error")
		return redirect(url_for("index"))

	updated_bookings = [item for item in bookings if item.get("reference") != reference]
	save_bookings(updated_bookings)

	return render_template("confirmation.html", action="canceled", booking=booking_to_cancel)


if __name__ == "__main__":
	app.run(debug=True)
