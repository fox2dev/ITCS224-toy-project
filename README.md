# ITCS224-toy-project

Hotel reservation web app built with Flask and local JSON storage.

## Features

- Search room availability by check-in and check-out dates
- View room types (Standard, Deluxe, Suite) with per-night pricing
- Reserve a room with guest name and email
- Receive booking confirmation with reference number (`BK-YYYYMMDD-XXXX`)
- Cancel an existing booking by reference number
- Mobile-friendly interface with large controls

## Tech Stack

- Python 3.10+
- Flask
- Local JSON persistence in `bookings.json`

## Room Inventory and Pricing

- Standard: 10 rooms, $120/night
- Deluxe: 6 rooms, $180/night
- Suite: 4 rooms, $260/night

## Booking Rules

- Check-out must be after check-in
- Same-day stay is not allowed
- Past dates are not allowed

## Run Locally

1. Create and activate a virtual environment.
2. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

3. Start the app:

	```bash
	flask --app app run --debug
	```

4. Open the local URL shown in your terminal.

## Data Storage

- Bookings are stored in `bookings.json` (one record per booking).
- Cancellations are hard-delete operations from the active booking list.