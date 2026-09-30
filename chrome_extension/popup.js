const LOCAL_SERVER = "http://127.0.0.1:8765";

const statusText = document.getElementById("status");
const statusDot = document.getElementById("status-dot");
const emptyState = document.getElementById("empty-state");

const recommendationSection =
  document.getElementById("recommendation");

const recommendedName =
  document.getElementById("recommended-name");

const recommendedPosition =
  document.getElementById("recommended-position");

const recommendedReason =
  document.getElementById("recommended-reason");

const rankingsElement =
  document.getElementById("rankings");

const saveStrategyButton =
  document.getElementById("save-strategy");

const strategyStatus =
  document.getElementById("strategy-status");

let lastVersion = null;

async function getDraftIdFromCurrentTab() {
  const tabs = await chrome.tabs.query({
    active: true,
    currentWindow: true
  });

  const tab = tabs[0];

  if (!tab?.url) {
    return null;
  }

  const url = new URL(tab.url);

  const match = url.pathname.match(
    /\/draft\/nfl\/(\d+)/i
  );

  return match ? match[1] : null;
}

function formatNumber(value, digits = 1) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "-";
  }

  const number = Number(value);

  return Number.isFinite(number)
    ? number.toFixed(digits)
    : String(value);
}

function setConnected(connected) {
  statusText.textContent = connected
    ? "Local runner connected"
    : "Local runner not connected";

  statusDot.classList.toggle(
    "connected",
    connected
  );
}

function createMetric(label, value) {
  const metric = document.createElement("span");
  const labelNode = document.createTextNode(`${label} `);
  const valueNode = document.createElement("b");

  valueNode.textContent = value;
  metric.append(labelNode, valueNode);

  return metric;
}

function renderRecommendation(recommendation) {
  if (!recommendation?.recommended_player) {
    emptyState.classList.remove("hidden");
    recommendationSection.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  recommendationSection.classList.remove("hidden");

  const player = recommendation.recommended_player;

  recommendedName.textContent = player.name || "Unknown";
  recommendedPosition.textContent = player.position || "";
  recommendedReason.textContent =
    recommendation.recommendation_reasoning ||
    player.reasoning ||
    "";

  rankingsElement.replaceChildren();

  for (const candidate of recommendation.rankings || []) {
    const card = document.createElement("div");
    card.className = "candidate card";

    const heading = document.createElement("div");
    heading.className = "candidate-heading";

    const name = document.createElement("strong");
    name.textContent =
      `${candidate.deterministic_rank}. ${candidate.name}`;

    const position = document.createElement("span");
    position.textContent = candidate.position || "";

    heading.append(name, position);

    const metrics = document.createElement("div");
    metrics.className = "metrics";
    metrics.append(
      createMetric(
        "ADP",
        formatNumber(candidate.adp)
      ),
      createMetric(
        "ECR",
        formatNumber(candidate.ecr)
      ),
      createMetric(
        "Proj",
        formatNumber(candidate.projected_points)
      )
    );

    const reasoning = document.createElement("p");
    reasoning.textContent = candidate.reasoning || "";

    card.append(heading, metrics, reasoning);
    rankingsElement.appendChild(card);
  }
}


function getSelectedStrategy() {
  return document.querySelector(
    'input[name="strategy"]:checked'
  )?.value || null;
}

function selectStrategy(strategy) {
  if (!strategy) return;

  const input = document.querySelector(
    `input[name="strategy"][value="${strategy}"]`
  );

  if (input) {
    input.checked = true;
    strategyStatus.textContent =
      `Current strategy: ${strategy}`;
  }
}

async function getStoredSleeperSession() {
  return new Promise(resolve => {
    chrome.storage.local.get(
      ["fantasyAgentSession"],
      result => {
        resolve(
          result.fantasyAgentSession || null
        );
      }
    );
  });
}

async function restoreSessionToBackend(storedSession) {
  if (!storedSession?.draft_id) {
    return null;
  }

  try {
    const response = await fetch(
      `${LOCAL_SERVER}/session`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(storedSession)
      }
    );

    if (!response.ok) {
      return null;
    }

    const payload = await response.json();
    return payload.session || null;
  } catch (_) {
    return null;
  }
}

async function loadSession() {
  try {
    const response = await fetch(
      `${LOCAL_SERVER}/session`,
      { cache: "no-store" }
    );

    if (response.ok) {
      const payload = await response.json();
      const session = payload.session || {};

      if (session.draft_id) {
        selectStrategy(session.strategy);
        return session;
      }
    }

    // If the page detected the draft before Python was running,
    // recover the draft data saved by background.js and send it again.
    const storedSession = await getStoredSleeperSession();
    const restoredSession = await restoreSessionToBackend(
      storedSession
    );

    if (restoredSession) {
      selectStrategy(restoredSession.strategy);
      return restoredSession;
    }

    return storedSession;
  } catch (_) {
    const storedSession = await getStoredSleeperSession();
    return storedSession;
  }
}

async function saveStrategy() {
  const strategy = getSelectedStrategy();

  if (!strategy) {
    strategyStatus.textContent =
      "Select a strategy first.";
    return;
  }

  const session = await loadSession();

  if (!session?.draft_id) {
    strategyStatus.textContent =
      "Open your Sleeper draft page first.";
    return;
  }

  saveStrategyButton.disabled = true;
  strategyStatus.textContent = "Saving...";

  try {
    const response = await fetch(
      `${LOCAL_SERVER}/session`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          draft_id: session.draft_id,
          strategy
        })
      }
    );

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(
        payload.error || `HTTP ${response.status}`
      );
    }

    strategyStatus.textContent =
      `Strategy set to ${strategy}.`;
  } catch (error) {
    strategyStatus.textContent =
      `Could not save strategy: ${error.message}`;
  } finally {
    saveStrategyButton.disabled = false;
  }
}

saveStrategyButton.addEventListener(
  "click",
  saveStrategy
);

async function refresh() {
  try {
    const response = await fetch(
      `${LOCAL_SERVER}/recommendation`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    setConnected(true);

    if (payload.version !== lastVersion) {
      lastVersion = payload.version;
      renderRecommendation(payload.recommendation);
    }
  } catch (_) {
    setConnected(false);
  }
}

loadSession();
refresh();
setInterval(refresh, 250);
setInterval(loadSession, 1500);
