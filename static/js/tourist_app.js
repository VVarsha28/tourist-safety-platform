// SafeTrail — Tourist Mobile Web App Script

let map = null;
let userMarker = null;
let currentCoords = { lat: 26.9205, lng: 75.8245 };
let sosTimer = null;
let countdownVal = 3;
let sosPollingInterval = null;

// Demo location coordinates presets
const DEMO_PRESETS = {
    palace: { lat: 26.9255, lng: 75.8240, label: "City Palace Heritage Corridor (Safe)" },
    bazaar: { lat: 26.9205, lng: 75.8245, label: "Johari Bazaar (Caution)" },
    mountain: { lat: 26.9405, lng: 75.8510, label: "Nahargarh Mountain Pass (Restricted)" }
};

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    startLocationTracking();
    startSOSPolling();
});

// Initialize Leaflet Map
function initMap() {
    map = L.map('tourist-map', {
        zoomControl: false
    }).setView([currentCoords.lat, currentCoords.lng], 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Custom pulse icon for tourist position
    const userIcon = L.divIcon({
        className: 'user-pin-container',
        html: `<div class="relative flex items-center justify-center">
                 <span class="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-sky-400 opacity-75"></span>
                 <span class="relative inline-flex rounded-full h-5 w-5 bg-sky-600 border-2 border-white shadow-lg"></span>
               </div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });

    userMarker = L.marker([currentCoords.lat, currentCoords.lng], { icon: userIcon }).addTo(map);
    userMarker.bindPopup('<strong class="text-xs">Your Current Location</strong>');

    // Load Zones and POIs
    loadMapLayers();
}

// Fetch and render zone polygons & POIs
function loadMapLayers() {
    fetch('/authority/api/telemetry')
        .then(r => r.json())
        .then(data => {
            // 1. Render Zones
            if (data.zones) {
                data.zones.forEach(zone => {
                    const coords = zone.coordinates;
                    if (!coords || coords.length === 0) return;

                    let color = '#10B981';
                    if (zone.risk_level === 'caution') color = '#F59E0B';
                    if (zone.risk_level === 'restricted') color = '#EF4444';

                    const poly = L.polygon(coords, {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.25,
                        weight: 2
                    }).addTo(map);

                    poly.bindPopup(`
                        <div class="text-xs p-1">
                            <span class="font-bold text-[10px] uppercase px-1.5 py-0.5 rounded text-white" style="background:${color}">${zone.risk_level}</span>
                            <div class="font-bold text-slate-900 mt-1">${zone.name}</div>
                            <div class="text-slate-600 text-[11px] mt-0.5">${zone.description}</div>
                        </div>
                    `);
                });
            }

            // 2. Render POIs
            if (data.pois) {
                data.pois.forEach(poi => {
                    let iconEmoji = '🏥';
                    if (poi.type === 'police') iconEmoji = '👮';
                    if (poi.type === 'embassy') iconEmoji = '🏛️';

                    const poiIcon = L.divIcon({
                        className: 'poi-pin',
                        html: `<div style="background:#fff; border:1px solid #cbd5e1; border-radius:10px; width:28px; height:28px; display:flex; align-items:center; justify-content:center; box-shadow:0 2px 4px rgba(0,0,0,0.15); font-size:14px;">${iconEmoji}</div>`,
                        iconSize: [28, 28],
                        iconAnchor: [14, 14]
                    });

                    const marker = L.marker([poi.lat, poi.lng], { icon: poiIcon }).addTo(map);
                    marker.bindPopup(`
                        <div class="text-xs p-1">
                            <span class="font-bold uppercase text-[10px] text-sky-700">${poi.type}</span>
                            <div class="font-bold text-slate-900">${poi.name}</div>
                            <div class="text-slate-500 text-[11px]">${poi.address}</div>
                            ${poi.phone ? `<a href="tel:${poi.phone}" class="inline-block mt-1 font-bold text-sky-600">📞 ${poi.phone}</a>` : ''}
                        </div>
                    `);
                });
            }
        })
        .catch(err => console.log("Map layer load error:", err));
}

// Start location tracking or sync
function startLocationTracking() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            // If user hasn't selected a simulated location, use browser GPS
            const simVal = document.getElementById('location-simulator').value;
            if (simVal === 'gps') {
                updateLocation(pos.coords.latitude, pos.coords.longitude);
            }
        }, () => {
            // Default to preset if denied
            console.log("Using default demo coordinates");
        });
    }

    // Ping location to server every 25 seconds
    setInterval(() => {
        sendLocationPing(currentCoords.lat, currentCoords.lng);
    }, 25000);
}

// Update coordinates and notify backend
function updateLocation(lat, lng) {
    currentCoords = { lat, lng };
    if (userMarker) {
        userMarker.setLatLng([lat, lng]);
    }
    if (map) {
        map.panTo([lat, lng]);
    }
    sendLocationPing(lat, lng);
}

function recenterMap() {
    if (map) {
        map.setView([currentCoords.lat, currentCoords.lng], 15);
    }
}

// Location Simulator dropdown handler
function simulateLocationChange(val) {
    if (val === 'gps') {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(pos => {
                updateLocation(pos.coords.latitude, pos.coords.longitude);
            });
        }
    } else if (DEMO_PRESETS[val]) {
        const p = DEMO_PRESETS[val];
        updateLocation(p.lat, p.lng);
    }
}

// Send location ping & parse returned risk + alerts
function sendLocationPing(lat, lng) {
    fetch('/tourist/api/location/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lng, accuracy: 10.0 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateSafetyScoreUI(data.risk);

            // If entering caution/restricted zone, display in-app banner
            if (data.new_alert) {
                showZoneAlert(data.new_alert);
            }
        }
    })
    .catch(err => console.error(err));
}

// Update the Safety Score widget in the top header
function updateSafetyScoreUI(risk) {
    if (!risk) return;
    const numElem = document.getElementById('score-number');
    const labelElem = document.getElementById('score-label');
    const dotElem = document.getElementById('score-dot');

    if (numElem) numElem.textContent = risk.score;
    if (dotElem) dotElem.style.backgroundColor = risk.color;
    if (labelElem) {
        labelElem.textContent = risk.level;
        labelElem.className = `text-[10px] font-bold px-2 py-0.5 rounded-full ${risk.badge_class} border mt-0.5`;
    }
}

function showZoneAlert(alertObj) {
    const banner = document.getElementById('zone-alert-banner');
    const title = document.getElementById('zone-alert-title');
    const msg = document.getElementById('zone-alert-msg');
    const action = document.getElementById('zone-alert-action');

    if (banner && title && msg) {
        title.textContent = alertObj.title;
        msg.textContent = alertObj.message;
        if (action && alertObj.suggested_action) {
            action.textContent = "Advice: " + alertObj.suggested_action;
        }
        banner.classList.remove('hidden');
    }
}

// ==================== EMERGENCY SOS SYSTEM ====================

function openSOSModal() {
    countdownVal = 3;
    document.getElementById('sos-countdown').textContent = countdownVal;
    document.getElementById('sos-modal').classList.remove('hidden');

    clearInterval(sosTimer);
    sosTimer = setInterval(() => {
        countdownVal -= 1;
        document.getElementById('sos-countdown').textContent = countdownVal;
        if (countdownVal <= 0) {
            clearInterval(sosTimer);
            executeSOSImmediate();
        }
    }, 1000);
}

function cancelSOSCountdown() {
    clearInterval(sosTimer);
    document.getElementById('sos-modal').classList.add('hidden');
}

function executeSOSImmediate() {
    clearInterval(sosTimer);
    document.getElementById('sos-modal').classList.add('hidden');

    fetch('/tourist/api/sos/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            lat: currentCoords.lat,
            lng: currentCoords.lng,
            voice_note_text: "Emergency SOS triggered by user via SafeTrail app."
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // Activate SOS UI banner
            const banner = document.getElementById('sos-active-banner');
            if (banner) banner.classList.remove('hidden');
            updateSOSProgress(data.status || 'active');

            if (data.simulated_sms) {
                alert(`📱 Simulated SMS dispatched to ${data.simulated_sms.contact_name} (${data.simulated_sms.recipient}):\n"${data.simulated_sms.message}"`);
            }
        }
    })
    .catch(err => console.error(err));
}

function updateSOSNote() {
    const text = document.getElementById('sos-note-input').value.trim();
    if (!text) return;

    fetch('/tourist/api/sos/update-note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_note_text: text })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert("Note transmitted to emergency response dispatch team.");
        }
    });
}

function startSOSPolling() {
    sosPollingInterval = setInterval(() => {
        fetch('/tourist/api/sos/status')
            .then(r => r.json())
            .then(data => {
                const banner = document.getElementById('sos-active-banner');
                if (!banner) return;

                if (data.active && data.sos) {
                    banner.classList.remove('hidden');
                    updateSOSProgress(data.sos.status);
                } else if (!data.active && data.sos && data.sos.status === 'resolved') {
                    updateSOSProgress('resolved');
                    setTimeout(() => {
                        banner.classList.add('hidden');
                    }, 5000);
                }
            })
            .catch(err => console.error(err));
    }, 4000);
}

function updateSOSProgress(status) {
    const badge = document.getElementById('sos-status-badge');
    if (badge) badge.textContent = status;

    const steps = ['active', 'acknowledged', 'dispatched', 'resolved'];
    const currIdx = steps.indexOf(status);

    steps.forEach((st, idx) => {
        const el = document.getElementById(`step-${st}`);
        if (el) {
            if (idx <= currIdx) {
                el.className = 'py-1 px-1 rounded bg-rose-700 text-white font-bold';
                if (st === 'resolved') el.className = 'py-1 px-1 rounded bg-emerald-600 text-white font-bold';
            } else {
                el.className = 'py-1 px-1 rounded bg-rose-950/60 text-rose-400';
            }
        }
    });
}

// ==================== AI SAFETY ASSISTANT ====================

function handleChatSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    appendChatMessage('user', msg);

    // Call API
    fetch('/tourist/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            appendChatMessage('ai', data.reply);
        }
    })
    .catch(err => {
        appendChatMessage('ai', "I apologize, could not retrieve safety details at this moment. For immediate danger, please dial 112 or hit SOS.");
    });
}

function sendQuickPrompt(promptText) {
    document.getElementById('chat-input').value = promptText;
    document.getElementById('ai-chat-form').dispatchEvent(new Event('submit'));
}

function appendChatMessage(sender, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'flex gap-2 items-start animate-fade-in';

    // Simple markdown bold formatting
    const formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');

    if (sender === 'user') {
        div.className += ' justify-end';
        div.innerHTML = `
            <div class="bg-sky-600 text-white p-2.5 rounded-2xl rounded-tr-none text-xs max-w-[85%] shadow-xs">
                ${formatted}
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="w-6 h-6 rounded-full bg-sky-600 text-white flex-shrink-0 flex items-center justify-center text-[10px]">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="bg-white p-2.5 rounded-2xl rounded-tl-none border border-slate-200 text-xs text-slate-700 max-w-[85%] shadow-xs">
                ${formatted}
            </div>
        `;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
