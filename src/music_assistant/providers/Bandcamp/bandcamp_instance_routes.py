from flask import Blueprint, request, jsonify
from .api import BandcampApiClient

bandcamp_bp = Blueprint("bandcamp", __name__)

# Mock database for instance configurations
INSTANCE_CONFIGS = {}

@bandcamp_bp.route("/instances", methods=["GET"])
def get_instances():
    """Fetch the list of Bandcamp instances."""
    return jsonify(list(INSTANCE_CONFIGS.values()))

@bandcamp_bp.route("/instances", methods=["POST"])
def add_instance():
    """Add a new Bandcamp instance."""
    data = request.json
    instance_id = data["instance_id"]
    INSTANCE_CONFIGS[instance_id] = data
    return jsonify({"message": "Instance added successfully"}), 201

@bandcamp_bp.route("/instances/<instance_id>", methods=["PUT"])
def update_instance(instance_id):
    """Update an existing Bandcamp instance."""
    data = request.json
    INSTANCE_CONFIGS[instance_id] = data
    return jsonify({"message": "Instance updated successfully"})

@bandcamp_bp.route("/instances/<instance_id>", methods=["DELETE"])
def delete_instance(instance_id):
    """Delete a Bandcamp instance."""
    INSTANCE_CONFIGS.pop(instance_id, None)
    return jsonify({"message": "Instance deleted successfully"})

@bandcamp_bp.route("/instances/<instance_id>/auth/test", methods=["POST"])
def test_authentication(instance_id):
    """Test authentication for a Bandcamp instance."""
    instance = INSTANCE_CONFIGS.get(instance_id)
    if not instance:
        return jsonify({"error": "Instance not found"}), 404

    auth_type = request.json.get("auth_type")
    bandcamp_client = BandcampApiClient()

    if auth_type == "cookies":
        auth_token = instance.get("auth_token")
        success = bandcamp_client.authenticate_with_cookies(auth_token)
    elif auth_type == "credentials":
        username = instance.get("username")
        password = instance.get("password")
        success = bandcamp_client.authenticate_with_credentials(username, password)
    else:
        return jsonify({"error": "Invalid auth_type"}), 400

    if success:
        return jsonify({"message": "Authentication successful"}), 200
    else:
        return jsonify({"message": "Authentication failed"}), 401