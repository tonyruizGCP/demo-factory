import os
import logging
from flask import Flask, request, jsonify
import vertexai

app = Flask(__name__)

# Config from environment variables
PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "us-central1")
INSTANCE_NAME = os.environ.get("INSTANCE_NAME")

# Initialize the High-Level SDK
vertexai.init(project=PROJECT_ID, location=LOCATION)
client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

@app.route("/", methods=["POST"])
def handle_memory():
  try:
    data = request.get_json(silent=True)
    if not data:
      return jsonify({"error": "Request body is empty or invalid JSON"}), 400

    action = data.get("action")
    user_id = data.get("user_id")
    if not user_id:
      return jsonify({"error": "Missing required parameter 'user_id'"}), 400

    scope = {"user_id": str(user_id)}

    if action == "retrieve":
      # Using high-level SDK path: client.agent_engines.memories.retrieve
      memories = client.agent_engines.memories.retrieve(
          name=INSTANCE_NAME,
          scope=scope
      )
      # memories is an iterable of the retrieved results
      facts = [m.memory.fact for m in memories]
      context = " ".join(facts) if facts else "No history found."
      return jsonify({"memory_context": context, "status": "success"})

    elif action == "persist":
      fact = data.get("fact")
      if not fact:
        return jsonify({"error": "Missing required parameter 'fact' for persist action"}), 400
      # Using high-level SDK path: client.agent_engines.memories.generate
      client.agent_engines.memories.generate(
          name=INSTANCE_NAME,
          direct_memories_source={"direct_memories": [{"fact": fact}]},
          scope=scope
      )
      return jsonify({"status": "success", "message": "Memory persisted."})

    return jsonify({"error": "Invalid action"}), 400

  except Exception as e:
    logging.error(f"Error: {str(e)}")
    return jsonify({"status": "error", "message": str(e)}), 200

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
