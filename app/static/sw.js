// Minimal service worker: lets phones offer "Install app" / "Add to Home screen".
// It does not cache answers. Health answers must always come fresh from the server.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
