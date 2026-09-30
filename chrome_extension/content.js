console.log("FantasyAgent content.js loaded");


function getDraftIdFromUrl() {
  const url = new URL(window.location.href);

  const match = url.pathname.match(
    /\/draft\/nfl\/(\d+)/i
  );

  return match ? match[1] : null;
}


function findSleeperIdentity() {
  const stores = [
    window.localStorage,
    window.sessionStorage
  ];

  let userId = null;
  let username = null;

  for (const store of stores) {
    for (let i = 0; i < store.length; i++) {
      const key = store.key(i);
      const raw = store.getItem(key);

      if (!key || !raw) {
        continue;
      }

      const normalizedKey = key
        .toLowerCase()
        .replace(/[_-]/g, "");

      if (
        normalizedKey === "userid" ||
        normalizedKey === "sleeperuserid"
      ) {
        userId = cleanStorageValue(raw);
      }

      if (
        normalizedKey === "username" ||
        normalizedKey === "sleeperusername"
      ) {
        username = cleanStorageValue(raw);
      }

      try {
        const parsed = JSON.parse(raw);

        const found = findIdentityInObject(
          parsed
        );

        if (!userId && found.user_id) {
          userId = found.user_id;
        }

        if (!username && found.username) {
          username = found.username;
        }
      } catch (_) {
        // Ignore non-JSON storage values.
      }

      if (userId && username) {
        return {
          user_id: userId,
          username
        };
      }
    }
  }

  return {
    user_id: userId,
    username
  };
}


function cleanStorageValue(value) {
  return String(value)
    .trim()
    .replace(/^"|"$/g, "");
}


function findIdentityInObject(
  value,
  depth = 0
) {
  if (
    value === null ||
    value === undefined ||
    depth > 6
  ) {
    return {
      user_id: null,
      username: null
    };
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const result = findIdentityInObject(
        item,
        depth + 1
      );

      if (
        result.user_id ||
        result.username
      ) {
        return result;
      }
    }

    return {
      user_id: null,
      username: null
    };
  }

  if (typeof value !== "object") {
    return {
      user_id: null,
      username: null
    };
  }

  let userId = null;
  let username = null;

  for (
    const [key, child]
    of Object.entries(value)
  ) {
    const normalizedKey = key
      .toLowerCase()
      .replace(/[_-]/g, "");

    if (
      (
        normalizedKey === "userid" ||
        normalizedKey === "sleeperuserid"
      ) &&
      (
        typeof child === "string" ||
        typeof child === "number"
      )
    ) {
      userId = String(child);
    }

    if (
      (
        normalizedKey === "username" ||
        normalizedKey === "sleeperusername"
      ) &&
      typeof child === "string"
    ) {
      username = child;
    }

    if (
      child &&
      typeof child === "object"
    ) {
      const nested = findIdentityInObject(
        child,
        depth + 1
      );

      if (!userId && nested.user_id) {
        userId = nested.user_id;
      }

      if (
        !username &&
        nested.username
      ) {
        username = nested.username;
      }
    }

    if (userId && username) {
      break;
    }
  }

  return {
    user_id: userId,
    username
  };
}


function sendCurrentSession() {
  const draftId = getDraftIdFromUrl();

  if (!draftId) {
    console.log(
      "FantasyAgent: no Sleeper draft ID found."
    );

    return;
  }

  const identity = findSleeperIdentity();

  const payload = {
    draft_id: draftId,
    sleeper_user_id:
      identity.user_id || null,
    sleeper_username:
      identity.username || null,
    sleeper_url:
      window.location.href
  };

  console.log(
    "FantasyAgent detected session:",
    payload
  );

  try {
    chrome.storage.local.set({
      fantasyAgentSession: payload
    });

    chrome.runtime.sendMessage(
      {
        type: "FANTASY_AGENT_SESSION",
        payload
      },
      response => {
        if (chrome.runtime.lastError) {
          console.log(
            "FantasyAgent message error:",
            chrome.runtime.lastError.message
          );

          return;
        }

        console.log(
          "FantasyAgent session sent:",
          response
        );
      }
    );
  } catch (error) {
    console.log(
      "FantasyAgent extension context ended:",
      error
    );
  }
}


sendCurrentSession();