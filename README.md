# Inventory Intelligence

Inventory Intelligence is a production-ready inventory and usage management platform built entirely with the Python standard library and modern, responsive front-end technologies. It offers inventory tracking, barcode-based adjustments, usage logging, automated shopping list management, and actionable dashboards without external dependencies.

## Features

- **Inventory Management**
  - Capture barcode/ID, name, brand, type, attributes, unit size, cost per unit, and stock thresholds.
  - Automatic cost-per-unit calculation based on the total cost and initial stock.
  - Real-time status alerts for low stock and overstock conditions.
  - Stock adjustments with audit trail logging.

- **Usage Tracking**
  - Record client or project usage with before/after state notes and date tracking.
  - Select multiple inventory items, automatically calculating cost based on consumption.
  - Deduct consumed inventory instantly and add depleted items to the shopping list.

- **Dashboard & Analytics**
  - Live metrics for total inventory value and units.
  - Inventory distribution and stock health charts rendered with the Canvas API.
  - Recent activity feed and client usage history summaries.

- **Shopping List Automation**
  - Items automatically move to the shopping list when stock hits zero.
  - Consolidated view of pending purchases with timestamps.

- **Accessible, Responsive UI**
  - Keyboard-friendly interactions, semantic markup, and support for reduced motion.
  - Responsive layouts tailored for desktop, tablet, and mobile screens.

## Project Structure

```
app.py            # HTTP server, REST API, and SQLite persistence
static/index.html # Front-end application markup
static/styles.css # Modern responsive design and theming
static/app.js     # Front-end logic, data fetching, charts, and interactivity
```

## Getting Started

### Prerequisites

- Python 3.11 or later (uses only standard library modules)

### Installation & Setup

1. Clone the repository and move into the project directory.
2. (Optional) Create and activate a virtual environment.
3. Start the server:

   ```bash
   python app.py
   ```

   The server initializes the SQLite database (`inventory.db`) automatically.

4. Visit [http://localhost:8000](http://localhost:8000) in a modern browser.

### Troubleshooting

- **IndentationError referencing `git apply`** – if you copied files from an earlier
  patch snippet, `app.py` may accidentally contain the literal patch instructions.
  Re-clone or re-download the repository so the first line of `app.py` begins with
  `import json` (or run `git checkout -- app.py` inside the repo) before starting the
  server.

## API Overview

All API endpoints return JSON responses and reside under `/api`.

| Method | Endpoint             | Description                                      |
| ------ | -------------------- | ------------------------------------------------ |
| GET    | `/api/dashboard`     | Summary metrics, alerts, recent activity/usage. |
| GET    | `/api/items`         | Retrieve all inventory items.                   |
| POST   | `/api/items`         | Create a new inventory item.                    |
| PUT    | `/api/items`         | Update metadata for an existing item.           |
| POST   | `/api/items/adjust`  | Add or deduct quantity for a given barcode.     |
| POST   | `/api/usage`         | Record usage and deduct stock automatically.    |
| GET    | `/api/shopping-list` | Retrieve items queued for replenishment.        |
| GET    | `/api/activity`      | Detailed inventory movement history.            |

## Deployment Notes

- The application runs as a WSGI-compatible HTTP server using `http.server` for simplicity.
- To deploy behind a production web server, place it behind a reverse proxy such as Nginx and run via a process manager (e.g., systemd).
- SQLite provides ACID-compliant storage for small-to-medium deployments. For large-scale scenarios, replace the database backend by adapting `get_connection()` and associated data-access functions.

## Testing

- The application is designed for manual QA via the browser UI and API testing tools (e.g., `curl`, Postman).
- Automated tests can be added by extending the server with integration test suites using Python's `unittest` and `http.client` modules.

## Accessibility & Compliance

- Semantic HTML structure with accessible labels and instructions.
- Color contrast meets WCAG AA guidelines with high-contrast badges for alerts.
- Reduced motion support honors user preferences via `prefers-reduced-motion` media query.

## License

This project is provided under the MIT License. Feel free to adapt it to your organization's needs.
