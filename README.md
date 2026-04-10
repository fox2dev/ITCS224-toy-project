# ITCS224 Toy Project

A lightweight hotel reservation web app built with Flask and local JSON storage.

The app supports room search, booking, and cancellation with a mobile-friendly interface.

## Features

- Search room availability by check-in and check-out date
- View room options with per-night prices and remaining inventory
- Complete a booking using guest name and email
- Receive a confirmation page with a generated reference number in the format `BK-YYYYMMDD-XXXX`
- Cancel an existing booking with a reference number
- Display validation and error messages for invalid input or unavailable rooms

## Tech Stack

- Python 3.10+
- Flask 3.x
- JSON file persistence (`bookings.json`)
- HTML templates + CSS (`templates/`, `static/style.css`)

## Room Types

- Standard: 10 rooms, $120/night
- Deluxe: 6 rooms, $180/night
- Suite: 4 rooms, $260/night

## Booking Rules

- Dates must be valid ISO date values from the form inputs
- Check-in date cannot be in the past
- Check-out date must be after check-in date
- Room type must be valid and currently available
- Guest name and guest email are required for booking

## Getting Started

1. Clone the repository and move into the project folder.
2. Create a virtual environment:

```bash
python -m venv .venv
```

3. Activate the environment:

```bash
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the app:

```bash
flask --app app run --debug
```

6. Open the local URL printed in the terminal (usually http://127.0.0.1:5000).

## How to Use

1. On the home page, enter check-in and check-out dates and submit the search form.
2. On the availability page, choose a room type and provide guest details.
3. Submit to complete the reservation and view the confirmation summary.
4. To cancel, return to the home page and submit a booking reference in the cancel form.

## Running Tests

Run the unit test suite with:

```bash
python -m unittest -v
```

The tests in `test_app.py` cover:

- Valid availability search flow
- Date validation behavior
- Successful booking persistence
- Canceling an existing booking
- Inventory calculation for overlapping bookings

## Project Structure

```text
.
|-- app.py
|-- bookings.json
|-- requirements.txt
|-- test_app.py
|-- static/
|   `-- style.css
`-- templates/
    |-- base.html
    |-- confirmation.html
    |-- index.html
    `-- results.html
```

## Routes

- `GET /` - Home page with search and cancellation forms
- `POST /search` - Validate dates and show room availability
- `POST /book` - Create a booking and show confirmation
- `POST /cancel` - Cancel a booking by reference

## Data Storage

Bookings are stored in `bookings.json` as an array of objects. A booking record includes:

- `reference`
- `guest_name`
- `guest_email`
- `room_type`
- `check_in`
- `check_out`
- `price_per_night`
- `nights`
- `total_price`
- `created_at`

Cancel operations remove the matching booking record from the JSON file.