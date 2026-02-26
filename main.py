"""Entrypoint for running the Flask task tracker app locally."""

from app import app


def main() -> None:
    """Run the Flask development server."""

    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
