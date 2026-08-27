const api = window.projectHopeDesktop;
const input = document.getElementById("server-url");
const connect = document.getElementById("connect-button");
const showcase = document.getElementById("showcase-button");
const status = document.getElementById("status");

function showStatus(message, error = false) {
  status.textContent = message;
  status.className = error ? "status error" : "status";
}

function busy(value) {
  connect.disabled = value;
  showcase.disabled = value;
  showcase.setAttribute("aria-busy", String(value));
}

const message = new URLSearchParams(window.location.search).get("message");
if (message) {
  showStatus(message, !message.startsWith("Preparing"));
  busy(message.startsWith("Preparing"));
}
api.onRuntimeStatus((text) => { showStatus(text); busy(true); });
api.getConfig().then((config) => {
  if (config.serverUrl) {
    input.value = config.serverUrl;
    document.getElementById("connection-details").open = true;
  }
}).catch(() => undefined);

showcase.addEventListener("click", async () => {
  busy(true);
  showStatus("Preparing your sample workspace…");
  try {
    const result = await api.startShowcase();
    if (!result.ok) showStatus(result.message, true);
  } catch { showStatus("The sample could not open. Close Project Hope and try again.", true); }
  finally { busy(false); }
});

document.getElementById("connect-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  busy(true);
  showStatus("Checking your charity workspace…");
  try {
    const result = await api.saveServerUrl(input.value);
    if (!result.ok) { showStatus(result.message, true); input.focus(); }
  } catch { showStatus("We could not connect. Check the workspace website and try again.", true); }
  finally { busy(false); }
});
