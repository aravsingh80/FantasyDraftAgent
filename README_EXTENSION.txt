FantasyAgent Chrome Extension Integration
========================================

WHAT IS INCLUDED
----------------
main.py
    Your current main runner with only the integration changes needed for:
    - automatic Sleeper draft ID from the active Sleeper draft page
    - automatic logged-in Sleeper user -> draft slot mapping
    - publishing the existing final recommendation to localhost

extension_backend/
    Tiny standard-library Python HTTP bridge. No Flask/FastAPI dependency.

chrome_extension/
    Manifest V3 Chrome extension. It does not contain fantasy ranking logic.

UNCHANGED FILES
---------------
Keep every other existing FantasyAgent Python/JSON file exactly as-is.
The updated main.py imports them exactly like your current runner.

INSTALL
-------
1. Put main.py in your FantasyAgent root, replacing your current main.py.
2. Put extension_backend/ in the FantasyAgent root.
3. Put chrome_extension/ in the FantasyAgent root.
4. In Chrome open chrome://extensions
5. Enable Developer mode.
6. Click Load unpacked.
7. Choose the chrome_extension folder.
8. Open the Sleeper draft page in Chrome.
9. From the FantasyAgent root in your VS Code terminal run:

   python main.py

STARTUP BEHAVIOR
----------------
- Python starts localhost on 127.0.0.1:8765.
- Python waits for a Sleeper draft page.
- The extension reads the draft ID from URLs such as:
  https://sleeper.com/draft/nfl/<draft_id>
- The extension searches Sleeper's page local/session storage for the logged-in
  user ID or username and sends only session-identification data to localhost.
- Python calls the Sleeper draft API and maps user_id through draft_order.
- If username was found but user_id was not, Python resolves it through
  Sleeper's public user endpoint first.
- If automatic slot resolution still fails, the old manual draft-slot prompt
  is used as a fallback.

WHAT STAYS MANUAL
-----------------
Draft strategy remains manual because balanced / RB-heavy / WR-heavy is your
own chosen strategy rather than a Sleeper draft setting.

TERMINAL OUTPUT
---------------
The existing draft-pick, roster, recommendation, and reasoning print paths are
unchanged. The localhost server suppresses its own HTTP request logging so it
does not spam the VS Code terminal.

EXTENSION OUTPUT
----------------
The extension receives only a compact recommendation view:
- recommended player
- top 5 ranked candidates
- position/team
- ADP
- ECR
- projected points
- deterministic reasoning

It does NOT receive or mirror the pick-by-pick terminal stream.
