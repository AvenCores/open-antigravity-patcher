import re
from packaging.version import Version

VERSION = "1.1.5"
MIN_AG_VERSION = "2.0.1"
AUTH_PATCH_SWITCH_VERSION = Version("1.23")
RUNTIME_SETTINGS_SWITCH_VERSION = Version("1.23")
CLOUD_CODE_ENDPOINT = "https://cloudcode-pa.googleapis.com"
RUNTIME_EXPERIMENTS_TO_DISABLE = (
    "CASCADE_DEFAULT_MODEL_OVERRIDE",
    "CASCADE_USE_EXPERIMENT_CHECKPOINTER",
    "CASCADE_NEW_MODELS_NUX",
    "CASCADE_NEW_WAVE_2_MODELS_NUX",
)
RUNTIME_EXPERIMENTS_VALUE = ",".join(RUNTIME_EXPERIMENTS_TO_DISABLE)

# Единственное место, где хранится GUID установщика Antigravity IDE
AG_REGISTRY_SUBKEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{AA73B3E3-C6C8-45C8-B1DC-4AE56C751432}_is1"

CSI = "\x1b["
COLOR_RESET = CSI + "0m"
COLOR_CYAN = CSI + "36m"
COLOR_GREEN = CSI + "32m"
COLOR_YELLOW = CSI + "33m"
COLOR_RED = CSI + "31m"
COLOR_BOLD = CSI + "1m"

