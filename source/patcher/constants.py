import re
from packaging.version import Version

VERSION = "1.2.0"
MIN_AG_VERSION = "2.1.0"
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
COLOR_DIM = CSI + "2m"
COLOR_GRAY = CSI + "90m"
COLOR_WHITE = CSI + "97m"
COLOR_MAGENTA = CSI + "35m"

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

LOCAL_PATCH_SERVER_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEA/IUQUX8vQ3LJKoyAS4eJ4Ylfcy/9t1T5ILsag/ZT336h/uid
NnZDLuKH1jobpfThJ49yOQiKxIunxepFXMtSphWydz8UmHdgnveEbqm8Zh64gomI
ILZCz2fPX0Kbwgd6jokwQG3nuKNkFD0ASTOnscscK4OvwPVV6VCQ7PnVUIzz4Dzt
D7aNBx4uPgECs26fxQ6vktUf0/r+oEXH3Z8fwUJSugYYiYiDSzzrwJySAAwYyEgl
cNGStyuivTwPtq5OUtJ5n1OSRy9ZG8qm6+t7fkDV+50t9W5HMnoxomHN02rIty7U
z5ViVDqvUcnJvDXWUiXJhrrrsveei2tjKA1NnQIDAQABAoH/QVkuH+kKEipiZOB3
UxSAWh1y1hxVTFxxHEdPVVcp3Wyn/4+zH6T7PebhwE7JWOlGWzaEGL5dKv/5Kv61
dI4plVGIHdP1QH+kQX9MhlbmqobIuP9eexivsXzr7XsPU+cbkEdwdTv7+4xNGe+v
Y0I644fsglZR5V2YHgj7eFgvG+jamu5gQRmixQomFeZuXKYuIsYK9GmbCkTc+L2h
D3aAMD71SXrds/ljGKs3Q97ohrptrfXYHVNYkKY+J3GVFQFybu3hpB//jw+6PVv6
cY/NOsXpzUkw5BISmEDjERI3wXYgJK6VqbLG3lRseXuVg+lB0ePyJPAtC9D06NXB
5fbxAoGBAP9p3qjqWfa9Z1VzWO+SL1jRzt5c/MsHasUZ4OCNK8PNCqZz4FL9WkHY
1iesFDSk0wKcgn/D5GlS7SooSYboDLV86MlgeFhviUNJMRjYOeg7RlG5VHqtAO5B
dPglGXcWOMjmkpPzhfItbVr6sip+9tMKRfLWFR1Espvszyo6QQwNAoGBAP0ZfjfW
PSHmgBkIS0VRPS6qAkRApOXjREgNPOgVKquM3UPQh7dQ52L8VCuzmB3+6/qDJTF2
LBtS35NsnoqjyRefU7PWf+E4/ONkItsn02ehXIAa324C0+NpeybdFQFuQPLaDGYr
JePRYPhbUVufzO8RNMn/WEB70wG/S2VuY5PRAoGAWiim/n1rMFv/g/xpone52uKE
4Z11Zr3BhL3z0ZBDqKRSZBt3ThQ8rg262to1b7fW/I7+ydb+Y+dv7He4LLTw94eW
LK+vC5ijnWrSt/Br0HxMAEEpfvxe3buhbI68BHuFo/UwPKWz3J8IgRsJlVKoEisI
MgY8Ac7kNYJMRp21pGkCgYEArMxi6CxUwHhmrLCE82ZrpxhbQ83+xxVK4QZotur8
nvMlfc85WWbbEzHDJbMQACqzYe13zzUnF+CU1EosU+tOt9oHg5jG5jXKMlWDlqyy
IOaCCNRQBwPXNkQl2HrIhJmJrkRAguCilc+1rNpryWpouC+/Iso6rovbnC3GhBHB
2oECgYAgC+PGYtYDHoHPypgfteuxlZU3TLSqh8AvWXUQfJYIuuRnLLfs73g3WQwN
ezLN4NGO7j3AEs7+ZrI2wP/vTktAy0NTnIiPqX6n+17F+ZGYBYurGB53qNM5e29D
Th7LHBMym9yAOtK39+Xe5DZF9Rum0WmQ/+t4X014bIDDoQq57A==
-----END RSA PRIVATE KEY-----"""

LOCAL_PATCH_SERVER_CERT = """-----BEGIN CERTIFICATE-----
MIIC1jCCAb6gAwIBAgIUFESrtRHXxbijQjSIWOFMtc4X2AMwDQYJKoZIhvcNAQEL
BQAwFDESMBAGA1UEAwwJMTI3LjAuMC4xMCAXDTI2MDYyNTE2MDcxN1oYDzIxMjYw
NjAyMTYwNzE3WjAUMRIwEAYDVQQDDAkxMjcuMC4wLjEwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQD8hRBRfy9DcskqjIBLh4nhiV9zL/23VPkguxqD9lPf
fqH+6J02dkMu4ofWOhul9OEnj3I5CIrEi6fF6kVcy1KmFbJ3PxSYd2Ce94Ruqbxm
HriCiYggtkLPZ89fQpvCB3qOiTBAbee4o2QUPQBJM6exyxwrg6/A9VXpUJDs+dVQ
jPPgPO0Pto0HHi4+AQKzbp/FDq+S1R/T+v6gRcfdnx/BQlK6BhiJiINLPOvAnJIA
DBjISCVw0ZK3K6K9PA+2rk5S0nmfU5JHL1kbyqbr63t+QNX7nS31bkcyejGiYc3T
asi3LtTPlWJUOq9Rycm8NdZSJcmGuuuy956La2MoDU2dAgMBAAGjHjAcMBoGA1Ud
EQQTMBGCCWxvY2FsaG9zdIcEfwAAATANBgkqhkiG9w0BAQsFAAOCAQEAymGpI1Ow
rbvEhUJSnuv2kYca0/bHq6njySOZzFwK2CjvJIDV+IorXfDAp3Ghpcq44rqjgzVm
Ig/RwbUSyrssiO9SMDA5gGb/yRpJ6ylmWhcpP0YqJeIFASyfz4Nv6lhigInVo3tx
LKvIVMJGkXFd9/AP793seSeRgBtus5FVh3yj6otQCx40r8PMir69WIfjLjbXAjYd
rZ3IvZGmBHgon7FnQ56Iriy6YpxTqKNpOxmYcc9BC6dHJzscPxxEDg+PswWEmQY5
31YnXgQPoSgUaNGIHNnfLDErFLt7lo2vWQ0SchX/I4ENkK7OCLLuFaYwKgtebaHh
2kQQqEhVMB6fzA==
-----END CERTIFICATE-----"""

ANTIGRAVITY_INJECTION_CODE_TEMPLATE = """
    // Bypass certificate errors for local servers (language server and patch server)
    try {
        electron_1.app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
            if (url.includes('127.0.0.1') || url.includes('localhost')) {
                event.preventDefault();
                callback(true);
            } else {
                callback(false);
            }
        });
    } catch (err) {
        console.error('[Debug] Failed to register certificate-error listener:', err);
    }

    // Redirect renderer console messages to main process logs
    if (process.env.AG_VERBOSE || process.env.AG_DEBUG || process.env.OPEN_ANTIGRAVITY_DEBUG) {
        try {
            electron_1.app.on('web-contents-created', (event, webContents) => {
                webContents.on('console-message', (ev, level, message, line, sourceId) => {
                    console.log(`[Renderer Console] ${message} (${sourceId}:${line})`);
                });
            });
        } catch (err) {
            console.error('[Debug] Failed to redirect renderer console:', err);
        }
    }

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
            
            const oldLs = 'function Ls(a,b){return kka(a,c=>{switch(c.methodKind){case "unary":return tka(b,c);case "server_streaming":return uka(b,c);case "client_streaming":return vka(b,c);case "bidi_streaming":return wka(b,c);default:return null}})}';
            const newLs = 'function Ls(a,b){var client=kka(a,c=>{switch(c.methodKind){case "unary":return tka(b,c);case "server_streaming":return uka(b,c);case "client_streaming":return vka(b,c);case "bidi_streaming":return wka(b,c);default:return null}});try{var wrap=function(name,mockFn){var orig=client[name];if(typeof orig==="function"){client[name]=async function(...args){try{var res=await orig.apply(client,args);return mockFn(res)}catch(e){console.error("[Wrapper Error] "+name+":",e);return mockFn(null)}}}};wrap("hasAuthToken",function(res){if(!res||!res.hasToken){return{hasToken:true,isGcpTos:false}}return res});wrap("getAuthStatus",function(res){if(!res||!res.authResult||!res.authResult.hasValidAuth){return{authResult:{hasValidAuth:true,grantedScopes:["https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/userinfo.profile"],isGcpTos:false,failureDetails:{case:""}}}}return res});wrap("validateProject",function(res){if(!res||!res.authResult||!res.authResult.hasValidAuth){return{authResult:{hasValidAuth:true,grantedScopes:["https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/userinfo.profile"],isGcpTos:false,failureDetails:{case:""}}}}return res});wrap("loginWithBrowser",function(res){if(!res||!res.authResult||!res.authResult.hasValidAuth){return{authResult:{hasValidAuth:true,grantedScopes:["https://www.googleapis.com/auth/userinfo.email","https://www.googleapis.com/auth/userinfo.profile"],isGcpTos:false,failureDetails:{case:""}}}}return res});wrap("getLocalUserInfo",function(res){if(!res||!res.username){return{username:"user",homeDirUri:"file:///home/user",machineType:"desktop"}}return res});wrap("getCascadeNuxes",function(res){if(!res||!res.nuxes){return{nuxes:[]}}return res});wrap("getUserStatus",function(res){if(!res||!res.userStatus||!res.userStatus.cascadeModelConfigData){var fallbackTier=(res&&res.userStatus&&res.userStatus.userTier)?res.userStatus.userTier:{name:"Google Internal",upgradeButtonText:""};var now=(new Date()).toISOString();var planInfo={planName:"Pro",teamsTier:"TEAMS_TIER_PRO",monthlyPromptCredits:1000,monthlyFlowCredits:1000,hasAutocompleteFastMode:true,allowStickyPremiumModels:true,allowPremiumCommandModels:true,hasTabToJump:true,cascadeWebSearchEnabled:true,browserEnabled:true};return{userStatus:{pro:true,disableTelemetry:false,name:"User",ignoreChatTelemetrySetting:false,teamId:"",email:"user@example.com",userFeatures:["USER_FEATURES_CORTEX"],teamsFeatures:[],permissions:[],planInfo:planInfo,planStatus:{planInfo:planInfo,availablePromptCredits:1000,availableFlowCredits:1000},hasUsedAntigravity:true,userUsedPromptCredits:0,userUsedFlowCredits:0,hasFingerprintSet:true,teamConfig:{},cascadeModelConfigData:{clientModelConfigs:[{label:"Gemini 3 Pro (High)",modelOrAlias:{model:"MODEL_PLACEHOLDER_M7"},quotaInfo:{remainingFraction:1,resetTime:now}},{label:"Claude Sonnet 4.5",modelOrAlias:{model:"MODEL_PLACEHOLDER_CLAUDE"},quotaInfo:{remainingFraction:1,resetTime:now}},{label:"Claude Opus 4.5 (Thinking)",modelOrAlias:{model:"MODEL_PLACEHOLDER_OPUS"},quotaInfo:{remainingFraction:1,resetTime:now}},{label:"GPT-OSS 120B (Medium)",modelOrAlias:{model:"MODEL_PLACEHOLDER_GPTOSS"},quotaInfo:{remainingFraction:1,resetTime:now}}],clientModelSorts:[],defaultOverrideModelConfig:{}},acceptedLatestTermsOfService:true,userDataCollectionForceDisabled:false,profilePictureUrl:"",userTier:fallbackTier}}}return res})}catch(err){console.error("[Wrapper Init Error]:",err)}return client}';
            
            nextContent = content.split(oldLs).join(newLs);
            applied = nextContent !== content;
            results.push({
                name: 'Mock auth client wrapper (frontend)',
                applied,
                detail: applied ? 'Injected auth wrapper into Ls factory' : 'Ls factory not found',
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
            const internalPatched = !content.includes('isGoogleInternal:!1')
                && content.includes('isGoogleInternal:!0');
            const clientWrapperPatched = content.includes('wrap("hasAuthToken"');
            return internalPatched && clientWrapperPatched;
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
        const https = require('https');
        const options = {
            key: "{key_pem}",
            cert: "{cert_pem}"
        };
        const localServer = https.createServer(options, (req, res) => {
            const requestUrl = new URL(req.url || '/', `https://127.0.0.1:${localServerPort || 0}`);
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
        if (process.env.AG_VERBOSE || process.env.AG_DEBUG || process.env.OPEN_ANTIGRAVITY_DEBUG) {
            console.log(`[Network Request] ${details.url}`);
        }
        if (details.url.endsWith('/main.js') && (details.url.includes('127.0.0.1') || details.url.includes('localhost'))) {
            if (localServerPort && !details.url.includes(`:${localServerPort}`)) {
                const redirectUrl = `https://127.0.0.1:${localServerPort}/main.js?source=${encodeURIComponent(details.url)}`;
                if (process.env.AG_VERBOSE || process.env.AG_DEBUG || process.env.OPEN_ANTIGRAVITY_DEBUG) {
                    console.log(`[Debug] Redirecting main.js request to local patch server: ${redirectUrl}`);
                }
                callback({ redirectURL: redirectUrl });
                return;
            }
        }
        callback({});
    });
"""
