const $ = (id) => document.getElementById(id);

function safe(value) {
  return String(value ?? "-")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setText(id, value) {
  const element = $(id);
  if (element) element.textContent = value ?? 0;
}

function showMessage(message) {
  const element = $("responseResult");
  if (element) element.textContent = message;
}

function riskClass(risk) {
  return String(risk || "").toLowerCase();
}

function renderServers(servers) {
  const grid = $("serverGrid");
  if (!grid) return;

  grid.innerHTML = servers.length
    ? servers.map((server) => `
      <article class="server-card">
        <div class="server-card-title">
          <h3>${safe(server.name || server.server || "Cloud Server")}</h3>
          <span class="status ${riskClass(server.status || server.health)}">
            ${safe(server.status || server.health || "Healthy")}
          </span>
        </div>
        <p><strong>${safe(server.metric || "Metric unavailable")}</strong></p>
<p>Role: <strong>${safe(server.role || "-")}</strong></p>
      </article>
    `).join("")
    : "<p>No server data available.</p>";
}

function renderIncidents(incidents) {
  const body = $("incidentBody");
  if (!body) return;

  body.innerHTML = incidents.length
    ? incidents.map((incident) => `
      <tr>
        <td>${safe(incident.id)}</td>
        <td>${safe(incident.timestamp)}</td>
        <td>${safe(incident.event_type || incident.type)}</td>
        <td>${safe(incident.server)}</td>
        <td>${safe(incident.source_ip || incident.ip || "Internal")}</td>
        <td><span class="severity ${riskClass(incident.risk)}">${safe(incident.risk)}</span></td>
        <td>${safe(incident.response)}</td>
        <td>${safe(incident.status)}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="8">No incidents recorded yet.</td></tr>`;
}

function renderTimeline(incidents) {
  const timeline = $("timeline");
  if (!timeline) return;

  timeline.innerHTML = incidents.slice(0, 8).map((incident) => `
    <div class="timeline-item ${riskClass(incident.risk)}">
      <strong>${safe(incident.event_type || incident.type)}</strong>
      <span>${safe(incident.timestamp)} — ${safe(incident.response)}</span>
    </div>
  `).join("") || "<p>No activity recorded yet.</p>";
}

function updateDashboard(data) {
  const incidents = data.incidents || data.events || [];
  const stats = data.stats || {};

  setText("totalEvents", stats.total_events ?? data.total_events ?? incidents.length);
  setText("highRisk", stats.high_risk ?? data.high_risk ??
    incidents.filter((item) => item.risk === "High").length);
  setText("monitoring", stats.monitoring ?? data.monitoring ??
    incidents.filter((item) => String(item.status).toLowerCase().includes("monitor")).length);
  setText("isolated", stats.isolated ?? data.isolated ??
    incidents.filter((item) => String(item.response).toLowerCase().includes("isolat")).length);

  renderServers(data.servers || data.server_status || []);
  renderIncidents(incidents);
  renderTimeline(incidents);
}

async function refreshDashboard() {
  try {
    const response = await fetch("/api/dashboard");
    if (!response.ok) throw new Error("Could not load dashboard data.");
    updateDashboard(await response.json());
  } catch (error) {
    showMessage(error.message);
  }
}

async function simulateScenario(scenario, button) {
  button.disabled = true;
  try {
    const response = await fetch(`/api/simulate/${scenario}`, { method: "POST" });
    const data = await response.json();

    if (!response.ok) throw new Error(data.message || "Simulation failed.");
    showMessage(data.message || data.response || `Simulation "${scenario}" completed.`);
    await refreshDashboard();
  } catch (error) {
    showMessage(error.message);
  } finally {
    button.disabled = false;
  }
}

async function resetDemo() {
  try {
    const response = await fetch("/api/reset", { method: "POST" });
    const data = await response.json();

    if (!response.ok) throw new Error(data.message || "Reset failed.");
    showMessage(data.message || "Demo reset successfully.");
    await refreshDashboard();
  } catch (error) {
    showMessage(error.message);
  }
}

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => simulateScenario(button.dataset.scenario, button));
});

$("resetButton")?.addEventListener("click", resetDemo);

refreshDashboard();
setInterval(refreshDashboard, 3000);