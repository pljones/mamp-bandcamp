from flask import Blueprint, request, jsonify

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