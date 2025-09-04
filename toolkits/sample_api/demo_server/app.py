import base64

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/hello/<salute>", methods=["POST"])
def hello_world(salute):
    """
    Hello world endpoint that matches the HelloWorld.json specification.

    Expected:
    - Path parameter: salute (the salutation)
    - Body parameter: sample_name (the name to greet)
    - Header: Authorization: Basic {api_key}

    Returns:
    - JSON response with message field
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    try:
        # Extract API key from Basic auth
        api_key = auth_header[6:]  # Remove "Basic " prefix

        if api_key != "12345":
            return jsonify({"error": "Invalid API key"}), 403

        # Get name from request body (JSON)
        data = request.get_json()
        if not data or "sample_name" not in data:
            return jsonify({"error": "Missing sample_name in request body"}), 400

        sample_name = data["sample_name"]

        # Create greeting message
        message = f"{salute.title()}, {sample_name}! Welcome to the Sample API."

        return jsonify({"message": message})

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    print("Starting Sample API Demo Server on http://localhost:9123")
    print("Endpoint: POST /hello/{salute}")
    print("Expected body: {'sample_name': 'YourName'}")
    print("Expected header: Authorization: Basic {your_api_key}")
    app.run(host="0.0.0.0", port=9123, debug=True)
