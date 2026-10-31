/**
 * GazeboExpress Authgear Client Configuration
 * This file configures the Authgear Web SDK endpoint and client ID.
 * The redirect URI dynamically defaults to window.location.origin (e.g. http://35.207.230.72 or http://localhost:8080)
 * so the same build works seamlessly on both local development and deployed GKE environments.
 */
window.GAZEBO_AUTH_CONFIG = {
    // Authgear Project Endpoint (e.g., https://<your-project>.authgear.cloud)
    endpoint: "https://shuffle-ylty8u.authgear.cloud",

    // Authgear OAuth Client ID (from Authgear Portal -> Applications)
    clientID: "a1d93aeb78d9f533",

    // Redirect URI: On production HTTPS, Authgear Web SDK finishAuthentication() requires
    // an exact trailing slash ('https://35-207-230-72.nip.io/').
    // On localhost, keep without trailing slash to match Authgear's registered localhost URI.
    redirectURI: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
        ? window.location.origin.replace(/\/+$/, '')
        : window.location.origin.replace(/\/+$/, '') + '/'
};
