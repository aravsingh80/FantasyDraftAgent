const LOCAL_SERVER = "http://127.0.0.1:8765";

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {
    if (message.type !== "FANTASY_AGENT_SESSION") {
      return;
    }

    const session = message.payload;

    chrome.storage.local.set({
      fantasyAgentSession: session
    });

    fetch(`${LOCAL_SERVER}/session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(session)
    })
      .then(async response => {
        if (!response.ok) {
          throw new Error(
            `Local server returned ${response.status}`
          );
        }

        sendResponse({
          ok: true,
          data: await response.json()
        });
      })
      .catch(error => {
        // The Python runner may simply not be open yet.
        sendResponse({
          ok: false,
          error: error.message
        });
      });

    return true;
  }
);
