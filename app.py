import copy
import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)

# Demo credentials. Change these before a real company deployment.
app.config["SECRET_KEY"] = os.environ.get(
    "SENTINEL_SECRET_KEY",
    "demo-only-change-this-secret-key"
)
ADMIN_USERNAME = os.environ.get("SENTINEL_ADMIN_USERNAME", "sentinel")
ADMIN_PASSWORD = os.environ.get("SENTINEL_ADMIN_PASSWORD", "Sentinel123!")

DEFAULT_SERVERS = [
    {
        "name": "Gateway 01",
        "role": "Public API Gateway",
        "status": "Healthy",
        "metric": "Latency 42 ms",
    },
    {
        "name": "Auth 01",
        "role": "Authentication Service",
        "status": "Healthy",
        "metric": "CPU 31%",
    },
    {
        "name": "Database 01",
        "role": "Primary Database",
        "status": "Healthy",
        "metric": "Disk free 64%",
    },
]

servers = []
incidents = []
incident_counter = 1000


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"message": "Admin login required."}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def timestamp():
    return datetime.now().strftime("%d %b %Y, %H:%M:%S")


def update_server(name, status, metric):
    for server in servers:
        if server["name"] == name:
            server["status"] = status
            server["metric"] = metric
            return


def add_incident(event_type, server, source_ip, risk, score, response, status, message):
    global incident_counter

    incident_counter += 1
    incidents.append(
        {
            "id": f"INC-{incident_counter}",
            "timestamp": timestamp(),
            "event_type": event_type,
            "server": server,
            "source_ip": source_ip,
            "risk": risk,
            "score": score,
            "response": response,
            "status": status,
            "message": message,
        }
    )


def reset_demo_data():
    global servers, incidents, incident_counter

    servers = copy.deepcopy(DEFAULT_SERVERS)
    incidents = []
    incident_counter = 1000


def create_scenario(scenario):
    if scenario == "normal":
        add_incident(
            "Normal server activity",
            "gateway-01",
            "10.10.2.18",
            "Low",
            8,
            "Event logged — no response required",
            "Logged",
            "Normal API request completed successfully.",
        )
        return 1

    if scenario == "brute_force":
        risk_levels = ["Low", "Low", "Low", "Medium", "Medium", "High"]

        for number, risk in enumerate(risk_levels, start=1):
            if risk == "High":
                response = "Source isolated (simulated)"
                status = "Isolated"
            elif risk == "Medium":
                response = "Monitoring enabled and alert flagged"
                status = "Monitoring"
            else:
                response = "Event logged — no response required"
                status = "Logged"

            add_incident(
                "Repeated failed login attempt",
                "auth-01",
                "203.0.113.44",
                risk,
                number * 15,
                response,
                status,
                f"Failed login attempt {number} from a simulated source.",
            )

        update_server("Auth 01", "Critical", "Authentication attack detected")
        return 6

    if scenario == "suspicious_ip":
        add_incident(
            "Suspicious IP detected",
            "gateway-01",
            "198.51.100.77",
            "High",
            88,
            "Source isolated (simulated)",
            "Isolated",
            "Known suspicious source detected in simulated traffic.",
        )
        update_server("Gateway 01", "Critical", "Suspicious source isolated")
        return 1

    if scenario == "traffic_spike":
        add_incident(
            "Unusual traffic spike",
            "gateway-01",
            "198.51.100.30",
            "Medium",
            64,
            "Monitoring enabled and alert flagged",
            "Monitoring",
            "Traffic exceeded the simulated monitoring threshold.",
        )
        update_server("Gateway 01", "Warning", "Traffic 890 Mbps")
        return 1

    if scenario == "cpu_high":
        add_incident(
            "High CPU utilization",
            "auth-01",
            "internal-monitor",
            "High",
            93,
            "Critical alert raised for operations team",
            "Escalated",
            "CPU utilization exceeded the simulated critical threshold.",
        )
        update_server("Auth 01", "Critical", "CPU 96%")
        return 1

    if scenario == "disk_low":
        add_incident(
            "Low disk space",
            "database-01",
            "internal-monitor",
            "High",
            91,
            "Critical alert raised for operations team",
            "Escalated",
            "Available database storage is below the simulated safe threshold.",
        )
        update_server("Database 01", "Critical", "Disk free 7%")
        return 1

    if scenario == "service_down":
        add_incident(
            "Service downtime detected",
            "gateway-01",
            "internal-monitor",
            "High",
            95,
            "Critical alert raised for operations team",
            "Escalated",
            "Gateway health check failed in the simulation.",
        )
        update_server("Gateway 01", "Critical", "Health check failed")
        return 1

    return 0


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = ADMIN_USERNAME
            return redirect(url_for("dashboard"))

        error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template("index.html", admin_username=session.get("admin_username"))


@app.get("/api/dashboard")
@login_required
def api_dashboard():
    return jsonify(
        {
            "stats": {
                "total_events": len(incidents),
                "high_risk": sum(item["risk"] == "High" for item in incidents),
                "monitoring": sum(item["status"] == "Monitoring" for item in incidents),
                "isolated": sum(item["status"] == "Isolated" for item in incidents),
            },
            "servers": servers,
            "incidents": list(reversed(incidents)),
        }
    )


@app.post("/api/simulate/<scenario>")
@login_required
def simulate(scenario):
    processed = create_scenario(scenario)

    if processed == 0:
        return jsonify({"message": "Unknown simulation scenario."}), 404

    return jsonify({"message": f"{processed} simulated event(s) processed."})


@app.post("/api/reset")
@login_required
def reset():
    reset_demo_data()
    return jsonify({"message": "Demo data reset."})


@app.get("/health")
def health():
    return jsonify({"status": "healthy", "mode": "simulation"})


reset_demo_data()

if __name__ == "__main__":
    app.run(debug=True) 