RE_AUTH_IS_GOOGLE_INTERNAL = re.compile(
    r'if\(\s*(?P<prefix>(?:this\.[A-Za-z_$][\w$]*\.send\(\{type:[^}]+\}\)\s*,\s*)?'
    r'this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)
RE_AUTH_IS_GOOGLE_INTERNAL_OLD = re.compile(
    r'if\(\s*(?P<prefix>this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)
RE_AUTH_IS_GOOGLE_INTERNAL_NEW = re.compile(
    r'if\(\s*(?P<prefix>this\.[A-Za-z_$][\w$]*\.send\(\{type:[^}]+\}\)\s*,\s*'
    r'this\.[A-Za-z_$][\w$]*\.resetIsTierGCPTos\(\)\s*,\s*)'
    r'this\.[A-Za-z_$][\w$]*\.isGoogleInternal\s*\)'
)

INTEGRITY_BLOCK_SIZE = 4 * 1024 * 1024
PACK_EXCLUDE_PATHS = {
    'downloaded_frontend_main.js',
    'frontend_patch_result.json',
    'dist/main.js.bak',
}

ANTIGRAVITY_INJECTION_CODE_TEMPLATE = """
    // Start local frontend patch server
    let localServerPort = 0;
    const frontendPatchCache = new Map();
    const frontendPatchFs = require('fs');
    const frontendPatchPath = require('path');
    const frontendPatchResultPath = frontendPatchPath.join('{dest_folder}', 'frontend_patch_result.json');
    const patchFrontendMainJs = (content) => {
        const results = [];
        if (content.includes('csrfToken') && content.includes('isGoogleInternal')) {
            let nextContent = content.split('isGoogleInternal:!1').join('isGoogleInternal:!0');
            let applied = nextContent !== content;
            results.push({
                name: 'isGoogleInternal:!1 -> isGoogleInternal:!0 (frontend)',
                applied,
                detail: applied ? 'Forced frontend isGoogleInternal to true' : 'isGoogleInternal:!1 not found',
            });
            content = nextContent;
            nextContent = content
                .split('SET_INELIGIBLE:{target:".loginError"')
                .join('SET_INELIGIBLE:{target:".signedIn"')
                .split('SET_ERROR:{target:".loginError"')
                .join('SET_ERROR:{target:".signedIn"');
            applied = nextContent !== content;
            results.push({
                name: 'SET_INELIGIBLE/SET_ERROR -> target:.signedIn (frontend)',
                applied,
                detail: applied ? 'Redirected ineligible/error states to signedIn' : 'loginError targets not found',
            });
            content = nextContent;
        }
        else {
            results.push({
                name: 'frontend marker check',
                applied: false,
                detail: 'csrfToken/isGoogleInternal markers not found',
            });
        }
        return { content, results };
    };
    const isFrontendMainPatched = (content) => {
        if (content.includes('csrfToken') && content.includes('isGoogleInternal')) {
            return !content.includes('isGoogleInternal:!1')
                && content.includes('SET_INELIGIBLE:{target:".signedIn"}');
        }
        return false;
    };
    const writeFrontendPatchResult = (sourceUrl, content, results) => {
        const verified = isFrontendMainPatched(content);
        try {
            frontendPatchFs.writeFileSync(frontendPatchResultPath, JSON.stringify({
                sourceUrl,
                verified,
                size: Buffer.byteLength(content, 'utf8'),
                results,
                at: new Date().toISOString(),
            }, null, 2));
        } catch (err) {
            console.error('[Debug] Failed to write frontend patch result:', err);
        }
        return verified;
    };
    const getPatchedFrontendMainJs = (sourceUrl) => {
        if (frontendPatchCache.has(sourceUrl)) {
            return frontendPatchCache.get(sourceUrl);
        }
        const patchPromise = new Promise((resolve, reject) => {
            const https = require('https');
            const agent = new https.Agent({ rejectUnauthorized: false });
            https.get(sourceUrl, { agent, headers: { 'Accept-Encoding': 'identity' } }, (upstream) => {
                const chunks = [];
                upstream.on('data', (chunk) => {
                    chunks.push(chunk);
                });
                upstream.on('end', () => {
                    const originalContent = Buffer.concat(chunks).toString('utf8');
                    const { content, results } = patchFrontendMainJs(originalContent);
                    for (const result of results) {
                        console.log(`[Debug] Frontend patch: ${result.name}; applied=${result.applied}; ${result.detail}`);
                    }
                    console.log(`[Debug] Frontend patch verification: ${writeFrontendPatchResult(sourceUrl, content, results) ? 'ok' : 'failed'}`);
                    resolve(Buffer.from(content, 'utf8'));
                });
                upstream.on('error', reject);
            }).on('error', reject);
        }).catch((err) => {
            frontendPatchCache.delete(sourceUrl);
            throw err;
        });
        frontendPatchCache.set(sourceUrl, patchPromise);
        return patchPromise;
    };
    try {
        const http = require('http');
        const localServer = http.createServer((req, res) => {
            const requestUrl = new URL(req.url || '/', `http://127.0.0.1:${localServerPort || 0}`);
            if (requestUrl.pathname === '/main.js') {
                const sourceUrl = requestUrl.searchParams.get('source');
                if (!sourceUrl) {
                    res.writeHead(400);
                    res.end();
                    return;
                }
                getPatchedFrontendMainJs(sourceUrl)
                    .then((content) => {
                    res.writeHead(200, {
                        'Content-Type': 'application/javascript; charset=utf-8',
                        'Access-Control-Allow-Origin': '*',
                        'Content-Length': content.length,
                    });
                    res.end(content);
                })
                    .catch((err) => {
                    console.error('[Debug] Local server failed to patch frontend main.js:', err);
                    res.writeHead(502);
                    res.end();
                });
                return;
            }
            res.writeHead(404);
            res.end();
        });
        localServer.listen(0, '127.0.0.1', () => {
            localServerPort = localServer.address().port;
            console.log(`[Debug] Local patch server listening on port ${localServerPort}`);
        });
    } catch (err) {
        console.error('[Debug] Failed to start local patch server:', err);
    }
    electron_1.session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
        console.log(`[Network Request] ${details.url}`);
        if (details.url.endsWith('/main.js') && details.url.includes('127.0.0.1')) {
            if (localServerPort && !details.url.includes(`:${localServerPort}`)) {
                const redirectUrl = `http://127.0.0.1:${localServerPort}/main.js?source=${encodeURIComponent(details.url)}`;
                console.log(`[Debug] Redirecting main.js request to local patch server: ${redirectUrl}`);
                callback({ redirectURL: redirectUrl });
                return;
            }
        }
        callback({});
    });
"""
